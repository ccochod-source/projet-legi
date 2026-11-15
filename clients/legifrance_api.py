"""Interface HTTP Légifrance ; aucun appel réseau n'est encore implémenté."""

from typing import Any

import httpx

import config


class ClientLegifrance:
    """Prévoit OAuth client_credentials, scope openid et cache mémoire du jeton.

    Le futur échange utilisera httpx.BasicAuth et LEGIFRANCE_TOKEN_URL.
    L'expiration sera mesurée avec une horloge monotone et une marge de 30 s.
    Aucun secret ni jeton ne devra figurer dans les réponses ou journaux.
    Les méthodes asynchrones renverront les données publiques brutes ; les
    outils assureront validation, normalisation des sources et erreurs métier.
    """

    def __init__(self) -> None:
        self.authentification = httpx.BasicAuth(
            config.LEGIFRANCE_CLIENT_ID, config.LEGIFRANCE_CLIENT_SECRET
        )
        self.url_jeton = config.LEGIFRANCE_TOKEN_URL
        self.url_base = config.LEGIFRANCE_BASE_URL
        self.delai_s = config.TIMEOUT_S
        self._jeton: str | None = None
        self._expiration_jeton: float = 0.0
        self._marge_expiration_s: float = 30.0

    async def _obtenir_jeton(self) -> str:
        """Réutilisera le cache ou demandera un jeton OAuth avec scope openid."""
        raise NotImplementedError("Authentification Légifrance non implémentée.")

    async def rechercher(
        self, question: str, fond: str, nb: int
    ) -> dict[str, Any]:
        """Recherchera des textes réels ; refusera les paramètres invalides."""
        raise NotImplementedError("Recherche Légifrance non implémentée.")

    async def consulter_article(self, article_id: str) -> dict[str, Any]:
        """Consultera un article identifié ; ne fabriquera aucun contenu."""
        raise NotImplementedError("Consultation Légifrance non implémentée.")
