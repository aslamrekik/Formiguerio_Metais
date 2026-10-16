// Cliente da API. Token em localStorage, Authorization: Bearer em toda chamada.
// 401 limpa o token e volta para o login.
//
// TODO US-03 a US-18: login, ligas, materias-primas, calcular, explicacao,
// analise final e download do relatorio.

export const BASE = import.meta.env.VITE_API_URL ?? "http://localhost:8000";

// TODO US-03: usar a mesma chave que o login gravar.
const TOKEN_KEY = "token";

async function req<T>(caminho: string, init: RequestInit = {}): Promise<T> {
  const token = localStorage.getItem(TOKEN_KEY);
  const resposta = await fetch(`${BASE}${caminho}`, {
    ...init,
    headers: {
      "Content-Type": "application/json",
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
      ...init.headers,
    },
  });
  if (resposta.status === 401) {
    localStorage.removeItem(TOKEN_KEY);
    // TODO US-03: rota real do login. O if evita recarregar a pagina em loop.
    if (window.location.pathname !== "/login") window.location.href = "/login";
    throw new Error("Sessão expirada");
  }
  if (!resposta.ok) {
    const corpo = await resposta.json().catch(() => ({}));
    throw new Error(corpo.detail ?? `Erro ${resposta.status}`);
  }
  return resposta.status === 204 ? (undefined as T) : resposta.json();
}

// ---- US-14: corridas e histórico ------------------------------------------
export type StatusCorrida = "RASCUNHO" | "CONFIRMADA" | "FINALIZADA";

export interface CorridaResumo {
  id: string;
  liga_id: string;
  status: StatusCorrida;
  versao_motor: string;
  versao_calibracao: number;
  criada_em: string;
  confirmada_em: string | null;
}

export interface Corrida extends CorridaResumo {
  usuario_id: string;
  entrada: Record<string, unknown>;
  resultado: Record<string, unknown>;
  explicacao: string | null;
  analise_final: Record<string, unknown> | null;
  finalizada_em: string | null;
}

export interface NovaCorrida {
  liga_id: string;
  entrada: Record<string, unknown>;
  resultado: Record<string, unknown>;
  explicacao?: string | null;
}

export interface FiltroHistorico {
  liga_id?: string;
  de?: string; // AAAA-MM-DD
  ate?: string; // AAAA-MM-DD
  status?: StatusCorrida;
}

export const salvarCorrida = (corrida: NovaCorrida) =>
  req<Corrida>("/corridas", { method: "POST", body: JSON.stringify(corrida) });

export const confirmarCorrida = (id: string) =>
  req<Corrida>(`/corridas/${id}/confirmar`, { method: "POST" });

export const obterCorrida = (id: string) => req<Corrida>(`/corridas/${id}`);

export const apagarRascunho = (id: string) =>
  req<void>(`/corridas/${id}`, { method: "DELETE" });

export function listarHistorico(filtro: FiltroHistorico = {}) {
  const params = new URLSearchParams();
  Object.entries(filtro).forEach(([chave, valor]) => {
    if (valor) params.set(chave, valor);
  });
  const consulta = params.toString();
  return req<{ total: number; itens: CorridaResumo[] }>(
    `/corridas${consulta ? `?${consulta}` : ""}`
  );
}
