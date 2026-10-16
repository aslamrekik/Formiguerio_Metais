"""Testes da explicacao com IA (US-11, US-12, US-13). Sem rede: o Gemini e simulado."""
import json

import pytest

from app.explicacao.contexto import AdicaoCtx, ContextoExplicacao, SemelhanteCtx
from app.explicacao.gemini import ClienteGemini, GeminiIndisponivel, montar_prompt
from app.explicacao.padrao import gerar_explicacao_padrao
from app.explicacao.servico import GEMINI, PADRAO, explicar
from app.explicacao.validador import (FormatoInvalido, checar_formato, extrair_numeros,
                                      validar_explicacao)
from app.services.explicacao import CorridaNaoEncontrada, gerar_explicacao


def contexto(**mudancas) -> ContextoExplicacao:
    base = dict(
        liga="A356",
        faixas={"Si": (6.5, 7.5), "Mg": (0.25, 0.45), "Fe": (0.0, 0.20)},
        banho={"Si": 6.15, "Mg": 0.33, "Fe": 0.23},
        massa_banho_kg=1000.0,
        status="OK",
        adicoes=(
            AdicaoCtx("Alumínio primário", 120.0, "ALUMINIO_PRIMARIO", {"Si": 0.05, "Fe": 0.06}),
            AdicaoCtx("Liga-mãe Al-Si 20%", 18.5, "LIGA_MAE", {"Si": 20.0, "Fe": 0.15}),
        ),
        composicao_prevista={"Si": 6.55, "Mg": 0.30, "Fe": 0.19},
        custo_total=2562.0,
        semelhantes=(
            SemelhanteCtx("0141", {"Si": 6.10, "Mg": 0.30}, {"Si": 6.70, "Mg": 0.38},
                          {"Si": 6.71, "Mg": 0.36}),
            SemelhanteCtx("0150", {"Si": 6.20, "Mg": 0.31}, {"Si": 6.60, "Mg": 0.34},
                          {"Si": 6.60, "Mg": 0.34}),
        ),
    )
    base.update(mudancas)
    return ContextoExplicacao(**base)


def boa_resposta() -> dict:
    return {
        "diagnostico": "Si abaixo da faixa (6,15%) e Fe acima do limite (0,23%).",
        "adicoes": [
            {"material": "Alumínio primário", "massa_kg": 120, "motivo": "diluir o Fe"},
            {"material": "Liga-mãe Al-Si 20%", "massa_kg": 18.5, "motivo": "repor o Si"},
        ],
        "alertas": ["Fe previsto em 0,19%, perto do limite de 0,20%."],
        "referencias": [{"corrida": "0141", "observacao": "Mg ficou 0,02 p.p. abaixo do previsto"}],
    }


def resposta_gemini(texto: str) -> dict:
    return {"candidates": [{"content": {"parts": [{"text": texto}]}}]}


class Transporte:
    """Simula o Gemini: lista de respostas (dict) ou excecoes, uma por chamada."""

    def __init__(self, *respostas):
        self.respostas = list(respostas)
        self.chamadas = []

    def __call__(self, url, cabecalhos, corpo, timeout_s):
        self.chamadas.append((url, cabecalhos, corpo, timeout_s))
        r = self.respostas.pop(0)
        if isinstance(r, Exception):
            raise r
        return r


def cliente(*respostas, chave="chave-teste"):
    t = Transporte(*respostas)
    return ClienteGemini(chave, "gemini-3.8-flash", "gemini-3.5-flash-lite", 15.0, t), t


# ------------------------------------------------------------------ validador (US-11)
def test_extrai_numeros_em_formato_brasileiro_e_ponto():
    achados = {t: v for t, v in extrair_numeros("Si 6,15%, Fe 0.19 e 1.200 kg")}
    assert 6.15 in achados["6,15"] and 0.19 in achados["0.19"]
    assert 1200.0 in achados["1.200"]


def test_resposta_correta_passa_no_validador():
    ctx = contexto()
    assert validar_explicacao(checar_formato(boa_resposta()), ctx.como_dict()).ok


def test_numero_inventado_e_reprovado():
    r = boa_resposta()
    r["alertas"] = ["Fe previsto em 0,27%, perto do limite."]
    v = validar_explicacao(checar_formato(r), contexto().como_dict())
    assert not v.ok and any("0,27" in p for p in v.invalidos)


def test_tolerancia_de_arredondamento_de_um_centesimo():
    r = boa_resposta()
    r["diagnostico"] = "Si abaixo da faixa (6,16%)."  # real: 6,15
    assert validar_explicacao(checar_formato(r), contexto().como_dict()).ok
    r["diagnostico"] = "Si abaixo da faixa (6,30%)."
    assert not validar_explicacao(checar_formato(r), contexto().como_dict()).ok


