"""Roda todos os casos de engine/tests/casos_reais (US-08).

Cada arquivo .json e uma corrida validada pelo engenheiro do cliente. Se um caso
divergir, o build falha. Nunca ajuste o caso para o motor passar: ajuste o motor,
ou confirme o caso com o cliente. Tolerancia: 0,01 p.p.

Formato do arquivo: ver engine/tests/casos_reais/ficticio-001.json e o README da
pasta. Chaves usadas: liga (com faixas), materiais, banho, esperado (status,
composicao_prevista e, opcionalmente, elemento_limitante). recuperacao e opcional.
"""
import json
from pathlib import Path

import pytest

from liga_engine.correcao import calcular_correcao
from liga_engine.tipos import Banho, Faixa, Liga, Material

PASTA = Path(__file__).parent / "casos_reais"
TOLERANCIA = 0.01
ARQUIVOS = sorted(PASTA.glob("*.json"))


def _monta_entrada(caso):
    """Constroi banho, liga, materiais e recuperacao a partir do JSON do caso."""
    liga = Liga(
        id=caso["liga"]["id"],
        nome=caso["liga"].get("nome", ""),
        norma=caso["liga"].get("norma", ""),
        faixas=tuple(
            Faixa(f["elemento"], f["min_pct"], f["max_pct"])
            for f in caso["liga"]["faixas"]
        ),
    )
    materiais = [
        Material(
            id=m["id"],
            nome=m.get("nome", m["id"]),
            tipo=m.get("tipo", "INSUMO"),
            composicao=m.get("composicao", {}),
            custo_kg=m.get("custo_kg", 0.0),
            estoque_kg=m.get("estoque_kg", 0.0),
            rendimento=m.get("rendimento", 1.0),
        )
        for m in caso["materiais"]
    ]
    b = caso["banho"]
    banho = Banho(
        massa_kg=b["massa_kg"],
        composicao=b.get("composicao", {}),
        capacidade_kg=b.get("capacidade_kg", 0.0),
    )
    return banho, liga, materiais, caso.get("recuperacao")


def test_existe_pelo_menos_um_caso():
    assert ARQUIVOS, "Nenhum caso em tests/casos_reais (US-08)"


@pytest.mark.parametrize("arquivo", ARQUIVOS, ids=[a.stem for a in ARQUIVOS])
def test_caso_real(arquivo):
    caso = json.loads(arquivo.read_text(encoding="utf-8"))
    banho, liga, materiais, recuperacao = _monta_entrada(caso)

    resultado = calcular_correcao(banho, liga, materiais, recuperacao=recuperacao)
    esperado = caso["esperado"]

    assert resultado.status == esperado["status"], (
        f"{arquivo.name}: status {resultado.status} != {esperado['status']}"
    )

    for elemento, valor in esperado.get("composicao_prevista", {}).items():
        obtido = resultado.composicao_prevista.get(elemento)
        assert obtido == pytest.approx(valor, abs=TOLERANCIA), (
            f"{arquivo.name}: {elemento} previsto {obtido} != esperado {valor} "
            f"(tolerancia {TOLERANCIA} p.p.)"
        )

    if "elemento_limitante" in esperado:
        assert resultado.elemento_limitante == esperado["elemento_limitante"], (
            f"{arquivo.name}: elemento_limitante {resultado.elemento_limitante} "
            f"!= esperado {esperado['elemento_limitante']}"
        )
