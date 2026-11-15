"""Indice pondéré déterministe des éléments détectés, jamais un avis juridique."""

POIDS = {"critique": 3, "avertissement": 2, "information": 1}
THEMES = ("Mentions légales", "Données personnelles", "Cookies et traceurs",
          "Commerce électronique", "Sécurité")
CATEGORIES = ("conforme", "a_corriger", "a_verifier", "non_applicable")


def indice(points: list[dict]) -> int | None:
    """Exclut du dénominateur les seuls constats d'applicabilité non établie."""
    retenus = [p for p in points if p["categorie"] != "non_applicable"]
    total = sum(POIDS[p["gravite"]] for p in retenus)
    detectes = sum(POIDS[p["gravite"]] for p in retenus if p["categorie"] == "conforme")
    return round(100 * detectes / total) if total else None


def construire_tableau_de_bord(constats: list[dict]) -> dict:
    """Classe les constats déjà validés et calcule score, sous-scores et compteurs."""
    points = []
    for constat in constats:
        categorie = {"conforme": "conforme", "manquant": "a_corriger",
                     "a_verifier": "a_verifier"}[constat["statut"]]
        if categorie == "a_verifier" and constat.get("applicable") is False:
            categorie = "non_applicable"
        point = {**constat, "categorie": categorie}
        if categorie not in {"a_corriger", "a_verifier"}:
            point.pop("action", None)
        points.append(point)
    return {
        "score": indice(points),
        "sous_scores": {theme: indice([p for p in points if p["theme"] == theme]) for theme in THEMES},
        "compteurs": {categorie: sum(p["categorie"] == categorie for p in points) for categorie in CATEGORIES},
        "points": points,
        "avertissement": "Indice des éléments détectés automatiquement, pas un verdict juridique.",
    }
