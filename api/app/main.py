"""Aplicacao FastAPI do LIGA APP."""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .config import config
from .routers import corridas

app = FastAPI(title="LIGA APP", version="0.1.0",
              description="Calculo e correcao de ligas secundarias de aluminio")

app.add_middleware(CORSMiddleware, allow_origins=[config.cors_origin],
                   allow_credentials=True, allow_methods=["*"], allow_headers=["*"])

# TODO: incluir auth e cadastros quando as US-03 a US-06 entrarem.
app.include_router(corridas.router)


@app.get("/saude", tags=["infra"])
def saude():
    """Usada pelo deploy e para acordar o servidor antes das demonstracoes."""
    return {"status": "ok"}
