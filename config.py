"""Configuration partagée ; aucune valeur secrète ne doit être journalisée."""

import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(Path(__file__).parent / ".env")

LEGIFRANCE_ENV = os.getenv("LEGIFRANCE_ENV", "sandbox")
if LEGIFRANCE_ENV not in {"sandbox", "production"}:
    raise ValueError("LEGIFRANCE_ENV doit valoir sandbox ou production.")

LEGIFRANCE_CLIENT_ID = os.getenv("LEGIFRANCE_CLIENT_ID", "")
LEGIFRANCE_CLIENT_SECRET = os.getenv("LEGIFRANCE_CLIENT_SECRET", "")
_PREFIXE = "sandbox-" if LEGIFRANCE_ENV == "sandbox" else ""
LEGIFRANCE_TOKEN_URL = f"https://{_PREFIXE}oauth.piste.gouv.fr/api/oauth/token"
LEGIFRANCE_BASE_URL = (
    f"https://{_PREFIXE}api.piste.gouv.fr/dila/legifrance/lf-engine-app"
)
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
GROQ_MODEL = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")
MISTRAL_API_KEY = os.getenv("MISTRAL_API_KEY", "")
TIMEOUT_S = float(os.getenv("TIMEOUT_S", "20"))
