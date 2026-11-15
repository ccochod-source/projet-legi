"""Vérifie les transports MCP et l'historique sans service distant."""

import json
import os
import subprocess
import sys

import anyio
import httpx
import pytest
from fastapi.testclient import TestClient

import config
import app.main as application
import app.historique as historique


@pytest.mark.parametrize("transport", ["stdio", "memoire"])
def test_session_mcp_protocole_reel(monkeypatch, transport):
    monkeypatch.setattr(config, "MCP_TRANSPORT", transport)

    async def verifier():
        async with application.ouvrir_mcp() as session:
            outils = await session.list_tools()
            assert {o.name for o in outils.tools} == application.OUTILS_AUTORISES
            resultat = await session.call_tool("consulter_article", {"article_id": "INVALIDE"})
            donnees = application.lire_resultat(resultat)
            assert donnees["statut"] == "erreur"

    anyio.run(verifier)


@pytest.mark.parametrize("code", [None, "incorrect", "autre"])
def test_code_acces_refuse(monkeypatch, code):
    monkeypatch.setattr(config, "APP_CODE_ACCES", "secret-simule")
    with TestClient(application.app, base_url="http://localhost") as client:
        entetes = {"X-Code-Acces": code} if code else {}
        for methode, chemin in [("GET", "/api/etat"), ("POST", "/api/chat")]:
            reponse = client.request(methode, chemin, headers=entetes)
            assert reponse.status_code == 401
            assert "Code d'accès" in reponse.json()["erreur"]
            assert reponse.headers["cache-control"] == "no-store"
        assert client.get("/").status_code == 200


@pytest.mark.parametrize("code", ["", "secret-simule"])
def test_acces_local_et_code_valide(monkeypatch, code):
    monkeypatch.setattr(config, "APP_CODE_ACCES", code)
    monkeypatch.setattr(config, "SUPABASE_URL", "")

    async def analyser(message):
        return {"statut": "ok", "reponse": "Rapport simulé"}

    monkeypatch.setattr(application, "analyser", analyser)
    monkeypatch.setattr(config, "GROQ_API_KEY", "simulee")
    with TestClient(application.app, base_url="http://localhost") as client:
        entetes = {"X-Code-Acces": code}
        assert client.get("/api/etat", headers=entetes).status_code == 200
        resultat = client.post("/api/chat", headers=entetes, json={"message": "Entreprise"})
        assert resultat.json()["reponse"] == "Rapport simulé"
        assert "historique" not in resultat.json()


@pytest.mark.parametrize("issue", [201, 503, "reseau"])
def test_insertion_supabase(monkeypatch, caplog, issue):
    monkeypatch.setattr(config, "SUPABASE_URL", "https://supabase.exemple")
    monkeypatch.setattr(config, "SUPABASE_SERVICE_ROLE_KEY", "cle-privee-simulee")
    appels = []

    def repondre(requete):
        appels.append(requete)
        if issue == "reseau":
            raise httpx.ConnectError("détail sensible simulé", request=requete)
        return httpx.Response(issue, text="détail sensible simulé")

    vrai_client = httpx.AsyncClient
    monkeypatch.setattr(historique.httpx, "AsyncClient", lambda **options: vrai_client(
        **options, transport=httpx.MockTransport(repondre)))

    async def verifier():
        return await historique.enregistrer_analyse("a" * 3000, {
            "statut": "ok", "reponse": "Rapport", "outils_appeles": [{"nom": "outil"}],
            "modeles_utilises": ["principal", "secours"],
        })

    assert anyio.run(verifier) == ("enregistre" if issue == 201 else "non_enregistre")
    assert len(appels) == 1
    assert str(appels[0].url) == "https://supabase.exemple/rest/v1/analyses"
    assert appels[0].headers["authorization"] == "Bearer cle-privee-simulee"
    ligne = json.loads(appels[0].content)
    assert len(ligne["question"]) == 2000
    assert ligne["rapport"] == "Rapport"
    assert ligne["modele"] == "principal, secours"
    assert "cle-privee" not in json.dumps(ligne)
    assert "détail sensible" not in caplog.text


def test_historique_absent_ou_partiel(monkeypatch):
    monkeypatch.setattr(config, "SUPABASE_URL", "https://supabase.exemple")
    monkeypatch.setattr(config, "SUPABASE_SERVICE_ROLE_KEY", "")
    assert anyio.run(historique.enregistrer_analyse, "Question", {}) is None


def test_reponse_preservee_si_historique_echoue(monkeypatch):
    monkeypatch.setattr(config, "APP_CODE_ACCES", "")
    monkeypatch.setattr(config, "GROQ_API_KEY", "")

    async def enregistrer(question, resultat):
        assert resultat["statut"] == "erreur"
        return "non_enregistre"

    monkeypatch.setattr(application, "enregistrer_analyse", enregistrer)
    with TestClient(application.app, base_url="http://localhost") as client:
        resultat = client.post("/api/chat", json={"message": "Entreprise"}).json()
        assert resultat["historique"] == "non_enregistre"
        assert "Clé Groq absente" in resultat["erreur"]


def test_configuration_vercel_automatique():
    environnement = {**os.environ, "VERCEL": "1"}
    environnement.pop("MCP_TRANSPORT", None)
    resultat = subprocess.run([sys.executable, "-c", "import config; import index; "
        "assert config.MCP_TRANSPORT == 'memoire'; "
        "assert index.app is not None"], env=environnement, capture_output=True)
    assert resultat.returncode == 0
