"""Acesso ao banco para corridas (DAS 9.3: service -> repository). So SQL aqui."""
import uuid
from datetime import date, datetime, time, timedelta, timezone

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..models import Corrida


def adicionar(db: Session, corrida: Corrida) -> Corrida:
    db.add(corrida)
    db.commit()
    db.refresh(corrida)
    return corrida


def obter(db: Session, corrida_id: uuid.UUID) -> Corrida | None:
    return db.get(Corrida, corrida_id)


def salvar(db: Session, corrida: Corrida) -> Corrida:
    db.commit()
    db.refresh(corrida)
    return corrida


def apagar(db: Session, corrida: Corrida) -> None:
    db.delete(corrida)
    db.commit()


def listar(db: Session, *, liga_id: str | None, de: date | None, ate: date | None,
           status: str | None, limite: int, deslocamento: int) -> tuple[int, list[Corrida]]:
    """Historico filtravel por liga e periodo (datas inclusivas, em UTC)."""
    filtros = []
    if liga_id:
        filtros.append(Corrida.liga_id == liga_id)
    if status:
        filtros.append(Corrida.status == status)
    if de:
        filtros.append(Corrida.criada_em >= datetime.combine(de, time.min, timezone.utc))
    if ate:
        filtros.append(Corrida.criada_em < datetime.combine(ate + timedelta(days=1), time.min, timezone.utc))

    total = db.scalar(select(func.count()).select_from(Corrida).where(*filtros)) or 0
    itens = db.scalars(select(Corrida).where(*filtros)
                       .order_by(Corrida.criada_em.desc())
                       .limit(limite).offset(deslocamento)).all()
    return total, list(itens)
