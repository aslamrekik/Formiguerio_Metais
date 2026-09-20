# Onboarding: primeiro dia no LIGA APP

## 1. Entenda o problema em 2 minutos

A fundição recebe sucata com composição variável. Para produzir uma liga dentro da
especificação, é preciso adicionar materiais ao banho. Hoje essa conta é feita à mão
e erra. Nós entregamos o cálculo certo, explicado, que aprende com as corridas reais.

## 2. Leia só a sua parte do DAS

| Você está em | Leia |
| --- | --- |
| Motor (Ruann, Grokoski) | seções 7, 12 e 14 |
| Backend (Arthur) | seções 7, 9, 10 e 11 |
| Frontend (Lucas, Gabriel) | seções 6, 8 e 14 |
| IA (Bueno, Pedro) | seções 8, 13 e 14 |

Todos: seções 3 (metas) e 5 (decisões). São duas páginas.

## 3. Rode o projeto

Siga o README. Se o `docker compose up` funcionar e o `/saude` responder, está pronto.

## 4. Pegue um cartão

No Trello, coluna **A fazer**. Regras: um cartão por pessoa em "Fazendo", limite de 5
na coluna. Se "Revisão e teste" encher (3), ajude a revisar antes de puxar outro.

## 5. Antes de abrir o PR

- [ ] `pytest engine/tests -q` verde (se mexeu no motor)
- [ ] `cd api && pytest -q` verde (se mexeu na API)
- [ ] `cd web && npm run build` verde (se mexeu no frontend)
- [ ] Critério de aceite do cartão conferido
- [ ] PR pequeno (se passar de 400 linhas, divida)

## 6. Dúvidas

- Dúvida técnica ou de arquitetura: Aslam
- Prazo, escopo, cliente: Lorenzo
- Dúvida sobre metalurgia: anote no cartão; vai para a validação semanal com o cliente
