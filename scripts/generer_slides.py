"""Génère la présentation interactive, synthèse du poster MCP."""

import json
from collections import Counter
from html import escape
from pathlib import Path


RACINE = Path(__file__).resolve().parents[1]
obligations = json.loads((RACINE / "regles/obligations.json").read_text())["obligations"]
themes = Counter(point["theme"] for point in obligations)
slides = []
icones = {
    "recherche": '<circle cx="10" cy="10" r="6"/><path d="m15 15 6 6"/>',
    "article": '<path d="M6 3h9l4 4v14H6zM14 3v5h5M9 12h7M9 16h7"/>',
    "entreprise": '<path d="M4 21V7h10v14M14 11h6v10M8 11h2M8 15h2M8 19h2M2 21h20"/>',
    "site": '<rect x="3" y="4" width="18" height="16" rx="2"/><path d="M3 9h18M7 6.5h.1M10 6.5h.1M7 14l3 3 7-5"/>',
    "bouclier": '<path d="m12 2 8 4v6c0 5-8 10-8 10S4 17 4 12V6zM8 12l3 3 5-6"/>',
    "source": '<path d="M9 15 15 9M8 17l-1 1a4 4 0 0 1-6-6l5-5a4 4 0 0 1 6 0M16 7l1-1a4 4 0 0 1 6 6l-5 5a4 4 0 0 1-6 0"/>',
    "donnees": '<rect x="5" y="10" width="14" height="11" rx="2"/><path d="M8 10V6a4 4 0 0 1 8 0v4M12 14v3"/>',
    "regles": '<path d="M4 6h16M4 12h16M4 18h16M8 3v6M16 9v6M10 15v6"/>',
}


def icone(nom):
    return '<svg class="icone" viewBox="0 0 24 24" aria-hidden="true" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round">' + icones[nom] + "</svg>"


def nombre(valeur):
    return f'<span class="compte" data-final="{valeur}" aria-hidden="true">{valeur}</span><span class="impression">{valeur}</span>'


def ajouter(rubrique, titre, contenu, classe="", sombre=False):
    numero = len(slides) + 1
    couleur = "sombre" if sombre else "claire"
    slides.append(
        f'<section class="slide {couleur} {classe}" aria-labelledby="titre-{numero}">'
        f'<header><span>PROJET LÉGI</span><span>{rubrique}</span></header>'
        f'<h1 id="titre-{numero}">{titre}</h1><div class="contenu">{contenu}</div>'
        f'<footer><span>MCP / Des faits, pas un verdict.</span><span>{numero:02}</span></footer></section>'
    )


def bloc(classe, titre, sous_titre, detail, extra=""):
    return (
        f'<button type="button" class="bloc {classe}" data-explication="{escape(detail, quote=True)}" aria-controls="explication-flux">'
        f"<b>{titre}</b><span>{sous_titre}</span>{extra}</button>"
    )


def fleche(classe, chemins, etiquette="", vue="0 0 40 20"):
    texte = f"<small>{etiquette}</small>" if etiquette else ""
    return (
        f'<div class="fleche {classe}"><svg viewBox="{vue}" preserveAspectRatio="none" aria-hidden="true">'
        f'<path class="liaison" d="{chemins}"/><path class="paquets" d="{chemins}"/></svg>{texte}</div>'
    )


ajouter("01 / LE POINT DE DÉPART", '<span>Le droit.</span><span>Des sources.</span><em>Pas des suppositions.</em>', '<p class="signature">Projet Légi — repérer, sourcer, vérifier.</p>', "couverture", sombre=True)
flux = '<div class="flux">'
flux += bloc("navigateur", "Navigateur", "page web + code d’accès",
             "Navigateur — l’utilisateur pose une question, donne une URL ou une entreprise. En ligne, un code d’accès protège le service.")
flux += fleche("f-question", "M0 10H40", "question")
flux += '<div class="pile">'
flux += bloc("groq", "IA Groq", "gpt-oss-120b · secours 20b",
             "IA Groq — choisit l’outil à appeler puis rédige la réponse. Elle ne voit aucune clé et ne touche jamais directement aux API.")
flux += fleche("f-groq", "M14 0V20M26 20V0", vue="0 0 40 20")
flux += bloc("app", "Application FastAPI", "app/main.py — orchestration",
             "Application FastAPI — borne la discussion : 3 tours, 6 appels d’outils, 50 s en ligne et 180 s en local. rapport.py valide les sources citées, tableau_de_bord.py calcule le score.",
             '<i>3 tours · 6 appels d’outils max</i><i>rapport.py : valide les sources</i><i>tableau_de_bord.py : score</i><i>50 s en ligne · 180 s en local</i>')
flux += fleche("f-supabase", "M20 0V20", vue="0 0 40 20")
flux += bloc("supabase", "Supabase", "historique (optionnel)",
             "Supabase — conserve l’historique des analyses. Optionnel : l’application fonctionne sans.")
