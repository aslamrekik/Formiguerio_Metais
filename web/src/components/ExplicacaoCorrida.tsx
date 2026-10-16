import { useEffect, useState } from "react";

import { gerarExplicacao, type ExplicacaoResposta } from "../lib/api";

export const MENSAGEM_ESPERA = "Aguarde um pouquinho, estamos preparando a explicação…";

interface Props {
  corridaId: string;
  /** Explicação já salva na corrida (histórico). Quando existe, não chama a API. */
  explicacaoSalva?: ExplicacaoResposta | null;
}

type Estado =
  | { tipo: "carregando" }
  | { tipo: "pronta"; dados: ExplicacaoResposta }
  | { tipo: "erro" };

const kg = (v: number) => v.toLocaleString("pt-BR", { maximumFractionDigits: 2 });

/** Explicação do cálculo (US-11). O resultado numérico já está na tela; isto chega depois. */
export default function ExplicacaoCorrida({ corridaId, explicacaoSalva }: Props) {
  const [estado, setEstado] = useState<Estado>(
    explicacaoSalva ? { tipo: "pronta", dados: explicacaoSalva } : { tipo: "carregando" }
  );
  const [tentativa, setTentativa] = useState(0);

  useEffect(() => {
    if (explicacaoSalva) {
      setEstado({ tipo: "pronta", dados: explicacaoSalva });
      return;
    }
    let cancelado = false;
    setEstado({ tipo: "carregando" });
    gerarExplicacao(corridaId)
      .then((dados) => !cancelado && setEstado({ tipo: "pronta", dados }))
      .catch(() => !cancelado && setEstado({ tipo: "erro" }));
    return () => {
      cancelado = true;
    };
  }, [corridaId, explicacaoSalva, tentativa]);

  return (
    <section aria-labelledby="titulo-explicacao" className="rounded-lg border border-slate-200 bg-white p-4">
      <h2 id="titulo-explicacao" className="text-base font-semibold">
        Explicação do cálculo
      </h2>

      {estado.tipo === "carregando" && (
        <p role="status" aria-live="polite" className="mt-3 animate-pulse text-sm text-slate-600">
          {MENSAGEM_ESPERA}
        </p>
      )}

      {estado.tipo === "erro" && (
        <div role="alert" className="mt-3 text-sm">
          <p className="text-red-700">Não foi possível carregar a explicação agora.</p>
          <button
            type="button"
            onClick={() => setTentativa((n) => n + 1)}
            className="mt-2 rounded-md border border-slate-300 px-4 text-slate-700 hover:bg-slate-50"
          >
            Tentar de novo
          </button>
        </div>
      )}

      {estado.tipo === "pronta" && <Conteudo dados={estado.dados} />}
    </section>
  );
}

function Conteudo({ dados }: { dados: ExplicacaoResposta }) {
  const { explicacao: e, origem } = dados;
  return (
    <div className="mt-3 space-y-4 text-sm">
      <p>{e.diagnostico}</p>

      {e.adicoes.length > 0 && (
        <div>
          <h3 className="font-medium">Adições</h3>
          <ul className="mt-1 list-disc space-y-1 pl-5">
            {e.adicoes.map((a) => (
              <li key={a.material}>
                <strong>{a.material}</strong>: {kg(a.massa_kg)} kg — {a.motivo}
              </li>
            ))}
          </ul>
        </div>
      )}

      {e.alertas.length > 0 && (
        <div className="rounded-md bg-amber-50 p-3 text-amber-900">
          <h3 className="font-medium">Atenção</h3>
          <ul className="mt-1 list-disc space-y-1 pl-5">
            {e.alertas.map((t) => (
              <li key={t}>{t}</li>
            ))}
          </ul>
        </div>
      )}

      {e.referencias.length > 0 && (
        <div>
          <h3 className="font-medium">Corridas parecidas</h3>
          <ul className="mt-1 space-y-1">
            {e.referencias.map((r) => (
              <li key={r.corrida}>
                <span className="font-medium">Corrida {r.corrida}:</span> {r.observacao}
              </li>
            ))}
          </ul>
        </div>
      )}

      <p className="text-xs text-slate-500">
        {origem === "GEMINI" ? "Texto gerado por IA a partir do resultado do motor." : "Explicação padrão (IA indisponível)."}
      </p>
    </div>
  );
}