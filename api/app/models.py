"""Tabelas do banco.

TODO US-02 (Arthur): criar os modelos SQLAlchemy conforme a secao 11 do DAS:
usuarios, materias_primas, composicoes, ligas, faixas, corridas, adicoes e
fatores_calibracao. Depois gerar a primeira migration com Alembic.
"""
from .db import Base  # noqa: F401
