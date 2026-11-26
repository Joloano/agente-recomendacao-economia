# AGENTS.md

Guia para agentes de IA (e pessoas) que trabalham neste repositório.

## O produto

Plataforma web que recomenda ações de economia de **energia** e de **água** para residências.
O agente percebe os equipamentos da casa, filtra as oportunidades elegíveis, calcula a
**utilidade ponderada** pelas prioridades dos moradores, ordena as recomendações e aprende
com o feedback (aceitar/rejeitar), atualizando o consumo estimado.

- **Cliente**: cadastra-se, gerencia suas residências e equipamentos, roda simulações e responde às recomendações.
- **Admin** (dono do sistema): gerencia tudo — usuários, residências, equipamentos, categorias e simulações de qualquer cliente.

## Stack

| Camada | Tecnologia |
|---|---|
| Backend | Python 3.12 (mínimo 3.11), FastAPI, SQLAlchemy 2, Alembic, Pydantic v2 |
| Banco | PostgreSQL 16 |
| Autenticação | JWT com PyJWT (OAuth2 password flow), senhas com argon2 |
| Frontend | Angular 22 (standalone, signals), Angular Material 3 |
| Testes | pytest + httpx (backend), Vitest (frontend) |
| Qualidade | ruff (lint + format), mypy, ESLint, Prettier |
| Infra | Docker, Dockerfile por serviço, docker compose |

Todo o backend é em Python. Nada de lógica de negócio no frontend.

## Estrutura

```
.
├── backend/
│   ├── app/
│   │   ├── api/          # routers FastAPI (v1)
│   │   ├── core/         # config, segurança, dependências
│   │   ├── modelos/      # modelos SQLAlchemy (tabelas)
│   │   ├── schemas/      # Pydantic
│   │   ├── services/     # regras de aplicação
│   │   ├── agente/       # núcleo do agente (puro, sem I/O)
│   │   └── main.py
│   ├── alembic/
│   ├── tests/
│   ├── Dockerfile
│   └── pyproject.toml
├── frontend/
│   ├── src/app/
│   ├── Dockerfile
│   └── nginx.conf
├── dados/                # datasets CSV de seed (energia e água)
├── docs/diagramas.md     # diagrama ER e de classes
├── legado/agente_energia.py  # versão original do Trabalho 2 (referência)
├── docker-compose.yml
├── .env.example
└── README.md
```

## Regras do agente (não alterar sem issue)

Elegibilidade: `reducao_uso == True`, `economia_potencial > 0`, `essencialidade != "essencial"`, `impacto_conforto_1a5 <= 3`.

Notas (1 a 5): economia `1 + 4 * (economia / maior_economia_elegivel)`, conforto `6 - impacto`,
flexibilidade `flexibilidade_1a5`, baixo esforço `6 - esforco`.

Utilidade: soma de `peso * nota`; os pesos da residência somam 1.
Desempate: maior utilidade → maior economia → ordem de cadastro. O consumo nunca fica negativo,
e uma recomendação já tratada não é processada de novo.

Água usa as mesmas regras, com economia em **litros/dia** e tarifa em **R$/m³**.
Cada recurso é uma `EstrategiaRecurso`; o núcleo do agente (`app/agente/`) é Python puro e testável sem banco.

## Convenções

- Código, nomes, mensagens e commits em **português**.
- Uma issue por branch (`feat/<n>-descricao`, `fix/...`, `docs/...`); PR com `Closes #<n>` usando o template.
- Commits e títulos de PR em [Conventional Commits](CONTRIBUTING.md#commits) (`feat(agente): adiciona ...`).
- Commits pequenos e separados por parte (backend, frontend, infra, docs).
- Siga a [Definição de Pronto](CONTRIBUTING.md#definição-de-pronto) e os [padrões de projeto](docs/padroes-de-projeto.md).
- Decisões difíceis de reverter ganham um ADR em `docs/adr/`.
- Sem atribuição de ferramentas de IA em commits, PRs ou issues.
- Toda rota nova tem teste; toda regra do agente tem teste unitário.
- Rotas de admin protegidas por `exigir_admin`; cliente só enxerga os próprios dados.
- Segredos só em `.env` (nunca commitado); `.env.example` sempre atualizado.
- Migrações sempre via Alembic, nunca `create_all` em produção.

## Comandos

```bash
docker compose up --build          # sobe db, api e web
docker compose exec api alembic upgrade head
docker compose exec api pytest
docker compose exec api ruff check .
```

API: http://localhost:8000/docs · Frontend: http://localhost:4200

## Diagramas

Ver [docs/diagramas.md](docs/diagramas.md). Atualize os diagramas no mesmo PR que mudar o modelo.
