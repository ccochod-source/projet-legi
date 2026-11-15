"""Serveur MCP : stdio par défaut, HTTP local avec --http."""

import argparse

from mcp.server.fastmcp import FastMCP

from outils.entreprises import verifier_entreprise
from outils.legifrance import consulter_article, rechercher_textes_loi
from outils.site_web import analyser_site

mcp = FastMCP("projet-legi", host="127.0.0.1", port=8000)
mcp.tool()(rechercher_textes_loi)
mcp.tool()(consulter_article)
mcp.tool()(verifier_entreprise)
mcp.tool()(analyser_site)


def lancer() -> None:
    """Choisit le transport sans lancer le serveur à l'importation."""
    analyseur = argparse.ArgumentParser(description="Serveur MCP projet-legi")
    analyseur.add_argument("--http", action="store_true", help="Activer HTTP local")
    arguments = analyseur.parse_args()
    mcp.run(transport="streamable-http" if arguments.http else "stdio")


if __name__ == "__main__":
    lancer()
