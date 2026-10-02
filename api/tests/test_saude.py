"""Teste de fumaca da API.

Verifica que o endpoint /saude responde e que a aplicacao inicializa corretamente.
"""
from fastapi.testclient import TestClient

from app.main import app

cliente = TestClient(app)


def test_saude():
    assert cliente.get("/saude").json() == {"status": "ok"}


def test_saude_nao_exige_login():
    """O endpoint de saude e publico, nao deve exigir autenticacao."""
    resp = cliente.get("/saude")
    assert resp.status_code == 200
