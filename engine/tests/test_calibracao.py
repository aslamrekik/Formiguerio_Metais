"""Testes da calibracao (US-17).

Cobrem: minimo de corridas, media das recuperacoes, limites 0,50 e 1,05, ganho
pequeno ignorado, peso maior para corridas recentes e o teste comparativo do
Trello (erro menor COM calibracao do que SEM).
"""
import pytest

from liga_engine.calibracao import RHO_MAX, RHO_MIN, calcular_fatores
from liga_engine.tipos import CorridaFinalizada, Material

AL_SI = Material(id="al-si-20", nome="Liga-mae Al-Si 20%",
                 composicao={"Si": 20.0}, custo_kg=26.0, estoque_kg=500.0)


def corrida(rho_real, m0=1000.0, c0=6.0, x=30.0, elemento="Si", data=None):
    """Corrida finalizada em que o elemento teve recuperacao real 'rho_real'.

    A massa entra inteira (Mf = M0 + x); o elemento aparece na final so na fracao
    rho_real do que foi adicionado - e assim que o motor modela a recuperacao.
    """
    mf = m0 + x
    cf = (m0 * c0 + rho_real * x * AL_SI.teor(elemento)) / mf
    return CorridaFinalizada(
        massa_inicial=m0, composicao_inicial={elemento: c0},
        massa_final=mf, composicao_final={elemento: cf},
        adicoes=((AL_SI, x),), data=data,
    )


def test_minimo_de_cinco_corridas():
    quatro = [corrida(0.8) for _ in range(4)]
    assert calcular_fatores(quatro) == {}


def test_media_das_recuperacoes():
    corridas = [corrida(0.8) for _ in range(5)]
    fatores = calcular_fatores(corridas)
    assert fatores["Si"] == pytest.approx(0.8, abs=1e-6)


def test_limite_superior():
    corridas = [corrida(1.30) for _ in range(5)]  # rho real 1,30
    assert calcular_fatores(corridas)["Si"] == pytest.approx(RHO_MAX)


def test_limite_inferior():
    corridas = [corrida(0.30) for _ in range(5)]  # rho real 0,30
    assert calcular_fatores(corridas)["Si"] == pytest.approx(RHO_MIN)


def test_ganho_pequeno_e_ignorado():
    # Adicao minuscula (0,02 p.p. ou menos) nao entra: Si fica de fora.
    corridas = [corrida(0.8, x=1.0) for _ in range(5)]
    assert "Si" not in calcular_fatores(corridas)


def test_elemento_nunca_adicionado_fica_de_fora():
    corridas = [corrida(0.8) for _ in range(5)]
    fatores = calcular_fatores(corridas)
    assert "Fe" not in fatores  # nenhuma adicao trouxe Fe


def test_corridas_recentes_pesam_mais():
    # 3 antigas com rho 0,60 e 2 recentes com rho 1,00. A media simples seria
    # 0,76; com peso maior nas recentes, o fator sobe.
    antigas = [corrida(0.60, data=i) for i in range(1, 4)]
    recentes = [corrida(1.00, data=i) for i in range(4, 6)]
    fator = calcular_fatores(antigas + recentes)["Si"]
    assert 0.80 < fator < 0.88


def test_calibracao_reduz_o_erro_previsto_x_real():
    # Criterio de aceite do Trello: erro medio previsto x real menor COM calibracao.
    rho_real = 0.8
    historico = [corrida(rho_real, data=i) for i in range(1, 6)]
    fator = calcular_fatores(historico)["Si"]

    # Nova corrida: 30 kg de Al-Si 20% num banho de 1000 kg com Si 6,0.
    m0, c0, x = 1000.0, 6.0, 30.0
    mf = m0 + x
    adicionado_si = x * AL_SI.teor("Si")

    def prever(rho):
        return (m0 * c0 + rho * adicionado_si) / mf

    real = prever(rho_real)              # o que de fato acontece no forno
    erro_sem = abs(prever(1.0) - real)   # supondo recuperacao total
    erro_com = abs(prever(fator) - real)  # usando o fator calibrado

    assert erro_com < erro_sem
    assert erro_com == pytest.approx(0.0, abs=1e-6)
