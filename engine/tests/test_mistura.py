"""Testes do calculo de mistura (US-07).

Cobrem: mistura simples, efeito do rendimento, mistura vazia, elemento ausente,
determinismo e o recorte por elementos controlados.
"""
import pytest

from liga_engine.mistura import composicao_mistura
from liga_engine.tipos import ELEMENTOS, Material


def _material(id, comp, rendimento=1.0):
    return Material(id=id, nome=id, composicao=comp, rendimento=rendimento)


def test_mistura_simples():
    # Duas massas iguais de teores 10% e 20% em Si, rendimento 1 -> media 15%.
    a = _material("a", {"Si": 10.0})
    b = _material("b", {"Si": 20.0})
    resultado = composicao_mistura([(a, 100.0), (b, 100.0)], elementos=("Si",))
    assert resultado["Si"] == pytest.approx(15.0, abs=0.01)


def test_efeito_do_rendimento():
    # O material com rendimento 0.5 pesa metade no calculo:
    # num = 100*10*1 + 100*20*0.5 = 2000; den = 100*1 + 100*0.5 = 150 -> 13.333%.
    a = _material("a", {"Si": 10.0}, rendimento=1.0)
    b = _material("b", {"Si": 20.0}, rendimento=0.5)
    resultado = composicao_mistura([(a, 100.0), (b, 100.0)], elementos=("Si",))
    assert resultado["Si"] == pytest.approx(2000.0 / 150.0, abs=0.01)


def test_elemento_ausente_conta_como_zero():
    # b nao tem Si; entra como 0. num = 100*10 + 100*0 = 1000; den = 200 -> 5%.
    a = _material("a", {"Si": 10.0})
    b = _material("b", {"Fe": 0.3})
    resultado = composicao_mistura([(a, 100.0), (b, 100.0)], elementos=("Si",))
    assert resultado["Si"] == pytest.approx(5.0, abs=0.01)


def test_mistura_vazia_devolve_dicionario_vazio():
    assert composicao_mistura([]) == {}


def test_massa_total_zero_devolve_dicionario_vazio():
    a = _material("a", {"Si": 10.0})
    assert composicao_mistura([(a, 0.0)]) == {}


def test_rendimento_zero_devolve_dicionario_vazio():
    a = _material("a", {"Si": 10.0}, rendimento=0.0)
    assert composicao_mistura([(a, 100.0)]) == {}


def test_usa_todos_os_elementos_controlados_por_padrao():
    a = _material("a", {"Si": 7.0, "Mg": 0.3})
    resultado = composicao_mistura([(a, 100.0)])
    assert set(resultado) == set(ELEMENTOS)
    # Al nao entra na lista de controlados (e o restante ate 100%).
    assert "Al" not in resultado


def test_deterministico():
    a = _material("a", {"Si": 6.5, "Fe": 0.12})
    b = _material("b", {"Si": 20.0, "Fe": 0.15}, rendimento=0.97)
    itens = [(a, 900.0), (b, 30.0)]
    assert composicao_mistura(itens) == composicao_mistura(itens)
