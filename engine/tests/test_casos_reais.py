"""Roda todos os casos de engine/tests/casos_reais (US-08).

Cada arquivo .json e uma corrida validada pelo engenheiro do cliente. Se um caso
divergir, o build falha. Nunca ajuste o caso para o motor passar: ajuste o motor,
ou confirme o caso com o cliente. Tolerancia: 0,01 p.p.

TODO US-08: ler os arquivos, montar a entrada do motor e comparar com o esperado.
"""
from pathlib import Path

PASTA = Path(__file__).parent / "casos_reais"
TOLERANCIA = 0.01


def test_existe_pelo_menos_um_caso():
    assert list(PASTA.glob("*.json")), "Nenhum caso em tests/casos_reais (US-08)"
