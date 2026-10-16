from __future__ import annotations

from dataclasses import dataclass, field

# Margem para o alerta de "perto do limite": 10% da largura da faixa (minimo 0,01 p.p.).
MARGEM_ALERTA_REL = 0.10
MARGEM_ALERTA_MIN = 0.01
# Desvio previsto x real abaixo disso nao vale ser citado como referencia.
DESVIO_MINIMO_REFERENCIA = 0.02

ABAIXO, DENTRO, ACIMA = "abaixo", "dentro", "acima"

def _mapa(d: dict) -> dict[str, float]:
    """A API trabalha com Decimal (DAS 9.3); aqui tudo vira float para comparar e serializar."""
    return {k: float(v) for k, v in d.items()}


def _set(obj, **campos) -> None:
    for nome, valor in campos.items():
        object.__setattr__(obj, nome, valor)  # dataclass frozen

@dataclass(frozen=True)
class AdicaoCtx:
    material: str
    massa_kg: float
    tipo: str | None = None  # SUCATA, LIGA_MAE, INSUMO, ALUMINIO_PRIMARIO
    composicao: dict[str, float] = field(default_factory=dict)  # teor % por elemento
         def __post_init__(self):
         _set(self, massa_kg=float(self.massa_kg), composicao=_mapa(self.composicao))


@dataclass(frozen=True)
class SemelhanteCtx:
    """Corrida finalizada da mesma liga, parecida com a atual."""
    id: str
    composicao_inicial: dict[str, float]
    composicao_prevista: dict[str, float]
    composicao_final: dict[str, float]
        def __post_init__(self):
        _set(self, composicao_inicial=_mapa(self.composicao_inicial),
         composicao_prevista=_mapa(self.composicao_prevista),
         composicao_final=_mapa(self.composicao_final))


@dataclass(frozen=True)
class ContextoExplicacao:
    liga: str
    faixas: dict[str, tuple[float, float]]  # elemento -> (min_pct, max_pct)
    banho: dict[str, float]  # composicao inicial, % por elemento
    massa_banho_kg: float
    status: str  # "OK" ou "INVIAVEL"
    adicoes: tuple[AdicaoCtx, ...]
    composicao_prevista: dict[str, float]
    custo_total: float | None = None
    elemento_impeditivo: str | None = None
    semelhantes: tuple[SemelhanteCtx, ...] = ()
        def __post_init__(self):
         _set(self,
          faixas={e: (float(lo), float(hi)) for e, (lo, hi) in self.faixas.items()},
         banho=_mapa(self.banho), massa_banho_kg=float(self.massa_banho_kg),
         composicao_prevista=_mapa(self.composicao_prevista),
         custo_total=None if self.custo_total is None else float(self.custo_total),
         adicoes=tuple(self.adicoes), semelhantes=tuple(self.semelhantes))

    # ---- situacao dos elementos ------------------------------------------------
    @staticmethod
    def situacao(valor: float, faixa: tuple[float, float]) -> str:
        minimo, maximo = faixa
        if valor < minimo:
            return ABAIXO
        if valor > maximo:
            return ACIMA
        return DENTRO

    def situacao_banho(self) -> dict[str, str]:
        return {e: self.situacao(self.banho.get(e, 0.0), f) for e, f in self.faixas.items()}

    def situacao_prevista(self) -> dict[str, str]:
        return {e: self.situacao(self.composicao_prevista.get(e, 0.0), f)
                for e, f in self.faixas.items()}

    def elementos_perto_do_limite(self) -> list[tuple[str, float, float]]:
        """(elemento, previsto, limite mais proximo) para os previstos dentro da faixa
        e a menos de MARGEM do limite. Elementos com minimo 0 so contam pelo maximo."""
        achados = []
        for elem, (minimo, maximo) in self.faixas.items():
            valor = self.composicao_prevista.get(elem)
            if valor is None or not (minimo <= valor <= maximo):
                continue
            margem = max(MARGEM_ALERTA_MIN, MARGEM_ALERTA_REL * (maximo - minimo))
            candidatos = [(maximo - valor, maximo)]
            if minimo > 0:
                candidatos.append((valor - minimo, minimo))
            distancia, limite = min(candidatos)
            if distancia <= margem + 1e-9:
                achados.append((elem, valor, limite))
        return achados

    # ---- desvios das corridas parecidas ---------------------------------------
    @staticmethod
    def desvios_previsto_real(s: SemelhanteCtx) -> dict[str, float]:
        """real - previsto, em p.p., arredondado a 2 casas. Negativo = ficou abaixo."""
        return {
            e: round(s.composicao_final[e] - s.composicao_prevista[e], 2)
            for e in s.composicao_final
            if e in s.composicao_prevista
        }

    # ---- representacao para prompt e validador --------------------------------
    def como_dict(self) -> dict:
        """Tudo que a IA pode ver e, portanto, tudo que ela pode citar."""
        sit_banho, sit_prev = self.situacao_banho(), self.situacao_prevista()
        return {
            "liga": self.liga,
            "status": self.status,
            "elemento_impeditivo": self.elemento_impeditivo,
            "massa_banho_kg": self.massa_banho_kg,
            "custo_total": self.custo_total,
            "elementos": [
                {
                    "elemento": e,
                    "faixa_min_pct": f[0],
                    "faixa_max_pct": f[1],
                    "banho_pct": self.banho.get(e),
                    "banho_situacao": sit_banho[e],
                    "previsto_pct": self.composicao_prevista.get(e),
                    "previsto_situacao": sit_prev[e],
                }
                for e, f in self.faixas.items()
            ],
            "adicoes": [
                {"material": a.material, "tipo": a.tipo, "massa_kg": a.massa_kg,
                 "composicao_pct": a.composicao}
                for a in self.adicoes
            ],
            "corridas_parecidas": [
                {
                    "corrida": s.id,
                    "composicao_inicial_pct": s.composicao_inicial,
                    "composicao_prevista_pct": s.composicao_prevista,
                    "composicao_final_pct": s.composicao_final,
                    "desvio_real_menos_previsto_pp": self.desvios_previsto_real(s),
                }
                for s in self.semelhantes
            ],
        }