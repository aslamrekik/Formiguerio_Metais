"""Testes das historias US-03 a US-06: login, materias-primas, ligas e importacao CSV."""
import csv
import io
from unittest.mock import patch

from fastapi.testclient import TestClient

from app.main import app
from app.config import config

cliente = TestClient(app)


# ──────────────────────────────────────────────────────────
# Helpers
# ──────────────────────────────────────────────────────────

def _obter_token() -> str:
    """Faz login e devolve o token Bearer."""
    resp = cliente.post("/auth/login", data={
        "username": config.admin_email,
        "password": config.admin_password,
    })
    assert resp.status_code == 200, resp.text
    return resp.json()["access_token"]


def _headers():
    return {"Authorization": f"Bearer {_obter_token()}"}


# ──────────────────────────────────────────────────────────
# US-03  Login do administrador
# ──────────────────────────────────────────────────────────

class TestLogin:
    def test_login_ok(self):
        resp = cliente.post("/auth/login", data={
            "username": config.admin_email,
            "password": config.admin_password,
        })
        assert resp.status_code == 200
        body = resp.json()
        assert "access_token" in body
        assert body["token_type"] == "bearer"

    def test_login_senha_errada(self):
        resp = cliente.post("/auth/login", data={
            "username": config.admin_email,
            "password": "senha-errada",
        })
        assert resp.status_code == 401

    def test_login_email_errado(self):
        resp = cliente.post("/auth/login", data={
            "username": "ninguem@liga.app",
            "password": config.admin_password,
        })
        assert resp.status_code == 401

    def test_rotas_sem_token_retornam_401(self):
        """Rotas protegidas devem retornar 401 sem autenticação."""
        rotas = [
            ("GET", "/materias-primas"),
            ("POST", "/materias-primas"),
            ("GET", "/ligas"),
            ("POST", "/ligas"),
        ]
        for metodo, rota in rotas:
            resp = getattr(cliente, metodo.lower())(rota)
            assert resp.status_code == 401, f"{metodo} {rota} deveria dar 401"


# ──────────────────────────────────────────────────────────
# US-04  Cadastro de matérias-primas
# ──────────────────────────────────────────────────────────

class TestMateriaPrima:
    MATERIA_VALIDA = {
        "nome": "Aluminio puro teste",
        "tipo": "ALUMINIO_PRIMARIO",
        "custo_kg": 18.0,
        "estoque_kg": 1000,
        "rendimento": 0.98,
        "composicoes": [
            {"elemento": "Si", "percentual": 0.05},
            {"elemento": "Fe", "percentual": 0.06},
        ]
    }

    def test_criar_materia_prima(self):
        resp = cliente.post("/materias-primas", json=self.MATERIA_VALIDA, headers=_headers())
        assert resp.status_code == 201
        body = resp.json()
        assert body["nome"] == "Aluminio puro teste"
        assert body["tipo"] == "ALUMINIO_PRIMARIO"
        # Deve ter Si, Fe e Al (autocomputado)
        elementos = {c["elemento"] for c in body["composicoes"]}
        assert "Al" in elementos

    def test_soma_elementos_com_al_deve_ser_100(self):
        """Se os elementos não-Al somarem mais que 100.01, deve rejeitar."""
        materia = {
            **self.MATERIA_VALIDA,
            "nome": "Impossivel",
            "composicoes": [
                {"elemento": "Si", "percentual": 60},
                {"elemento": "Fe", "percentual": 50},
            ]
        }
        resp = cliente.post("/materias-primas", json=materia, headers=_headers())
        assert resp.status_code == 422

    def test_valores_negativos_rejeitados(self):
        materia = {
            **self.MATERIA_VALIDA,
            "nome": "Negativo",
            "custo_kg": -5,
        }
        resp = cliente.post("/materias-primas", json=materia, headers=_headers())
        assert resp.status_code == 422

    def test_listar_materias_primas(self):
        resp = cliente.get("/materias-primas", headers=_headers())
        assert resp.status_code == 200
        assert isinstance(resp.json(), list)

    def test_tipos_validos(self):
        """Apenas os tipos definidos devem ser aceitos."""
        for tipo in ["SUCATA", "LIGA_MAE", "INSUMO", "ALUMINIO_PRIMARIO"]:
            materia = {
                **self.MATERIA_VALIDA,
                "nome": f"Teste tipo {tipo}",
                "tipo": tipo,
            }
            resp = cliente.post("/materias-primas", json=materia, headers=_headers())
            assert resp.status_code == 201, f"Tipo {tipo} deveria ser aceito"

    def test_tipo_invalido_rejeitado(self):
        materia = {
            **self.MATERIA_VALIDA,
            "nome": "Tipo invalido",
            "tipo": "INEXISTENTE",
        }
        resp = cliente.post("/materias-primas", json=materia, headers=_headers())
        assert resp.status_code == 422


