"""Calibracao: aprende a recuperacao de cada elemento com as corridas reais (DAS 12.3).

rho_E = (Mf*cf_E - M0*c0_E) / soma(x_j * c_j,E)

Mf, cf = massa e teor finais; M0, c0 = massa e teor iniciais; x_j = kg adicionados
do material j; c_j,E = teor do elemento no material. rho e a fracao do elemento
adicionado que realmente aparece na analise final.

Regras (DAS 12.3):
- so considera elementos com adicao esperada acima de 0,02 p.p. na corrida;
- minimo de 5 corridas finalizadas da liga (senao devolve vazio);
- media ponderada, corridas recentes pesam mais;
- resultado limitado entre 0,50 e 1,05;
- cada recalculo gera uma nova versao (a versao e responsabilidade da API).

US-17 (Ruann, Grokoski).
"""
from .tipos import ELEMENTOS

MIN_CORRIDAS = 5
GANHO_MINIMO = 0.02
RHO_MIN, RHO_MAX = 0.50, 1.05


def calcular_fatores(corridas: list, elementos: tuple = ELEMENTOS) -> dict:
    """Recuperacao calibrada por elemento a partir das corridas finalizadas.

    corridas: lista de CorridaFinalizada. Devolve {elemento: recuperacao} apenas
    para os elementos com dados suficientes; vazio quando ha menos de 5 corridas.
    """
    if len(corridas) < MIN_CORRIDAS:
        return {}

    ordenadas = _ordenar_por_data(corridas)
    fatores = {}
    for elemento in elementos:
        soma_peso = 0.0
        soma_ponderada = 0.0
        for posicao, corrida in enumerate(ordenadas):
            rho = _rho_da_corrida(corrida, elemento)
            if rho is None:
                continue
            peso = posicao + 1  # corridas mais recentes (posicao maior) pesam mais
            soma_ponderada += peso * rho
            soma_peso += peso
        if soma_peso > 0:
            fatores[elemento] = _limitar(soma_ponderada / soma_peso)
    return fatores


def _rho_da_corrida(corrida, elemento):
    """rho do elemento nesta corrida, ou None se a adicao foi pequena demais."""
    Mf = float(corrida.massa_final)
    if Mf <= 0:  # pragma: no cover - guarda: corrida finalizada sempre tem massa > 0
        return None
    adicionado = corrida.elemento_adicionado(elemento)  # kg*% (denominador)
    # Adicao esperada, em p.p. sobre a massa final. Abaixo de 0,02 p.p. o rho fica
    # instavel (denominador minusculo), entao a corrida nao entra para esse elemento.
    if adicionado / Mf <= GANHO_MINIMO:
        return None
    M0 = float(corrida.massa_inicial)
    cf = float(corrida.composicao_final.get(elemento, 0.0))
    c0 = float(corrida.composicao_inicial.get(elemento, 0.0))
    return (Mf * cf - M0 * c0) / adicionado


def _ordenar_por_data(corridas):
    """Ordena da mais antiga para a mais recente quando todas tem data."""
    if all(getattr(c, "data", None) is not None for c in corridas):
        return sorted(corridas, key=lambda c: c.data)
    return list(corridas)


def _limitar(valor):
    return max(RHO_MIN, min(RHO_MAX, valor))
