"""Explicacao padrao gerada em Python (US-12, DAS 13.4).

Garante que 100% dos calculos tenham explicacao, mesmo sem o Gemini. Usa os
mesmos campos do DAS 13.3: lista os elementos fora da faixa, as adicoes com o
motivo por regra simples (diluicao ou reposicao) e os elementos proximos do
limite. Todo numero vem do contexto, entao ela sempre passa no validador.
"""
from __future__ import annotations

from .contexto import (ABAIXO, ACIMA, DESVIO_MINIMO_REFERENCIA, AdicaoCtx,
                       ContextoExplicacao)

MAX_REFERENCIAS = 3


def _pct(valor: float) -> str:
    return f"{valor:.2f}".replace(".", ",")


def _juntar(partes: list[str]) -> str:
    if len(partes) <= 1:
        return "".join(partes)
    return ", ".join(partes[:-1]) + " e " + partes[-1]


def _diagnostico(ctx: ContextoExplicacao) -> str:
    if ctx.status == "INVIAVEL":
        texto = (f"Não foi possível enquadrar a liga {ctx.liga} com o estoque e a "
                 f"capacidade disponíveis.")
        if ctx.elemento_impeditivo:
            texto += f" O elemento que impede é o {ctx.elemento_impeditivo}."
        return texto

    achados = []
    for elem, situacao in ctx.situacao_banho().items():
        minimo, maximo = ctx.faixas[elem]
        valor = ctx.banho.get(elem, 0.0)
        if situacao == ABAIXO:
            achados.append(f"{elem} abaixo da faixa ({_pct(valor)}%, mínimo {_pct(minimo)}%)")
        elif situacao == ACIMA:
            achados.append(f"{elem} acima do limite ({_pct(valor)}%, máximo {_pct(maximo)}%)")
    if not achados:
        return f"Todos os elementos do banho já estão dentro da faixa da liga {ctx.liga}."
    return _juntar(achados) + "."


def _motivo(a: AdicaoCtx, ctx: ContextoExplicacao) -> str:
    situacao = ctx.situacao_banho()
    diluir = [e for e, s in situacao.items()
              if s == ACIMA and a.composicao.get(e, 0.0) < ctx.banho.get(e, 0.0)]
    repor = [e for e, s in situacao.items()
             if s == ABAIXO and a.composicao.get(e, 0.0) > ctx.banho.get(e, 0.0)]
    # Reposicao tem prioridade: uma liga-mae rica em Si tambem dilui um pouco o Fe,
    # mas o motivo de usa-la e repor o Si.
    if repor:
        return "repor " + _juntar(repor)
    if diluir:
        return "diluir " + _juntar(diluir)
    if a.tipo == "ALUMINIO_PRIMARIO":
        return "diluir o banho"
    return "ajustar a composição"


def _alertas(ctx: ContextoExplicacao) -> list[str]:
    if ctx.status == "INVIAVEL":
        return ["Sem solução viável: revise o estoque, a capacidade do forno ou a liga-alvo."]
    return [f"{e} previsto em {_pct(valor)}%, perto do limite de {_pct(limite)}%."
            for e, valor, limite in ctx.elementos_perto_do_limite()]


def _referencias(ctx: ContextoExplicacao) -> list[dict]:
    candidatas = []
    for s in ctx.semelhantes:
        desvios = ctx.desvios_previsto_real(s)
        if not desvios:
            continue
        elem, desvio = max(desvios.items(), key=lambda kv: (abs(kv[1]), kv[0]))
        if abs(desvio) >= DESVIO_MINIMO_REFERENCIA - 1e-9:
            lado = "abaixo" if desvio < 0 else "acima"
            candidatas.append((abs(desvio), s.id, f"{elem} ficou {_pct(abs(desvio))} p.p. "
                                                  f"{lado} do previsto"))
    candidatas.sort(key=lambda c: (-c[0], c[1]))
    return [{"corrida": cid, "observacao": obs} for _, cid, obs in candidatas[:MAX_REFERENCIAS]]


def gerar_explicacao_padrao(ctx: ContextoExplicacao) -> dict:
    """Explicacao no formato do DAS 13.3, montada por template."""
    adicoes = [] if ctx.status == "INVIAVEL" else [
        {"material": a.material, "massa_kg": a.massa_kg, "motivo": _motivo(a, ctx)}
        for a in ctx.adicoes
    ]
    return {
        "diagnostico": _diagnostico(ctx),
        "adicoes": adicoes,
        "alertas": _alertas(ctx),
        "referencias": _referencias(ctx),
    }