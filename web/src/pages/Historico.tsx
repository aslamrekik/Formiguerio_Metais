import { FormEvent, useEffect, useState } from "react";

import {
  CorridaResumo,
  FiltroHistorico,
  StatusCorrida,
  listarHistorico,
} from "../lib/api";

const COR_STATUS: Record<StatusCorrida, string> = {
  RASCUNHO: "bg-slate-200 text-slate-700",
  CONFIRMADA: "bg-blue-100 text-blue-800",
  FINALIZADA: "bg-green-100 text-green-800",
};

const formatarData = (iso: string) =>
  new Date(iso).toLocaleString("pt-BR", { dateStyle: "short", timeStyle: "short" });

// US-14: histórico filtrável por liga e período.
export default function Historico() {
  const [filtro, setFiltro] = useState<FiltroHistorico>({});
  const [corridas, setCorridas] = useState<CorridaResumo[]>([]);
  const [total, setTotal] = useState(0);
  const [carregando, setCarregando] = useState(true);
  const [erro, setErro] = useState<string | null>(null);

  async function buscar(f: FiltroHistorico) {
    setCarregando(true);
    setErro(null);
    try {
      const resposta = await listarHistorico(f);
      setCorridas(resposta.itens);
      setTotal(resposta.total);
    } catch (e) {
      setErro(e instanceof Error ? e.message : "Erro ao carregar o histórico");
    } finally {
      setCarregando(false);
    }
  }

  useEffect(() => {
    buscar({});
  }, []);

  function aplicar(e: FormEvent) {
    e.preventDefault();
    buscar(filtro);
  }

  const campo = "rounded border border-slate-300 px-2 py-1 text-sm";

  return (
    <section>
      <h2 className="text-lg font-semibold">Histórico de corridas</h2>

      <form onSubmit={aplicar} className="mt-4 flex flex-wrap items-end gap-3">
        <label className="text-sm">
          Liga
          <input
            className={`${campo} ml-2`}
            placeholder="ex.: A356"
            value={filtro.liga_id ?? ""}
            onChange={(e) => setFiltro({ ...filtro, liga_id: e.target.value })}
          />
        </label>
        <label className="text-sm">
          De
          <input
            type="date"
            className={`${campo} ml-2`}
            value={filtro.de ?? ""}
            onChange={(e) => setFiltro({ ...filtro, de: e.target.value })}
          />
        </label>
        <label className="text-sm">
          Até
          <input
            type="date"
            className={`${campo} ml-2`}
            value={filtro.ate ?? ""}
            onChange={(e) => setFiltro({ ...filtro, ate: e.target.value })}
          />
        </label>
        <button type="submit" className="rounded bg-slate-800 px-3 py-1 text-sm text-white">
          Filtrar
        </button>
        <button
          type="button"
          className="text-sm text-slate-600 underline"
          onClick={() => {
            setFiltro({});
            buscar({});
          }}
        >
          Limpar
        </button>
      </form>

      {erro && <p className="mt-4 text-sm text-red-600">{erro}</p>}
      {carregando && <p className="mt-4 text-sm text-slate-500">Carregando…</p>}

      {!carregando && !erro && (
        <>
          <p className="mt-4 text-sm text-slate-500">{total} corrida(s)</p>
          <table className="mt-2 w-full text-left text-sm">
            <thead className="border-b border-slate-300 text-slate-600">
              <tr>
                <th className="py-2">Data</th>
                <th>Liga</th>
                <th>Estado</th>
                <th>Motor</th>
                <th>Calibração</th>
              </tr>
            </thead>
            <tbody>
              {corridas.map((c) => (
                <tr key={c.id} className="border-b border-slate-200">
                  <td className="py-2">{formatarData(c.criada_em)}</td>
                  <td>{c.liga_id}</td>
                  <td>
                    <span className={`rounded px-2 py-0.5 text-xs ${COR_STATUS[c.status]}`}>
                      {c.status}
                    </span>
                  </td>
                  <td>v{c.versao_motor}</td>
                  <td>v{c.versao_calibracao}</td>
                </tr>
              ))}
              {corridas.length === 0 && (
                <tr>
                  <td colSpan={5} className="py-6 text-center text-slate-500">
                    Nenhuma corrida encontrada.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </>
      )}
    </section>
  );
}
