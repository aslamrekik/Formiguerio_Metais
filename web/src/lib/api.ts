// Cliente da API. Token em localStorage, Authorization: Bearer em toda chamada.
// 401 limpa o token e volta para o login.
//
// TODO US-03 a US-18: login, ligas, materias-primas, calcular, explicacao,
// confirmar, analise final, historico e download do relatorio.

export const BASE = import.meta.env.VITE_API_URL ?? "http://localhost:8000";

// ---------------------------------------------------------------- explicacao (US-11)
const CHAVE_TOKEN = "liga_token";

export type OrigemExplicacao = "GEMINI" | "PADRAO";

/** Formato do DAS 13.3. */
export interface Explicacao {
  diagnostico: string;
  adicoes: { material: string; massa_kg: number; motivo: string }[];
  alertas: string[];
  referencias: { corrida: string; observacao: string }[];
}

export interface ExplicacaoResposta {
  explicacao: Explicacao;
  origem: OrigemExplicacao;
}

// Uma chamada por corrida por vez: evita pedir duas vezes ao Gemini (ex.: React StrictMode).
const explicacoesEmAndamento = new Map<string, Promise<ExplicacaoResposta>>();

/** POST /corridas/{id}/explicacao. O backend salva e nunca gera duas vezes. */
export function gerarExplicacao(corridaId: string): Promise<ExplicacaoResposta> {
  const existente = explicacoesEmAndamento.get(corridaId);
  if (existente) return existente;

  const token = localStorage.getItem(CHAVE_TOKEN);
  const promessa = fetch(`${BASE}/corridas/${encodeURIComponent(corridaId)}/explicacao`, {
    method: "POST",
    headers: token ? { Authorization: `Bearer ${token}` } : {},
  })
    .then((resp) => {
      if (resp.status === 401) {
        localStorage.removeItem(CHAVE_TOKEN);
        window.location.assign("/login");
      }
      if (!resp.ok) throw new Error(`Falha ao gerar a explicação (HTTP ${resp.status})`);
      return resp.json() as Promise<ExplicacaoResposta>;
    })
    .finally(() => explicacoesEmAndamento.delete(corridaId));

  explicacoesEmAndamento.set(corridaId, promessa);
  return promessa;
}