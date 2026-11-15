"""Moteur de règles : applique regles/obligations.json à un site analysé.

Le moteur ne connaît aucune règle « en dur » : il lit le fichier JSON et
applique des types de détection simples (https, page, mots_cles, siren,
traceurs). Chaque vérification renvoie un statut parmi conforme / manquant
/ a_verifier, une preuve courte et la référence légale. Il n'y a jamais de
verdict global.
"""

import json
import re
from functools import lru_cache
from pathlib import Path
from typing import Any

from erreurs import ErreurOutil

CHEMIN_REGLES = Path(__file__).parent / "obligations.json"
STATUTS = ("conforme", "manquant", "a_verifier")
CHAMPS_REQUIS = ("id", "theme", "description", "reference_legale", "verification", "gravite", "detection")
GRAVITES = {"information", "avertissement", "critique"}
TYPES_DETECTION = {"https", "page", "mots_cles", "siren", "traceurs"}
APPLICABILITES = {"toujours", "professionnel", "e_commerce", "traceurs"}
LONGUEUR_MAX_EXTRAIT = 80

MOTIF_EMAIL = re.compile(r"[\w.+-]+@[\w-]+(?:\.[\w-]+)+")
MOTIF_TELEPHONE = re.compile(r"(?:\+\d{1,3}[\s.\-]?|\b0)[1-9](?:[\s.\-]?\d{2}){4}\b")

EXPLICATIONS_APPLICABILITE = {
    "professionnel": (
        "Obligation propre aux professionnels : rien sur le site ne permet "
        "d'établir que l'éditeur en est un."
    ),
    "e_commerce": (
        "Obligation de vente en ligne : aucun indice de vente en ligne détecté. "
        "À vérifier si le site vend à des consommateurs."
    ),
    "traceurs": (
        "Obligation liée aux traceurs : aucun traceur ni bandeau connu dans le "
        "HTML initial (ceux ajoutés par JavaScript ne sont pas visibles)."
    ),
}


def masquer_donnees(texte: str) -> str:
    """Masque e-mails et numéros de téléphone (données possiblement personnelles)."""
    texte = MOTIF_EMAIL.sub("[e-mail masqué]", texte)
    return MOTIF_TELEPHONE.sub("[téléphone masqué]", texte)


def _valider(donnees: Any) -> dict[str, Any]:
    """Vérifie la structure du fichier de règles ; lève ErreurOutil sinon."""
    if not isinstance(donnees, dict) or not isinstance(donnees.get("obligations"), list):
        raise ErreurOutil("Fichier de règles invalide : liste « obligations » absente.")
    identifiants = set()
    for obligation in donnees["obligations"]:
        manquants = [champ for champ in CHAMPS_REQUIS if champ not in obligation]
        if manquants:
            raise ErreurOutil(f"Règle incomplète ({', '.join(manquants)}) dans obligations.json.")
        if obligation["id"] in identifiants:
            raise ErreurOutil(f"Règle en double dans obligations.json : {obligation['id']}.")
        identifiants.add(obligation["id"])
        if obligation["gravite"] not in GRAVITES:
            raise ErreurOutil(f"Gravité inconnue pour la règle {obligation['id']}.")
        if obligation["detection"].get("type") not in TYPES_DETECTION:
            raise ErreurOutil(f"Type de détection inconnu pour la règle {obligation['id']}.")
        if obligation.get("applicabilite", "toujours") not in APPLICABILITES:
            raise ErreurOutil(f"Applicabilité inconnue pour la règle {obligation['id']}.")
        for motif in obligation["detection"].get("motifs", []):
            re.compile(motif)
    if not isinstance(donnees.get("signatures"), dict):
        raise ErreurOutil("Fichier de règles invalide : « signatures » absentes.")
    return donnees


