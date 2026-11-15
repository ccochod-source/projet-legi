#!/bin/bash
# Archive les fichiers de rendu, jamais les clés ni l'environnement.
set -euo pipefail
cd "$(dirname "$0")/.."
PYTHON=""
for candidat in .venv/bin/python python3 python3.12 python3.11 python3.10; do
  if command -v "$candidat" >/dev/null 2>&1 && "$candidat" -c 'import sys; sys.exit(sys.version_info < (3, 10))' 2>/dev/null; then
    PYTHON="$candidat"
    break
  fi
done
if [ -z "$PYTHON" ]; then
  echo "Python 3.10 ou plus récent est nécessaire pour créer le ZIP."
  exit 1
fi
"$PYTHON" - <<'PY'
"""Construit une archive portable, sans suivre de liens symboliques."""
from datetime import datetime
from pathlib import Path
from zipfile import ZipFile, ZIP_DEFLATED

racine = Path.cwd()
destination = racine / ('projet-legi-rendu-' + datetime.now().strftime('%Y%m%d-%H%M%S-%f') + '.zip')
exclus = {'.venv', 'venv', '__pycache__', '.pytest_cache', '.git', '.mypy_cache', '.ruff_cache', 'node_modules', '.idea', '.vscode', '.devin', '.DS_Store'}

def fichiers(dossier):
    for chemin in sorted(dossier.iterdir()):
        if chemin.is_symlink() or chemin.name in exclus:
            continue
        if chemin.name.startswith('.env') and chemin.name != '.env.example':
            continue
        if chemin.is_dir():
            yield from fichiers(chemin)
        elif chemin.suffix.lower() not in {'.zip', '.pyc', '.pyo', '.log', '.pem', '.key'}:
            yield chemin

with ZipFile(destination, 'w', compression=ZIP_DEFLATED) as archive:
    for chemin in fichiers(racine):
        archive.write(chemin, 'projet-legi/' + chemin.relative_to(racine).as_posix())
print('Archive créée : ' + destination.name)
PY
