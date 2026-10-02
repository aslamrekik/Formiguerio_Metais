"""Configuracao dos testes: substitui o banco PostgreSQL por SQLite em memoria."""
import os

# Troca o banco ANTES de qualquer import da app
os.environ["DATABASE_URL"] = "sqlite:///./test.db"

from sqlalchemy import create_engine, StaticPool
from sqlalchemy.orm import sessionmaker

from app.db import Base, get_db
from app.main import app

# Cria engine SQLite em memoria para testes
engine_teste = create_engine(
    "sqlite:///./test.db",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
SessaoTeste = sessionmaker(bind=engine_teste, autoflush=False, expire_on_commit=False)


def override_get_db():
    db = SessaoTeste()
    try:
        yield db
    finally:
        db.close()


# Sobrescreve a dependencia de banco
app.dependency_overrides[get_db] = override_get_db

# Cria todas as tabelas para testes
Base.metadata.create_all(bind=engine_teste)
