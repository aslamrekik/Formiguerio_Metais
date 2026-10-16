"""Regras de aplicacao da corrida salva (US-14, DAS 7.2).

RASCUNHO -> CONFIRMADA -> FINALIZADA. Corrida confirmada nao se apaga nem se altera.
A versao do motor e da calibracao e carimbada AQUI, nunca vem do cliente.
"""
import uuid
from datetime import date, datetime, timezone

from liga_engine.versao import VERSAO_MOTOR
from sqlalchemy.orm import Session

from ..models import CONFIRMADA, RASCUNHO, Corrida
from ..repositories import corridas as repo
from ..schemas import CorridaIn


class CorridaNaoEncontrada(Exception):
    pass


class CorridaImutavel(Exception):
    """Tentativa de alterar ou apagar corrida que ja nao e rascunho."""


def versao_calibracao_atual(liga_id: str) -> int:
    """TODO US-17: devolver a versao vigente em fatores_calibracao. 0 = sem calibracao."""
    return 0


def salvar_rascunho(db: Session, usuario_id: str, dados: CorridaIn) -> Corrida:
    corrida = Corrida(
        liga_id=dados.liga_id,
        usuario_id=usuario_id,
        status=RASCUNHO,
        entrada=dados.entrada,
        resultado=dados.resultado,
        explicacao=dados.explicacao,
        versao_motor=VERSAO_MOTOR,
        versao_calibracao=versao_calibracao_atual(dados.liga_id),
    )
    return repo.adicionar(db, corrida)


def obter(db: Session, corrida_id: uuid.UUID) -> Corrida:
    corrida = repo.obter(db, corrida_id)
    if corrida is None:
        raise CorridaNaoEncontrada(str(corrida_id))
    return corrida


def confirmar(db: Session, corrida_id: uuid.UUID) -> Corrida:
    corrida = obter(db, corrida_id)
    if corrida.status != RASCUNHO:
        raise CorridaImutavel(f"corrida ja esta {corrida.status}")
    corrida.status = CONFIRMADA
    corrida.confirmada_em = datetime.now(timezone.utc)
    return repo.salvar(db, corrida)


def apagar(db: Session, corrida_id: uuid.UUID) -> None:
    corrida = obter(db, corrida_id)
    if corrida.status != RASCUNHO:
        raise CorridaImutavel(f"corrida {corrida.status} nao pode ser apagada")
    repo.apagar(db, corrida)


def historico(db: Session, *, liga_id: str | None = None, de: date | None = None,
              ate: date | None = None, status: str | None = None,
              limite: int = 50, deslocamento: int = 0):
    return repo.listar(db, liga_id=liga_id, de=de, ate=ate, status=status,
                       limite=limite, deslocamento=deslocamento)
