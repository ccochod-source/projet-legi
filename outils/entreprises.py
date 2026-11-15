"""Outil de recherche d'identité d'une entreprise."""

from typing import Any

from erreurs import ErreurOutil, convertir_erreur


async def verifier_entreprise(nom_ou_siren: str) -> dict[str, Any]:
    """Recherche une entreprise par nom ou SIREN dans l'API publique.

    Refusera une entrée vide ou un SIREN mal formé ; ne présentera pas une
    homonymie comme une identification certaine, ni une inscription comme
    preuve de conformité. Renverra entreprises et sources.
    Aucun appel réseau pour le moment : outil non implémenté.
    """
    return convertir_erreur(ErreurOutil("Vérification d'entreprise non implémentée."))
