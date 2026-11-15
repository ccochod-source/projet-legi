"""Historique optionnel côté serveur ; aucune clé transmise au navigateur."""

import logging

import anyio
import httpx

import config

journal = logging.getLogger(__name__)


async def enregistrer_analyse(question: str, resultat: dict) -> str | None:
    """Échoue sans interrompre l'analyse, sans journaliser de données sensibles."""
    if not (config.SUPABASE_URL and config.SUPABASE_SERVICE_ROLE_KEY):
        return None
    ligne = {
        "question": question[:2000],
        "rapport": resultat.get("reponse") or resultat.get("erreur", ""),
        "outils": resultat.get("outils_appeles", []),
        "statut": resultat.get("statut", "erreur"),
        "modele": ", ".join(resultat.get("modeles_utilises", [])) or config.GROQ_MODEL,
    }
    try:
        with anyio.fail_after(5):
            return await inserer_ligne(ligne)
    except Exception:
        journal.warning("Historique Supabase non enregistré ; analyse conservée dans la réponse.")
        return "non_enregistre"


async def inserer_ligne(ligne: dict) -> str:
    """Insère une ligne avec la clé privilégiée exclusivement côté serveur."""
    async with httpx.AsyncClient(timeout=5, follow_redirects=False) as client:
        reponse = await client.post(
            config.SUPABASE_URL + "/rest/v1/analyses", json=ligne,
            headers={"apikey": config.SUPABASE_SERVICE_ROLE_KEY,
                     "Authorization": "Bearer " + config.SUPABASE_SERVICE_ROLE_KEY,
                     "Prefer": "return=minimal"},
        )
        reponse.raise_for_status()
    return "enregistre"
