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


ajouter("01 / LE POINT DE DÉPART", '<span>Le droit.</span><span>Des sources.</span><em>Pas des suppositions.</em>', '<p class="signature">Projet Légi — repérer, sourcer, vérifier.</p>', "couverture", sombre=True)
blocs = [
    ("Navigateur", "Une URL, une entreprise ou une question juridique."),
    ("App", "L’application contrôle les appels et construit le rapport."),
    ("MCP", "Quatre outils, un protocole. Le serveur lit les sources et applique les règles."),
    ("API officielles", "Légifrance, Recherche d’entreprises. MCP lit aussi le site public analysé."),
]
flux = '<div class="flux"><svg viewBox="0 0 1000 180" aria-hidden="true"><path class="liaison" d="M95 140H905M365 30V140"/><path class="paquets" d="M95 140H905M365 30V140"/></svg>'
flux += '<button class="bloc groq" data-explication="Groq propose les outils ; les faits viennent du MCP." aria-controls="explication-flux">Groq <span>propose les appels</span></button>'
for index, (titre, detail) in enumerate(blocs):
    flux += f'<button class="bloc bloc-{index}" data-explication="{escape(detail, quote=True)}" aria-controls="explication-flux">{titre}</button>'
flux += '</div><p id="explication-flux" class="explication" aria-live="polite">Survolez ou sélectionnez un bloc pour découvrir son rôle.</p><p class="impression">Sources : Légifrance, Recherche d’entreprises et site public analysé.</p>'
ajouter("02 / LE PRINCIPE", 'L’IA choisit.<br><em>Le code vérifie.</em>', flux, "architecture")
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
