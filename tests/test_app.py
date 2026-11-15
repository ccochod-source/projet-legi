"""Vérifie l'application avec Groq et MCP simulés, sans accès réseau."""

import copy
import json
import os
import subprocess
import sys
from contextlib import asynccontextmanager
from types import SimpleNamespace
from zipfile import ZipFile

import anyio
import groq
import httpx
import pytest
from fastapi.testclient import TestClient
from groq.types.chat import ChatCompletion
from mcp.types import CallToolResult, TextContent

import app.main as application
from app.rapport import construire_rapport

SOURCE = {"titre": "Texte officiel simulé", "reference": "Article de test",
          "url": "https://www.legifrance.gouv.fr/loda/article_lc/ARTICLE_TEST",
          "date_recuperation": "2026-11-15T12:00:00Z"}
PREUVE = "Les mentions légales sont absentes de la page consultée."
RESULTAT = {"statut": "ok", "analyse": {"constat": PREUVE}, "sources": [SOURCE]}


def rapport_json(**changements):
    """Fabrique un constat de test, pas un avis juridique."""
    point = {"point": "Mentions sur la page", "statut": "manquant", "preuve": PREUVE,
             "reference": SOURCE["reference"], "url": SOURCE["url"]}
    point.update(changements)
    return json.dumps({"points": [point], "informations_manquantes": ["Pages non consultées"]})


def completion(contenu=None, nom=None, arguments=None, nombre=1):
    """Construit les objets du client officiel Groq sans envoyer de requête."""
    message = {"role": "assistant", "content": contenu}
    if nom:
        message["tool_calls"] = [
            {"id": f"appel_{numero}", "type": "function", "function": {
                "name": nom, "arguments": arguments if arguments is not None else '{"url":"https://exemple.fr"}',
            }} for numero in range(nombre)
        ]
    return ChatCompletion.model_validate({
        "id": "discussion-test", "created": 0, "model": "modele-simule", "object": "chat.completion",
        "choices": [{"index": 0, "finish_reason": "tool_calls" if nom else "stop", "message": message}],
    })


@pytest.fixture
def simulation(monkeypatch):
    """Installe deux doubles asynchrones et conserve les appels pour assertion."""
    etat = SimpleNamespace(
        reponses=[completion(nom="analyser_site"), completion(rapport_json())],
        resultat=RESULTAT, appels=[], demandes=[], ferme=False,
        outils=[SimpleNamespace(name="analyser_site", description="Analyse simulée",
                               inputSchema={"type": "object", "properties": {"url": {"type": "string"}}})],
    )

    class SessionSimulee:
        async def list_tools(self):
            return SimpleNamespace(tools=etat.outils)

        async def call_tool(self, nom, arguments):
            etat.appels.append((nom, arguments))
            if isinstance(etat.resultat, Exception):
                raise etat.resultat
            return CallToolResult(content=[], structuredContent=etat.resultat)

    @asynccontextmanager
    async def mcp_simule():
        try:
            yield SessionSimulee()
        finally:
            etat.ferme = True

    class GroqSimule:
        def __init__(self, **options):
            etat.options = options
            self.chat = SimpleNamespace(completions=self)

        async def __aenter__(self):
            return self

        async def __aexit__(self, *arguments):
            return False

        async def create(self, **demande):
            await anyio.lowlevel.checkpoint()
            etat.demandes.append(copy.deepcopy(demande))
            reponse = etat.reponses.pop(0)
            if isinstance(reponse, Exception):
                raise reponse
            return reponse

    monkeypatch.setattr(application.config, "GROQ_API_KEY", "valeur-simulee")
    monkeypatch.setattr(application, "ouvrir_mcp", mcp_simule)
    monkeypatch.setattr(application, "AsyncGroq", GroqSimule)
    return etat


@pytest.fixture
def client():
    """Le navigateur et le serveur ASGI restent dans le processus de test."""
    with TestClient(application.app, base_url="http://127.0.0.1:8001") as navigateur:
        yield navigateur


def test_page_et_configuration_sans_cle(client, monkeypatch):
    monkeypatch.setattr(application.config, "GROQ_API_KEY", "")
    assert "Votre rapport" in client.get("/").text
    assert client.get("/static/app.js").status_code == 200
    assert client.get("/static/style.css").status_code == 200
    assert client.get("/api/etat").json()["groq_configure"] is False
    resultat = client.post("/api/chat", json={"message": "Mon projet"}).json()
    assert resultat["statut"] == "erreur"
    assert "Clé Groq absente" in resultat["erreur"]


@pytest.mark.parametrize("message", ["", "  ", "ab", "a" * 6001])
def test_demande_invalide(client, message):
    assert client.post("/api/chat", json={"message": message}).status_code == 422


