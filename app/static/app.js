/* Le rapport utilise textContent : aucun HTML produit par l'IA n'est exécuté. */
const element = (identifiant) => document.getElementById(identifiant);
let markdown = "";

async function appelerApi(url, options = {}) {
  const envoyer = () => fetch(url, {
    ...options,
    headers: {
      ...options.headers,
      "X-Code-Acces": sessionStorage.getItem("code-acces") || "",
    },
  });
  let reponse = await envoyer();
  if (reponse.status === 401) {
    sessionStorage.removeItem("code-acces");
    const code = window.prompt("Code d'accès à projet-legi :");
    if (code) {
      sessionStorage.setItem("code-acces", code);
      reponse = await envoyer();
    }
    if (reponse.status === 401) {
      sessionStorage.removeItem("code-acces");
      throw new Error("Code d'accès absent ou incorrect. Rechargez la page pour réessayer.");
    }
  }
  return reponse;
}

function ajouterTexte(parent, balise, texte, classe = "") {
  const noeud = document.createElement(balise);
  noeud.textContent = texte;
  if (classe) noeud.className = classe;
  parent.append(noeud);
  return noeud;
}

function afficherOutils(appels = []) {
  element("outils").replaceChildren();
  element("journal").hidden = appels.length === 0;
  for (const appel of appels) {
    ajouterTexte(
      element("outils"),
      "li",
      `${appel.nom} — ${appel.statut === "ok" ? "terminé" : "erreur"}${appel.erreur ? " : " + appel.erreur : ""}`,
    );
  }
}

function afficherRapport(donnees) {
  element("tableau-de-bord").hidden = !donnees.tableau_de_bord;
  element("detail-rapport").open = !donnees.tableau_de_bord;
  if (donnees.tableau_de_bord) afficherTableauDeBord(donnees.tableau_de_bord);
  element("points").replaceChildren();
  for (const point of donnees.points) {
    const ligne = document.createElement("tr");
    ajouterTexte(ligne, "td", point.point);
    const celluleStatut = ajouterTexte(ligne, "td", "");
    ajouterTexte(celluleStatut, "span", point.statut, `statut ${point.statut}`);
    ajouterTexte(ligne, "td", point.preuve);
    const reference = ajouterTexte(ligne, "td", "");
    if (point.url && point.url.startsWith("https://")) {
      const lien = ajouterTexte(reference, "a", point.reference);
      lien.href = point.url;
      lien.target = "_blank";
      lien.rel = "noopener noreferrer";
    } else {
      reference.textContent = point.reference;
    }
    element("points").append(ligne);
  }
  element("manquantes").replaceChildren();
  for (const texte of donnees.informations_manquantes)
    ajouterTexte(element("manquantes"), "li", texte);
  markdown = donnees.reponse;
  element("rapport").hidden = false;
  element("telecharger").hidden = false;
}

function couleurScore(score) {
  return score === null ? "neutre" : score < 50 ? "rouge" : score < 80 ? "orange" : "vert";
}

