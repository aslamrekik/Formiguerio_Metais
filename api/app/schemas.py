from enum import Enum
from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field, model_validator, ConfigDict

class TipoMateriaPrima(str, Enum):
    SUCATA = "SUCATA"
    LIGA_MAE = "LIGA_MAE"
    INSUMO = "INSUMO"
    ALUMINIO_PRIMARIO = "ALUMINIO_PRIMARIO"

class ComposicaoIn(BaseModel):
    """Schema para entrada de composição química."""
    elemento: str = Field(min_length=1, max_length=3)
    percentual: float = Field(ge=0, le=100)

class ComposicaoOut(ComposicaoIn):
    """Schema para saída de composição química."""
    id: int
    model_config = ConfigDict(from_attributes=True)

class MateriaPrimaIn(BaseModel):
    """Schema para entrada de matéria-prima."""
    nome: str = Field(min_length=1, max_length=120)
    tipo: TipoMateriaPrima
    custo_kg: float = Field(gt=0)
    estoque_kg: float = Field(ge=0)
    rendimento: float = Field(gt=0, le=1)
    composicoes: List[ComposicaoIn] = Field(min_length=1)

    @model_validator(mode='after')
    def validar_composicao(self):
        elementos = []
        for comp in self.composicoes:
            if comp.elemento.upper() in elementos:
                raise ValueError(f"Elemento duplicado na composição: {comp.elemento}")
            elementos.append(comp.elemento.upper())

        soma_nao_al = 0.0
        tem_al = False
        percentual_al = 0.0

        for comp in self.composicoes:
            if comp.elemento.upper() == "AL":
                tem_al = True
                percentual_al = comp.percentual
            else:
                soma_nao_al += comp.percentual
        
        if soma_nao_al > 100.01:
            raise ValueError(f"A soma dos percentuais dos elementos não-Al excede 100%: {soma_nao_al:.2f}%")
            
        total = soma_nao_al
        if tem_al:
            total += percentual_al
            if abs(total - 100.0) > 0.01:
                 raise ValueError(f"A soma total da composição deve ser 100%. Soma atual: {total:.2f}%")
        else:
            percentual_al = 100.0 - soma_nao_al
            if percentual_al < 0 and soma_nao_al <= 100.01:
                percentual_al = 0.0
            self.composicoes.append(ComposicaoIn(elemento="Al", percentual=percentual_al))
            
        return self

class MateriaPrimaOut(BaseModel):
    """Schema para saída de matéria-prima."""
    id: int
    nome: str
    tipo: TipoMateriaPrima
    custo_kg: float
    estoque_kg: float
    rendimento: float
    composicoes: List[ComposicaoOut]
    criado_em: Optional[datetime] = None
    model_config = ConfigDict(from_attributes=True)

class FaixaIn(BaseModel):
    """Schema para entrada de faixa de elementos na liga."""
    elemento: str = Field(min_length=1, max_length=3)
    min_pct: float = Field(ge=0, le=100)
    max_pct: float = Field(ge=0, le=100)

    @model_validator(mode='after')
    def validar_limites(self):
        if self.min_pct > self.max_pct:
            raise ValueError(f"Percentual mínimo ({self.min_pct}%) não pode ser maior que o máximo ({self.max_pct}%) para o elemento {self.elemento}")
        return self

class FaixaOut(FaixaIn):
    """Schema para saída de faixa de elementos na liga."""
    id: int
    model_config = ConfigDict(from_attributes=True)

class LigaIn(BaseModel):
    """Schema para entrada de liga."""
    nome: str = Field(min_length=1, max_length=60)
    norma: str = Field(min_length=1, max_length=120)
    faixas: List[FaixaIn] = Field(min_length=1)

    @model_validator(mode='after')
    def validar_faixas(self):
        elementos = []
        for faixa in self.faixas:
            if faixa.elemento.upper() in elementos:
                raise ValueError(f"Elemento duplicado nas faixas de composição: {faixa.elemento}")
            elementos.append(faixa.elemento.upper())
        return self

class LigaOut(BaseModel):
    """Schema para saída de liga."""
    id: int
    nome: str
    norma: str
    faixas: List[FaixaOut]
    criado_em: Optional[datetime] = None
    model_config = ConfigDict(from_attributes=True)

class LinhaErro(BaseModel):
    """Schema para erro de linha na importação."""
    linha: int
    motivo: str

class ResultadoImportacao(BaseModel):
    """Schema para resultado de importação em lote."""
    importadas: int
    erros: List[LinhaErro]

class TokenOut(BaseModel):
    """Schema para saída de token de acesso."""
    access_token: str
    token_type: str = 'bearer'

class LoginIn(BaseModel):
    """Schema para credenciais de login."""
    email: str
    senha: str
