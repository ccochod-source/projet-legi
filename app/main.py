"""Interface web ; le futur client MCP utilisera exclusivement stdio.

L'orchestrateur ouvrira server.py avec StdioServerParameters/stdio_client,
initialisera ClientSession, puis traduira list_tools pour Groq. Il exécutera
les appels proposés par le modèle via call_tool et renverra leurs résultats
au modèle. Aucune boucle, requête Groq ou session MCP n'est implémentée ici.
"""

from pathlib import Path
from typing import Any

import uvicorn
from fastapi import FastAPI
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field

import config
from erreurs import ErreurOutil, convertir_erreur

app = FastAPI(title="projet-legi")
PAGE_ACCUEIL = Path(__file__).parent / "static" / "index.html"


class RequeteDiscussion(BaseModel):
    """Message et historique fournis par l'interface locale."""

    message: str
    historique: list[dict[str, str]] = Field(default_factory=list)


@app.get("/", response_class=FileResponse)
async def accueil() -> FileResponse:
    """Sert l'unique page HTML locale."""
    return FileResponse(PAGE_ACCUEIL)


@app.post("/api/chat")
async def discuter(requete: RequeteDiscussion) -> dict[str, Any]:
    """Prévoit Groq et MCP stdio ; aucune analyse n'est effectuée.

    Le succès contiendra statut, reponse et sources. Les erreurs suivent le
    contrat des outils. Les secrets restent uniquement côté serveur.
    """
    return convertir_erreur(ErreurOutil("Discussion Groq/MCP non implémentée."))


if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8001)
