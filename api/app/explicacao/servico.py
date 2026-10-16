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

from .contexto import ContextoExplicacao
from .gemini import ClienteGemini, GeminiIndisponivel
from .padrao import gerar_explicacao_padrao
from .validador import validar_explicacao

log = logging.getLogger(__name__)

GEMINI, PADRAO = "GEMINI", "PADRAO"  # valores de OrigemExplicacao (DAS 7)


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


def _padrao(ctx: ContextoExplicacao, motivo: str) -> ResultadoExplicacao:
    log.warning("explicacao padrao usada: %s", motivo)
    return ResultadoExplicacao(gerar_explicacao_padrao(ctx), PADRAO, motivo)


def explicar(ctx: ContextoExplicacao, cliente: ClienteGemini | None = None) -> ResultadoExplicacao:
    cliente = cliente if cliente is not None else criar_cliente()
    if not cliente.configurado:
        return _padrao(ctx, "GEMINI_API_KEY nao configurada")

    contexto = ctx.como_dict()
    modelos = [cliente.modelo]
    if cliente.modelo_reserva and cliente.modelo_reserva != cliente.modelo:
        modelos.append(cliente.modelo_reserva)

    explicacao, falhas = None, []
    for modelo in modelos:
        try:
            explicacao = cliente.gerar(contexto, modelo)
            break
        except GeminiIndisponivel as erro:
            falhas.append(f"{modelo}: {erro}")
    if explicacao is None:
        return _padrao(ctx, "; ".join(falhas))

    validacao = validar_explicacao(explicacao, contexto)
    if not validacao.ok:
        return _padrao(ctx, "validador reprovou: " + "; ".join(validacao.invalidos))
    return ResultadoExplicacao(explicacao, GEMINI)