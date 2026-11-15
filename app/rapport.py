"""Vérifie les preuves et références avant de produire le rapport Markdown."""

import html
import json
import re
import unicodedata
from typing import Any, Literal
from urllib.parse import urlsplit

from pydantic import BaseModel, Field, ValidationError

from erreurs import ErreurOutil
from app.tableau_de_bord import construire_tableau_de_bord
from regles.moteur import charger_regles


class PointPropose(BaseModel):
    """Un constat du modèle, encore non validé."""

    point: str = Field(min_length=1, max_length=250)
    statut: Literal["conforme", "manquant", "a_verifier"]
    preuve: str = Field(default="", max_length=1500)
    reference: str = Field(default="", max_length=500)
    url: str = Field(default="", max_length=2000)


class RapportPropose(BaseModel):
    """Le modèle ne peut ajouter de conclusion globale libre."""

    points: list[PointPropose] = Field(max_length=30)
    informations_manquantes: list[str] = Field(default_factory=list, max_length=30)


def url_legale(url: str) -> bool:
    """Une page commerciale ou un registre d'entreprises n'est pas une loi."""
    try:
        morceaux = urlsplit(url)
        hote = morceaux.hostname or ""
        domaines = ("legifrance.gouv.fr", "eur-lex.europa.eu", "cnil.fr",
                    "service-public.fr", "service-public.gouv.fr", "economie.gouv.fr")
        return (morceaux.scheme == "https" and not morceaux.username
                and not morceaux.password and morceaux.port in {None, 443}
                and not any(caractere in url for caractere in "\n\r\t <>")
                and any(hote == domaine or hote.endswith("." + domaine) for domaine in domaines))
    except ValueError:
        return False


def valeurs_textuelles(valeur: Any) -> list[str]:
    """Collecte les faits citables sans confondre source et preuve."""
    if isinstance(valeur, str):
        return [valeur]
    if isinstance(valeur, list):
        return [texte for enfant in valeur for texte in valeurs_textuelles(enfant)]
    if isinstance(valeur, dict):
        return [texte for cle, enfant in valeur.items()
                if cle not in {"sources", "statut"} for texte in valeurs_textuelles(enfant)]
    return []


def cellule(texte: str) -> str:
    """Échappe le Markdown et le HTML pour l'export."""
    texte = html.escape(texte, quote=True).replace("\n", " ").replace("\r", " ")
    for caractere in ("\\", "|", "[", "]", "*", "_", "`", "#"):
        texte = texte.replace(caractere, "\\" + caractere)
    return texte


def conclusion_globale(texte: str) -> bool:
    """Écarte les formulations usuelles de certification globale du rapport."""
    normalise = "".join(caractere for caractere in unicodedata.normalize("NFKD", texte.lower())
                        if not unicodedata.combining(caractere))
    return bool(re.search(
        r"\b(global\w*|legalite)\b|\b(site|projet)\b.{0,25}\b(conforme|legal)\b"
        r"|\btout\b.{0,15}\b(conforme|legal)\b|\b(conformite|legal)\b.{0,15}\b(site|projet)\b",
        normalise,
    ))


def rapport_depuis_outils(resultats: list[dict[str, Any]]) -> dict[str, Any] | None:
    """Restitue les constats structurés sans demander à l'IA de les réécrire.

    Les statuts du moteur restent souverains ; la validation des références
    et preuves est la même que pour une proposition du modèle.
    """
    points = []
    limites = []
    constats_site = []
    regles = {o["id"]: o for o in charger_regles()["obligations"]}
    for resultat in resultats:
        if resultat.get("statut") != "ok":
            continue
        analyse = resultat.get("analyse", {})
        for constat in analyse.get("verifications", []):
            constats_site.append((len(points), constat))
            reference = constat["reference"]
            points.append({
                "point": constat["id"].replace("_", " "), "statut": constat["statut"],
                "preuve": constat["preuve"], "url": reference.get("url", ""),
                "reference": reference.get("legifrance_id") or
                    f"{reference['texte']}, article {reference['article']}",
            })
        if analyse.get("limites"):
            limites.append(analyse["limites"])
        if "entreprises" in resultat:
            limites.extend([resultat.get("message", ""), resultat.get("avertissement", "")])
            for entreprise in resultat["entreprises"]:
                for cle in ("nom", "siren", "etat"):
                    points.append({"point": f"Identité publique — {cle}", "statut": "a_verifier",
                                   "preuve": entreprise.get(cle) or "", "reference": "", "url": ""})
            if not resultat["entreprises"]:
                limites.append("Aucune entreprise trouvée ; aucune identité n'est établie.")
        article = resultat.get("article")
        if article:
            points.append({
                "point": f"Article {article.get('numero_article') or ''} — {article.get('titre') or article['id']}"[:250],
                "statut": "a_verifier", "preuve": article["texte"][:1200],
                "reference": article["id"], "url": article["url"],
            })
            limites.append("Articles consultés : extraits, état et applicabilité à vérifier ; aucune conformité n'est déduite de leur lecture.")
    if not points and not limites:
        return None
    rapport = construire_rapport(json.dumps({
        "points": points[:30], "informations_manquantes": [limite for limite in limites if limite][:30],
    }, ensure_ascii=False), resultats)
    if constats_site:
        constats = []
        for index, constat in constats_site:
            if index >= len(rapport["points"]):
                continue
            regle = regles.get(constat["id"], {})
            constats.append({
                **rapport["points"][index], "id": constat["id"],
                "libelle": regle.get("libelle", constat.get("libelle", constat["id"])),
                "theme": regle.get("theme", constat.get("theme", "Mentions légales")),
                "gravite": regle.get("gravite", constat.get("gravite", "information")),
                "applicable": constat.get("applicable", True),
                "action": regle.get("action", constat.get("action", "Vérifiez ce point manuellement.")),
            })
        rapport["tableau_de_bord"] = construire_tableau_de_bord(constats)
    return rapport


