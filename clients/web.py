"""Interface de récupération sécurisée des pages web publiques."""

from typing import Any


async def recuperer_page(url: str) -> dict[str, Any]:
    """Renverra url, contenu, type_contenu et date_recuperation.

    N'acceptera que HTTP/HTTPS ; refusera les IP privées, locales et réservées,
    y compris après résolution DNS et à chaque redirection. Imposera une
    limite de taille et TIMEOUT_S. Aucun accès réseau n'est encore effectué.
    """
    raise NotImplementedError("Récupération de page non implémentée.")