def test_site_externe_refuse(client):
    resultat = client.post("/api/chat", json={"message": "Analyse"}, headers={"Origin": "https://autre-site.fr"})
    assert resultat.status_code == 403
    assert client.get("/", headers={"Host": "autre-site.fr"}).status_code == 400


def test_cycle_complet(client, simulation):
    resultat = client.post("/api/chat", json={"message": "https://exemple.fr"}).json()
    assert resultat["statut"] == "ok"
    assert resultat["points"][0]["statut"] == "manquant"
    assert "| Point | Statut | Preuve | Référence légale |" in resultat["reponse"]
    assert resultat["sources"] == [SOURCE]
    assert resultat["outils_appeles"] == [{"nom": "analyser_site", "statut": "ok"}]
    assert simulation.appels == [("analyser_site", {"url": "https://exemple.fr"})]
    assert simulation.demandes[0]["tools"][0]["function"]["name"] == "analyser_site"
    retour = simulation.demandes[1]["messages"][-1]
    assert retour["role"] == "tool" and retour["tool_call_id"] == "appel_0"
    assert json.loads(retour["content"]) == RESULTAT
    assert simulation.ferme


def test_description_projet_et_plusieurs_tours(client, simulation):
    simulation.outils[0].name = "rechercher_textes_loi"
    simulation.reponses = [completion(nom="rechercher_textes_loi", arguments='{"question":"Boutique en France"}'),
                          completion(nom="rechercher_textes_loi", arguments='{"question":"Information des clients"}'),
                          completion(rapport_json())]
    resultat = client.post("/api/chat", json={"message": "Je prépare une boutique en France"}).json()
    assert resultat["statut"] == "ok"
    assert len(resultat["outils_appeles"]) == 2
    assert len(simulation.demandes) == 3


@pytest.mark.parametrize("changements", [
    {"reference": "Article inventé"}, {"url": "https://invente.fr/loi"},
    {"preuve": "Une preuve jamais renvoyée par les outils"},
])
def test_refus_des_inventions(client, simulation, changements):
    simulation.reponses[-1] = completion(rapport_json(statut="conforme", **changements))
    resultat = client.post("/api/chat", json={"message": "https://exemple.fr"}).json()
    assert resultat["points"][0]["statut"] == "a_verifier"
    assert "https://invente.fr" not in resultat["reponse"]
    assert "Article inventé" not in resultat["reponse"]


def test_erreur_outil_ne_devient_pas_une_conformite(client, simulation):
    simulation.resultat = {"statut": "erreur", "erreur": "Clé Légifrance expirée."}
    simulation.reponses[-1] = completion(rapport_json(statut="conforme"))
    resultat = client.post("/api/chat", json={"message": "Mon site"}).json()
    assert resultat["points"][0]["statut"] == "a_verifier"
    assert resultat["outils_appeles"][0]["erreur"] == "Clé Légifrance expirée."
    assert "Clé Légifrance expirée" in resultat["reponse"]
    assert resultat["sources"] == []


@pytest.mark.parametrize("nom, arguments", [("outil_inconnu", "{}"), ("analyser_site", "pas du json"), ("analyser_site", "[]")])
def test_appel_non_valide_sans_execution(client, simulation, nom, arguments):
    simulation.reponses[0] = completion(nom=nom, arguments=arguments)
    resultat = client.post("/api/chat", json={"message": "Mon site"}).json()
    assert simulation.appels == []
    assert resultat["outils_appeles"][0]["statut"] == "erreur"
    assert resultat["points"][0]["statut"] == "a_verifier"


def test_exception_outil_est_presentee_sans_detail(client, simulation):
    simulation.resultat = RuntimeError("Détail interne à masquer")
    resultat = client.post("/api/chat", json={"message": "Mon site"}).json()
    assert resultat["outils_appeles"][0]["statut"] == "erreur"
    assert "Détail interne" not in json.dumps(resultat)


@pytest.mark.parametrize("code, classe, attendu", [
    (401, groq.AuthenticationError, "Clé Groq invalide"),
    (429, groq.RateLimitError, "Quota Groq atteint"),
    (400, groq.BadRequestError, "Groq a refusé"),
])
def test_erreurs_groq(client, simulation, code, classe, attendu):
    reponse = httpx.Response(code, request=httpx.Request("POST", "https://api.groq.com"))
    simulation.reponses = [classe("Détail interne du fournisseur", response=reponse, body={})]
    resultat = client.post("/api/chat", json={"message": "Mon site"}).json()
    assert resultat["statut"] == "erreur"
    assert attendu in resultat["erreur"]
    assert "Détail interne" not in resultat["erreur"]
    assert simulation.ferme