flux += "</div>"
flux += fleche("f-session", "M0 10H40", "session MCP<br>stdio / mémoire")
flux += '<div class="mcp">'
flux += bloc("entete", "Serveur MCP — server.py", "FastMCP(&quot;projet-legi&quot;) · 4 outils",
             "Serveur MCP — expose quatre outils par un protocole standard. Session en stdio en local, en mémoire en ligne. C’est lui qui lit les sources, jamais l’IA.")
flux += '<div class="outils-mcp">'
for classe, titre, sous_titre, detail in [
    ("outil-mcp", "rechercher_textes_loi", "Légifrance", "rechercher_textes_loi — trouve codes et lois sur Légifrance : titre, référence et extrait officiel."),
    ("outil-mcp", "consulter_article", "Légifrance", "consulter_article — lit un article précis de Légifrance, avec son texte et sa version en vigueur."),
    ("outil-mcp", "verifier_entreprise", "registre", "verifier_entreprise — identité publique d’une entreprise par nom ou SIREN, sans données sur les dirigeants."),
    ("outil-mcp coeur", "analyser_site", "cœur du projet", "analyser_site — lit la page d’accueil et les pages légales d’un site, puis applique les règles de conformité."),
]:
    flux += bloc(classe, titre, sous_titre, detail)
flux += "</div>"
flux += bloc("moteur", "regles/obligations.json + moteur.py", f"{len(obligations)} obligations → conforme / manquant / à vérifier",
             f"Moteur de règles — {len(obligations)} obligations fixes, chacune avec un statut et une preuve. L’IA ne peut pas réécrire ces statuts.")
flux += "</div>"
flux += fleche("f-sources", "M0 50L40 15M0 50H40M0 50L40 85", vue="0 0 40 100")
flux += '<div class="sources">'
flux += bloc("source", "Légifrance — API PISTE", "OAuth2 client_credentials · Sandbox",
             "Légifrance (API PISTE) — authentification OAuth2 client_credentials en sandbox. Le jeton est mis en cache et renouvelé 30 s avant expiration.",
             "<i>jeton en cache, renouvelé 30 s avant</i>")
flux += bloc("source", "Recherche d’entreprises", "recherche-entreprises.api.gouv.fr",
             "Recherche d’entreprises — API publique de l’État, gratuite et sans clé.",
             "<i>gratuite, sans clé</i>")
flux += bloc("source", "Le site web analysé", "HTML initial · 6 pages max",
             "Site analysé — HTML initial uniquement, 6 pages maximum. Protection anti-SSRF, 2 Mo par page, 5 redirections au plus.",
             "<i>anti-SSRF · 2 Mo · 5 redirections</i>")
flux += "</div></div>"
flux += '<p id="explication-flux" class="explication" aria-live="polite">Survolez ou sélectionnez un bloc pour découvrir son rôle.</p>'
ajouter("02 / LE PRINCIPE", "L’IA choisit. <em>Le code vérifie.</em>", flux, "architecture")
parcours = '<ol class="etapes"><li><b>01</b>Question</li><li><b>02</b>Choix d’outils</li><li><b>03</b>Lecture réelle</li><li><b>04</b>Rapport sourcé</li></ol><div class="quatre outils">'
for titre, sous_titre, detail, symbole in [
    ("rechercher_textes_loi", "Repérer", "Codes ou lois : titre, référence et extrait officiel.", "recherche"),
    ("consulter_article", "Lire", "Un article précis, avec son texte et sa version.", "article"),
    ("verifier_entreprise", "Identifier", "Identité publique par nom ou SIREN, sans dirigeants.", "entreprise"),
    ("analyser_site", "Observer", "HTML initial et liens légaux ; six pages maximum.", "site"),
]:
    parcours += f'<article class="outil"><button type="button" aria-expanded="false" aria-controls="detail-{titre}">{icone(symbole)}<span>{titre}</span><small>{sous_titre} <span aria-hidden="true">+</span></small></button><p class="detail" id="detail-{titre}">{detail}</p></article>'
parcours += '</div><p class="aide">Sélectionnez un outil pour en savoir plus.</p>'
ajouter("03 / LE PARCOURS", 'Une question.<br>Quatre outils.', parcours, "parcours", sombre=True)
ordre = ["Mentions légales", "Données personnelles", "Cookies et traceurs", "Commerce électronique", "Sécurité"]
analyse = '<div class="themes">' + "".join(f'<div><strong aria-label="{themes[theme]}">{nombre(themes[theme])}</strong><span>{escape(theme)}</span></div>' for theme in ordre) + '</div><div class="chips" aria-label="Statuts">'
for statut, classe, detail in [
    ("Conforme", "ok", "Élément détecté, avec une preuve. Ce n’est pas une validation juridique."),
    ("Manquant", "ko", "Élément non trouvé dans les pages réellement lues."),
    ("À vérifier", "av", "Page illisible, absente ou preuve insuffisante : contrôle manuel nécessaire."),
    ("Non applicable", "na", "Contexte non établi, par exemple aucun indice de vente : exclu du score."),
]:
    analyse += f'<button type="button" class="chip {classe}" data-sens="{escape(detail, quote=True)}" aria-pressed="false" aria-controls="sens-statut">{statut}</button>'
