"""Teste de fumaca da API.

TODO: cobrir tambem login, cadastros e calculo conforme as historias forem saindo.
"""
from fastapi.testclient import TestClient

from app.main import app

cliente = TestClient(app)


def test_saude():
    assert cliente.get("/saude").json() == {"status": "ok"}
