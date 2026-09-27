"""Testes dos tipos de dominio (US-07)."""
from liga_engine.tipos import (
    VERSAO_MOTOR,
    Banho,
    Faixa,
    Liga,
    Material,
    ResultadoCorrecao,
    STATUS_OK,
)


def _liga_a356():
    faixas = (
        Faixa("Si", 6.5, 7.5),
        Faixa("Mg", 0.25, 0.45),
        Faixa("Fe", 0.0, 0.2),
    )
    return Liga(id="a356", nome="A356", norma="AA/ASTM B26", faixas=faixas)


def test_material_teor_presente_e_ausente():
    m = Material(id="m", nome="m", composicao={"Si": 20.0})
    assert m.teor("Si") == 20.0
    assert m.teor("Cu") == 0.0


def test_banho_teor():
    b = Banho(massa_kg=1000.0, composicao={"Si": 6.15}, capacidade_kg=1500.0)
    assert b.teor("Si") == 6.15
    assert b.teor("Mg") == 0.0


def test_liga_faixa_de():
    liga = _liga_a356()
    assert liga.faixa_de("Si").max_pct == 7.5
    assert liga.faixa_de("Cu") is None


def test_dentro_da_faixa_ok():
    liga = _liga_a356()
    assert liga.dentro_da_faixa({"Si": 7.0, "Mg": 0.33, "Fe": 0.12})


def test_dentro_da_faixa_abaixo_do_minimo():
    liga = _liga_a356()
    assert not liga.dentro_da_faixa({"Si": 6.0, "Mg": 0.33, "Fe": 0.12})


def test_dentro_da_faixa_acima_do_maximo():
    liga = _liga_a356()
    assert not liga.dentro_da_faixa({"Si": 7.0, "Mg": 0.33, "Fe": 0.5})


def test_dentro_da_faixa_com_tolerancia():
    liga = _liga_a356()
    # 7.505 estoura por 0.005, mas passa com tolerancia de 0.01.
    assert liga.dentro_da_faixa({"Si": 7.505, "Mg": 0.33, "Fe": 0.12}, tolerancia=0.01)


def test_resultado_correcao_guarda_versao_do_motor():
    r = ResultadoCorrecao(status=STATUS_OK)
    assert r.versao_motor == VERSAO_MOTOR
    assert r.versao_calibracao is None
    assert r.adicoes == []