@lru_cache(maxsize=1)
def charger_regles() -> dict[str, Any]:
    """Lit et valide obligations.json (une seule fois par processus)."""
    try:
        donnees = json.loads(CHEMIN_REGLES.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        raise ErreurOutil("Impossible de lire le fichier de règles obligations.json.") from None
    return _valider(donnees)


def chercher_motif(motifs: list[str], texte: str) -> str | None:
    """Renvoie le premier passage correspondant à un des motifs, ou None."""
    for motif in motifs:
        trouve = re.search(motif, texte, re.IGNORECASE)
        if trouve:
            return trouve.group(0)
    return None


def _extrait(texte: str) -> str:
    texte = masquer_donnees(" ".join(texte.split()))
    if len(texte) > LONGUEUR_MAX_EXTRAIT:
        texte = texte[: LONGUEUR_MAX_EXTRAIT - 1] + "…"
    return texte


def _applicable(applicabilite: str, contexte: dict[str, Any]) -> bool:
    """Indique si l'analyse a établi que l'obligation s'applique au site."""
    if applicabilite == "professionnel":
        return contexte["professionnel"]
    if applicabilite == "e_commerce":
        return contexte["e_commerce"]
    if applicabilite == "traceurs":
        traceurs = contexte["traceurs"]
        return bool(traceurs["actifs"] or traceurs["bloques"] or traceurs["cookies"] or contexte["cmp"])
    return True


def _url_non_lue(contexte: dict[str, Any], pages: tuple[str, ...]) -> str | None:
    """URL de la première page liée mais non récupérée parmi ces pages."""
    for type_page in pages:
        if type_page in contexte["erreurs_pages"]:
            return contexte["erreurs_pages"][type_page]["url"]
    return None


def _absent(
    obligation: dict[str, Any], contexte: dict[str, Any], explication: str, pages: tuple[str, ...] = ()
) -> tuple[str, str]:
    """Statut quand l'élément n'est pas trouvé : manquant seulement si c'est sûr."""
    non_lues = [t for t in pages if t in contexte["erreurs_pages"]]
    if non_lues:
        return "a_verifier", (
            f"{explication} Page(s) liée(s) mais non récupérée(s) : "
            + ", ".join(contexte["erreurs_pages"][t]["url"] for t in non_lues) + "."
        )
    applicabilite = obligation.get("applicabilite", "toujours")
    if not _applicable(applicabilite, contexte):
        return "a_verifier", f"{explication} {EXPLICATIONS_APPLICABILITE[applicabilite]}"
    if not contexte["contenu_lisible"]:
        return "a_verifier", (
            f"{explication} La page d'accueil contient très peu de texte "
            "(site probablement généré en JavaScript) : vérification manuelle nécessaire."
        )
    return "manquant", explication


def _detecter_page(obligation, contexte):
    type_page = obligation["detection"]["page"]
    page = contexte["pages"].get(type_page)
    if page:
        return "conforme", f"Page trouvée : {page['url']}", page["url"]
    if type_page in contexte["erreurs_pages"]:
        erreur = contexte["erreurs_pages"][type_page]
        return "a_verifier", f"Lien trouvé mais page non récupérée : {erreur['erreur']}", erreur["url"]
    statut, preuve = _absent(obligation, contexte, "Aucun lien vers cette page trouvé sur la page d'accueil.")
    return statut, preuve, contexte["url_finale"]


def _detecter_mots_cles(obligation, contexte):
    detection = obligation["detection"]
    for type_page in detection["pages"]:
        page = contexte["pages"].get(type_page)
        if not page:
            continue
        trouve = chercher_motif(detection["motifs"], page["texte"])
        if trouve:
            return "conforme", f"« {_extrait(trouve)} » trouvé sur {page['url']}", page["url"]
    lues = [contexte["pages"][t]["url"] for t in detection["pages"] if t in contexte["pages"]]
    explication = "Mention non trouvée dans les pages lues : " + (", ".join(lues) or "aucune") + "."
    statut, preuve = _absent(obligation, contexte, explication, tuple(detection["pages"]))
    pages = tuple(detection["pages"])
    return statut, preuve, (_url_non_lue(contexte, pages) or (lues[0] if lues else contexte["url_finale"]))


def _detecter_https(obligation, contexte):
    url = contexte["url_finale"]
    if url.startswith("https://"):
        return "conforme", f"Page servie en HTTPS : {url}", url
    return "manquant", f"Page servie sans chiffrement (HTTP) : {url}", url


def _detecter_siren(obligation, contexte):
    resultat = contexte.get("siren") or {}
    if resultat.get("statut") in STATUTS:
        return resultat["statut"], resultat["preuve"], resultat.get("url_preuve")
    pages = ("mentions_legales", "cgv", "cgu")
    statut, preuve = _absent(obligation, contexte, "Aucun numéro SIREN, SIRET ou RCS trouvé dans les pages lues.", pages)
    return statut, preuve, _url_non_lue(contexte, pages) or contexte["url_finale"]


def _detecter_traceurs(obligation, contexte):
    traceurs = contexte["traceurs"]
    cmp = contexte["cmp"]
    url = contexte["url_finale"]
    actifs = traceurs["actifs"] + [f"cookie {nom}" for nom in traceurs["cookies"]]
    # Un « chargeur » (ex. Google Tag Manager) ne dépose rien par lui-même :
    # il peut charger le bandeau de consentement, on ne conclut donc pas.
    chargeurs = obligation["detection"].get("chargeurs", [])
    if actifs and not cmp and all(nom in chargeurs for nom in actifs):
        return "a_verifier", (
            "Chargeur de balises détecté (" + ", ".join(actifs) + ") sans outil de consentement "
            "connu dans le HTML initial : vérifier ce qu'il charge avant l'accord de l'internaute."
        ), url
    if actifs and not cmp:
        return "manquant", (
            "Traceurs chargés dès le HTML initial : " + ", ".join(actifs)
            + " ; aucun outil de consentement (bandeau/CMP) connu détecté."
        ), url
    if actifs:
        return "a_verifier", (
            "Traceurs détectés (" + ", ".join(actifs) + ") et outil de consentement détecté ("
            + ", ".join(cmp) + ") : vérifier qu'aucun traceur ne se déclenche avant l'accord ou après un refus."
        ), url
    if cmp or traceurs["bloques"]:
        bloques = f" Traceurs en attente de consentement : {', '.join(traceurs['bloques'])}." if traceurs["bloques"] else ""
        return "a_verifier", (
            "Outil de consentement détecté (" + (", ".join(cmp) or "attributs de blocage")
            + ")." + bloques + " Tester manuellement le refus des cookies."
        ), url
    return "a_verifier", (
        "Aucun traceur connu dans le HTML initial ; ceux injectés ensuite par JavaScript "
        "ne sont pas visibles par cette analyse."
    ), url


DETECTEURS = {
    "https": _detecter_https,
    "page": _detecter_page,
    "mots_cles": _detecter_mots_cles,
    "siren": _detecter_siren,
    "traceurs": _detecter_traceurs,
}


def evaluer_obligations(regles: dict[str, Any], contexte: dict[str, Any]) -> list[dict[str, Any]]:
    """Applique chaque obligation au contexte du site et renvoie les vérifications."""
    verifications = []
    for obligation in regles["obligations"]:
        detecteur = DETECTEURS[obligation["detection"]["type"]]
        statut, preuve, url_preuve = detecteur(obligation, contexte)
        verifications.append({
            "id": obligation["id"],
            "theme": obligation["theme"],
            "description": obligation["description"],
            "statut": statut,
            "preuve": masquer_donnees(preuve),
            "url_preuve": url_preuve,
            "methode": obligation["verification"],
            "gravite": obligation["gravite"],
            "reference": obligation["reference_legale"],
            "autres_references": obligation.get("autres_references", []),
        })
    return verifications
