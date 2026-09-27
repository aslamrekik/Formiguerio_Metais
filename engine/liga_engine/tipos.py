"""Tipos do dominio usados pelo motor (ver DAS secao 7, diagrama de classes).

US-07 (Ruann, Grokoski): Material, Faixa, Liga, Banho, Adicao, Desvio e
ResultadoCorrecao como dataclasses, seguindo o diagrama de classes do DAS.

Sao objetos de valor: o motor recebe dados prontos e devolve resultado, sem tocar
banco nem rede (DAS 9.3). Teores e massas em float64; o arredondamento fica na saida.
"""
from dataclasses import dataclass, field
from typing import Optional

from .versao import VERSAO_MOTOR

# Elementos controlados no MVP. Al e o restante ate 100%.
# Confirmar a lista final com o engenheiro do cliente.
ELEMENTOS = ("Si", "Fe", "Cu", "Mn", "Mg", "Zn", "Ti", "Ni", "Pb", "Sn")

# Status possiveis de uma correcao (DAS 12.4).
STATUS_OK = "OK"
STATUS_INVIAVEL = "INVIAVEL"


@dataclass(frozen=True)
class Material:
    """Materia-prima disponivel para adicao (DAS 7, classe MateriaPrima).

    composicao: teor em % por elemento, ex. {"Si": 20.0, "Fe": 0.15}. Elemento
    ausente conta como 0. Al e implicito (o restante ate 100%).
    rendimento: fracao da massa que vira metal util no banho (0 < r <= 1).
    """
    id: str
    nome: str
    tipo: str = "INSUMO"
    composicao: dict = field(default_factory=dict)
    custo_kg: float = 0.0
    estoque_kg: float = 0.0
    rendimento: float = 1.0

    def teor(self, elemento: str) -> float:
        """Teor % do elemento neste material; 0 se ausente."""
        return float(self.composicao.get(elemento, 0.0))


@dataclass(frozen=True)
class Faixa:
    """Faixa min/max de um elemento na liga-alvo (DAS 7, classe FaixaElemento)."""
    elemento: str
    min_pct: float
    max_pct: float


@dataclass(frozen=True)
class Liga:
    """Liga comercial que se quer produzir, com faixa por elemento (DAS 7)."""
    id: str
    nome: str
    norma: str = ""
    faixas: tuple = ()

    def faixa_de(self, elemento: str) -> Optional[Faixa]:
        """Faixa do elemento, ou None se a liga nao controla esse elemento."""
        for f in self.faixas:
            if f.elemento == elemento:
                return f
        return None

    def dentro_da_faixa(self, composicao: dict, tolerancia: float = 0.0) -> bool:
        """True se todos os elementos controlados estao dentro da faixa."""
        for f in self.faixas:
            teor = float(composicao.get(f.elemento, 0.0))
            if teor < f.min_pct - tolerancia or teor > f.max_pct + tolerancia:
                return False
        return True


@dataclass(frozen=True)
class Banho:
    """Metal liquido dentro do forno no inicio da corrida (DAS 1.3)."""
    massa_kg: float
    composicao: dict = field(default_factory=dict)
    capacidade_kg: float = 0.0

    def teor(self, elemento: str) -> float:
        return float(self.composicao.get(elemento, 0.0))


@dataclass(frozen=True)
class Adicao:
    """Quantidade de um material a adicionar no banho (DAS 7, classe Adicao)."""
    material_id: str
    massa_kg: float


@dataclass(frozen=True)
class Desvio:
    """Previsto x faixa de um elemento apos a correcao."""
    elemento: str
    previsto: float
    minimo: float
    maximo: float
    dentro: bool


@dataclass(frozen=True)
class CorridaFinalizada:
    """Corrida ja finalizada, usada como dado de entrada da calibracao (US-17).

    adicoes: tupla de (Material, massa_kg) realmente adicionados na corrida.
    data: qualquer valor ordenavel (ISO ou datetime) para dar mais peso as
    corridas recentes; opcional.
    """
    massa_inicial: float
    composicao_inicial: dict
    massa_final: float
    composicao_final: dict
    adicoes: tuple = ()
    data: Optional[object] = None

    def elemento_adicionado(self, elemento: str) -> float:
        """Massa*teor do elemento somada nas adicoes (kg*%), o denominador de rho."""
        return sum(massa * material.teor(elemento)
                   for material, massa in self.adicoes)


@dataclass
class ResultadoCorrecao:
    """Saida do motor de correcao (DAS 12.2).

    status: STATUS_OK ou STATUS_INVIAVEL.
    elemento_limitante: quando inviavel, o elemento que impede a solucao.
    versao_motor / versao_calibracao: gravadas na corrida (AD-06).
    """
    status: str
    adicoes: list = field(default_factory=list)
    composicao_prevista: dict = field(default_factory=dict)
    desvios: list = field(default_factory=list)
    custo_total: float = 0.0
    elemento_limitante: Optional[str] = None
    versao_motor: str = VERSAO_MOTOR
    versao_calibracao: Optional[str] = None
