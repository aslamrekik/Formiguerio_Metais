"""Protege a regra mais importante da arquitetura (DAS 9.3).

O engine e Python puro: nao pode importar nada da api, nem banco, nem rede.
"""
from pathlib import Path

ENGINE = Path(__file__).resolve().parents[2] / "engine" / "liga_engine"
PROIBIDOS = ("from app", "import app", "sqlalchemy", "httpx", "requests", "fastapi")


def test_engine_nao_depende_da_api():
    for arquivo in ENGINE.rglob("*.py"):
        texto = arquivo.read_text(encoding="utf-8")
        for termo in PROIBIDOS:
            assert termo not in texto, f"{arquivo.name} nao pode usar {termo}"
