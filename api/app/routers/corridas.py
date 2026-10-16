"""Calculo, explicacao, historico, analise final e relatorio.

Rotas previstas no DAS 9.4 (US-09 a US-18):
POST /corridas, POST /corridas/{id}/explicacao, POST /corridas/{id}/confirmar,
PUT /corridas/{id}/analise-final, GET /corridas, GET /corridas/{id},
GET /corridas/{id}/relatorio.pdf, POST /corridas/importar.

US-14 (este arquivo): POST /corridas, POST /corridas/{id}/confirmar,
GET /corridas, GET /corridas/{id} e DELETE /corridas/{id} (so rascunho).
"""
import uuid
from datetime import date
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy.orm import Session

from ..db import get_db
from ..schemas import CorridaIn, CorridaOut, HistoricoOut
from ..services import corridas as servico

try:
    from ..security import usuario_atual
except ImportError:  # US-03 ainda nao entrou nesta branch: falha fechada (401).
    def usuario_atual():
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Autenticacao (US-03) indisponivel")

router = APIRouter(prefix="/corridas", tags=["corridas"], dependencies=[Depends(usuario_atual)])


def _id_do_usuario(usuario) -> str:
    return str(getattr(usuario, "id", usuario))


def _traduzir(exc: Exception) -> HTTPException:
    if isinstance(exc, servico.CorridaNaoEncontrada):
        return HTTPException(status.HTTP_404_NOT_FOUND, "Corrida nao encontrada")
    return HTTPException(status.HTTP_409_CONFLICT, str(exc))


@router.post("", response_model=CorridaOut, status_code=status.HTTP_201_CREATED)
def salvar_corrida(dados: CorridaIn, db: Session = Depends(get_db),
                   usuario=Depends(usuario_atual)):
    """Salva a corrida como RASCUNHO, carimbando usuario e versoes do motor/calibracao."""
    return servico.salvar_rascunho(db, _id_do_usuario(usuario), dados)


@router.get("", response_model=HistoricoOut)
def listar_historico(
    liga_id: str | None = None,
    de: date | None = Query(None, description="Data inicial (inclusiva)"),
    ate: date | None = Query(None, description="Data final (inclusiva)"),
    status_: Literal["RASCUNHO", "CONFIRMADA", "FINALIZADA"] | None = Query(None, alias="status"),
    limite: int = Query(50, ge=1, le=200),
    deslocamento: int = Query(0, ge=0),
    db: Session = Depends(get_db),
):
    """Historico filtravel por liga e periodo, da mais recente para a mais antiga."""
    if de and ate and de > ate:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "'de' nao pode ser depois de 'ate'")
    total, itens = servico.historico(db, liga_id=liga_id, de=de, ate=ate, status=status_,
                                     limite=limite, deslocamento=deslocamento)
    return HistoricoOut(total=total, itens=itens)


@router.get("/{corrida_id}", response_model=CorridaOut)
def detalhar_corrida(corrida_id: uuid.UUID, db: Session = Depends(get_db)):
    try:
        return servico.obter(db, corrida_id)
    except servico.CorridaNaoEncontrada as exc:
        raise _traduzir(exc)


@router.post("/{corrida_id}/confirmar", response_model=CorridaOut)
def confirmar_corrida(corrida_id: uuid.UUID, db: Session = Depends(get_db)):
    """RASCUNHO -> CONFIRMADA. Depois disso a corrida fica imutavel."""
    try:
        return servico.confirmar(db, corrida_id)
    except (servico.CorridaNaoEncontrada, servico.CorridaImutavel) as exc:
        raise _traduzir(exc)


@router.delete("/{corrida_id}", status_code=status.HTTP_204_NO_CONTENT)
def apagar_rascunho(corrida_id: uuid.UUID, db: Session = Depends(get_db)):
    """Apaga so rascunho. Corrida confirmada ou finalizada devolve 409."""
    try:
        servico.apagar(db, corrida_id)
    except (servico.CorridaNaoEncontrada, servico.CorridaImutavel) as exc:
        raise _traduzir(exc)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
