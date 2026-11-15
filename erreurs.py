"""Erreurs présentables à l'utilisateur, sans détails internes ni secrets."""

from typing import Any


class ErreurOutil(Exception):
    """Porte un message français clair, sans donnée sensible."""


def convertir_erreur(erreur: ErreurOutil) -> dict[str, Any]:
    """Convertit une erreur métier en réponse standard d'un outil."""
    return {"statut": "erreur", "erreur": str(erreur)}
