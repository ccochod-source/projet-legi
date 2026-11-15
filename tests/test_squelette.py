"""Vérifie l'import, les interfaces MCP et les réponses des bouchons."""

import asyncio
import importlib

import pytest

from outils.legifrance import consulter_article, rechercher_textes_loi


def test_import_serveur() -> None:
    serveur = importlib.import_module("server")
    assert serveur.mcp.name == "projet-legi"


def test_outils_enregistres() -> None:
    from server import mcp

    outils = asyncio.run(mcp.list_tools())
    assert {outil.name for outil in outils} == {
        "rechercher_textes_loi", "consulter_article",
        "verifier_entreprise", "analyser_site",
    }


@pytest.mark.parametrize("valeur", ["exemple", ""])
@pytest.mark.parametrize("outil", [rechercher_textes_loi, consulter_article])
def test_bouchons_sans_donnees_inventees(outil, valeur: str) -> None:
    resultat = asyncio.run(outil(valeur))
    assert set(resultat) == {"statut", "erreur"}
    assert resultat["statut"] == "erreur"
    assert "non implémentée" in resultat["erreur"]
