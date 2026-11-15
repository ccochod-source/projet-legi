"""Vérifie l'import du serveur et l'enregistrement des outils MCP."""

import asyncio
import importlib


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
