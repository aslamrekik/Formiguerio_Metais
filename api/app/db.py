"""Conexao com o PostgreSQL (Supabase em staging e producao)."""
from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from .config import config

engine = create_engine(config.database_url, pool_pre_ping=True)
Sessao = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


class Base(DeclarativeBase):
    pass


def get_db():
    db = Sessao()
    try:
        yield db
    finally:
        db.close()
