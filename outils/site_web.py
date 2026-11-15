"""Outil d'analyse des éléments publics d'un site web.

Étapes : 1) récupérer la page d'accueil (client web sécurisé) ; 2) trouver
les liens vers les pages légales (mentions légales, confidentialité, cookies,
CGV, CGU) ; 3) récupérer ces pages ; 4) détecter traceurs, outil de
consentement, vente en ligne et numéro SIREN (vérifié dans le répertoire) ;
5) appliquer les règles de regles/obligations.json.
Le résultat liste des points conforme / manquant / a_verifier, jamais un
verdict global. Aucun e-mail ni téléphone n'est renvoyé.
"""

import asyncio
import re
from typing import Any
from urllib.parse import urldefrag, urljoin

from bs4 import BeautifulSoup

from clients.web import recuperer_page
from erreurs import ErreurOutil, convertir_erreur
from outils.entreprises import chercher_entreprises, siren_valide
from regles.moteur import LONGUEUR_TEXTE_LISIBLE, charger_regles, chercher_motif, evaluer_obligations

TYPES_PAGES_LEGALES = ("mentions_legales", "confidentialite", "cookies", "cgv", "cgu")
MAX_PAGES = 6  # page d'accueil + 5 pages légales au maximum
MAX_SIREN_VERIFIES = 2
# Types de <script> exécutés par le navigateur ; tout autre type (ex. text/plain
# utilisé par les CMP) bloque le script jusqu'au consentement.
TYPES_SCRIPT_EXECUTES = ("", "text/javascript", "application/javascript", "module", "text/ecmascript", "application/ecmascript")
AVERTISSEMENT = (
    "Analyse automatique d'indices publics : ce n'est ni un avis juridique ni "
    "une certification. « conforme » signifie seulement que l'élément a été "
    "détecté ; le contenu exact reste à faire valider."
)
LIMITES = (
    "Seul le HTML initial est lu (pas de JavaScript exécuté) ; au plus "
    f"{MAX_PAGES} pages ; les traceurs ajoutés dynamiquement (par exemple via "
    "Google Tag Manager) et le comportement réel du bandeau cookies ne sont pas testés."
)


def normaliser_url(url: str) -> str:
    """Ajoute https:// si l'utilisateur a seulement donné un nom de domaine."""
    url = (url or "").strip()
    if not url:
        raise ErreurOutil("Indiquez l'adresse du site à analyser.")
    if "://" not in url:
        url = "https://" + url
    return url


def extraire_texte(html: str) -> str:
    """Texte visible d'une page HTML, espaces normalisés."""
    soupe = BeautifulSoup(html, "html.parser")
    for balise in soupe(["script", "style", "noscript", "template", "svg"]):
        balise.decompose()
    return " ".join(soupe.get_text(" ").split())


def trouver_liens_legaux(soupe: BeautifulSoup, url_base: str, signatures: dict[str, Any]) -> dict[str, str]:
    """Associe à chaque type de page légale le premier lien correspondant.

    Le texte du lien (ou son title / aria-label) est prioritaire sur l'adresse.
    """
    base = soupe.find("base", href=True)
    if base:
        url_base = urljoin(url_base, base["href"].strip())
    liens = []
    for balise in soupe.find_all("a", href=True):
        href = balise["href"].strip()
        if not href or href.startswith(("#", "mailto:", "tel:", "javascript:")):
            continue
        adresse = urldefrag(urljoin(url_base, href))[0]
        if not adresse.startswith(("http://", "https://")):
            continue
        texte = " ".join([balise.get_text(" ", strip=True), balise.get("title", ""), balise.get("aria-label", "")]).strip()
        liens.append((texte, adresse))

    trouves: dict[str, str] = {}
    for critere in ("texte", "adresse"):
        for type_page in TYPES_PAGES_LEGALES:
            if type_page in trouves:
                continue
            # Les motifs sont essayés dans l'ordre : le premier est le plus fiable.
            for motif in signatures[type_page][critere]:
                for texte, adresse in liens:
                    cible = texte if critere == "texte" else adresse
                    if cible and chercher_motif([motif], cible):
                        trouves[type_page] = adresse
                        break
                if type_page in trouves:
                    break
    return trouves


