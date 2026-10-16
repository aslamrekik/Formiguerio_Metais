"""Tabelas do banco.

TODO US-02 (Arthur): criar os modelos SQLAlchemy conforme a secao 11 do DAS:
usuarios, materias_primas, composicoes, ligas, faixas, corridas, adicoes e
fatores_calibracao. Depois gerar a primeira migration com Alembic.

US-14: a tabela `corridas` abaixo guarda a corrida salva. Quando a US-02 entrar,
trocar `liga_id` e `usuario_id` por ForeignKey para `ligas.id` e `usuarios.id`.
"""
import uuid
from datetime import datetime, timezone

from sqlalchemy import (JSON, CheckConstraint, DateTime, DDL, Index, Integer,
                        String, Text, Uuid, event)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from .db import Base

# JSON generico (SQLite nos testes) e JSONB no PostgreSQL.
Json = JSON().with_variant(JSONB(), "postgresql")

RASCUNHO, CONFIRMADA, FINALIZADA = "RASCUNHO", "CONFIRMADA", "FINALIZADA"
STATUS = (RASCUNHO, CONFIRMADA, FINALIZADA)


def _agora() -> datetime:
    return datetime.now(timezone.utc)


class Corrida(Base):
    """Uma corrida salva. Estados: RASCUNHO -> CONFIRMADA -> FINALIZADA (DAS 7.2)."""

    __tablename__ = "corridas"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    liga_id: Mapped[str] = mapped_column(String(64), index=True)
    usuario_id: Mapped[str] = mapped_column(String(64))
    status: Mapped[str] = mapped_column(String(12), default=RASCUNHO)
    entrada: Mapped[dict] = mapped_column(Json)
    resultado: Mapped[dict] = mapped_column(Json)
    explicacao: Mapped[str | None] = mapped_column(Text, nullable=True)
    versao_motor: Mapped[str] = mapped_column(String(32))
    versao_calibracao: Mapped[int] = mapped_column(Integer, default=0)
    analise_final: Mapped[dict | None] = mapped_column(Json, nullable=True)  # US-16
    criada_em: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_agora)
    confirmada_em: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    finalizada_em: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    __table_args__ = (
        CheckConstraint(f"status IN {STATUS}", name="ck_corridas_status"),
        Index("ix_corridas_liga_criada", "liga_id", "criada_em"),
    )


# Garantia no banco (alem da API): corrida confirmada nao e apagada nem alterada.
# Na CONFIRMADA so podem mudar status, analise_final e finalizada_em (US-16).
# Atencao: em DDL() o caractere % literal precisa ser escrito %%.
# Ao criar a migration do Alembic, copiar este SQL para o upgrade().
_FUNCAO = DDL("""
CREATE OR REPLACE FUNCTION corridas_imutaveis() RETURNS trigger AS $$
BEGIN
  IF TG_OP = 'DELETE' THEN
    IF OLD.status <> 'RASCUNHO' THEN
      RAISE EXCEPTION 'corrida %% esta %% e nao pode ser apagada', OLD.id, OLD.status;
    END IF;
    RETURN OLD;
  END IF;
  IF OLD.status <> 'RASCUNHO' THEN
    IF (NEW.id, NEW.liga_id, NEW.usuario_id, NEW.entrada, NEW.resultado,
        NEW.explicacao, NEW.versao_motor, NEW.versao_calibracao,
        NEW.criada_em, NEW.confirmada_em)
       IS DISTINCT FROM
       (OLD.id, OLD.liga_id, OLD.usuario_id, OLD.entrada, OLD.resultado,
        OLD.explicacao, OLD.versao_motor, OLD.versao_calibracao,
        OLD.criada_em, OLD.confirmada_em) THEN
      RAISE EXCEPTION 'corrida %% esta %% e nao pode ser alterada', OLD.id, OLD.status;
    END IF;
    IF NEW.status = 'RASCUNHO' OR (OLD.status = 'FINALIZADA' AND NEW.status <> 'FINALIZADA') THEN
      RAISE EXCEPTION 'corrida nao volta para um estado anterior';
    END IF;
  END IF;
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;
""")
_TRIGGER = DDL("""
CREATE TRIGGER corridas_imutaveis BEFORE UPDATE OR DELETE ON corridas
FOR EACH ROW EXECUTE FUNCTION corridas_imutaveis();
""")
event.listen(Corrida.__table__, "after_create", _FUNCAO.execute_if(dialect="postgresql"))
event.listen(Corrida.__table__, "after_create", _TRIGGER.execute_if(dialect="postgresql"))
