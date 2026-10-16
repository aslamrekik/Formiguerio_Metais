"""Camada de aplicacao da explicacao (US-11, US-12, US-13): POST /corridas/{id}/explicacao.

Regra do DAS 9.3: router -> service -> repository. Este servico nao conhece
SQLAlchemy; recebe um repositorio que cumpre o protocolo abaixo (Arthur, US-02).

Explicacao ja salva nao chama a IA de novo: historico e PDF so leem o que esta
na corrida. A chamada repetida do endpoint tambem devolve a explicacao salva.

Ligacao no router (corridas.py), quando o repositorio existir:

    @router.post("/{corrida_id}/explicacao")
    def gerar(corrida_id: UUID, repo=Depends(get_repositorio_corridas)):
        try:
            r = gerar_explicacao(corrida_id, repo)
        except CorridaNaoEncontrada:
            raise HTTPException(404, "Corrida nao encontrada")
        return {"explicacao": r.explicacao, "origem": r.origem}

No detalhe da corrida e no PDF, use explicacao_ou_padrao(corrida_id, repo).
"""
from __future__ import annotations

from typing import Protocol

from ..explicacao.contexto import ContextoExplicacao
from ..explicacao.gemini import ClienteGemini
from ..explicacao.servico import (OrigemExplicacao, ResultadoExplicacao, explicar,
                                  explicar_com_padrao)


class CorridaNaoEncontrada(Exception):
    pass


class RepositorioExplicacao(Protocol):
    def explicacao_salva(self, corrida_id) -> tuple[dict, str] | None:
        """(explicacao, origem) se a corrida ja tem explicacao; senao None."""

    def contexto_para_explicar(self, corrida_id) -> ContextoExplicacao | None:
        """Resultado do motor + banho + faixas + ate 5 corridas parecidas (US-13).
        None quando a corrida nao existe."""

    def salvar_explicacao(self, corrida_id, explicacao: dict, origem: str) -> None:
        """Grava em corridas.explicacao e corridas.origem_explicacao."""


def gerar_explicacao(corrida_id, repo: RepositorioExplicacao,
                     cliente: ClienteGemini | None = None) -> ResultadoExplicacao:
    salva = repo.explicacao_salva(corrida_id)
    if salva is not None:
        explicacao, origem = salva
        return ResultadoExplicacao(explicacao, origem)

    contexto = repo.contexto_para_explicar(corrida_id)
    if contexto is None:
        raise CorridaNaoEncontrada(str(corrida_id))

    resultado = explicar(contexto, cliente)
    # A corrida guarda a origem (GEMINI ou PADRAO); valor fora do enum nao e gravado.
    repo.salvar_explicacao(corrida_id, resultado.explicacao, OrigemExplicacao(resultado.origem).value)
    return resultado


def explicacao_ou_padrao(corrida_id, repo: RepositorioExplicacao) -> ResultadoExplicacao:
    """Para historico e PDF: devolve a explicacao salva e NUNCA chama a IA.

    Corrida sem explicacao salva (ex.: a tela fechou antes da segunda chamada)
    recebe a explicacao padrao, sem gravar: assim o endpoint POST ainda pode
    gerar a versao com IA depois. Garante que todo calculo tenha explicacao.
    """
    salva = repo.explicacao_salva(corrida_id)
    if salva is not None:
        return ResultadoExplicacao(salva[0], salva[1])
    contexto = repo.contexto_para_explicar(corrida_id)
    if contexto is None:
        raise CorridaNaoEncontrada(str(corrida_id))
    return explicar_com_padrao(contexto, "corrida sem explicacao salva")