def test_massa_diferente_do_motor_e_reprovada():
    r = boa_resposta()
    r["adicoes"][0]["massa_kg"] = 150
    v = validar_explicacao(checar_formato(r), contexto().como_dict())
    assert not v.ok


def test_material_e_corrida_inventados_sao_reprovados():
    r = boa_resposta()
    r["adicoes"].append({"material": "Silício metálico", "massa_kg": 120, "motivo": "repor"})
    r["referencias"] = [{"corrida": "9999", "observacao": "sem numeros"}]
    problemas = validar_explicacao(checar_formato(r), contexto().como_dict()).invalidos
    assert any("Silício metálico" in p for p in problemas)
    assert any("9999" in p for p in problemas)


def test_numero_no_nome_do_material_e_permitido():
    r = boa_resposta()
    r["adicoes"][1]["motivo"] = "usar a liga-mãe de 20% de Si"
    assert validar_explicacao(checar_formato(r), contexto().como_dict()).ok


@pytest.mark.parametrize("bruto", [[], {"diagnostico": ""}, {"diagnostico": "x", "adicoes": "a"},
                                   {"diagnostico": "x", "adicoes": [{"material": "a"}]},
                                   {"diagnostico": "x", "alertas": [1]}])
def test_formato_invalido(bruto):
    with pytest.raises(FormatoInvalido):
        checar_formato(bruto)


# ------------------------------------------------------------------ explicacao padrao (US-12)
def test_padrao_cobre_diagnostico_adicoes_alertas_e_referencias():
    p = gerar_explicacao_padrao(contexto())
    assert "Si abaixo da faixa (6,15%, mínimo 6,50%)" in p["diagnostico"]
    assert "Fe acima do limite (0,23%, máximo 0,20%)" in p["diagnostico"]
    assert p["adicoes"][0]["motivo"] == "diluir Fe"
    assert p["adicoes"][1]["motivo"] == "repor Si"  # reposicao tem prioridade
    assert p["alertas"] == ["Si previsto em 6,55%, perto do limite de 6,50%.",
                            "Fe previsto em 0,19%, perto do limite de 0,20%."]
    assert p["referencias"] == [{"corrida": "0141", "observacao": "Mg ficou 0,02 p.p. abaixo do previsto"}]


def test_padrao_sempre_passa_no_validador_e_no_formato():
    for ctx in (contexto(), contexto(adicoes=(), banho={"Si": 7.0, "Mg": 0.3, "Fe": 0.1}),
                contexto(status="INVIAVEL", adicoes=(), elemento_impeditivo="Fe"),
                contexto(semelhantes=())):
        p = gerar_explicacao_padrao(ctx)
        assert checar_formato(p) == p
        assert validar_explicacao(p, ctx.como_dict()).ok, p


def test_padrao_banho_dentro_da_faixa():
    p = gerar_explicacao_padrao(contexto(banho={"Si": 7.0, "Mg": 0.3, "Fe": 0.1}))
    assert p["diagnostico"] == "Todos os elementos do banho já estão dentro da faixa da liga A356."


def test_padrao_inviavel_cita_elemento_impeditivo_e_nao_lista_adicoes():
    p = gerar_explicacao_padrao(contexto(status="INVIAVEL", elemento_impeditivo="Fe"))
    assert "O elemento que impede é o Fe" in p["diagnostico"] and p["adicoes"] == []


def test_padrao_e_deterministica():
    assert gerar_explicacao_padrao(contexto()) == gerar_explicacao_padrao(contexto())


# ------------------------------------------------------------------ cliente Gemini (US-11)
def test_chamada_usa_temperatura_json_timeout_e_chave_no_cabecalho():
    c, t = cliente(resposta_gemini(json.dumps(boa_resposta())))
    c.gerar(contexto().como_dict(), "gemini-3.8-flash")
    url, cab, corpo, timeout = t.chamadas[0]
    assert url.endswith("/models/gemini-3.8-flash:generateContent")
    assert "chave-teste" not in url and cab["x-goog-api-key"] == "chave-teste"
    assert corpo["generationConfig"]["temperature"] == 0.2
    assert corpo["generationConfig"]["responseMimeType"] == "application/json"
    assert timeout == 15.0


def test_prompt_traz_o_resultado_do_motor_e_nao_identifica_empresa():
    prompt = montar_prompt(contexto().como_dict())
    assert "Alumínio primário" in prompt and "120" in prompt
    assert "Formigueiro" not in prompt


def test_aceita_json_dentro_de_cerca_markdown():
    c, _ = cliente(resposta_gemini("```json\n" + json.dumps(boa_resposta()) + "\n```"))
    assert c.gerar(contexto().como_dict(), "m")["diagnostico"].startswith("Si abaixo")


