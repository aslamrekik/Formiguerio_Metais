# LIGA APP

Cálculo e correção da composição química de ligas secundárias de alumínio.
MVP para a **Formigueiro Metais** · entrega em 30/10/2026.

> Este repositório traz a **estrutura e as dependências**. A implementação é da
> equipe, história por história. Cada arquivo tem no topo a referência ao DAS e a
> história correspondente (`TODO US-xx`).

| Documento | Para quem |
| --- | --- |
| Visão e Escopo | cliente |
| DAS (arquitetura) | equipe |
| Plano de Projeto | equipe |

## Rodando o projeto

Precisa de: Docker, Node 20 e Python 3.12.

```bash
# banco + API
docker compose up --build        # http://localhost:8000/saude e /docs

# frontend
cd web && cp .env.example .env && npm install && npm run dev   # http://localhost:5173

# motor
pip install -e "engine[dev]"
pytest engine/tests -q
```

## Estrutura

```
web/       React + Vite + TypeScript + Tailwind
  src/lib/api.ts        cliente da API
  src/pages/            Login, Cadastros, Cálculo, Histórico
api/       FastAPI: routers -> services -> repositories
  app/routers/          auth, cadastros, corridas
  app/services/         regras de aplicação, conversa com o engine
  app/explicacao/       Gemini, validador de números, explicação padrão
  app/relatorios/       PDF com WeasyPrint
  tests/                testes da API (inclui o teste de arquitetura)
engine/    Python puro: motor de cálculo e calibração (sem banco, sem rede)
  tests/casos_reais/    corridas validadas pelo cliente, rodam no CI
exemplos/  planilhas modelo para o cliente preencher
```

## Regras que não se negociam

1. **A IA não calcula.** Os números vêm do `engine`. O Gemini só explica, e todo
   número da explicação passa pelo validador.
2. **`engine/` não importa nada de `api/`**, não acessa banco e não faz rede.
   Existe um teste que falha se isso for quebrado (`api/tests/test_arquitetura.py`).
3. **Todo cálculo tem explicação.** Se o Gemini falha, entra a explicação padrão.
4. **Casos reais são a régua da precisão.** `engine/tests/casos_reais/` roda no CI;
   se um caso divergir, o build falha. Nunca ajuste o caso para o motor passar.
5. **Corrida confirmada não se apaga**, e guarda a versão do motor e da calibração.

## Ambientes

| Ambiente | Branch | Banco |
| --- | --- | --- |
| Local | `feature/US-xx` | PostgreSQL do `docker compose` |
| Staging | `develop` | Supabase `liga-staging` |
| Produção | `main` | Supabase `liga-prod` |

Variáveis de ambiente: ver `api/app/config.py` e a seção 10.3 do DAS.
Nenhuma chave vai para o repositório.

## Fluxo de trabalho

Branch `feature/US-xx-descricao` → PR com o template → 1 aprovação (Lorenzo ou Aslam)
→ merge em `develop` (publica em staging) → fim de sprint: `develop` em `main`.

Commits: `feat:`, `fix:`, `test:`, `docs:`, `chore:`. PR de até 400 linhas.

## Equipe

| Frente | Pessoas | Histórias |
| --- | --- | --- |
| Motor e calibração | Ruann Walter, Matheus Grokoski | US-07, 08, 09, 17 |
| Backend | Arthur Pessoa | US-02 a 06, 14, 15, 16, 18 |
| Frontend | Lucas Perusselli, Gabriel Canoff | US-03 a 06, 10, 14, 15, 18 |
| Explicação com IA | Matheus Bueno, Pedro Basílio | US-11, 12, 13 |
| Gestão, arquitetura, revisão de PR, QA e deploy | Lorenzo Pedrozo, Aslam Rekik | US-01, 19, 20 |
