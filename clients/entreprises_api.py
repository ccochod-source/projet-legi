"""Interface de https://recherche-entreprises.api.gouv.fr, sans clé."""

from typing import Any


async def rechercher_entreprise(requete: str) -> dict[str, Any]:
    """Recherchera par nom ou SIREN ; refusera une requête vide.

    Renverra les données publiques brutes, sans inventer de société.
    """
    raise NotImplementedError("Recherche d'entreprise non implémentée.")