@pytest.mark.parametrize("resp", [{}, {"candidates": []}, resposta_gemini(""),
                                  resposta_gemini("nao e json"), resposta_gemini("[1]")])
def test_respostas_inutilizaveis_viram_indisponivel(resp):
    c, _ = cliente(resp)
    with pytest.raises(GeminiIndisponivel):
        c.gerar(contexto().como_dict(), "m")


# ------------------------------------------------------------------ orquestracao (DAS 13.2)
def test_caminho_feliz_usa_gemini():
    c, t = cliente(resposta_gemini(json.dumps(boa_resposta())))
    r = explicar(contexto(), c)
    assert r.origem == GEMINI and r.explicacao["alertas"] and len(t.chamadas) == 1


def test_falha_do_principal_tenta_o_reserva_uma_vez():
    c, t = cliente(GeminiIndisponivel("HTTP 429"), resposta_gemini(json.dumps(boa_resposta())))
    r = explicar(contexto(), c)
    assert r.origem == GEMINI
    assert [x[0].split("/models/")[1].split(":")[0] for x in t.chamadas] == \
        ["gemini-3.8-flash", "gemini-3.5-flash-lite"]


def test_principal_e_reserva_falhando_cai_na_padrao():
    c, t = cliente(GeminiIndisponivel("timeout"), GeminiIndisponivel("HTTP 500"))
    r = explicar(contexto(), c)
    assert r.origem == PADRAO and len(t.chamadas) == 2 and "timeout" in r.motivo_padrao


def test_numero_invalido_cai_na_padrao_sem_expor_a_resposta_da_ia():
    ruim = boa_resposta()
    ruim["diagnostico"] = "Si em 9,99%."
    c, _ = cliente(resposta_gemini(json.dumps(ruim)))
    r = explicar(contexto(), c)
    assert r.origem == PADRAO and "9,99" not in json.dumps(r.explicacao)
    assert "validador" in r.motivo_padrao


def test_sem_chave_nao_chama_a_rede_e_usa_a_padrao():
    c, t = cliente(chave="")
    assert explicar(contexto(), c).origem == PADRAO and t.chamadas == []


# ------------------------------------------------------------------ servico da aplicacao
class RepoFalso:
    def __init__(self, salva=None, ctx=None):
        self.salva, self.ctx, self.gravado = salva, ctx, None

    def explicacao_salva(self, _id):
        return self.salva

    def contexto_para_explicar(self, _id):
        return self.ctx

    def salvar_explicacao(self, _id, explicacao, origem):
        self.gravado = (explicacao, origem)


def test_gera_e_salva_na_corrida():
    repo = RepoFalso(ctx=contexto())
    c, _ = cliente(resposta_gemini(json.dumps(boa_resposta())))
    r = gerar_explicacao("c1", repo, c)
    assert repo.gravado == (r.explicacao, GEMINI)


def test_explicacao_ja_salva_nao_chama_a_ia_de_novo():
    repo = RepoFalso(salva=({"diagnostico": "salva"}, GEMINI), ctx=contexto())
    c, t = cliente()
    r = gerar_explicacao("c1", repo, c)
    assert r.explicacao == {"diagnostico": "salva"} and t.chamadas == [] and repo.gravado is None


def test_corrida_inexistente():
    c, _ = cliente()
    with pytest.raises(CorridaNaoEncontrada):
        gerar_explicacao("x", RepoFalso(), c)


# ------------------------------------------------------------------ transporte real (httpx)
def test_transporte_httpx_traduz_timeout_e_http_429_em_indisponivel():
    httpx = pytest.importorskip("httpx")
    from unittest import mock

    from app.explicacao.gemini import _transporte_httpx

    with mock.patch.object(httpx, "post", side_effect=httpx.ReadTimeout("lento")):
        with pytest.raises(GeminiIndisponivel):
            _transporte_httpx("https://x", {}, {}, 15.0)

    limite = httpx.Response(429, request=httpx.Request("POST", "https://x"))
    with mock.patch.object(httpx, "post", return_value=limite):
        with pytest.raises(GeminiIndisponivel, match="429"):
            _transporte_httpx("https://x", {}, {}, 15.0)

    ok = httpx.Response(200, json={"a": 1}, request=httpx.Request("POST", "https://x"))
    with mock.patch.object(httpx, "post", return_value=ok) as post:
        assert _transporte_httpx("https://x", {"h": "1"}, {"c": 1}, 15.0) == {"a": 1}
        assert post.call_args.kwargs["timeout"].read == 15.0

 # ------------------------------------------------------------------ US-12: nenhum calculo sem explicacao
