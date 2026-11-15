#!/bin/bash
# Lancement local pour macOS. Aucun secret n'est affiché dans le Terminal.
set -euo pipefail
cd "$(dirname "$0")"
umask 077

PYTHON=""
for candidat in python3 python3.12 python3.11 python3.10; do
  if command -v "$candidat" >/dev/null 2>&1 && "$candidat" -c 'import sys; sys.exit(sys.version_info < (3, 10))' 2>/dev/null; then
    PYTHON="$candidat"
    break
  fi
done
if [ -z "$PYTHON" ]; then
  echo "Python 3.10 ou plus récent est nécessaire."
  echo "Installez Python depuis https://www.python.org/downloads/macos/"
  echo "ou avec Homebrew : brew install python@3.12"
  echo "Puis relancez : bash lancer.sh"
  exit 1
fi

if [ ! -d .venv ]; then
  echo "Création de l'environnement Python…"
  "$PYTHON" -m venv .venv
fi
if ! .venv/bin/python -c 'import sys; sys.exit(sys.version_info < (3, 10))' 2>/dev/null; then
  echo "L'environnement .venv est incompatible. Renommez ce dossier puis relancez lancer.sh."
  exit 1
fi
echo "Installation des dépendances (Internet nécessaire au premier lancement)…"
if ! .venv/bin/python -m pip install --quiet -r requirements.txt; then
  echo "Installation impossible. Vérifiez votre connexion Internet puis relancez lancer.sh."
  exit 1
fi
if [ ! -f .env ]; then
  cp .env.example .env
fi
chmod 600 .env

# python-dotenv conserve les variables existantes, même vides : retirons
# seulement les valeurs absentes ou d'exemple pour laisser .env prendre effet.
for nom in GROQ_API_KEY LEGIFRANCE_CLIENT_ID LEGIFRANCE_CLIENT_SECRET; do
  valeur="${!nom-}"
  valeur="${valeur//[[:space:]]/}"
  case "$valeur" in
    ""|votre_cle|votre_identifiant|votre_secret) unset "$nom" ;;
  esac
done
unset valeur nom

.venv/bin/python - <<'PY'
"""Demande les clés manquantes sans les afficher ni les passer en arguments."""
import getpass
import os
from pathlib import Path
from dotenv import dotenv_values, set_key

fichier = Path('.env')
valeurs = dotenv_values(fichier)
exemples = {'', 'votre_cle', 'votre_identifiant', 'votre_secret'}
cles = [
    ('GROQ_API_KEY', 'Clé Groq gratuite (https://console.groq.com/keys)', True),
    ('LEGIFRANCE_CLIENT_ID', 'Identifiant PISTE Légifrance (Entrée pour ignorer)', False),
    ('LEGIFRANCE_CLIENT_SECRET', 'Secret PISTE Légifrance (Entrée pour ignorer)', False),
]
for nom, libelle, obligatoire in cles:
    if (os.getenv(nom) or valeurs.get(nom) or '').strip() not in exemples:
        continue
    try:
        terminal = open('/dev/tty', 'w')
    except OSError:
        raise SystemExit('Clé manquante : ' + nom + '. Lancez ce script dans un Terminal interactif.')
    with terminal:
        valeur = getpass.getpass(libelle + ' : ', stream=terminal).strip()
    if not valeur and obligatoire:
        raise SystemExit('Clé Groq nécessaire. Créez-la gratuitement puis relancez lancer.sh.')
    set_key(str(fichier), nom, valeur)
print('Configuration prête. Les clés restent dans .env, à ne jamais partager.')
PY

# Un délai bref laisse à Uvicorn le temps de démarrer avant d'ouvrir le navigateur.
if [ "$(uname -s)" = "Darwin" ]; then
  (sleep 2; open "http://127.0.0.1:8001") &
fi
echo "Application : http://127.0.0.1:8001 — gardez ce Terminal ouvert. Arrêt : Ctrl+C."
exec .venv/bin/python -m app.main