@pytest.mark.parametrize("erreur, attendu", [
    (groq.APIConnectionError(request=httpx.Request("POST", "https://api.groq.com")), "Connexion à Groq impossible"),
    (groq.APITimeoutError(request=httpx.Request("POST", "https://api.groq.com")), "Délai d'analyse dépassé"),
])
def test_reseau_et_delai_groq(client, simulation, erreur, attendu):
    simulation.reponses = [erreur]
    assert attendu in client.post("/api/chat", json={"message": "Mon projet"}).json()["erreur"]


def test_mcp_ne_demarre_pas(client, simulation, monkeypatch):
    @asynccontextmanager
    async def echec_mcp():
        raise OSError("Détail système à masquer")
        yield

    monkeypatch.setattr(application, "ouvrir_mcp", echec_mcp)
    resultat = client.post("/api/chat", json={"message": "Mon site"}).json()
    assert "MCP ne démarre pas" in resultat["erreur"]
    assert simulation.demandes == []


@pytest.mark.parametrize("limite, valeur, attendu", [("MAX_TOURS", 1, "Limite de tours"), ("MAX_APPELS", 0, "Limite d'appels")])
def test_boucle_bornee(client, simulation, monkeypatch, limite, valeur, attendu):
    monkeypatch.setattr(application, limite, valeur)
    resultat = client.post("/api/chat", json={"message": "Mon site"}).json()
    assert attendu in resultat["erreur"]
    assert simulation.ferme


def test_aucun_outil_appele(client, simulation):
    simulation.reponses = [completion(rapport_json(statut="conforme"))]
    assert "Aucun outil" in client.post("/api/chat", json={"message": "Mon site"}).json()["erreur"]


def test_aucun_outil_disponible(client, simulation):
    simulation.outils = []
    assert "aucun des outils" in client.post("/api/chat", json={"message": "Mon site"}).json()["erreur"]
    assert simulation.demandes == []


def test_rapport_inexploitable(client, simulation):
    simulation.reponses[-1] = completion("Votre site est légal !")
    assert "Format du rapport" in client.post("/api/chat", json={"message": "Mon site"}).json()["erreur"]


def test_resultat_mcp_texte_et_format_inattendu():
    resultat = CallToolResult(content=[TextContent(type="text", text=json.dumps(RESULTAT))])
    assert application.lire_resultat(resultat) == RESULTAT
    resultat.content[0].text = "Réponse pas en JSON"
    assert application.lire_resultat(resultat)["statut"] == "erreur"
    resultat.isError = True
    assert application.lire_resultat(resultat)["statut"] == "erreur"


def test_resultat_vide_ne_prouve_rien():
    resultat = construire_rapport(rapport_json(statut="conforme"), [{"statut": "ok", "textes": [], "sources": []}])
    assert resultat["points"][0]["statut"] == "a_verifier"


def test_markdown_echappe_et_conclusion_libre_ignoree():
    objet = json.loads(rapport_json(point="<script>test</script> | [lien](javascript:alerte)"))
    objet["conclusion"] = "Tout est conforme"
    resultat = construire_rapport(json.dumps(objet), [RESULTAT])
    assert "<script>" not in resultat["reponse"]
    assert "Tout est conforme" not in resultat["reponse"]
    assert "\\|" in resultat["reponse"]


@pytest.mark.parametrize("texte", ["Conformité globale", "Légalité du projet", "Votre site est conforme", "Tout est légal"])
def test_constat_global_ecarte(texte):
    resultat = construire_rapport(rapport_json(point=texte, statut="conforme"), [RESULTAT])
    assert resultat["points"][0]["statut"] == "a_verifier"
    assert texte not in resultat["reponse"]


@pytest.mark.parametrize("donnees", [
    {"statut": "ok", "sources": None}, {"statut": "ok", "sources": ["source incorrecte"]},
    {"statut": "ok", "sources": [{}]}, {"statut": "erreur", "erreur": {}},
])
def test_contrat_mcp_inattendu(donnees):
    assert application.lire_resultat(CallToolResult(content=[], structuredContent=donnees))["statut"] == "erreur"


def test_delai_total_borne(client, simulation, monkeypatch):
    monkeypatch.setattr(application, "DELAI_ANALYSE_S", 0)
    assert "Délai d'analyse dépassé" in client.post("/api/chat", json={"message": "Mon projet"}).json()["erreur"]


def test_plusieurs_appels_dans_un_tour(client, simulation):
    simulation.reponses[0] = completion(nom="analyser_site", nombre=2)
    resultat = client.post("/api/chat", json={"message": "Mon site"}).json()
    assert len(resultat["outils_appeles"]) == 2
    assert len(simulation.appels) == 2


