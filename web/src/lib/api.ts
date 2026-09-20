// Cliente da API. Token em localStorage, Authorization: Bearer em toda chamada.
// 401 limpa o token e volta para o login.
//
// TODO US-03 a US-18: login, ligas, materias-primas, calcular, explicacao,
// confirmar, analise final, historico e download do relatorio.

export const BASE = import.meta.env.VITE_API_URL ?? "http://localhost:8000";
