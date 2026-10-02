from fastapi import APIRouter, Depends, HTTPException, UploadFile, status
from sqlalchemy.orm import Session, selectinload
from typing import List
import csv
import io

from ..db import get_db
from ..security import usuario_atual
from ..models import (
    MateriaPrima, Composicao, Liga, Faixa, TipoMateriaPrima
)
from ..schemas import (
    MateriaPrimaIn, MateriaPrimaOut,
    LigaIn, LigaOut,
    LinhaErro, ResultadoImportacao,
    ComposicaoIn
)

router = APIRouter(tags=['cadastros'])

# --- Matérias-primas ---

@router.post("/materias-primas", response_model=MateriaPrimaOut, status_code=status.HTTP_201_CREATED)
def criar_materia_prima(
    materia_in: MateriaPrimaIn,
    db: Session = Depends(get_db),
    usuario: str = Depends(usuario_atual)
):
    """Cria uma nova matéria-prima e suas composições."""
    nova_materia = MateriaPrima(
        nome=materia_in.nome,
        tipo=materia_in.tipo,
        custo_kg=materia_in.custo_kg,
        estoque_kg=materia_in.estoque_kg,
        rendimento=materia_in.rendimento
    )
    db.add(nova_materia)
    db.flush()
    
    for comp in materia_in.composicoes:
        nova_comp = Composicao(
            materia_prima_id=nova_materia.id,
            elemento=comp.elemento,
            percentual=comp.percentual
        )
        db.add(nova_comp)
        
    db.commit()
    db.refresh(nova_materia)
    return nova_materia


@router.get("/materias-primas", response_model=List[MateriaPrimaOut])
def listar_materias_primas(
    db: Session = Depends(get_db),
    usuario: str = Depends(usuario_atual)
):
    """Lista todas as matérias-primas com suas composições."""
    materias = db.query(MateriaPrima).options(selectinload(MateriaPrima.composicoes)).all()
    return materias


@router.put("/materias-primas/{id}", response_model=MateriaPrimaOut)
def atualizar_materia_prima(
    id: int,
    materia_in: MateriaPrimaIn,
    db: Session = Depends(get_db),
    usuario: str = Depends(usuario_atual)
):
    """Atualiza uma matéria-prima e substitui todas as suas composições."""
    materia = db.query(MateriaPrima).options(selectinload(MateriaPrima.composicoes)).filter(MateriaPrima.id == id).first()
    if not materia:
        raise HTTPException(status_code=404, detail="Matéria-prima não encontrada")
        
    materia.nome = materia_in.nome
    materia.tipo = materia_in.tipo
    materia.custo_kg = materia_in.custo_kg
    materia.estoque_kg = materia_in.estoque_kg
    materia.rendimento = materia_in.rendimento
    
    db.query(Composicao).filter(Composicao.materia_prima_id == id).delete()
    
    for comp in materia_in.composicoes:
        nova_comp = Composicao(
            materia_prima_id=id,
            elemento=comp.elemento,
            percentual=comp.percentual
        )
        db.add(nova_comp)
        
    db.commit()
    db.refresh(materia)
    return materia


@router.post("/materias-primas/importar", response_model=ResultadoImportacao)
def importar_materias_primas_csv(
    arquivo: UploadFile,
    db: Session = Depends(get_db),
    usuario: str = Depends(usuario_atual)
):
    """
    Importa matérias-primas a partir de um arquivo CSV.
    Colunas esperadas: nome,tipo,custo_kg,estoque_kg,rendimento,Si,Fe,Cu,Mn,Mg,Zn,Ti
    """
    conteudo = arquivo.file.read().decode("utf-8")
    leitor = csv.DictReader(io.StringIO(conteudo))
    
    elementos_csv = ["Si", "Fe", "Cu", "Mn", "Mg", "Zn", "Ti"]
    
    sucesso_count = 0
    erros = []
    
    linha_numero = 1
    for linha in leitor:
        try:
            nome = linha["nome"]
            tipo = TipoMateriaPrima(linha["tipo"])
            custo_kg = float(linha["custo_kg"])
            estoque_kg = float(linha["estoque_kg"])
            rendimento = float(linha["rendimento"])
            
            composicoes_in = []
            for el in elementos_csv:
                if el in linha and linha[el].strip():
                    pct = float(linha[el])
                    if pct > 0:
                        composicoes_in.append(ComposicaoIn(elemento=el, percentual=pct))
            
            materia_in = MateriaPrimaIn(
                nome=nome,
                tipo=tipo,
                custo_kg=custo_kg,
                estoque_kg=estoque_kg,
                rendimento=rendimento,
                composicoes=composicoes_in
            )
            
            nova_materia = MateriaPrima(
                nome=materia_in.nome,
                tipo=materia_in.tipo,
                custo_kg=materia_in.custo_kg,
                estoque_kg=materia_in.estoque_kg,
                rendimento=materia_in.rendimento
            )
            db.add(nova_materia)
            db.flush()
            
            for comp in materia_in.composicoes:
                nova_comp = Composicao(
                    materia_prima_id=nova_materia.id,
                    elemento=comp.elemento,
                    percentual=comp.percentual
                )
                db.add(nova_comp)
                
            db.commit()
            sucesso_count += 1
            
        except Exception as e:
            db.rollback()
            erros.append(LinhaErro(linha=linha_numero, motivo=str(e)))
            
        linha_numero += 1
        
    return ResultadoImportacao(importadas=sucesso_count, erros=erros)

# --- Ligas ---

@router.post("/ligas", response_model=LigaOut, status_code=status.HTTP_201_CREATED)
def criar_liga(
    liga_in: LigaIn,
    db: Session = Depends(get_db),
    usuario: str = Depends(usuario_atual)
):
    """Cria uma nova liga e suas faixas."""
    nova_liga = Liga(
        nome=liga_in.nome,
        norma=liga_in.norma
    )
    db.add(nova_liga)
    db.flush()
    
    for faixa in liga_in.faixas:
        nova_faixa = Faixa(
            liga_id=nova_liga.id,
            elemento=faixa.elemento,
            min_pct=faixa.min_pct,
            max_pct=faixa.max_pct
        )
        db.add(nova_faixa)
        
    db.commit()
    db.refresh(nova_liga)
    return nova_liga


@router.get("/ligas", response_model=List[LigaOut])
def listar_ligas(
    db: Session = Depends(get_db),
    usuario: str = Depends(usuario_atual)
):
    """Lista todas as ligas com suas faixas."""
    ligas = db.query(Liga).options(selectinload(Liga.faixas)).all()
    return ligas


@router.put("/ligas/{id}", response_model=LigaOut)
def atualizar_liga(
    id: int,
    liga_in: LigaIn,
    db: Session = Depends(get_db),
    usuario: str = Depends(usuario_atual)
):
    """Atualiza uma liga e substitui todas as suas faixas."""
    liga = db.query(Liga).options(selectinload(Liga.faixas)).filter(Liga.id == id).first()
    if not liga:
        raise HTTPException(status_code=404, detail="Liga não encontrada")
        
    liga.nome = liga_in.nome
    liga.norma = liga_in.norma
    
    db.query(Faixa).filter(Faixa.liga_id == id).delete()
    
    for faixa in liga_in.faixas:
        nova_faixa = Faixa(
            liga_id=id,
            elemento=faixa.elemento,
            min_pct=faixa.min_pct,
            max_pct=faixa.max_pct
        )
        db.add(nova_faixa)
        
    db.commit()
    db.refresh(liga)
    return liga
