"""Tests sans réseau de verifier_entreprise et du client API entreprises."""

import asyncio
import json

import httpx
import pytest

import clients.entreprises_api as api
import outils.entreprises as entreprises
from erreurs import ErreurOutil
from outils.entreprises import (
    chercher_entreprises,
    filtrer_entreprise,
    normaliser_requete,
    siren_valide,
    verifier_entreprise,
)

CHAMPS_AUTORISES = {
    "siren", "nom", "etat", "date_creation", "activite_principale",
    "commune_siege", "code_postal_siege",
}
CLES_SOURCE = {"titre", "reference", "url", "date_recuperation"}


def resultat_brut(siren="433891850", etat="A", nature="5599"):
    """Résultat tel que renvoyé par l'API, avec des données à ne pas transmettre."""
    return {
        "siren": siren,
        "nom_complet": "SOCIETE EXEMPLE",
        "etat_administratif": etat,
        "nature_juridique": nature,
        "date_creation": "2000-12-04",
        "activite_principale": "58.13Z",
        "siege": {
            "adresse": "12 RUE SECRETE 75013 PARIS",
            "numero_voie": "12",
            "libelle_commune": "PARIS 13",
            "code_postal": "75013",
        },
        "dirigeants": [{"nom": "DUPONT", "prenoms": "Jean"}],
    }


def client_simule(gestionnaire):
    return httpx.AsyncClient(transport=httpx.MockTransport(gestionnaire))


def reponse_json(donnees, code=200, en_tetes=None):
    return httpx.Response(code, content=json.dumps(donnees), headers={"Content-Type": "application/json", **(en_tetes or {})})


def chercher(requete, gestionnaire):
    async def lancer():
        async with client_simule(gestionnaire) as client:
            return await chercher_entreprises(requete, client=client)
    return asyncio.run(lancer())


# --- Validation de l'entrée -------------------------------------------------

@pytest.mark.parametrize("siren", ["433891850", "403554181", "356000000"])
def test_siren_valides(siren):
    assert siren_valide(siren)


@pytest.mark.parametrize("siren", ["433891851", "12345678", "abcdefghi", ""])
def test_siren_invalides(siren):
    assert not siren_valide(siren)


def test_siret_ramene_au_siren():
    assert normaliser_requete("433 891 850 00011") == ("433891850", "433891850")


def test_nom_conserve():
    assert normaliser_requete("  Le Monde ") == ("Le Monde", None)


@pytest.mark.parametrize("entree", ["", "   ", "433891851", "1234"])
def test_entrees_refusees(entree):
    resultat = asyncio.run(verifier_entreprise(entree))
    assert resultat["statut"] == "erreur"
    assert set(resultat) == {"statut", "erreur"}


def test_requete_trop_courte_refusee_sans_appel():
    def gestionnaire(requete):
        raise AssertionError("aucun appel réseau attendu")
    with pytest.raises(ErreurOutil, match="3 caractères"):
        chercher("ab", gestionnaire)


# --- Filtrage des champs (liste blanche) ------------------------------------

def test_liste_blanche_sans_dirigeants_ni_adresse():
    filtre = filtrer_entreprise(resultat_brut())
    assert set(filtre) == CHAMPS_AUTORISES
    texte = json.dumps(filtre)
    assert "DUPONT" not in texte and "RUE SECRETE" not in texte
    assert filtre["commune_siege"] == "PARIS 13"
    assert filtre["etat"] == "active"


def test_etat_cesse():
    assert filtrer_entreprise(resultat_brut(etat="C"))["etat"] == "cessée"


def test_nom_entrepreneur_individuel_masque():
    filtre = filtrer_entreprise({**resultat_brut(nature="1000"), "nom_complet": "JEAN DUPONT"})
    assert "DUPONT" not in filtre["nom"]


# --- Appels à l'API simulée -------------------------------------------------

def test_recherche_par_nom_limitee_a_5_resultats():
    appels = []

    def gestionnaire(requete):
        appels.append(requete)
        resultats = [resultat_brut(siren=f"{i:09d}") for i in range(8)]
        return reponse_json({"results": resultats, "total_results": 42})

    resultat = chercher("Société exemple", gestionnaire)
    assert resultat["statut"] == "ok"
    assert len(resultat["entreprises"]) == 5
    assert all(set(e) == CHAMPS_AUTORISES for e in resultat["entreprises"])
    assert "homonymies" in resultat["message"]
    assert appels[0].url.params["q"] == "Société exemple"
    assert int(appels[0].url.params["per_page"]) <= 5
    assert "dirigeants" not in json.dumps(resultat)
    assert all(set(s) == CLES_SOURCE for s in resultat["sources"])