def test_zip_exclut_les_fichiers_prives_et_caches(tmp_path):
    dossier = tmp_path / "projet"
    (dossier / "scripts").mkdir(parents=True)
    script = dossier / "scripts/faire_zip.sh"
    script.write_text((application.RACINE / "scripts/faire_zip.sh").read_text())
    for nom in ["README.md", ".env.example", ".env", ".env.sauvegarde", "ancien.zip", "cle.pem",
                ".git/config", ".venv/config", "__pycache__/module.pyc", ".pytest_cache/cache"]:
        chemin = dossier / nom
        chemin.parent.mkdir(parents=True, exist_ok=True)
        chemin.write_text("contenu fictif")
    (dossier / "lien").symlink_to(dossier / ".env")
    subprocess.run(["bash", str(script)], check=True, capture_output=True, text=True)
    with ZipFile(next(dossier.glob("projet-legi-rendu-*.zip"))) as archive:
        assert set(archive.namelist()) == {
            "projet-legi/README.md", "projet-legi/.env.example", "projet-legi/scripts/faire_zip.sh",
        }


@pytest.mark.parametrize("url", [
    "javascript:alerte", "http://www.legifrance.gouv.fr/article",
    "https://www.legifrance.gouv.fr.autre-site.fr/article",
    "https://identifiant@www.legifrance.gouv.fr/article", "https://exemple.fr/mentions",
])
def test_lien_non_juridique_ecarte_meme_si_renvoye_par_outil(url):
    resultat = {**RESULTAT, "sources": [{**SOURCE, "url": url}]}
    rapport = construire_rapport(rapport_json(url=url, statut="conforme"), [resultat])
    assert rapport["points"][0]["statut"] == "a_verifier"
    assert rapport["points"][0]["url"] == ""
    assert rapport["sources"] == []


@pytest.mark.parametrize("valeur_exportee", ["", "  ", "votre_cle", " votre_cle ", "valeur-environnement-simulee"])
def test_lanceur_ignore_environnement_vide_ou_exemple(tmp_path, valeur_exportee):
    dossier = tmp_path / "projet avec espaces"
    (dossier / ".venv/bin").mkdir(parents=True)
    (dossier / "lancer.sh").write_text((application.RACINE / "lancer.sh").read_text())
    (dossier / ".env").write_text(
        "GROQ_API_KEY=valeur-fichier-simulee\n"
        "LEGIFRANCE_CLIENT_ID=valeur-fichier-simulee\n"
        "LEGIFRANCE_CLIENT_SECRET=valeur-fichier-simulee\n"
    )
    # Intercepte uniquement pip et le lancement final ; les étapes Python
    # de lecture/écriture des clés restent celles du vrai script.
    python_simule = dossier / ".venv/bin/python"
    python_simule.write_text(f"#!{sys.executable}\n" + '''
import os
import sys
from dotenv import load_dotenv
if sys.argv[1:3] == ['-m', 'pip']:
    sys.exit(0)
if sys.argv[1:] == ['-m', 'app.main']:
    load_dotenv('.env')
    assert os.getenv('GROQ_API_KEY') == os.environ['ATTENDU_GROQ_TEST']
    assert os.getenv('LEGIFRANCE_CLIENT_ID') == 'valeur-fichier-simulee'
    assert os.getenv('LEGIFRANCE_CLIENT_SECRET') == 'valeur-fichier-simulee'
    print('Configuration effective validée')
else:
    os.execv(sys.executable, [sys.executable, *sys.argv[1:]])
''')
    python_simule.chmod(0o755)
    outils = dossier / "outils-simules"
    outils.mkdir()
    uname = outils / "uname"
    uname.write_text("#!/bin/sh\nprintf 'Linux\\n'\n")
    uname.chmod(0o755)
    attendu = valeur_exportee if valeur_exportee == "valeur-environnement-simulee" else "valeur-fichier-simulee"
    environnement = {**os.environ, "GROQ_API_KEY": valeur_exportee,
                     "LEGIFRANCE_CLIENT_ID": "", "LEGIFRANCE_CLIENT_SECRET": "votre_secret",
                     "ATTENDU_GROQ_TEST": attendu, "PATH": str(outils) + os.pathsep + os.environ["PATH"]}
    resultat = subprocess.run(["bash", str(dossier / "lancer.sh")], env=environnement,
                              capture_output=True, text=True, timeout=20)
    assert resultat.returncode == 0, resultat.stderr
    assert "Configuration effective validée" in resultat.stdout
    assert "valeur-fichier-simulee" not in resultat.stdout + resultat.stderr