def analyser_traceurs(html: str, cookies: list[str], signatures: dict[str, Any]) -> tuple[dict[str, list[str]], list[str]]:
    """Repère les traceurs connus dans les balises <script> et les outils de consentement."""
    soupe = BeautifulSoup(html, "html.parser")
    actifs: set[str] = set()
    bloques: set[str] = set()
    for script in soupe.find_all("script"):
        if script.find_parent("noscript"):
            continue
        contenu = (script.get("src", "") + " " + (script.string or "")).lower()
        type_script = script.get("type", "").lower()
        bloque = type_script.split(";")[0].strip() not in TYPES_SCRIPT_EXECUTES
        for nom, motifs in signatures["traceurs"].items():
            if any(motif in contenu for motif in motifs):
                (bloques if bloque else actifs).add(nom)
    cookies_traceurs = sorted(
        nom for nom in cookies if nom.startswith(tuple(signatures["cookies_traceurs"]))
    )
    html_minuscule = html.lower()
    cmp = sorted(
        nom for nom, motifs in signatures["cmp"].items()
        if any(motif in html_minuscule for motif in motifs)
    )
    return {"actifs": sorted(actifs), "bloques": sorted(bloques - actifs), "cookies": cookies_traceurs}, cmp


def detecter_e_commerce(html: str, motifs: list[str]) -> list[str]:
    """Renvoie les indices de vente en ligne trouvés dans le HTML (vide si aucun)."""
    indices = []
    for motif in motifs:
        trouve = re.search(motif, html, re.IGNORECASE)
        if trouve:
            indices.append(" ".join(trouve.group(0).split())[:60])
    return indices


def extraire_sirens(pages: dict[str, dict[str, Any]], motifs: list[str]) -> list[dict[str, Any]]:
    """Cherche des numéros SIREN près des mentions SIREN/SIRET/RCS/TVA."""
    candidats: dict[str, dict[str, Any]] = {}
    for type_page in ("mentions_legales", "cgv", "cgu", "accueil", "confidentialite", "cookies"):
        page = pages.get(type_page)
        if not page:
            continue
        for motif in motifs:
            for trouve in re.finditer(motif, page["texte"], re.IGNORECASE):
                numero = re.sub(r"\D", "", trouve.group(1))
                if numero not in candidats:
                    candidats[numero] = {"siren": numero, "url": page["url"], "valide": siren_valide(numero)}
    return list(candidats.values())


async def verifier_siren_trouve(candidats: list[dict[str, Any]]) -> tuple[dict[str, Any], dict[str, Any] | None, list[dict[str, Any]]]:
    """Vérifie les SIREN trouvés dans le répertoire officiel.

    Renvoie (résultat pour la règle, entreprise retenue, sources API).
    """
    valides = [c for c in candidats if c["valide"]][:MAX_SIREN_VERIFIES]
    if not valides:
        if candidats:
            numero = candidats[0]
            return {
                "statut": "a_verifier",
                "preuve": f"Numéro {numero['siren']} trouvé mais sa clé de contrôle est invalide : ce n'est pas un SIREN valide.",
                "url_preuve": numero["url"],
            }, None, []
        return {}, None, []

    sources: list[dict[str, Any]] = []
    dernier_resultat: dict[str, Any] = {}
    for candidat in valides:
        try:
            reponse = await chercher_entreprises(candidat["siren"])
        except ErreurOutil as erreur:
            dernier_resultat = {
                "statut": "a_verifier",
                "preuve": f"SIREN {candidat['siren']} trouvé mais non vérifié : {erreur}",
                "url_preuve": candidat["url"],
            }
            continue
        sources.extend(reponse["sources"])
        if not reponse["entreprises"]:
            dernier_resultat = {
                "statut": "a_verifier",
                "preuve": f"SIREN {candidat['siren']} trouvé sur le site mais absent du répertoire des entreprises.",
                "url_preuve": candidat["url"],
            }
            continue
        entreprise = reponse["entreprises"][0]
        if entreprise["etat"] == "active":
            return {
                "statut": "conforme",
                "preuve": (
                    f"SIREN {candidat['siren']} trouvé ; répertoire : {entreprise['nom']}, "
                    f"entreprise active ({entreprise['commune_siege'] or 'commune inconnue'})."
                ),
                "url_preuve": candidat["url"],
            }, entreprise, sources
        return {
            "statut": "a_verifier",
            "preuve": f"SIREN {candidat['siren']} trouvé, mais l'entreprise est indiquée « {entreprise['etat']} » dans le répertoire.",
            "url_preuve": candidat["url"],
        }, entreprise, sources
    return dernier_resultat, None, sources


