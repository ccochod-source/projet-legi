"""Génère la synthèse de présentation du poster MCP et des règles du projet."""

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


def tuile(titre, texte, symbole):
    return f'<div class="tuile">{icone(symbole)}<h2>{titre}</h2><p>{texte}</p></div>'


def ajouter(rubrique, titre, contenu, classe="", sombre=False):
    numero = len(slides) + 1
    couleur = "sombre" if sombre else "claire"
    slides.append(
        f'<section class="slide {couleur} {classe}" aria-labelledby="titre-{numero}">'
        f'<header><span>PROJET LÉGI</span><span>{rubrique}</span></header>'
        f'<h1 id="titre-{numero}">{titre}</h1><div class="contenu">{contenu}</div>'
        f'<footer><span>MCP / Des faits, pas un verdict.</span><span>{numero:02}</span></footer></section>'
    )


ajouter("01 / INTRODUCTION", 'Le droit.<br>Des sources.<br><em>Pas des suppositions.</em>', '<p class="signature">Projet Légi — comprendre le rôle du MCP.</p>', "couverture", sombre=True)
ajouter("02 / LE PROBLÈME", 'Une URL.<br>Que faut-il vérifier ?', '<div class="trois mots"><p>Identifier<br><span>l’éditeur</span></p><p>Repérer<br><span>les obligations</span></p><p>Retrouver<br><span>les sources</span></p></div>')
ajouter("03 / LE PRINCIPE", 'L’IA choisit.<br><em>Le code vérifie.</em>', '<p class="signature">Les faits viennent des outils. Chaque affirmation doit être sourcée.</p>', "manifeste", sombre=True)
ajouter("04 / ARCHITECTURE", 'Quatre blocs.<br>Des rôles clairs.', '<div class="groq">Groq <span>propose les appels à l’application</span></div><div class="chaine"><div>Navigateur</div><span>→</span><div>App</div><span>→</span><div>MCP</div><span>→</span><div>API officielles</div></div><p class="note">MCP lit aussi le site public analysé.</p>', "architecture")
ajouter("05 / LE PARCOURS", 'De la question<br>aux preuves.', '<ol class="etapes"><li><b>01</b>Question</li><li><b>02</b>Choix d’outils</li><li><b>03</b>Lecture réelle</li><li><b>04</b>Rapport sourcé</li></ol>', sombre=True)
ajouter("06 / LA BOÎTE À OUTILS", 'Quatre outils.<br>Pas de magie.', '<div class="deux outils">' + tuile("rechercher_textes_loi", "Repérer un texte officiel.", "recherche") + tuile("consulter_article", "Lire un article précis.", "article") + tuile("verifier_entreprise", "Retrouver une identité publique.", "entreprise") + tuile("analyser_site", "Observer les pages et appliquer les règles.", "site") + '</div>')
ajouter("07 / ZOOM SUR LE SITE", 'Lire. Détecter.<br><em>Documenter.</em>', '<div class="zoom"><div><strong>6</strong><span>pages maximum</span></div><ul><li>HTML réellement reçu</li><li>Liens légaux suivis</li><li>Preuves et sources conservées</li></ul></div>', sombre=True)
ordre = ["Mentions légales", "Données personnelles", "Cookies et traceurs", "Commerce électronique", "Sécurité"]
ajouter("08 / LE PÉRIMÈTRE", f'<em>{len(obligations)}</em> obligations.<br>Cinq thèmes.', '<div class="themes">' + "".join(f'<div><strong>{themes[theme]}</strong><span>{escape(theme)}</span></div>' for theme in ordre) + '</div>')
ajouter("09 / LES STATUTS", 'Nuancer.<br>Toujours.', '<div class="deux statuts"><div class="ok"><h2>Conforme</h2><p>Élément détecté.</p></div><div class="ko"><h2>Manquant</h2><p>Absent des pages lues.</p></div><div class="av"><h2>À vérifier</h2><p>Preuve insuffisante.</p></div><div class="na"><h2>Non applicable</h2><p>Contexte non établi.</p></div></div>', sombre=True)
ajouter("10 / L’INDICE", 'Un indice.<br>Pas un verdict.', '<div class="score"><div class="jauge"><svg viewBox="0 0 240 240" aria-label="92 sur 100"><circle class="piste" cx="120" cy="120" r="100"/><circle class="valeur" cx="120" cy="120" r="100" pathLength="100" stroke-dasharray="92 100"/></svg><strong>92<span>/100</span></strong></div><div><p class="formule">100 × poids conformes<br>÷ poids applicables</p><p class="note">Service-public.fr · exemple observé</p><p class="note">Non applicables exclus · poids 3 / 2 / 1</p></div></div>', "indice")
ajouter("11 / LES GARDE-FOUS", 'La confiance<br>se construit.', '<div class="quatre">' + tuile("Sources vérifiées", "Pas de référence inventée.", "source") + tuile("Accès publics", "Destinations privées bloquées.", "bouclier") + tuile("Données limitées", "E-mails et téléphones masqués.", "donnees") + tuile("Règles fixes", "Statuts non réécrits par l’IA.", "regles") + '</div>', sombre=True)
ajouter("12 / DEUX MODES", 'Même MCP.<br>Deux terrains.', '<div class="deux modes"><div><span class="sur-titre">SUR VOTRE MACHINE</span><h2>Local</h2><p>MCP en stdio<br>Clés dans .env</p></div><div><span class="sur-titre">SUR VERCEL</span><h2>En ligne</h2><p>MCP en mémoire<br>Code d’accès requis</p></div></div>')
ajouter("13 / LES ESSAIS", 'Des résultats.<br><em>Des limites aussi.</em>', '<div class="trois resultats"><div><strong>281</strong><span>tests automatisés</span></div><div><strong>7/7</strong><span>injections déjouées</span></div><div><strong>92 <i>/</i> 7</strong><span>indices observés /100</span></div></div><p class="note">API simulées · essais d’injection · service-public.fr / example.com</p>', sombre=True)
ajouter("14 / LES LIMITES", 'Savoir ce que<br>l’on ne sait pas.', '<ol class="limites"><li>Pas un avis juridique</li><li>HTML initial, sans JavaScript</li><li>Six pages maximum</li><li>Règles et mots-clés imparfaits</li><li>Certains sites bloquent la lecture</li><li>Quotas Groq et délais bornés</li></ol>')
ajouter("15 / À RETENIR", 'Mieux repérer.<br><em>Vérifier ensemble.</em>', '<p class="signature">Un outil préparatoire, jamais une certification.</p><div class="liens"><a href="https://github.com/ccochod-source/projet-legi">github.com/ccochod-source/projet-legi</a><a href="https://projet-legi.vercel.app">projet-legi.vercel.app</a></div>', "conclusion", sombre=True)

document = '''<!doctype html>
<html lang="fr"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Projet Légi — Présentation MCP</title>
<link rel="stylesheet" href="/static/slides.css">
<script src="/static/slides.js" defer></script></head>
<body class="presentation"><main class="cadre" aria-label="Présentation MCP">
<progress id="progression" max="15" value="1" aria-label="Progression de la présentation"></progress>'''
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