analyse += '</div><p id="sens-statut" class="explication" aria-live="polite">Chaque point reçoit un statut et une preuve.</p>'
ajouter("04 / ANALYSER UN SITE", f'<em>{len(obligations)}</em> obligations.<br>Cinq thèmes.', analyse, "analyse")
score = '<div class="score"><div class="jauge score-92"><svg viewBox="0 0 240 240" aria-hidden="true"><circle class="piste" cx="120" cy="120" r="100"/><circle class="valeur" cx="120" cy="120" r="100" pathLength="100"/></svg><strong aria-label="92 sur 100"><span id="nombre-score" class="compte" data-final="92" aria-hidden="true">92</span><span class="impression">92</span><small>/100</small></strong></div><div><p class="formule">100 × points obtenus<br>÷ points possibles</p><p class="note">Critique 3 · avertissement 2 · info 1</p><p class="note">Non applicables exclus</p><div class="choix" aria-label="Exemple observé"><button type="button" data-score="92" aria-pressed="true">service-public.fr · 92</button><button type="button" data-score="7" aria-pressed="false">example.com · 7</button></div><p class="aide">Exemples observés, pas des certifications.</p></div></div>'
ajouter("05 / L’INDICE", 'Un indice.<br><em>Pas un verdict.</em>', score, "indice", sombre=True)
confiance = '<div class="quatre protections">'
for titre, detail, symbole in [
    ("Sources vérifiées", "Pas de référence inventée.", "source"),
    ("Accès publics", "Destinations privées bloquées.", "bouclier"),
    ("Données limitées", "E-mails et téléphones masqués.", "donnees"),
    ("Règles fixes", "Statuts non réécrits par l’IA.", "regles"),
]:
    confiance += f'<div>{icone(symbole)}<h2>{titre}</h2><p>{detail}</p></div>'
confiance += '</div><div class="resultats"><div><strong aria-label="281">' + nombre(281) + '</strong><span>tests automatisés · API simulées</span></div><div><strong aria-label="7 sur 7">' + nombre(7) + '<small>/7</small></strong><span>injections déjouées lors des essais</span></div></div><div class="modes"><div class="choix" aria-label="Mode MCP"><button type="button" data-mode="local" aria-pressed="true">Local</button><button type="button" data-mode="ligne" aria-pressed="false">En ligne</button></div><p id="mode-detail" aria-live="polite">MCP en stdio · clés dans .env</p><p class="impression">Local : MCP en stdio · clés dans .env<br>En ligne : MCP en mémoire · code d’accès requis</p></div>'
ajouter("06 / LA CONFIANCE", 'Des garde-fous.<br>Des essais.', confiance, "confiance")
limites = '<ol class="limites"><li>Pas un avis juridique</li><li>HTML initial, sans JavaScript</li><li>Six pages maximum</li><li>Règles et mots-clés imparfaits</li><li>Certains sites bloquent la lecture</li><li>Quotas Groq et délais bornés</li></ol><div class="liens"><a href="https://github.com/ccochod-source/projet-legi">github.com/ccochod-source/projet-legi</a><a href="https://projet-legi.vercel.app">projet-legi.vercel.app</a></div>'
ajouter("07 / LIMITES & PERSPECTIVE", 'Mieux repérer.<br><em>Vérifier ensemble.</em>', limites, "conclusion", sombre=True)

document = '''<!doctype html>
<html lang="fr"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Projet Légi — Présentation MCP</title>
<link rel="stylesheet" href="/static/slides.css">
<script src="/static/slides.js" defer></script></head>
<body class="presentation"><main class="cadre" aria-label="Présentation MCP">
<progress id="progression" max="7" value="1" aria-label="Progression de la présentation"></progress>'''
document += "\n".join(slides)
document += '''</main><nav class="commandes" aria-label="Navigation des diapositives">
<button id="precedent" type="button" aria-label="Diapositive précédente">←</button>
<output id="compteur" aria-live="polite"></output>
<button id="suivant" type="button" aria-label="Diapositive suivante">→</button>
<button id="plein-ecran" type="button">Plein écran</button>
<a href="/static/slides_mcp.pdf" download>Télécharger le PDF</a>
<a href="/schema">Poster</a></nav></body></html>'''
(RACINE / "app/static/slides.html").write_text(document)
print(f"{len(slides)} diapositives générées.")