# ──────────────────────────────────────────────────────────
# US-05  Importar matérias-primas via CSV
# ──────────────────────────────────────────────────────────

class TestImportacaoCSV:
    def test_importar_csv_valido(self):
        csv_conteudo = (
            "nome,tipo,custo_kg,estoque_kg,rendimento,Si,Fe,Cu,Mn,Mg,Zn,Ti\n"
            "CSV Puro,ALUMINIO_PRIMARIO,18.00,2000,0.98,0.05,0.06,0.01,0,0,0,0.01\n"
        )
        arquivo = io.BytesIO(csv_conteudo.encode("utf-8"))
        resp = cliente.post(
            "/materias-primas/importar",
            files={"arquivo": ("materias.csv", arquivo, "text/csv")},
            headers=_headers(),
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["importadas"] >= 1
        assert len(body["erros"]) == 0

    def test_linhas_invalidas_retornam_numero_e_motivo(self):
        csv_conteudo = (
            "nome,tipo,custo_kg,estoque_kg,rendimento,Si,Fe,Cu,Mn,Mg,Zn,Ti\n"
            "Valido,ALUMINIO_PRIMARIO,18.00,2000,0.98,0.05,0.06,0.01,0,0,0,0.01\n"
            "Invalido,TIPO_ERRADO,18.00,2000,0.98,0.05,0.06,0.01,0,0,0,0.01\n"
        )
        arquivo = io.BytesIO(csv_conteudo.encode("utf-8"))
        resp = cliente.post(
            "/materias-primas/importar",
            files={"arquivo": ("materias.csv", arquivo, "text/csv")},
            headers=_headers(),
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["importadas"] >= 1
        assert len(body["erros"]) >= 1
        # O erro deve ter numero da linha e motivo
        erro = body["erros"][0]
        assert "linha" in erro
        assert "motivo" in erro


# ──────────────────────────────────────────────────────────
# US-06  Cadastro de ligas-alvo
# ──────────────────────────────────────────────────────────

class TestLiga:
    LIGA_VALIDA = {
        "nome": "A356 Teste",
        "norma": "AA/ASTM B26",
        "faixas": [
            {"elemento": "Si", "min_pct": 6.5, "max_pct": 7.5},
            {"elemento": "Mg", "min_pct": 0.25, "max_pct": 0.45},
            {"elemento": "Fe", "min_pct": 0, "max_pct": 0.20},
        ]
    }

    def test_criar_liga(self):
        resp = cliente.post("/ligas", json=self.LIGA_VALIDA, headers=_headers())
        assert resp.status_code == 201
        body = resp.json()
        assert body["nome"] == "A356 Teste"
        assert body["norma"] == "AA/ASTM B26"
        assert len(body["faixas"]) == 3

    def test_minimo_maior_que_maximo_rejeitado(self):
        liga = {
            **self.LIGA_VALIDA,
            "nome": "Liga invertida",
            "faixas": [
                {"elemento": "Si", "min_pct": 8.0, "max_pct": 6.0},
            ]
        }
        resp = cliente.post("/ligas", json=liga, headers=_headers())
        assert resp.status_code == 422

    def test_norma_obrigatoria(self):
        liga = {
            "nome": "Sem norma",
            "norma": "",
            "faixas": [
                {"elemento": "Si", "min_pct": 6.5, "max_pct": 7.5},
            ]
        }
        resp = cliente.post("/ligas", json=liga, headers=_headers())
        assert resp.status_code == 422

    def test_listar_ligas(self):
        resp = cliente.get("/ligas", headers=_headers())
        assert resp.status_code == 200
        assert isinstance(resp.json(), list)

    def test_elemento_duplicado_rejeitado(self):
        liga = {
            **self.LIGA_VALIDA,
            "nome": "Liga dup",
            "faixas": [
                {"elemento": "Si", "min_pct": 6.5, "max_pct": 7.5},
                {"elemento": "Si", "min_pct": 6.0, "max_pct": 7.0},
            ]
        }
        resp = cliente.post("/ligas", json=liga, headers=_headers())
        assert resp.status_code == 422
