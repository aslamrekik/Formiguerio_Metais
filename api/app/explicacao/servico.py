"""Orquestra a explicacao de uma corrida (DAS 13.2, passos 3 a 7; US-11 e US-12).

    1. modelo principal (GEMINI_MODEL)
    2. se falhar ou estourar o tempo: UMA tentativa com o modelo reserva
    3. validar: todo numero do texto precisa existir no resultado do motor
    4. se ainda falhar ou nao passar no validador: explicacao padrao em Python

Sempre devolve uma explicacao e a origem (GEMINI ou PADRAO).
"""
from __future__ import annotations

import logging
from dataclasses import dataclass
from enum import Enum

from .contexto import ContextoExplicacao
from .gemini import ClienteGemini, GeminiIndisponivel
from .padrao import gerar_explicacao_padrao
from .validador import validar_explicacao

log = logging.getLogger(__name__)


class OrigemExplicacao(str, Enum):
    """Gravada em corridas.origem_explicacao (DAS 7 e 11)."""
    GEMINI = "GEMINI"
    PADRAO = "PADRAO"


GEMINI, PADRAO = OrigemExplicacao.GEMINI.value, OrigemExplicacao.PADRAO.value


@dataclass(frozen=True)
class ResultadoExplicacao:
    explicacao: dict
    origem: str  # GEMINI ou PADRAO
    motivo_padrao: str | None = None  # por que caiu na explicacao padrao (so para log/teste)


def criar_cliente() -> ClienteGemini:
    """Cliente configurado pelas variaveis de ambiente (DAS 10.3)."""
    from ..config import config

    return ClienteGemini(config.gemini_api_key, config.gemini_model,
                         config.gemini_model_reserva, config.gemini_timeout_s)


def explicar_com_padrao(ctx: ContextoExplicacao, motivo: str) -> ResultadoExplicacao:
    """Explicacao padrao (US-12). Nunca levanta excecao: ultimo recurso e um texto minimo."""
    log.warning("explicacao padrao usada: %s", motivo)
    try:
        explicacao = gerar_explicacao_padrao(ctx)
    except Exception:  # noqa: BLE001 - 100% dos calculos precisam de explicacao
        log.exception("falha ao montar a explicacao padrao")
        explicacao = {
            "diagnostico": "Explicação detalhada indisponível. Consulte o resultado do cálculo.",
            "adicoes": [{"material": a.material, "massa_kg": a.massa_kg, "motivo": ""}
                        for a in getattr(ctx, "adicoes", ())],
            "alertas": [], "referencias": [],
        }
    return ResultadoExplicacao(explicacao, PADRAO, motivo)


def explicar(ctx: ContextoExplicacao, cliente: ClienteGemini | None = None) -> ResultadoExplicacao:
    """Sempre devolve uma explicacao, mesmo com erro inesperado na camada de IA."""
    try:
        return _explicar_com_ia(ctx, cliente)
    except Exception as erro:  # noqa: BLE001 - nenhum calculo fica sem explicacao
        log.exception("erro inesperado na explicacao com IA")
        return explicar_com_padrao(ctx, f"erro inesperado: {type(erro).__name__}")


def _explicar_com_ia(ctx: ContextoExplicacao, cliente: ClienteGemini | None) -> ResultadoExplicacao:
    cliente = cliente if cliente is not None else criar_cliente()
    if not cliente.configurado:
        return explicar_com_padrao(ctx, "GEMINI_API_KEY nao configurada")

    contexto = ctx.como_dict()
    modelos = [cliente.modelo]
    if cliente.modelo_reserva and cliente.modelo_reserva != cliente.modelo:
        modelos.append(cliente.modelo_reserva)

    explicacao, falhas = None, []
    for modelo in modelos:  # principal, depois UMA tentativa no reserva
        try:
            explicacao = cliente.gerar(contexto, modelo)
            break
        except GeminiIndisponivel as erro:
            falhas.append(f"{modelo}: {erro}")
    if explicacao is None:
        return explicar_com_padrao(ctx, "; ".join(falhas))

    validacao = validar_explicacao(explicacao, contexto)
    if not validacao.ok:
        return explicar_com_padrao(ctx, "validador reprovou: " + "; ".join(validacao.invalidos))
    return ResultadoExplicacao(explicacao, GEMINI)