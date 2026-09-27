"""Testes da correcao de menor custo (US-09).

Cobrem: reposicao de elemento abaixo da faixa, diluicao de elemento acima do
limite, caso inviavel com elemento limitante, escolha da opcao mais barata,
respeito a estoque/capacidade e reprodutibilidade.
"""
import pytest

from liga_engine.correcao import calcular_correcao
from liga_engine.tipos import (
    STATUS_INVIAVEL,
    STATUS_OK,
    Banho,
    Faixa,
    Liga,
    Material,
)

# Materiais base (do exemplos/materias-primas.csv).
AL_PRIM = Material(id="al-prim", nome="Aluminio primario",
                   composicao={"Si": 0.05, "Fe": 0.06}, custo_kg=18.0,
                   estoque_kg=2000.0)
AL_SI_20 = Material(id="al-si-20", nome="Liga-mae Al-Si 20%",
                    composicao={"Si": 20.0, "Fe": 0.15}, custo_kg=26.0,
                    estoque_kg=500.0)


def _adicoes(resultado):
    return {a.material_id: a.massa_kg for a in resultado.adicoes}


def test_repoe_elemento_abaixo_da_faixa():
    # Caso ficticio-001: Si em 6,15 precisa subir para dentro de [6,5; 7,5].
    liga = Liga(id="a356", nome="A356", faixas=(
        Faixa("Si", 6.5, 7.5), Faixa("Mg", 0.25, 0.45), Faixa("Fe", 0.0, 0.2)))
    banho = Banho(massa_kg=1000.0,
                  composicao={"Si": 6.15, "Mg": 0.33, "Fe": 0.12},
                  capacidade_kg=1500.0)

    r = calcular_correcao(banho, liga, [AL_PRIM, AL_SI_20])

    assert r.status == STATUS_OK
    assert r.composicao_prevista["Si"] == pytest.approx(6.5, abs=0.01)
    assert r.composicao_prevista["Mg"] == pytest.approx(0.32, abs=0.01)
    assert r.composicao_prevista["Fe"] == pytest.approx(0.12, abs=0.01)
    # So faz sentido adicionar a liga-mae rica em Si, nao diluir com primario.
    assert _adicoes(r).get("al-si-20", 0) > 0
    assert "al-prim" not in _adicoes(r)
    assert all(d.dentro for d in r.desvios)


def test_dilui_elemento_acima_do_limite():
    # Fe acima do maximo; a unica saida e diluir com material pobre em Fe.
    liga = Liga(id="fe", nome="controla Fe", faixas=(Faixa("Fe", 0.0, 0.2),))
    banho = Banho(massa_kg=1000.0, composicao={"Fe": 0.25}, capacidade_kg=3000.0)

    r = calcular_correcao(banho, liga, [AL_PRIM])

    assert r.status == STATUS_OK
    assert r.composicao_prevista["Fe"] <= 0.2 + 1e-6
    assert _adicoes(r)["al-prim"] > 0


def test_inviavel_informa_elemento_limitante():
    # Nenhum material chega a Si 21%: mesmo Al-Si 20% puro dilui abaixo disso.
    liga = Liga(id="x", nome="impossivel", faixas=(Faixa("Si", 21.0, 25.0),))
    banho = Banho(massa_kg=1000.0, composicao={"Si": 6.0}, capacidade_kg=5000.0)

    r = calcular_correcao(banho, liga, [AL_SI_20])

    assert r.status == STATUS_INVIAVEL
    assert r.elemento_limitante == "Si"
    assert r.adicoes == []


def test_escolhe_a_opcao_mais_barata():
    # Duas ligas-mae equivalentes em Si; deve usar a mais barata.
    barata = Material(id="barata", nome="Al-Si barata",
                      composicao={"Si": 20.0}, custo_kg=26.0, estoque_kg=500.0)
    cara = Material(id="cara", nome="Al-Si cara",
                    composicao={"Si": 20.0}, custo_kg=40.0, estoque_kg=500.0)
    liga = Liga(id="si", nome="controla Si", faixas=(Faixa("Si", 6.5, 7.5),))
    banho = Banho(massa_kg=1000.0, composicao={"Si": 6.15}, capacidade_kg=1500.0)

    r = calcular_correcao(banho, liga, [cara, barata])

    assert r.status == STATUS_OK
    assert "barata" in _adicoes(r)
    assert "cara" not in _adicoes(r)


