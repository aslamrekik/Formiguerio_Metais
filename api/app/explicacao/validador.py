"""Validador da explicacao (DAS 13.2, passo 5; US-11).

Regra: todo numero citado no texto precisa existir no contexto enviado a IA
(resultado do motor, faixas, analise do banho e corridas parecidas), com
tolerancia de arredondamento de 0,01. Se um numero nao existir, a explicacao e
descartada e entra a explicacao padrao.

Alem dos numeros, confere o formato da resposta e que a IA nao inventou
materiais nem corridas de referencia.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field

TOLERANCIA = 0.01

# Um numero com separadores: 6,15  0.19  1.200,50  0141
_NUMERO = re.compile(r"\d+(?:[.,]\d+)*")


class FormatoInvalido(ValueError):
    """A resposta nao tem o formato do DAS 13.3."""


@dataclass
class ResultadoValidacao:
    ok: bool
    invalidos: list[str] = field(default_factory=list)  # problemas encontrados


# --------------------------------------------------------------------------- numeros
def _interpretacoes(token: str) -> set[float]:
    """Valores possiveis de um token. '1.200' pode ser 1,2 ou 1200; aceita-se qualquer um."""
    if token.isdigit():
        return {float(token)}
    tem_ponto, tem_virgula = "." in token, "," in token
    if tem_ponto and tem_virgula:
        decimal = "," if token.rfind(",") > token.rfind(".") else "."
        milhar = "." if decimal == "," else ","
        return {float(token.replace(milhar, "").replace(decimal, "."))}
    sep = "." if tem_ponto else ","
    partes = token.split(sep)
    opcoes: set[float] = set()
    if len(partes) == 2:
        opcoes.add(float(f"{partes[0]}.{partes[1]}"))
    if all(len(p) == 3 for p in partes[1:]):  # milhar: 1.200 ou 1.200.300
        opcoes.add(float("".join(partes)))
    return opcoes or {float("".join(partes))}


def extrair_numeros(texto: str) -> list[tuple[str, set[float]]]:
    """Devolve (trecho, valores possiveis) para cada numero encontrado no texto."""
    return [(t, _interpretacoes(t)) for t in _NUMERO.findall(texto)]


def _coletar_numeros(obj, destino: list[float]) -> None:
    """Numeros reais e numeros dentro de strings (ex.: 'Liga-mae Al-Si 20%', id '0141')."""
    if isinstance(obj, bool) or obj is None:
        return
    if isinstance(obj, (int, float)):
        destino.append(abs(float(obj)))
    elif isinstance(obj, str):
        for _, valores in extrair_numeros(obj):
            destino.extend(valores)
    elif isinstance(obj, dict):
        for v in obj.values():
            _coletar_numeros(v, destino)
    elif isinstance(obj, (list, tuple)):
        for v in obj:
            _coletar_numeros(v, destino)


def numeros_permitidos(contexto: dict) -> list[float]:
    permitidos: list[float] = []
    _coletar_numeros(contexto, permitidos)
    return permitidos


def _textos(explicacao: dict) -> list[str]:
    """Todo texto que o usuario vai ler."""
    saida = [explicacao.get("diagnostico", "")]
    saida += [f'{a.get("material", "")} {a.get("motivo", "")}' for a in explicacao.get("adicoes", [])]
    saida += list(explicacao.get("alertas", []))
    saida += [r.get("observacao", "") for r in explicacao.get("referencias", [])]
    return saida


# --------------------------------------------------------------------------- formato
def checar_formato(bruto) -> dict:
    """Garante o formato do DAS 13.3 e devolve so os campos conhecidos."""
    if not isinstance(bruto, dict):
        raise FormatoInvalido("a resposta nao e um objeto JSON")
    diag = bruto.get("diagnostico")
    if not isinstance(diag, str) or not diag.strip():
        raise FormatoInvalido("diagnostico ausente")

    adicoes = bruto.get("adicoes", [])
    alertas = bruto.get("alertas", [])
    refs = bruto.get("referencias", [])
    if not (isinstance(adicoes, list) and isinstance(alertas, list) and isinstance(refs, list)):
        raise FormatoInvalido("adicoes, alertas e referencias devem ser listas")

    limpas = []
    for a in adicoes:
        massa = a.get("massa_kg") if isinstance(a, dict) else None
        if not (isinstance(a, dict) and isinstance(a.get("material"), str)
                and isinstance(massa, (int, float)) and not isinstance(massa, bool)
                and isinstance(a.get("motivo", ""), str)):
            raise FormatoInvalido("adicao mal formada")
        limpas.append({"material": a["material"], "massa_kg": massa, "motivo": a.get("motivo", "")})
    if not all(isinstance(t, str) for t in alertas):
        raise FormatoInvalido("alerta deve ser texto")
    refs_limpas = []
    for r in refs:
        if not (isinstance(r, dict) and isinstance(r.get("corrida"), (str, int))
                and isinstance(r.get("observacao", ""), str)):
            raise FormatoInvalido("referencia mal formada")
        refs_limpas.append({"corrida": str(r["corrida"]), "observacao": r.get("observacao", "")})
    return {"diagnostico": diag.strip(), "adicoes": limpas,
            "alertas": [t.strip() for t in alertas], "referencias": refs_limpas}


# --------------------------------------------------------------------------- validacao
def validar_explicacao(explicacao: dict, contexto: dict,
                       tolerancia: float = TOLERANCIA) -> ResultadoValidacao:
    """explicacao ja passou por checar_formato; contexto e ContextoExplicacao.como_dict()."""
    problemas: list[str] = []
    permitidos = numeros_permitidos(contexto)

    for texto in _textos(explicacao):
        for trecho, valores in extrair_numeros(texto):
            if not any(abs(v - p) <= tolerancia + 1e-9 for v in valores for p in permitidos):
                problemas.append(f"numero {trecho} nao existe no resultado")

    massas = [x["massa_kg"] for x in contexto.get("adicoes", [])]
    materiais = {x["material"].strip().casefold() for x in contexto.get("adicoes", [])}
    for a in explicacao.get("adicoes", []):
        if not any(abs(a["massa_kg"] - m) <= tolerancia + 1e-9 for m in massas):
            problemas.append(f"massa {a['massa_kg']} kg nao existe no resultado")
        if a["material"].strip().casefold() not in materiais:
            problemas.append(f"material {a['material']!r} nao faz parte do resultado")

    ids = {c["corrida"] for c in contexto.get("corridas_parecidas", [])}
    for r in explicacao.get("referencias", []):
        if r["corrida"] not in ids:
            problemas.append(f"corrida {r['corrida']!r} nao foi enviada como referencia")

    return ResultadoValidacao(ok=not problemas, invalidos=problemas)
