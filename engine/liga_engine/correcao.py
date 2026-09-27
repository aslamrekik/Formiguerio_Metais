"""Correcao do banho pelo menor custo, por programacao linear (DAS 12.2).

minimizar   soma(p_j * x_j)
sujeito a   L_E * (M0 + soma x_j) <= M0*c0_E + soma(x_j * c_j,E * rho_E)
                                  <= U_E * (M0 + soma x_j)
            0 <= x_j <= estoque_j
            M0 + soma x_j <= capacidade

x_j = kg adicionados do material j; p_j = custo/kg; L_E, U_E = faixa da liga;
rho_E = recuperacao calibrada do elemento (1 quando nao ha calibracao).

Regras (DAS 12.4):
- adicao so aumenta a proporcao de um elemento; excesso de Fe/Cu so se corrige
  diluindo com material pobre nesse elemento (isso emerge das restricoes lineares);
- sem solucao viavel, devolver status INVIAVEL e o elemento que impede;
- mesma entrada, mesma saida, sempre (HiGHS e deterministico).

US-09 (Ruann, Grokoski).
"""
import numpy as np
from scipy.optimize import linprog

from .tipos import (
    ELEMENTOS,
    STATUS_INVIAVEL,
    STATUS_OK,
    Adicao,
    Desvio,
    ResultadoCorrecao,
)
from .versao import VERSAO_MOTOR

# Massa abaixo disso (kg) e ruido do solver, nao uma adicao real.
_EPS = 1e-6
# Folga para a comparacao "dentro da faixa" nao tropecar no arredondamento do solver.
_FOLGA = 1e-6


def calcular_correcao(banho, liga, materiais, recuperacao: dict = None,
                      versao_calibracao: str = None):
    """Correcao de menor custo para enquadrar o banho na liga-alvo (DAS 12.2).

    Devolve um ResultadoCorrecao. status=OK traz as adicoes em kg, a composicao
    prevista, os desvios por elemento e o custo total. status=INVIAVEL traz o
    elemento_limitante que impede a solucao dentro do estoque e da capacidade.
    """
    recuperacao = recuperacao or {}
    n = len(materiais)

    # Sem materiais: so da para aceitar o banho como esta.
    if n == 0:
        return _resultado_sem_adicao(banho, liga, versao_calibracao)

    custo = [float(m.custo_kg) for m in materiais]
    bounds = [(0.0, float(m.estoque_kg)) for m in materiais]
    A_ub, b_ub = _restricoes(banho, liga, materiais, recuperacao)

    solucao = _resolver(custo, A_ub, b_ub, bounds)
    if solucao is not None and solucao.success:
        x = solucao.x
        adicoes = [Adicao(materiais[j].id, float(x[j]))
                   for j in range(n) if x[j] > _EPS]
        prevista = _composicao_prevista(banho, materiais, x, recuperacao, liga)
        desvios = [_desvio(f, prevista) for f in liga.faixas]
        custo_total = float(sum(custo[j] * x[j] for j in range(n)))
        return ResultadoCorrecao(
            status=STATUS_OK,
            adicoes=adicoes,
            composicao_prevista=prevista,
            desvios=desvios,
            custo_total=custo_total,
            versao_motor=VERSAO_MOTOR,
            versao_calibracao=versao_calibracao,
        )

    limitante = _elemento_limitante(banho, liga, materiais, recuperacao,
                                    custo, bounds)
    return ResultadoCorrecao(
        status=STATUS_INVIAVEL,
        composicao_prevista=_composicao_prevista(banho, materiais,
                                                 np.zeros(n), recuperacao, liga),
        elemento_limitante=limitante,
        versao_motor=VERSAO_MOTOR,
        versao_calibracao=versao_calibracao,
    )


