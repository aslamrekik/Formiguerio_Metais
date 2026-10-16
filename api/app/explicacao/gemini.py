"""Cliente do Gemini (DAS 13; US-11). A IA nao calcula: recebe o resultado pronto.

Chamada unica por modelo: temperatura 0,2, resposta em JSON e tempo maximo de
15 s (config.gemini_timeout_s). A ordem modelo principal -> modelo reserva ->
explicacao padrao fica em servico.py.

Seguranca: a chave vai no cabecalho (nunca na URL) e nada que identifique a
empresa ou os clientes dela entra no prompt (DAS 15).
"""
from __future__ import annotations

import json
import re
from typing import Callable

from .validador import FormatoInvalido, checar_formato

URL_BASE = "https://generativelanguage.googleapis.com/v1beta/models"
TEMPERATURA = 0.2

INSTRUCAO_SISTEMA = """\
Você explica, em português do Brasil, a correção de composição química de uma \
liga secundária de alumínio para o engenheiro de uma fundição.

REGRAS OBRIGATÓRIAS
1. Você NÃO calcula nada. O resultado do motor de cálculo já está pronto no JSON \
recebido. Apenas explique.
2. Só cite números que estejam escritos no JSON. Copie cada número exatamente como \
aparece (no máximo 2 casas decimais). Não some, não subtraia, não converta, não \
arredonde e não estime.
3. Só cite materiais listados em "adicoes" e corridas listadas em "corridas_parecidas".
4. Não invente causas metalúrgicas nem recomendações além do que o JSON mostra.
5. Se "status" for "INVIAVEL", explique que não há solução e qual é o "elemento_impeditivo"; \
"adicoes" deve ficar vazia.
6. Texto curto, direto e sem enfeites.

FORMATO DA RESPOSTA: somente um objeto JSON, sem markdown e sem texto fora dele:
{
  "diagnostico": "texto: quais elementos do banho estão fora da faixa e por quê",
  "adicoes": [{"material": "nome exato do material", "massa_kg": <número do JSON>, "motivo": "diluir ... ou repor ..."}],
  "alertas": ["texto: elementos previstos perto do limite da faixa"],
  "referencias": [{"corrida": "id exato da corrida parecida", "observacao": "texto sobre o desvio previsto x real"}]
}
Use listas vazias quando não houver adições, alertas ou referências.
"""


class GeminiIndisponivel(Exception):
    """Erro, limite, timeout ou resposta inutilizavel. Quem chama tenta o reserva."""


# (url, cabecalhos, corpo, timeout_s) -> resposta JSON decodificada
Transporte = Callable[[str, dict, dict, float], dict]


def montar_prompt(contexto: dict) -> str:
    dados = json.dumps(contexto, ensure_ascii=False, separators=(",", ":"))
    return ("Explique a correção abaixo. Os dados do JSON são a única fonte de números.\n"
            f"DADOS:\n{dados}")


def montar_corpo(contexto: dict) -> dict:
    return {
        "systemInstruction": {"parts": [{"text": INSTRUCAO_SISTEMA}]},
        "contents": [{"role": "user", "parts": [{"text": montar_prompt(contexto)}]}],
        "generationConfig": {"temperature": TEMPERATURA,
                             "responseMimeType": "application/json"},
    }


def _transporte_httpx(url: str, cabecalhos: dict, corpo: dict, timeout_s: float) -> dict:
    import httpx  # importado aqui para o modulo carregar sem rede nos testes

    try:
        resp = httpx.post(url, headers=cabecalhos, json=corpo, timeout=httpx.Timeout(timeout_s))
    except httpx.HTTPError as erro:  # timeout, conexao, TLS
        raise GeminiIndisponivel(f"falha de rede: {type(erro).__name__}") from None
    if resp.status_code >= 400:  # 429 (limite do plano gratuito), 5xx, 401...
        raise GeminiIndisponivel(f"HTTP {resp.status_code}")
    try:
        return resp.json()
    except ValueError:
        raise GeminiIndisponivel("resposta nao e JSON") from None


_CERCA = re.compile(r"^\s*```(?:json)?\s*|\s*```\s*$", re.IGNORECASE)


def _extrair_texto(resposta: dict) -> str:
    try:
        candidato = resposta["candidates"][0]
        partes = candidato["content"]["parts"]
    except (KeyError, IndexError, TypeError):
        raise GeminiIndisponivel("resposta sem conteudo (bloqueio ou vazia)") from None
    texto = "".join(p.get("text", "") for p in partes if isinstance(p, dict))
    if not texto.strip():
        raise GeminiIndisponivel("resposta vazia")
    return texto


class ClienteGemini:
    def __init__(self, api_key: str, modelo: str, modelo_reserva: str,
                 timeout_s: float = 15.0, transporte: Transporte | None = None):
        self.api_key = api_key
        self.modelo = modelo
        self.modelo_reserva = modelo_reserva
        self.timeout_s = timeout_s
        self._transporte = transporte or _transporte_httpx

    @property
    def configurado(self) -> bool:
        return bool(self.api_key)

    def gerar(self, contexto: dict, modelo: str) -> dict:
        """Uma chamada a um modelo. Devolve a explicacao no formato do DAS 13.3
        ou levanta GeminiIndisponivel."""
        url = f"{URL_BASE}/{modelo}:generateContent"
        cabecalhos = {"x-goog-api-key": self.api_key, "Content-Type": "application/json"}
        resposta = self._transporte(url, cabecalhos, montar_corpo(contexto), self.timeout_s)
        texto = _CERCA.sub("", _extrair_texto(resposta))
        try:
            return checar_formato(json.loads(texto))
        except (ValueError, FormatoInvalido) as erro:  # JSON quebrado ou fora do formato
            raise GeminiIndisponivel(f"resposta invalida: {erro}") from None