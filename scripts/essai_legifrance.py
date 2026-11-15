"""Essai manuel réel : python scripts/essai_legifrance.py depuis le projet.

Les identifiants sont lus dans .env par config.py. Seules les réponses
filtrées des outils sont affichées, jamais les réponses OAuth ou brutes.
L'option --article permet de choisir un LEGIARTI trouvé sur Légifrance.
Sans article dans la recherche, on lit l'exemple officiel DILA, en le
signalant explicitement : il ne constitue pas un résultat de la recherche.
"""

import argparse
import asyncio
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from outils.legifrance import consulter_article, rechercher_textes_loi

# Exemple DILA : article L. 36-11 au 1er janvier 2018 (version historique).
# https://github.com/pylegifrance/pylegifrance/blob/main/docs/raw/legifrance/exemples-d-utilisation-de-l-api.md
ARTICLE_EXEMPLE_DILA = "LEGIARTI000033219357"


async def essayer(article_id: str | None) -> int:
    """Cherche « mentions légales » puis lit un article réellement identifié."""
    recherche = await rechercher_textes_loi("mentions légales")
    print(json.dumps(recherche, ensure_ascii=False, indent=2))
    if recherche["statut"] != "ok":
        return 1
    if article_id is None:
        article_id = next((
            texte["id"] for texte in recherche["textes"]
            if texte["id"].startswith("LEGIARTI")
        ), None)
    if article_id is None:
        print(
            "Aucun identifiant d'article dans cette recherche. "
            "Lecture séparée de l'article historique d'exemple DILA "
            f"{ARTICLE_EXEMPLE_DILA}, qui n'est pas un résultat de cette recherche."
        )
        article_id = ARTICLE_EXEMPLE_DILA
    article = await consulter_article(article_id)
    print(json.dumps(article, ensure_ascii=False, indent=2))
    return 0 if article["statut"] == "ok" else 1


if __name__ == "__main__":
    analyseur = argparse.ArgumentParser(
        description="Essai réel des outils Légifrance", add_help=False,
    )
    analyseur.add_argument("-h", "--help", action="help", help="Afficher cette aide et quitter")
    analyseur.add_argument("--article", help="Identifiant LEGIARTI à lire après la recherche")
    arguments = analyseur.parse_args()
    raise SystemExit(asyncio.run(essayer(arguments.article)))
