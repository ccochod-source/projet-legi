"use strict";

const diapositives = Array.from(document.querySelectorAll(".slide"));
const precedent = document.getElementById("precedent");
const suivant = document.getElementById("suivant");
const compteur = document.getElementById("compteur");
const pleinEcran = document.getElementById("plein-ecran");
const progression = document.getElementById("progression");
let position = 0;
const mouvementReduit = window.matchMedia("(prefers-reduced-motion: reduce)");
const animations = new Map();

function compter(element) {
  cancelAnimationFrame(animations.get(element));
  const cible = Number(element.dataset.final);
  if (mouvementReduit.matches) {
    element.textContent = String(cible);
    return;
  }
  const debut = performance.now();
  element.textContent = "0";
  function avancer(instant) {
    const fraction = Math.min(1, (instant - debut) / 1300);
    element.textContent = String(Math.round(cible * (1 - Math.pow(1 - fraction, 3))));
    if (fraction < 1) animations.set(element, requestAnimationFrame(avancer));
    else animations.delete(element);
  }
  animations.set(element, requestAnimationFrame(avancer));
}

function animerJauge() {
  const jauge = document.querySelector(".jauge");
  jauge.classList.remove("animer");
  void jauge.offsetWidth;
  jauge.classList.add("animer");
}

function animerSlide(slide) {
  slide.querySelectorAll(".compte").forEach(compter);
  if (slide.querySelector(".jauge")) animerJauge();
}

function afficher() {
  const valeur = Number(location.hash.slice(1));
  position = Number.isInteger(valeur) && valeur >= 1 && valeur <= diapositives.length ? valeur - 1 : 0;
  diapositives.forEach((slide, index) => {
    const etaitActive = slide.classList.contains("active");
    slide.classList.toggle("active", index === position);
    slide.setAttribute("aria-hidden", String(index !== position));
    if (index === position && !etaitActive) animerSlide(slide);
    if (index !== position) {
      slide.querySelectorAll(".compte").forEach((element) => {
        cancelAnimationFrame(animations.get(element));
        animations.delete(element);
      });
    }
  });
  compteur.textContent = `${position + 1} / ${diapositives.length}`;
  progression.max = diapositives.length;
  progression.value = position + 1;
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
document.querySelectorAll(".bloc").forEach((bloc) => {
  function expliquer() {
    document.getElementById("explication-flux").textContent = bloc.dataset.explication;
  }
  bloc.addEventListener("pointerenter", expliquer);
  bloc.addEventListener("focus", expliquer);
  bloc.addEventListener("click", expliquer);
});

document.querySelectorAll(".outil button").forEach((bouton) => {
  bouton.addEventListener("click", () => {
    const ouvert = bouton.getAttribute("aria-expanded") !== "true";
    bouton.setAttribute("aria-expanded", String(ouvert));
    bouton.closest(".outil").classList.toggle("ouverte", ouvert);
  });
});

document.querySelectorAll("[data-sens]").forEach((bouton) => {
  bouton.addEventListener("click", () => {
    document.querySelectorAll("[data-sens]").forEach((autre) => autre.setAttribute("aria-pressed", String(autre === bouton)));
    document.getElementById("sens-statut").textContent = bouton.dataset.sens;
  });
});

document.querySelectorAll("[data-score]").forEach((bouton) => {
  bouton.addEventListener("click", () => {
    const score = bouton.dataset.score;
    const nombre = document.getElementById("nombre-score");
    document.querySelectorAll("[data-score]").forEach((autre) => autre.setAttribute("aria-pressed", String(autre === bouton)));
    nombre.dataset.final = score;
    nombre.parentElement.setAttribute("aria-label", `${score} sur 100`);
    const jauge = document.querySelector(".jauge");
    jauge.classList.toggle("score-7", score === "7");
    jauge.classList.toggle("score-92", score === "92");
    compter(nombre);
    animerJauge();
  });
});

document.querySelectorAll("[data-mode]").forEach((bouton) => {
  bouton.addEventListener("click", () => {
    document.querySelectorAll("[data-mode]").forEach((autre) => autre.setAttribute("aria-pressed", String(autre === bouton)));
    document.getElementById("mode-detail").textContent = bouton.dataset.mode === "local" ? "MCP en stdio · clés dans .env" : "MCP en mémoire · code d’accès requis";
  });
});

mouvementReduit.addEventListener("change", () => animerSlide(diapositives[position]));
afficher();
