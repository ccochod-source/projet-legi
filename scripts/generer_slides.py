"""Génère la présentation statique à partir du poster MCP."""

from pathlib import Path

from bs4 import BeautifulSoup


RACINE = Path(__file__).resolve().parents[1]
source = BeautifulSoup((RACINE / "app/static/schema.html").read_text(), "html.parser")
sections = []
for titre in source.select("h2"):
    contenu = []
    for noeud in titre.next_siblings:
        if getattr(noeud, "name", None) == "h2":
            break
        if getattr(noeud, "name", None):
            contenu.append(noeud)
    sections.append(contenu)

slides = []


def ajouter(titre, contenu, classe=""):
    numero = len(slides) + 1
    slides.append(
        f'<section class="slide {classe}" aria-labelledby="titre-{numero}">'
        f'<h1 id="titre-{numero}">{titre}</h1><div class="contenu">{contenu}</div>'
        f'<footer>Projet Légi · MCP <span>{numero}</span></footer></section>'
    )


ajouter("Projet Légi — comment marche le MCP", str(source.select_one(".sub")) + str(source.select_one(".phrase")), "titre")
for index, (titre, cadrage) in enumerate([
    ("Architecture · navigateur et orchestration", "0 0 780 430"),
    ("Architecture · serveur MCP et sources", "750 0 910 430"),
]):
    svg = BeautifulSoup(str(sections[0][0]), "html.parser")
    svg.svg["viewbox"] = cadrage
    for noeud in list(svg.svg.find_all(recursive=False)):
        if noeud.name == "defs":
            continue
        x = float(noeud.get("x", noeud.get("x1", "0")))
        if (index == 0 and x >= 750) or (index == 1 and x < 750):
            noeud.decompose()
    for identifiant in ("a", "b"):
        svg.find(id=identifiant)["id"] = f"fleche-{index}-{identifiant}"
        for ligne in svg.select(f'[marker-end="url(#{identifiant})"]'):
            ligne["marker-end"] = f"url(#fleche-{index}-{identifiant})"
    ajouter(titre, str(svg), "diagramme")
ajouter("Déroulé d’une question", str(sections[1][0]), "etapes")
outils = sections[2][0].find_all("div", recursive=False)
for i, titre in enumerate(["Les outils · rechercher et consulter", "Les outils · identifier et analyser"]):
    ajouter(titre, '<div class="grid g2">' + "".join(map(str, outils[i * 2:i * 2 + 2])) + "</div>" + str(sections[2][1]))
obligations = sections[3][0].find_all("div", recursive=False)
ajouter("Les 21 obligations", str(obligations[0]), "obligations")
ajouter("Un statut et une preuve pour chaque point", str(obligations[1]), "statuts")
ajouter("Le tableau de bord · l’indice /100", str(sections[4][0]), "indice")
gardes = sections[5][0].find_all("div", recursive=False)
for i, titre in enumerate(["Garde-fous · sources et lecture", "Garde-fous · données et robustesse"]):
    ajouter(titre, '<div class="grid g2">' + "".join(map(str, gardes[i * 2:i * 2 + 2])) + "</div>")
ajouter("Deux modes, mêmes outils", str(sections[6][0]))
ajouter("Tests et essais réels", str(sections[7][0]))
limites = sections[8][0].find_all("div", recursive=False)
for i in range(2):
    ajouter(f"Les limites à assumer · {i + 1}/2", '<div class="lim">' + "".join(map(str, limites[i * 6:i * 6 + 6])) + "</div>")
ajouter("Des faits sourcés, pas un verdict juridique", str(source.select_one(".phrase")) + '<p><a href="https://github.com/ccochod-source/projet-legi">github.com/ccochod-source/projet-legi</a></p><p><a href="https://projet-legi.vercel.app">projet-legi.vercel.app</a></p>', "titre")

document = '''<!doctype html>
<html lang="fr"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Projet Légi — Présentation MCP</title>
<link rel="stylesheet" href="/static/schema.css">
<link rel="stylesheet" href="/static/slides.css">
<script src="/static/slides.js" defer></script></head>
<body class="presentation"><main class="cadre" aria-label="Présentation MCP">'''
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
