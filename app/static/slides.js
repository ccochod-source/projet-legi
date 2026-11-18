"use strict";

const diapositives = Array.from(document.querySelectorAll(".slide"));
const precedent = document.getElementById("precedent");
const suivant = document.getElementById("suivant");
const compteur = document.getElementById("compteur");
const pleinEcran = document.getElementById("plein-ecran");
let position = 0;

function afficher() {
  const valeur = Number(location.hash.slice(1));
  position = Number.isInteger(valeur) && valeur >= 1 && valeur <= diapositives.length ? valeur - 1 : 0;
  diapositives.forEach((slide, index) => {
    slide.classList.toggle("active", index === position);
    slide.setAttribute("aria-hidden", String(index !== position));
  });
  compteur.textContent = `${position + 1} / ${diapositives.length}`;
  precedent.disabled = position === 0;
  suivant.disabled = position === diapositives.length - 1;
}

function aller(index) {
  location.hash = String(Math.max(0, Math.min(diapositives.length - 1, index)) + 1);
  afficher();
}

async function basculerPleinEcran() {
  try {
    if (document.fullscreenElement) await document.exitFullscreen();
    else if (document.documentElement.requestFullscreen) await document.documentElement.requestFullscreen();
  } catch {
    pleinEcran.textContent = "Plein écran indisponible";
  }
}

precedent.addEventListener("click", () => aller(position - 1));
suivant.addEventListener("click", () => aller(position + 1));
pleinEcran.addEventListener("click", basculerPleinEcran);
window.addEventListener("hashchange", afficher);
document.addEventListener("keydown", (event) => {
  if (event.altKey || event.ctrlKey || event.metaKey || event.target.closest("input, textarea, select, [contenteditable]")) return;
  if (event.key === " " && event.target.closest("button, a")) return;
  const destinations = {ArrowLeft: position - 1, PageUp: position - 1, ArrowRight: position + 1, PageDown: position + 1, " ": position + 1, Home: 0, End: diapositives.length - 1};
  if (Object.hasOwn(destinations, event.key)) {
    event.preventDefault();
    aller(destinations[event.key]);
  } else if (event.key.toLowerCase() === "f") {
    event.preventDefault();
    basculerPleinEcran();
  }
});
afficher();
