"""Aplicacao FastAPI do LIGA APP."""
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .config import config
from .db import engine, Base
from .routers import auth, cadastros, corridas

# Importa os models para que o Base.metadata conheça todas as tabelas
from . import models  # noqa: F401


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Cria as tabelas no banco ao iniciar (desenvolvimento e staging)."""
    Base.metadata.create_all(bind=engine)
    yield


app = FastAPI(
    title="LIGA APP",
    version="0.1.0",
    description="Calculo e correcao de ligas secundarias de aluminio",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[config.cors_origin],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Routers
app.include_router(auth.router)
app.include_router(cadastros.router)
app.include_router(corridas.router)


@app.get("/saude", tags=["infra"])
def saude():
    """Usada pelo deploy e para acordar o servidor antes das demonstracoes."""
    return {"status": "ok"}
