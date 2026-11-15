"""Accès asynchrone à l'API officielle Légifrance, sans exposer de secrets."""

import asyncio
import math
import re
import time
from datetime import date
from typing import Any

import httpx

import config
from erreurs import ErreurOutil

# Seuls les corpus législatifs dont le format est traité sont proposés.
FONDS_AUTORISES = frozenset({"CODE_DATE", "CODE_ETAT", "LODA_DATE", "LODA_ETAT"})
LONGUEUR_QUESTION_MAX = 1000
NB_RESULTATS_MAX = 10
IDENTIFIANT_ARTICLE = re.compile(r"LEGIARTI[0-9]{12}\Z")
ERREUR_FORMAT = "Le format de réponse de Légifrance a changé ou est incomplet."


def valider_recherche(question: str, fond: str, nb: int) -> str:
    """Valide les paramètres avant tout accès réseau et nettoie la question."""
    if not isinstance(question, str) or not question.strip():
        raise ErreurOutil("La question juridique doit être un texte non vide.")
    if len(question) > LONGUEUR_QUESTION_MAX:
        raise ErreurOutil("La question doit contenir au maximum 1000 caractères.")
    if not isinstance(fond, str) or fond not in FONDS_AUTORISES:
        raise ErreurOutil("Fond autorisé : CODE_DATE, CODE_ETAT, LODA_DATE ou LODA_ETAT.")
    if type(nb) is not int or not 1 <= nb <= NB_RESULTATS_MAX:
        raise ErreurOutil("Le nombre de résultats doit être un entier entre 1 et 10.")
    return question.strip()


def valider_article(article_id: str) -> None:
    """Distingue un article LEGIARTI d'un texte entier LEGITEXT."""
    if not isinstance(article_id, str) or not IDENTIFIANT_ARTICLE.fullmatch(article_id):
        raise ErreurOutil(
            "L'identifiant doit être LEGIARTI suivi de 12 chiffres. "
            "Un identifiant LEGITEXT désigne un texte entier, pas un article."
        )