def _restricoes(banho, liga, materiais, recuperacao, ignorar=None):
    """Monta A_ub e b_ub das faixas (duas linhas por elemento) e da capacidade."""
    M0 = float(banho.massa_kg)
    A_ub, b_ub = [], []
    for f in liga.faixas:
        if ignorar is not None and f.elemento == ignorar:
            continue
        rho = float(recuperacao.get(f.elemento, 1.0))
        c0 = banho.teor(f.elemento)
        # Limite inferior: soma x_j*(L - c_j*rho) <= M0*(c0 - L)
        A_ub.append([f.min_pct - m.teor(f.elemento) * rho for m in materiais])
        b_ub.append(M0 * (c0 - f.min_pct))
        # Limite superior: soma x_j*(c_j*rho - U) <= M0*(U - c0)
        A_ub.append([m.teor(f.elemento) * rho - f.max_pct for m in materiais])
        b_ub.append(M0 * (f.max_pct - c0))
    cap = float(banho.capacidade_kg)
    if cap > 0:
        A_ub.append([1.0] * len(materiais))
        b_ub.append(cap - M0)
    return A_ub, b_ub


def _resolver(custo, A_ub, b_ub, bounds):
    """Resolve a PL com HiGHS. A_ub vazio vira None (so restricoes de caixa)."""
    A = np.array(A_ub, dtype=float) if A_ub else None
    b = np.array(b_ub, dtype=float) if b_ub else None
    return linprog(c=custo, A_ub=A, b_ub=b, bounds=bounds, method="highs")


def _composicao_prevista(banho, materiais, x, recuperacao, liga):
    """Teor previsto por elemento apos as adicoes (mesmo modelo das restricoes).

    C_E = (M0*c0_E + soma x_j*c_j,E*rho_E) / (M0 + soma x_j). O banho conta
    integralmente; as adicoes contam pela recuperacao rho_E do elemento.
    """
    M0 = float(banho.massa_kg)
    total = M0 + float(sum(x))
    if total <= 0:  # pragma: no cover - guarda: banho real sempre tem massa > 0
        return {}
    elementos = set(banho.composicao) | {f.elemento for f in liga.faixas}
    for m in materiais:
        elementos |= set(m.composicao)
    elementos &= set(ELEMENTOS)

    prevista = {}
    for E in sorted(elementos):
        rho = float(recuperacao.get(E, 1.0))
        num = banho.teor(E) * M0 + sum(
            x[j] * materiais[j].teor(E) * rho for j in range(len(materiais))
        )
        prevista[E] = num / total
    return prevista


def _desvio(faixa, prevista):
    teor = float(prevista.get(faixa.elemento, 0.0))
    dentro = faixa.min_pct - _FOLGA <= teor <= faixa.max_pct + _FOLGA
    return Desvio(faixa.elemento, teor, faixa.min_pct, faixa.max_pct, dentro)


def _elemento_limitante(banho, liga, materiais, recuperacao, custo, bounds):
    """Elemento que impede a solucao: aquele cuja retirada torna o problema viavel.

    Testa cada elemento da faixa, em ordem. Se nenhum sozinho resolve, devolve o
    primeiro da faixa (fallback deterministico).
    """
    for faixa in liga.faixas:
        A_ub, b_ub = _restricoes(banho, liga, materiais, recuperacao,
                                 ignorar=faixa.elemento)
        solucao = _resolver(custo, A_ub, b_ub, bounds)
        if solucao is not None and solucao.success:
            return faixa.elemento
    return liga.faixas[0].elemento if liga.faixas else None


def _resultado_sem_adicao(banho, liga, versao_calibracao):
    """Sem materiais disponiveis: aceita o banho se ja estiver na faixa."""
    prevista = dict(banho.composicao)
    desvios = [_desvio(f, prevista) for f in liga.faixas]
    dentro = all(d.dentro for d in desvios)
    limitante = None if dentro else next(
        (d.elemento for d in desvios if not d.dentro), None)
    return ResultadoCorrecao(
        status=STATUS_OK if dentro else STATUS_INVIAVEL,
        composicao_prevista=prevista,
        desvios=desvios,
        elemento_limitante=limitante,
        versao_motor=VERSAO_MOTOR,
        versao_calibracao=versao_calibracao,
    )
