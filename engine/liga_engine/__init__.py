"""Motor de calculo do LIGA APP.

Python puro: nao importa nada de api/, nao acessa banco e nao faz rede (DAS 9.3).
Exporte aqui o que a API deve consumir.
"""
from .versao import VERSAO_MOTOR
from .tipos import (
    ELEMENTOS,
    STATUS_OK,
    STATUS_INVIAVEL,
    Material,
    Faixa,
    Liga,
    Banho,
    Adicao,
    Desvio,
    ResultadoCorrecao,
)
from .mistura import composicao_mistura

__all__ = [
    "VERSAO_MOTOR",
    "ELEMENTOS",
    "STATUS_OK",
    "STATUS_INVIAVEL",
    "Material",
    "Faixa",
    "Liga",
    "Banho",
    "Adicao",
    "Desvio",
    "ResultadoCorrecao",
    "composicao_mistura",
]