class ClientLegifrance:
    """Garde le jeton en mémoire ; les outils filtrent ensuite les données.

    Les charges utiles suivent les exemples DILA de septembre 2025 et le
    Swagger archivé par PyLegifrance. L'authentification Basic Auth suit
    l'essai sandbox réalisé par l'utilisateur (pas de clés dans le corps).
    Un transport peut être injecté pour tester sans réseau.
    """

    def __init__(self, *, transport: httpx.AsyncBaseTransport | None = None) -> None:
        self.authentification = httpx.BasicAuth(
            config.LEGIFRANCE_CLIENT_ID, config.LEGIFRANCE_CLIENT_SECRET
        )
        self._identifiants_presents = bool(
            config.LEGIFRANCE_CLIENT_ID and config.LEGIFRANCE_CLIENT_SECRET
        )
        self.url_jeton = config.LEGIFRANCE_TOKEN_URL
        self.url_base = config.LEGIFRANCE_BASE_URL
        self.delai_s = config.TIMEOUT_S
        self._transport = transport
        self._jeton: str | None = None
        self._expiration_jeton = 0.0
        self._marge_expiration_s = 30.0
        self._verrou_jeton = asyncio.Lock()

    async def _envoyer(self, url: str, **parametres: Any) -> httpx.Response:
        """Ferme chaque connexion ; ne reprend jamais le corps d'une erreur."""
        try:
            async with httpx.AsyncClient(
                timeout=self.delai_s, transport=self._transport,
                follow_redirects=False,
            ) as session:
                return await session.post(url, **parametres)
        except httpx.TimeoutException:
            raise ErreurOutil("Légifrance met trop de temps à répondre. Réessayez plus tard.") from None
        except httpx.RequestError:
            raise ErreurOutil("Connexion à Légifrance impossible. Vérifiez le réseau.") from None

    @staticmethod
    def _verifier_statut(reponse: httpx.Response, *, oauth: bool = False) -> None:
        """Traduit uniquement le code HTTP, jamais un message distant sensible."""
        code = reponse.status_code
        if 200 <= code < 300:
            return
        if code == 400:
            message = (
                "Authentification PISTE refusée : vérifiez les identifiants et l'environnement."
                if oauth else "Légifrance refuse les paramètres de recherche ou de consultation (400)."
            )
        elif code == 401:
            message = "Authentification Légifrance refusée (401) : clé invalide, expirée ou révoquée."
        elif code == 403:
            message = "Accès Légifrance interdit (403). Vérifiez la souscription PISTE et l'environnement."
        elif code == 404:
            message = (
                "Service d'authentification PISTE introuvable (404)."
                if oauth else "Article ou ressource Légifrance introuvable (404)."
            )
        elif code == 429:
            message = "Quota Légifrance atteint (429). Attendez avant de réessayer."
        elif 500 <= code <= 599:
            message = "Le service Légifrance est temporairement indisponible (erreur serveur)."
        else:
            message = "Réponse HTTP inattendue de Légifrance. Réessayez plus tard."
        raise ErreurOutil(message)

    @staticmethod
    def _lire_json(reponse: httpx.Response) -> dict[str, Any]:
        """Détecte notamment une page HTML ou une réponse JSON incompatible."""
        try:
            donnees = reponse.json()
        except ValueError:
            raise ErreurOutil(ERREUR_FORMAT) from None
        if not isinstance(donnees, dict):
            raise ErreurOutil(ERREUR_FORMAT)
        return donnees

    async def _obtenir_jeton(self) -> str:
        """Réutilise le cache ou demande un jeton avec une marge d'expiration."""
        async with self._verrou_jeton:
            if self._jeton and time.monotonic() < self._expiration_jeton:
                return self._jeton
            if not self._identifiants_presents:
                raise ErreurOutil(
                    "Renseignez LEGIFRANCE_CLIENT_ID et LEGIFRANCE_CLIENT_SECRET "
                    "dans le fichier .env pour utiliser Légifrance."
                )
            debut = time.monotonic()
            reponse = await self._envoyer(
                self.url_jeton, auth=self.authentification,
                data={"grant_type": "client_credentials", "scope": "openid"},
                headers={"Accept": "application/json"},
            )
            self._verifier_statut(reponse, oauth=True)
            donnees = self._lire_json(reponse)
            jeton = donnees.get("access_token")
            duree = donnees.get("expires_in")
            if (
                not isinstance(jeton, str)
                or not re.fullmatch(r"[A-Za-z0-9._~+/-]+=*", jeton)
                or str(donnees.get("token_type", "")).lower() != "bearer"
                or type(duree) not in (int, float)
                or not math.isfinite(duree) or duree <= 0
            ):
                raise ErreurOutil("La réponse OAuth de PISTE a changé ou est incomplète.")
            self._jeton = jeton
            marge = min(self._marge_expiration_s, duree / 2)
            self._expiration_jeton = debut + duree - marge
            return jeton

    async def _appeler(self, chemin: str, contenu: dict[str, Any]) -> dict[str, Any]:
        """Renouvelle le jeton une seule fois si l'API répond 401."""
        for essai in range(2):
            jeton = await self._obtenir_jeton()
            reponse = await self._envoyer(
                f"{self.url_base}{chemin}", json=contenu,
                headers={"Authorization": f"Bearer {jeton}", "Accept": "application/json"},
            )
            if reponse.status_code == 401:
                if self._jeton == jeton:
                    self._jeton = None
                    self._expiration_jeton = 0.0
                if essai == 0:
                    continue
            self._verifier_statut(reponse)
            return self._lire_json(reponse)
        raise ErreurOutil("Authentification Légifrance refusée après renouvellement.")

    async def rechercher(self, question: str, fond: str, nb: int) -> dict[str, Any]:
        """Recherche dans les codes ou textes consolidés à la date du jour."""
        question = valider_recherche(question, fond, nb)
        filtres = []
        if fond.endswith("_DATE"):
            filtres.append({"facette": "DATE_VERSION", "singleDate": date.today().isoformat()})
        return await self._appeler("/search", {
            "fond": fond,
            "recherche": {
                "champs": [{
                    "typeChamp": "ALL",
                    "criteres": [{"typeRecherche": "TOUS_LES_MOTS_DANS_UN_CHAMP",
                                  "valeur": question, "operateur": "ET"}],
                    "operateur": "ET",
                }],
                "filtres": filtres, "operateur": "ET",
                "pageNumber": 1, "pageSize": nb,
                "sort": "PERTINENCE", "typePagination": "DEFAUT",
            },
        })

    async def consulter_article(self, article_id: str) -> dict[str, Any]:
        """Consulte exclusivement un article, jamais un identifiant de texte."""
        valider_article(article_id)
        return await self._appeler("/consult/getArticle", {"id": article_id})