def test_respeita_o_estoque():
    # Estoque insuficiente da unica fonte de Si -> inviavel por Si.
    pouco = Material(id="pouco", nome="Al-Si pouco",
                     composicao={"Si": 20.0}, custo_kg=26.0, estoque_kg=5.0)
    liga = Liga(id="si", nome="controla Si", faixas=(Faixa("Si", 6.5, 7.5),))
    banho = Banho(massa_kg=1000.0, composicao={"Si": 6.15}, capacidade_kg=1500.0)

    r = calcular_correcao(banho, liga, [pouco])

    assert r.status == STATUS_INVIAVEL
    assert r.elemento_limitante == "Si"


def test_respeita_a_capacidade():
    # Capacidade quase esgotada nao deixa adicionar o suficiente -> inviavel.
    liga = Liga(id="si", nome="controla Si", faixas=(Faixa("Si", 6.5, 7.5),))
    banho = Banho(massa_kg=1000.0, composicao={"Si": 6.15}, capacidade_kg=1010.0)

    r = calcular_correcao(banho, liga, [AL_SI_20])

    assert r.status == STATUS_INVIAVEL
    assert r.elemento_limitante == "Si"


def test_banho_ja_dentro_nao_adiciona_nada():
    liga = Liga(id="si", nome="controla Si", faixas=(Faixa("Si", 6.5, 7.5),))
    banho = Banho(massa_kg=1000.0, composicao={"Si": 7.0}, capacidade_kg=1500.0)

    r = calcular_correcao(banho, liga, [AL_SI_20])

    assert r.status == STATUS_OK
    assert r.adicoes == []
    assert r.custo_total == 0.0


def test_sem_materiais_aceita_banho_dentro_da_faixa():
    liga = Liga(id="si", nome="controla Si", faixas=(Faixa("Si", 6.5, 7.5),))
    dentro = Banho(massa_kg=1000.0, composicao={"Si": 7.0})
    fora = Banho(massa_kg=1000.0, composicao={"Si": 6.0})

    assert calcular_correcao(dentro, liga, []).status == STATUS_OK
    r = calcular_correcao(fora, liga, [])
    assert r.status == STATUS_INVIAVEL
    assert r.elemento_limitante == "Si"


def test_grava_versao_do_motor_e_da_calibracao():
    liga = Liga(id="si", nome="controla Si", faixas=(Faixa("Si", 6.5, 7.5),))
    banho = Banho(massa_kg=1000.0, composicao={"Si": 6.15}, capacidade_kg=1500.0)

    r = calcular_correcao(banho, liga, [AL_SI_20], versao_calibracao="cal-3")

    assert r.versao_motor  # nao vazio
    assert r.versao_calibracao == "cal-3"


def test_reprodutibilidade_mesma_entrada_mesma_saida():
    liga = Liga(id="a356", nome="A356", faixas=(
        Faixa("Si", 6.5, 7.5), Faixa("Mg", 0.25, 0.45), Faixa("Fe", 0.0, 0.2)))
    banho = Banho(massa_kg=1000.0,
                  composicao={"Si": 6.15, "Mg": 0.33, "Fe": 0.12},
                  capacidade_kg=1500.0)

    r1 = calcular_correcao(banho, liga, [AL_PRIM, AL_SI_20])
    r2 = calcular_correcao(banho, liga, [AL_PRIM, AL_SI_20])

    assert _adicoes(r1) == _adicoes(r2)
    assert r1.composicao_prevista == r2.composicao_prevista


def test_duas_faixas_inviaveis_usa_fallback():
    # Si e Mn ambos inalcancaveis; nenhum sozinho resolve -> fallback na 1a faixa.
    liga = Liga(id="x", nome="dupla", faixas=(
        Faixa("Si", 21.0, 25.0), Faixa("Mn", 50.0, 60.0)))
    banho = Banho(massa_kg=1000.0, composicao={"Si": 6.0, "Mn": 0.1},
                  capacidade_kg=5000.0)

    r = calcular_correcao(banho, liga, [AL_SI_20])

    assert r.status == STATUS_INVIAVEL
    assert r.elemento_limitante == "Si"


def test_calibracao_muda_o_resultado():
    # Recuperacao de Si menor exige adicionar mais liga-mae.
    liga = Liga(id="si", nome="controla Si", faixas=(Faixa("Si", 6.5, 7.5),))
    banho = Banho(massa_kg=1000.0, composicao={"Si": 6.15}, capacidade_kg=2000.0)

    sem = calcular_correcao(banho, liga, [AL_SI_20])
    com = calcular_correcao(banho, liga, [AL_SI_20], recuperacao={"Si": 0.8})

    assert com.status == STATUS_OK
    assert _adicoes(com)["al-si-20"] > _adicoes(sem)["al-si-20"]
