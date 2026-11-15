"""Accès à https://recherche-entreprises.api.gouv.fr (API publique, sans clé).

Ce client renvoie la réponse brute de l'API. Le filtrage des champs (liste
blanche) est fait par l'outil, jamais ici. Toute panne devient une
ErreurOutil avec un message clair, sans détail technique ni secret.
"""

import asyncio
from typing import Any

import httpx

import config
from erreurs import ErreurOutil

URL_RECHERCHE = "https://recherche-entreprises.api.gouv.fr/search"
USER_AGENT = "projet-legi/0.1 (projet etudiant de verification de conformite)"
NB_MAX_RESULTATS = 5
# Au-delà de ce délai d'attente imposé par l'API, on n'attend pas : on prévient.
ATTENTE_MAX_RETRY_S = 3.0


def _lire_retry_after(reponse: httpx.Response) -> float | None:
    """Lit l'en-tête Retry-After (en secondes) s'il est présent et valide."""
    valeur = reponse.headers.get("Retry-After", "").strip()
    if valeur.isdigit():
        return float(valeur)
    return None


async def rechercher_entreprise(
    requete: str,
    nb_resultats: int = NB_MAX_RESULTATS,
    *,
    client: httpx.AsyncClient | None = None,
) -> dict[str, Any]:
    """Recherche par nom ou SIREN et renvoie le JSON brut de l'API.

    Refuse une requête vide ou trop courte (l'API exige 3 caractères).
    Un 429 (quota) est réessayé une seule fois si Retry-After est court.
    """
    requete = (requete or "").strip()
    if len(requete) < 3:
        raise ErreurOutil("La recherche doit contenir au moins 3 caractères.")
    if len(requete) > 200:
        raise ErreurOutil("La recherche est trop longue (200 caractères maximum).")
    nb_resultats = max(1, min(int(nb_resultats), NB_MAX_RESULTATS))
    parametres = {"q": requete, "per_page": nb_resultats, "page": 1}

    client_cree = client is None
    if client is None:
        client = httpx.AsyncClient(
            timeout=config.TIMEOUT_S, headers={"User-Agent": USER_AGENT}
        )
    try:
        for tentative in range(2):
            try:
                reponse = await client.get(URL_RECHERCHE, params=parametres)
            except httpx.TimeoutException:
                raise ErreurOutil(
                    "L'API Recherche d'entreprises n'a pas répondu à temps."
                ) from None
            except httpx.HTTPError:
                raise ErreurOutil(
                    "Impossible de joindre l'API Recherche d'entreprises "
                    "(problème réseau)."
                ) from None

            if reponse.status_code == 429:
                attente = _lire_retry_after(reponse)
                if tentative == 0 and attente is not None and attente <= ATTENTE_MAX_RETRY_S:
                    await asyncio.sleep(attente)
                    continue
                delai = f" Réessayez dans {int(attente)} s." if attente else " Réessayez plus tard."
                raise ErreurOutil(
                    "Quota de l'API Recherche d'entreprises atteint." + delai
                )
            break

        if reponse.status_code == 400:
            raise ErreurOutil("Requête refusée par l'API Recherche d'entreprises.")
        if reponse.status_code >= 500:
            raise ErreurOutil(
                "L'API Recherche d'entreprises est momentanément indisponible."
            )
        if reponse.status_code != 200:
            raise ErreurOutil(
                f"Réponse inattendue de l'API Recherche d'entreprises "
                f"(code HTTP {reponse.status_code})."
            )
        try:
            donnees = reponse.json()
        except ValueError:
            raise ErreurOutil(
                "Réponse illisible de l'API Recherche d'entreprises "
                "(format modifié ?)."
            ) from None
        if not isinstance(donnees, dict) or not isinstance(donnees.get("results"), list):
            raise ErreurOutil(
                "Le format de l'API Recherche d'entreprises a changé : "
                "résultats introuvables."
            )
        return donnees
    finally:
        if client_cree:
            await client.aclose()
