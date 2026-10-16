"""Schemas Pydantic de entrada e saida.

TODO US-03 a US-15: Login, Token, MateriaPrimaIn/Out, LigaIn/Out, CalculoIn,
AnaliseFinalIn. Validacoes obrigatorias do DAS 7.1:
- soma dos elementos com Al = 100% (+-0,01);
- min_pct <= max_pct em cada faixa.
"""
import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


# ---- US-14: salvar corrida e ver historico ---------------------------------
class CorridaIn(BaseModel):
    """O que o cliente envia ao salvar. Usuario e versoes NUNCA vem do cliente."""

    liga_id: str = Field(min_length=1, max_length=64)
    entrada: dict
    resultado: dict
    explicacao: str | None = None


class CorridaResumo(BaseModel):
    """Linha do historico."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    liga_id: str
    status: str
    versao_motor: str
    versao_calibracao: int
    criada_em: datetime
    confirmada_em: datetime | None = None


class CorridaOut(CorridaResumo):
    """Corrida completa (detalhe)."""

    usuario_id: str
    entrada: dict
    resultado: dict
    explicacao: str | None = None
    analise_final: dict | None = None
    finalizada_em: datetime | None = None


class HistoricoOut(BaseModel):
    total: int
    itens: list[CorridaResumo]