async def _recuperer_pages_legales(liens: dict[str, str], accueil: dict[str, Any]) -> tuple[dict[str, Any], dict[str, Any]]:
    """Récupère les pages légales (une seule fois par URL), en parallèle."""
    a_telecharger = []
    for adresse in liens.values():
        if adresse not in a_telecharger and adresse != accueil["url"]:
            a_telecharger.append(adresse)
    a_telecharger = a_telecharger[: MAX_PAGES - 1]
    resultats = await asyncio.gather(*(recuperer_page(u) for u in a_telecharger), return_exceptions=True)
    par_url = dict(zip(a_telecharger, resultats))
    par_url[accueil["url"]] = accueil

    pages, erreurs = {}, {}
    for type_page, adresse in liens.items():
        resultat = par_url.get(adresse)
        if resultat is None:
            erreurs[type_page] = {"url": adresse, "erreur": "Limite du nombre de pages atteinte."}
        elif isinstance(resultat, ErreurOutil):
            erreurs[type_page] = {"url": adresse, "erreur": str(resultat)}
        elif isinstance(resultat, BaseException):
            erreurs[type_page] = {"url": adresse, "erreur": "Erreur inattendue pendant la récupération."}
        else:
            pages[type_page] = resultat
    return pages, erreurs


def _sources(pages: dict[str, Any], regles: dict[str, Any], sources_api: list[dict[str, Any]]) -> list[dict[str, Any]]:
    sources = [{
        "titre": f"Page analysée ({type_page.replace('_', ' ')})",
        "reference": page["url"],
        "url": page["url"],
        "date_recuperation": page["date_recuperation"],
    } for type_page, page in pages.items()]
    vues = set()
    for obligation in regles["obligations"]:
        for ref in [obligation["reference_legale"], *obligation.get("autres_references", [])]:
            cle = (ref["texte"], ref["article"])
            if cle in vues:
                continue
            vues.add(cle)
            sources.append({
                "titre": f"{ref['texte']}, article {ref['article']}",
                "reference": ref.get("legifrance_id") or f"{ref['texte']}, article {ref['article']}",
                "url": ref.get("url", ""),
                "date_recuperation": regles["verifie_le"],
            })
    deja = {(s["url"], s["reference"]) for s in sources}
    for source in sources_api:
        if (source["url"], source["reference"]) not in deja:
            sources.append(source)
            deja.add((source["url"], source["reference"]))
    return sources


