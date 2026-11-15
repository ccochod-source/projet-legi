"""Indice de détection déterministe : pondération, exclusions et incertitude."""

import pytest

from app.tableau_de_bord import construire_tableau_de_bord
from regles.moteur import charger_regles


def point(statut="conforme", gravite="information", theme="Sécurité", applicable=True):
    return {"id": "test", "libelle": "Point de test", "statut": statut, "gravite": gravite,
            "theme": theme, "applicable": applicable, "preuve": "Preuve", "reference": "Source",
            "url": "https://eur-lex.europa.eu/", "action": "Vérifiez le point."}


def test_poids_et_sous_scores():
    tableau = construire_tableau_de_bord([
        point(gravite="critique"), point("manquant"),
        point("a_verifier", "avertissement", "Mentions légales"),
    ])
    assert tableau["score"] == 50
    assert tableau["sous_scores"]["Sécurité"] == 75
    assert tableau["sous_scores"]["Mentions légales"] == 0
    assert tableau["sous_scores"]["Commerce électronique"] is None
    assert tableau["compteurs"] == {"conforme": 1, "a_corriger": 1, "a_verifier": 1, "non_applicable": 0}
    assert "action" not in tableau["points"][0]
    assert tableau["points"][1]["action"]


def test_exclusion_applicabilite_sans_exclure_incertitude():
    tableau = construire_tableau_de_bord([
        point(), point("a_verifier"), point("a_verifier", "critique", applicable=False),
    ])
    assert tableau["score"] == 50
    assert tableau["compteurs"]["non_applicable"] == 1
    assert "action" not in tableau["points"][2]


@pytest.mark.parametrize("points", [[], [point("a_verifier", applicable=False)]])
def test_score_nul_sans_denominateur(points):
    tableau = construire_tableau_de_bord(points)
    assert tableau["score"] is None
    assert all(score is None for score in tableau["sous_scores"].values())


def test_regles_libelles_et_actions():
    for regle in charger_regles()["obligations"]:
        assert regle["libelle"].strip()
        assert regle["action"].strip()
