"""Calibracao: aprende a recuperacao de cada elemento com as corridas reais (DAS 12.3).

rho_E = (Mf*cf_E - M0*c0_E) / soma(x_j * c_j,E)

Regras:
- so considera elementos com ganho esperado acima de 0,02 p.p.;
- minimo de 5 corridas finalizadas da liga;
- media ponderada, corridas recentes pesam mais;
- resultado limitado entre 0,50 e 1,05;
- cada recalculo gera uma nova versao.

TODO US-17 (Ruann, Grokoski).
"""

MIN_CORRIDAS = 5
GANHO_MINIMO = 0.02
RHO_MIN, RHO_MAX = 0.50, 1.05


def calcular_fatores(corridas: list, elementos: tuple) -> dict:
    """Devolve {elemento: recuperacao}. Vazio quando nao ha dados suficientes."""
    raise NotImplementedError("US-17")