function afficherTableauDeBord(donnees) {
  const racine = element("tableau-de-bord");
  racine.replaceChildren();
  const entete = ajouterTexte(racine, "div", "", "dashboard-entete");
  const jauge = ajouterTexte(entete, "div", "", "jauge " + couleurScore(donnees.score));
  const svg = document.createElementNS("http://www.w3.org/2000/svg", "svg");
  svg.setAttribute("viewBox", "0 0 120 120");
  svg.setAttribute("aria-hidden", "true");
  for (const classe of ["piste", "arc"]) {
    const cercle = document.createElementNS(svg.namespaceURI, "circle");
    for (const [cle, valeur] of Object.entries({cx: 60, cy: 60, r: 51, pathLength: 100, class: classe}))
      cercle.setAttribute(cle, valeur);
    if (classe === "arc") cercle.setAttribute("stroke-dasharray", `${donnees.score ?? 0} 100`);
    svg.append(cercle);
  }
  jauge.append(svg);
  ajouterTexte(jauge, "strong", donnees.score === null ? "—" : `${donnees.score}`, "score-valeur");
  const texte = ajouterTexte(entete, "div", "");
  ajouterTexte(texte, "p", "INDICE DE DÉTECTION / 100", "surtitre");
  ajouterTexte(texte, "h3", donnees.score === null ? "Aucun point évaluable" : `${donnees.score} / 100 éléments pondérés`);
  ajouterTexte(texte, "p", donnees.avertissement, "dashboard-avertissement");
  ajouterTexte(texte, "p", "Les points non applicables sont exclus du calcul : leur applicabilité reste à confirmer.", "aide");
  const themes = ajouterTexte(racine, "div", "", "dashboard-themes");
  for (const [theme, score] of Object.entries(donnees.sous_scores)) {
    const ligne = ajouterTexte(themes, "div", "", "theme-score " + couleurScore(score));
    ajouterTexte(ligne, "span", theme);
    ajouterTexte(ligne, "strong", score === null ? "Non évalué" : `${score} / 100`);
    const barre = document.createElement("progress");
    barre.max = 100;
    barre.value = score ?? 0;
    barre.setAttribute("aria-label", `${theme} : ${score === null ? "non évalué" : score + " sur 100"}`);
    ligne.append(barre);
  }
  const titres = {a_corriger: "À corriger", a_verifier: "À vérifier", conforme: "Conformes", non_applicable: "Non applicable"};
  const compteurs = ajouterTexte(racine, "div", "", "dashboard-compteurs");
  for (const [categorie, titre] of Object.entries(titres)) {
    const compteur = ajouterTexte(compteurs, "div", "", "compteur " + categorie);
    ajouterTexte(compteur, "strong", donnees.compteurs[categorie]);
    ajouterTexte(compteur, "span", titre);
  }
  const priorites = {critique: 0, avertissement: 1, information: 2};
  for (const [categorie, titre] of Object.entries(titres)) {
    const section = ajouterTexte(racine, categorie === "non_applicable" ? "details" : "section", "", "dashboard-section");
    ajouterTexte(section, categorie === "non_applicable" ? "summary" : "h3", `${titre} · ${donnees.compteurs[categorie]}`);
    if (categorie === "non_applicable") ajouterTexte(section, "p", "Applicabilité non établie automatiquement, à confirmer selon votre activité.", "aide");
    const points = donnees.points.filter(p => p.categorie === categorie).sort((a, b) => priorites[a.gravite] - priorites[b.gravite]);
    if (!points.length) ajouterTexte(section, "p", "Aucun point dans cette catégorie.", "aide");
    for (const point of points) {
      const carte = ajouterTexte(section, "article", "", "carte-point " + categorie);
      ajouterTexte(carte, "p", `${point.theme} · ${point.gravite}`, "carte-meta");
      ajouterTexte(carte, "h4", point.libelle);
      if (point.action) ajouterTexte(carte, "p", point.action, "carte-action");
      ajouterTexte(carte, "p", point.preuve, "carte-preuve");
      if (point.url && point.url.startsWith("https://")) {
        const lien = ajouterTexte(carte, "a", point.reference);
        lien.href = point.url;
        lien.target = "_blank";
        lien.rel = "noopener noreferrer";
      }
    }
  }
}

element("formulaire").addEventListener("submit", async (evenement) => {
  evenement.preventDefault();
  const message = element("demande").value.trim();
  if (message.length < 3) {
    element("erreur").textContent =
      "Décrivez votre demande en au moins trois caractères.";
    element("erreur").hidden = false;
    return;
  }
  element("analyser").disabled = true;
  element("rapport").hidden = true;
  element("telecharger").hidden = true;
  element("attente").hidden = true;
  element("erreur").hidden = true;
  element("progression").hidden = false;
  element("progression").textContent =
    "Vérification en cours… L’IA consulte les outils et leurs sources. Jusqu’à trois minutes peuvent être nécessaires.";
  element("zone-resultat").setAttribute("aria-busy", "true");
  afficherOutils();
  markdown = "";
  try {
    const reponse = await appelerApi("/api/chat", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ message }),
    });
    const donnees = await reponse.json();
    afficherOutils(donnees.outils_appeles);
    if (!reponse.ok || donnees.statut !== "ok") {
      throw new Error(
        donnees.erreur ||
          "Demande refusée. Vérifiez la longueur de votre texte et réessayez.",
      );
    }
    afficherRapport(donnees);
    element("progression").textContent =
      "Rapport prêt. Les points non documentés restent à vérifier.";
  } catch (erreur) {
    element("erreur").textContent =
      erreur instanceof TypeError
        ? "Connexion à l’application locale perdue. Vérifiez que lancer.sh fonctionne encore."
        : erreur.message;
    element("erreur").hidden = false;
    element("progression").hidden = true;
  } finally {
    element("analyser").disabled = false;
    element("zone-resultat").setAttribute("aria-busy", "false");
  }
});

element("telecharger").addEventListener("click", () => {
  const adresse = URL.createObjectURL(
    new Blob([markdown], { type: "text/markdown;charset=utf-8" }),
  );
  const lien = document.createElement("a");
  lien.href = adresse;
  lien.download = "rapport-legi.md";
  lien.click();
  setTimeout(() => URL.revokeObjectURL(adresse), 1000);
});

appelerApi("/api/etat")
  .then((reponse) => reponse.json())
  .then((etat) => {
    element("configuration").textContent = etat.groq_configure
      ? "Groq configuré · " + etat.modele
      : "Clé Groq manquante : relancez lancer.sh pour la renseigner.";
  })
  .catch((erreur) => {
    element("configuration").textContent =
      erreur.message || "Application indisponible. Relancez lancer.sh.";
  });