def test_reserva_so_e_tentado_uma_vez_e_depois_vem_a_padrao():
    c, t = cliente(GeminiIndisponivel("HTTP 429"), GeminiIndisponivel("HTTP 429"))
    r = explicar(contexto(), c)
    assert r.origem == PADRAO and len(t.chamadas) == 2
    assert "gemini-3.8-flash: HTTP 429" in r.motivo_padrao and "gemini-3.5-flash-lite" in r.motivo_padrao


def test_erro_inesperado_na_camada_de_ia_ainda_gera_explicacao():
    def quebrado(*_):
        raise RuntimeError("bug qualquer")

    c = ClienteGemini("k", "m1", "m2", 15.0, quebrado)
    r = explicar(contexto(), c)
    assert r.origem == PADRAO and "RuntimeError" in r.motivo_padrao and r.explicacao["diagnostico"]


def test_se_ate_a_padrao_falhar_sobra_um_texto_minimo():
    from unittest import mock

    with mock.patch("app.explicacao.servico.gerar_explicacao_padrao", side_effect=ValueError("x")):
        r = explicar(contexto(), cliente(chave="")[0])
    assert r.origem == PADRAO and r.explicacao["diagnostico"]
    assert [a["material"] for a in r.explicacao["adicoes"]] == ["Alumínio primário", "Liga-mãe Al-Si 20%"]


def test_origem_e_um_dos_dois_valores_do_enum():
    from app.explicacao.servico import OrigemExplicacao

    assert {o.value for o in OrigemExplicacao} == {"GEMINI", "PADRAO"}
    c, _ = cliente(resposta_gemini(json.dumps(boa_resposta())))
    assert OrigemExplicacao(explicar(contexto(), c).origem) is OrigemExplicacao.GEMINI
    assert OrigemExplicacao(explicar(contexto(), cliente(chave="")[0]).origem) is OrigemExplicacao.PADRAO


def test_grava_na_corrida_a_origem_certa_nos_dois_caminhos():
    ok, falha = RepoFalso(ctx=contexto()), RepoFalso(ctx=contexto())
    gerar_explicacao("1", ok, cliente(resposta_gemini(json.dumps(boa_resposta())))[0])
    gerar_explicacao("2", falha, cliente(GeminiIndisponivel("x"), GeminiIndisponivel("y"))[0])
    assert ok.gravado[1] == "GEMINI" and falha.gravado[1] == "PADRAO"
    assert falha.gravado[0]["diagnostico"]


def test_valores_decimal_da_api_funcionam_no_prompt_validador_e_padrao():
    from decimal import Decimal as D

    ctx = ContextoExplicacao(
        liga="A356",
        faixas={"Si": (D("6.5"), D("7.5")), "Fe": (D("0"), D("0.20"))},
        banho={"Si": D("6.15"), "Fe": D("0.23")}, massa_banho_kg=D("1000"), status="OK",
        adicoes=(AdicaoCtx("Alumínio primário", D("120.0"), "ALUMINIO_PRIMARIO", {"Fe": D("0.06")}),),
        composicao_prevista={"Si": D("6.55"), "Fe": D("0.19")}, custo_total=D("2160.00"),
        semelhantes=(SemelhanteCtx("0141", {"Si": D("6.1")}, {"Si": D("6.7")}, {"Si": D("6.72")}),))
    json.dumps(ctx.como_dict())  # nao pode quebrar
    montar_prompt(ctx.como_dict())
    padrao = gerar_explicacao_padrao(ctx)
    json.dumps(padrao)
    assert validar_explicacao(padrao, ctx.como_dict()).ok
    resposta = {"diagnostico": "Fe acima do limite (0,23%).",
                "adicoes": [{"material": "Alumínio primário", "massa_kg": 120, "motivo": "diluir Fe"}],
                "alertas": [], "referencias": []}
    c, _ = cliente(resposta_gemini(json.dumps(resposta)))
    assert explicar(ctx, c).origem == GEMINI


def test_historico_e_pdf_nunca_chamam_a_ia():
    from app.services.explicacao import explicacao_ou_padrao

    c, t = cliente()
    salva = RepoFalso(salva=({"diagnostico": "salva"}, "GEMINI"), ctx=contexto())
    assert explicacao_ou_padrao("1", salva).explicacao == {"diagnostico": "salva"}
    sem = RepoFalso(ctx=contexto())
    r = explicacao_ou_padrao("2", sem)
    assert r.origem == PADRAO and r.explicacao["diagnostico"] and sem.gravado is None
    with pytest.raises(CorridaNaoEncontrada):
        explicacao_ou_padrao("3", RepoFalso())
    assert t.chamadas == []