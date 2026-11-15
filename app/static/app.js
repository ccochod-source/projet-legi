/* Le rapport utilise textContent : aucun HTML produit par l'IA n'est exécuté. */
const element = (identifiant) => document.getElementById(identifiant);
let markdown = "";

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
    const reponse = await fetch("/api/chat", {
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

fetch("/api/etat")
  .then((reponse) => reponse.json())
  .then((etat) => {
    element("configuration").textContent = etat.groq_configure
      ? "Groq configuré · " + etat.modele
      : "Clé Groq manquante : relancez lancer.sh pour la renseigner.";
  })
  .catch(() => {
    element("configuration").textContent =
      "Application indisponible. Relancez lancer.sh.";
  });