async def _analyser(url: str) -> dict[str, Any]:
    url_demandee = normaliser_url(url)
    regles = charger_regles()
    signatures = regles["signatures"]

    accueil = await recuperer_page(url_demandee)
    soupe = BeautifulSoup(accueil["contenu"], "html.parser")
    liens = trouver_liens_legaux(soupe, accueil["url"], signatures["liens"])
    pages_legales, erreurs = await _recuperer_pages_legales(liens, accueil)

    pages = {"accueil": accueil, **pages_legales}
    for page in pages.values():
        page.setdefault("texte", extraire_texte(page["contenu"]))

    confidentialite = pages.get("confidentialite")
    if confidentialite:
        confidentialite["pertinence_confirmee"] = any(
            chercher_motif(o["detection"].get("motifs", []), confidentialite["texte"])
            for o in regles["obligations"] if o["id"].startswith("rgpd_")
        )

    for page in pages_legales.values():
        liens_secondaires = trouver_liens_legaux(
            BeautifulSoup(page["contenu"], "html.parser"), page["url"], signatures["liens"]
        )
        for type_page, adresse in liens_secondaires.items():
            if type_page not in liens:
                erreurs[type_page] = {
                    "url": adresse,
                    "erreur": "Lien trouvé sur une page secondaire, non récupéré dans cette analyse bornée.",
                }

    traceurs, cmp = analyser_traceurs(accueil["contenu"], accueil.get("cookies_deposes", []), signatures)
    indices_vente = detecter_e_commerce(accueil["contenu"], signatures["e_commerce"])
    if "cgv" in liens:
        indices_vente.append("lien vers des conditions générales de vente")
    candidats = extraire_sirens(pages, signatures["siren"])
    resultat_siren, entreprise, sources_api = await verifier_siren_trouve(candidats)
    textes_editeur = " ".join(pages[t]["texte"] for t in ("mentions_legales", "cgv", "cgu", "accueil") if t in pages)
    professionnel = bool(
        any(c["valide"] for c in candidats) or indices_vente
        or chercher_motif(signatures["professionnel"], textes_editeur)
    )

    contexte = {
        "url_finale": accueil["url"],
        "pages": {t: {
            "url": p["url"], "texte": p["texte"],
            "pertinence_confirmee": p.get("pertinence_confirmee", True),
        } for t, p in pages.items()},
        "erreurs_pages": erreurs,
        "contenu_lisible": len(accueil["texte"]) >= LONGUEUR_TEXTE_LISIBLE,
        "e_commerce": bool(indices_vente),
        "professionnel": professionnel,
        "traceurs": traceurs,
        "cmp": cmp,
        "siren": resultat_siren,
    }
    verifications = evaluer_obligations(regles, contexte)
    resume = {statut: sum(1 for v in verifications if v["statut"] == statut) for statut in ("conforme", "manquant", "a_verifier")}

    return {
        "statut": "ok",
        "analyse": {
            "url_demandee": url_demandee,
            "url_analysee": accueil["url"],
            "pages_analysees": [{"type": t, "url": p["url"]} for t, p in pages.items()],
            "pages_non_recuperees": [{"type": t, **e} for t, e in erreurs.items()],
            "vente_en_ligne_detectee": bool(indices_vente),
            "indices_vente_en_ligne": indices_vente,
            "editeur_professionnel_detecte": professionnel,
            "traceurs_detectes": traceurs["actifs"],
            "traceurs_bloques_avant_consentement": traceurs["bloques"],
            "cookies_traceurs_deposes": traceurs["cookies"],
            "outils_consentement_detectes": cmp,
            "entreprise_verifiee": entreprise,
            "verifications": verifications,
            "resume": resume,
            "avertissement": AVERTISSEMENT,
            "limites": LIMITES,
        },
        "sources": _sources(pages, regles, sources_api),
    }


async def analyser_site(url: str) -> dict[str, Any]:
    """Analyse un site public au regard des obligations de regles/obligations.json.

    Récupère la page d'accueil et jusqu'à 5 pages légales liées (http/https
    seulement, adresses privées refusées, taille et délai bornés). Chaque
    vérification a un statut conforme / manquant / a_verifier, une preuve
    courte et sa référence légale. Pas de verdict global, pas d'e-mail ni
    de téléphone renvoyé, aucune donnée inventée.
    """
    try:
        return await _analyser(url)
    except ErreurOutil as erreur:
        return convertir_erreur(erreur)
    except Exception:
        return convertir_erreur(ErreurOutil("Erreur inattendue pendant l'analyse du site."))