def test_recherche_par_siren_garde_la_correspondance_exacte():
    def gestionnaire(requete):
        return reponse_json({"results": [resultat_brut(siren="111111118"), resultat_brut()]})

    resultat = chercher("433891850", gestionnaire)
    assert [e["siren"] for e in resultat["entreprises"]] == ["433891850"]
    assert resultat["recherche_par_siren"] is True


def test_aucun_resultat_sans_invention():
    resultat = chercher("zzzz introuvable", lambda r: reponse_json({"results": [], "total_results": 0}))
    assert resultat["statut"] == "ok"
    assert resultat["entreprises"] == []
    assert "Aucune entreprise" in resultat["message"]
    assert resultat["sources"]


def test_quota_429_avec_retry_after_long():
    def gestionnaire(requete):
        return reponse_json({}, code=429, en_tetes={"Retry-After": "60"})

    with pytest.raises(ErreurOutil, match="Quota.*60 s"):
        chercher("exemple", gestionnaire)


def test_quota_429_retry_after_court_puis_succes(monkeypatch):
    attentes = []

    async def faux_sleep(secondes):
        attentes.append(secondes)

    monkeypatch.setattr(api.asyncio, "sleep", faux_sleep)
    reponses = iter([
        reponse_json({}, code=429, en_tetes={"Retry-After": "1"}),
        reponse_json({"results": [resultat_brut()]}),
    ])
    resultat = chercher("exemple", lambda r: next(reponses))
    assert attentes == [1.0]
    assert len(resultat["entreprises"]) == 1


@pytest.mark.parametrize("reponse, message", [
    (httpx.Response(500), "indisponible"),
    (httpx.Response(400), "refusée"),
    (httpx.Response(418), "code HTTP 418"),
    (httpx.Response(200, content=b"<html>pas du json</html>"), "illisible"),
    (httpx.Response(200, json={"autre": []}), "format"),
])
def test_erreurs_api(reponse, message):
    with pytest.raises(ErreurOutil, match=message):
        chercher("exemple", lambda r: reponse)


def test_erreur_reseau():
    def gestionnaire(requete):
        raise httpx.ConnectError("panne", request=requete)
    with pytest.raises(ErreurOutil, match="problème réseau"):
        chercher("exemple", gestionnaire)


def test_delai_depasse():
    def gestionnaire(requete):
        raise httpx.ReadTimeout("lent", request=requete)
    with pytest.raises(ErreurOutil, match="à temps"):
        chercher("exemple", gestionnaire)


# --- L'outil ne lève jamais d'exception -------------------------------------

def test_outil_convertit_les_erreurs(monkeypatch):
    async def faux_client(*args, **kwargs):
        raise ErreurOutil("Quota de l'API Recherche d'entreprises atteint.")

    monkeypatch.setattr(entreprises, "rechercher_entreprise", faux_client)
    assert asyncio.run(verifier_entreprise("exemple")) == {
        "statut": "erreur", "erreur": "Quota de l'API Recherche d'entreprises atteint.",
    }


def test_outil_convertit_les_erreurs_inattendues(monkeypatch):
    async def faux_client(*args, **kwargs):
        raise RuntimeError("bug interne avec détail technique")

    monkeypatch.setattr(entreprises, "rechercher_entreprise", faux_client)
    resultat = asyncio.run(verifier_entreprise("exemple"))
    assert resultat["statut"] == "erreur"
    assert "détail technique" not in resultat["erreur"]


def test_outil_succes(monkeypatch):
    async def faux_client(requete, nb, **kwargs):
        return {"results": [resultat_brut()], "total_results": 1}

    monkeypatch.setattr(entreprises, "rechercher_entreprise", faux_client)
    resultat = asyncio.run(verifier_entreprise("433891850"))
    assert resultat["statut"] == "ok"
    assert resultat["entreprises"][0]["siren"] == "433891850"
    assert "ne prouve pas" in resultat["avertissement"]
    assert all(set(s) == CLES_SOURCE for s in resultat["sources"])
