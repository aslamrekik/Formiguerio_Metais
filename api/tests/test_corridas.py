"""US-14: salvar corrida, imutabilidade da confirmada e historico filtravel.

Usa SQLite em memoria. O trigger do PostgreSQL nao roda aqui; a regra e coberta
pelo service (409) e o trigger deve ser conferido no staging.
"""
from datetime import datetime, timezone

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.db import Base, get_db
from app.main import app
from app.models import Corrida
from app.routers.corridas import usuario_atual
from liga_engine.versao import VERSAO_MOTOR

CORRIDA = {
    "liga_id": "A356",
    "entrada": {"massa_kg": 1000, "composicao": {"Si": 6.1, "Mg": 0.3}},
    "resultado": {"status": "OK", "adicoes": [{"material": "Al-Si 20%", "kg": 35}]},
    "explicacao": "Adicionar 35 kg de Al-Si 20% para levar o Si a 6,5%.",
}


@pytest.fixture()
def sessao():
    motor = create_engine("sqlite://", connect_args={"check_same_thread": False},
                          poolclass=StaticPool)
    Base.metadata.create_all(motor)
    Sessao = sessionmaker(bind=motor, expire_on_commit=False)
    with Sessao() as s:
        yield s


@pytest.fixture()
def cliente(sessao):
    app.dependency_overrides[get_db] = lambda: sessao
    app.dependency_overrides[usuario_atual] = lambda: "admin-1"
    yield TestClient(app)
    app.dependency_overrides.clear()


def _salvar(cliente, **extra):
    r = cliente.post("/corridas", json={**CORRIDA, **extra})
    assert r.status_code == 201, r.text
    return r.json()


def test_exige_login(sessao):
    app.dependency_overrides[get_db] = lambda: sessao
    try:
        assert TestClient(app).get("/corridas").status_code == 401
    finally:
        app.dependency_overrides.clear()


def test_salva_com_tudo_o_que_o_criterio_pede(cliente):
    c = _salvar(cliente)
    assert c["status"] == "RASCUNHO"
    assert c["entrada"] == CORRIDA["entrada"]
    assert c["resultado"] == CORRIDA["resultado"]
    assert c["explicacao"] == CORRIDA["explicacao"]
    assert c["usuario_id"] == "admin-1"
    assert c["versao_motor"] == VERSAO_MOTOR
    assert c["versao_calibracao"] == 0


def test_cliente_nao_escolhe_versao_nem_usuario(cliente):
    c = _salvar(cliente, versao_motor="9.9.9", usuario_id="outro", versao_calibracao=7)
    assert c["versao_motor"] == VERSAO_MOTOR
    assert c["usuario_id"] == "admin-1"
    assert c["versao_calibracao"] == 0


def test_confirmar_muda_estado(cliente):
    c = _salvar(cliente)
    r = cliente.post(f"/corridas/{c['id']}/confirmar")
    assert r.status_code == 200
    assert r.json()["status"] == "CONFIRMADA"
    assert r.json()["confirmada_em"] is not None


def test_confirmada_nao_pode_ser_apagada(cliente):
    c = _salvar(cliente)
    cliente.post(f"/corridas/{c['id']}/confirmar")
    assert cliente.delete(f"/corridas/{c['id']}").status_code == 409
    assert cliente.get(f"/corridas/{c['id']}").status_code == 200


def test_confirmada_nao_pode_ser_confirmada_de_novo(cliente):
    c = _salvar(cliente)
    cliente.post(f"/corridas/{c['id']}/confirmar")
    assert cliente.post(f"/corridas/{c['id']}/confirmar").status_code == 409


def test_nao_existe_rota_para_alterar_corrida(cliente):
    c = _salvar(cliente)
    cliente.post(f"/corridas/{c['id']}/confirmar")
    assert cliente.put(f"/corridas/{c['id']}", json=CORRIDA).status_code == 405
    assert cliente.patch(f"/corridas/{c['id']}", json=CORRIDA).status_code == 405


def test_rascunho_pode_ser_apagado(cliente):
    c = _salvar(cliente)
    assert cliente.delete(f"/corridas/{c['id']}").status_code == 204
    assert cliente.get(f"/corridas/{c['id']}").status_code == 404


def test_corrida_inexistente(cliente):
    inexistente = "00000000-0000-0000-0000-000000000000"
    assert cliente.get(f"/corridas/{inexistente}").status_code == 404
    assert cliente.post(f"/corridas/{inexistente}/confirmar").status_code == 404


def test_historico_filtra_por_liga_e_periodo(cliente, sessao):
    def criar(liga, dia):
        sessao.add(Corrida(liga_id=liga, usuario_id="admin-1", entrada={}, resultado={},
                           versao_motor=VERSAO_MOTOR, versao_calibracao=0,
                           criada_em=datetime(2026, 10, dia, 12, 0, tzinfo=timezone.utc)))
    criar("A356", 1); criar("A356", 10); criar("A356", 20); criar("A380", 10)
    sessao.commit()

    todas = cliente.get("/corridas").json()
    assert todas["total"] == 4

    a356 = cliente.get("/corridas", params={"liga_id": "A356"}).json()
    assert a356["total"] == 3 and {i["liga_id"] for i in a356["itens"]} == {"A356"}

    periodo = cliente.get("/corridas", params={"liga_id": "A356", "de": "2026-10-05",
                                               "ate": "2026-10-15"}).json()
    assert periodo["total"] == 1

    # datas inclusivas: o dia 10 aparece quando de = ate = 10
    assert cliente.get("/corridas", params={"de": "2026-10-10", "ate": "2026-10-10"}).json()["total"] == 2


def test_historico_ordena_da_mais_recente_e_pagina(cliente, sessao):
    for dia in (1, 2, 3):
        sessao.add(Corrida(liga_id="A356", usuario_id="admin-1", entrada={}, resultado={},
                           versao_motor=VERSAO_MOTOR, versao_calibracao=0,
                           criada_em=datetime(2026, 10, dia, tzinfo=timezone.utc)))
    sessao.commit()
    pagina = cliente.get("/corridas", params={"limite": 2}).json()
    assert pagina["total"] == 3 and len(pagina["itens"]) == 2
    assert pagina["itens"][0]["criada_em"] > pagina["itens"][1]["criada_em"]


def test_periodo_invertido_e_rejeitado(cliente):
    r = cliente.get("/corridas", params={"de": "2026-10-20", "ate": "2026-10-01"})
    assert r.status_code == 422
