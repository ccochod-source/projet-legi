"""Outil d'analyse des éléments publics d'un site."""

from typing import Any

from erreurs import ErreurOutil, convertir_erreur


async def analyser_site(url: str) -> dict[str, Any]:
    """Analysera une page publique au regard des obligations documentées.

    Refusera les schémas autres que HTTP/HTTPS, les destinations privées,
    les pages trop volumineuses et les dépassements de délai, via le client
    web. Ne contournera aucune authentification et ne certifiera jamais une
    conformité globale. Renverra analyse et sources, sans données inventées.
    Aucun accès réseau pour le moment : outil non implémenté.
    """
    return convertir_erreur(ErreurOutil("Analyse de site non implémentée."))