def construire_rapport(contenu: str, resultats: list[dict[str, Any]]) -> dict[str, Any]:
    """Un constat sans source connue ou preuve exacte devient a_verifier."""
    try:
        proposition = RapportPropose.model_validate(json.loads(contenu))
    except (ValueError, ValidationError) as erreur:
        raise ErreurOutil("Format du rapport Groq invalide. Relancez une analyse plus précise.") from erreur
    sources: dict[tuple[str, str], dict[str, str]] = {}
    preuves: list[str] = []
    for resultat in resultats:
        if resultat.get("statut") != "ok":
            continue
        preuves.extend(valeurs_textuelles(resultat))
        for source in resultat.get("sources", []):
            if not isinstance(source, dict):
                continue
            reference, url = source.get("reference"), source.get("url")
            if isinstance(reference, str) and reference and isinstance(url, str) and url_legale(url):
                sources[(reference, url)] = source
    points = []
    manquantes = [texte[:1000] for texte in proposition.informations_manquantes
                 if not conclusion_globale(texte)]
    for point in proposition.points:
        if conclusion_globale(point.point) or conclusion_globale(point.preuve):
            points.append({"point": "Périmètre de vérification à préciser", "statut": "a_verifier",
                           "preuve": "Un constat doit porter sur une obligation précise.",
                           "reference": "Référence légale à rechercher", "url": ""})
            manquantes.append("Décrire une obligation précise à vérifier, sans conclusion sur le projet entier.")
            continue
        source = sources.get((point.reference, point.url))
        preuve_connue = len(point.preuve.strip()) >= 4 and any(point.preuve in texte for texte in preuves)
        statut = point.statut if source and preuve_connue else "a_verifier"
        if not source:
            manquantes.append("Référence légale à rechercher pour : " + point.point)
        points.append({
            "point": point.point, "statut": statut,
            "preuve": point.preuve if preuve_connue else "Preuve non retrouvée dans les résultats des outils.",
            "reference": source["reference"] if source else "Référence légale à rechercher",
            "url": source["url"] if source else "",
        })
    if not points:
        points.append({"point": "Vérification à compléter", "statut": "a_verifier",
                       "preuve": "Aucun constat documenté par les outils.",
                       "reference": "Référence légale à rechercher", "url": ""})
    manquantes.append("Ce rapport porte seulement sur les éléments consultés ; l'applicabilité et les points non documentés restent à vérifier.")
    for resultat in resultats:
        if resultat.get("statut") == "erreur":
            manquantes.append("Vérification incomplète : " + str(resultat.get("erreur", "outil indisponible")))
    manquantes = list(dict.fromkeys(manquantes))
    lignes = ["# Rapport de vérification", "", "| Point | Statut | Preuve | Référence légale |",
              "| --- | --- | --- | --- |"]
    for point in points:
        reference = cellule(point["reference"])
        if point["url"]:
            url = point["url"].replace("(", "%28").replace(")", "%29")
            reference = f"[{reference}](<{url}>)"
        lignes.append("| " + " | ".join([cellule(point["point"]), point["statut"],
                                          cellule(point["preuve"]), reference]) + " |")
    lignes.extend(["", "## Informations manquantes et limites", ""])
    lignes.extend("- " + cellule(texte) for texte in manquantes)
    lignes.extend(["", "Ce rapport préparatoire ne constitue pas un avis juridique."])
    utilisees = {(point["reference"], point["url"]) for point in points if point["url"]}
    return {"reponse": "\n".join(lignes), "points": points,
            "informations_manquantes": manquantes,
            "sources": [sources[cle] for cle in sorted(utilisees)]}
