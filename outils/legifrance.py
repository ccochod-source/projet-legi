"""Outils de consultation du droit via Légifrance."""

from typing import Any

from erreurs import ErreurOutil, convertir_erreur


async def rechercher_textes_loi(
    question: str, fond: str = "CODE_DATE", nb_resultats: int = 5
) -> dict[str, Any]:
    """Recherche des textes publics pertinents pour une question juridique.

    Le fond sélectionne le corpus Légifrance et nb_resultats limite la liste.
    Refusera une question vide, un fond inconnu ou un nombre hors limites.
    Ne fournira ni texte inventé ni avis juridique définitif.
    Renverra textes et sources selon le contrat commun. Non implémenté.
    """
    return convertir_erreur(ErreurOutil("Recherche de textes non implémentée."))


async def consulter_article(article_id: str) -> dict[str, Any]:
    """Consulte un article officiel à partir de son identifiant Légifrance.

    Refusera un identifiant vide ou invalide ; ne reconstituera pas un article
    absent. Renverra article et sources selon le contrat commun.
    Aucun appel réseau pour le moment : outil non implémenté.
    """
    return convertir_erreur(ErreurOutil("Consultation d'article non implémentée."))
