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
GROQ_MODEL = os.getenv("GROQ_MODEL", "openai/gpt-oss-120b")
GROQ_MODEL_SECOURS = os.getenv("GROQ_MODEL_SECOURS", "openai/gpt-oss-20b")
MISTRAL_API_KEY = os.getenv("MISTRAL_API_KEY", "")
TIMEOUT_S = float(os.getenv("TIMEOUT_S", "20"))
VERCEL = bool(os.getenv("VERCEL"))
MCP_TRANSPORT = os.getenv("MCP_TRANSPORT", "memoire" if VERCEL else "stdio")
if MCP_TRANSPORT not in {"stdio", "memoire"}:
    raise ValueError("MCP_TRANSPORT doit valoir stdio ou memoire.")
APP_CODE_ACCES = os.getenv("APP_CODE_ACCES", "")
SUPABASE_URL = os.getenv("SUPABASE_URL", "").rstrip("/")
SUPABASE_SERVICE_ROLE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY", "")
