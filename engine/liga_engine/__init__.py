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
    CorridaFinalizada,
)
from .mistura import composicao_mistura
from .correcao import calcular_correcao
from .calibracao import calcular_fatores

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
    "CorridaFinalizada",
    "composicao_mistura",
    "calcular_correcao",
    "calcular_fatores",
]
