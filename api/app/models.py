import enum
from datetime import datetime
from typing import List

from sqlalchemy import DateTime, Enum, Float, ForeignKey, Integer, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .db import Base


class TipoMateriaPrima(str, enum.Enum):
    """Tipos de matéria-prima disponíveis no sistema."""
    SUCATA = "SUCATA"
    LIGA_MAE = "LIGA_MAE"
    INSUMO = "INSUMO"
    ALUMINIO_PRIMARIO = "ALUMINIO_PRIMARIO"


class MateriaPrima(Base):
    """Modelo representando uma matéria-prima, com seu custo, estoque e rendimento."""
    __tablename__ = "materias_primas"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    nome: Mapped[str] = mapped_column(String(120), nullable=False, unique=True)
    tipo: Mapped[TipoMateriaPrima] = mapped_column(Enum(TipoMateriaPrima), nullable=False)
    custo_kg: Mapped[float] = mapped_column(Float, nullable=False)
    estoque_kg: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    rendimento: Mapped[float] = mapped_column(Float, nullable=False, default=1.0)
    
    criado_em: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    atualizado_em: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), onupdate=func.now()
    )

    composicoes: Mapped[List["Composicao"]] = relationship(
        "Composicao", back_populates="materia_prima", cascade="all, delete-orphan"
    )


class Composicao(Base):
    """Composição química de uma matéria-prima (percentual de um elemento)."""
    __tablename__ = "composicoes"
    __table_args__ = (
        UniqueConstraint("materia_prima_id", "elemento", name="uq_composicao_mp_elemento"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    materia_prima_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("materias_primas.id"), nullable=False
    )
    elemento: Mapped[str] = mapped_column(String(3), nullable=False)
    percentual: Mapped[float] = mapped_column(Float, nullable=False)

    materia_prima: Mapped["MateriaPrima"] = relationship(
        "MateriaPrima", back_populates="composicoes"
    )


class Liga(Base):
    """Modelo representando uma liga-alvo de alumínio."""
    __tablename__ = "ligas"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    nome: Mapped[str] = mapped_column(String(60), nullable=False, unique=True)
    norma: Mapped[str] = mapped_column(String(120), nullable=False)
    
    criado_em: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    atualizado_em: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), onupdate=func.now()
    )

    faixas: Mapped[List["Faixa"]] = relationship(
        "Faixa", back_populates="liga", cascade="all, delete-orphan"
    )


class Faixa(Base):
    """Faixa de tolerância (mínima e máxima) de um elemento para uma liga específica."""
    __tablename__ = "faixas"
    __table_args__ = (
        UniqueConstraint("liga_id", "elemento", name="uq_faixa_liga_elemento"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    liga_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("ligas.id"), nullable=False
    )
    elemento: Mapped[str] = mapped_column(String(3), nullable=False)
    min_pct: Mapped[float] = mapped_column(Float, nullable=False)
    max_pct: Mapped[float] = mapped_column(Float, nullable=False)

    liga: Mapped["Liga"] = relationship(
        "Liga", back_populates="faixas"
    )
