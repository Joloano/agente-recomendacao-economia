# Changelog

Todas as mudanças relevantes deste projeto são registradas aqui.
O formato segue o [Keep a Changelog](https://keepachangelog.com/pt-BR/1.1.0/) e o projeto usa [SemVer](https://semver.org/lang/pt-BR/).

## [Não lançado]

### Alterado
- Repositório reorganizado em monorepo: `backend/`, `frontend/`, `docs/` e `legado/` (agente de terminal original, agora executável de qualquer pasta).

### Adicionado
- Frontend Angular 22 com Angular Material 3: layout responsivo (barra superior, menu lateral que esconde itens de admin, atalho para o conteúdo), tema energia/água, `pt-BR`, `ApiService` que traduz erros RFC 7807, sessão com sinais, proxy de desenvolvimento, ESLint, Prettier e Vitest.
- Imagem Docker da API: multi-stage, base fixada por digest, dependências com hashes (`requirements-lock.txt`), usuário sem privilégios e código só leitura, `HEALTHCHECK` de liveness e entrypoint que migra (com advisory lock entre réplicas) e sobe o Uvicorn.
- Rota `/api/v1/health/live` (liveness sem banco) e Dependabot para a imagem base, dependências Python e Actions.
- Banco PostgreSQL: modelos SQLAlchemy 2 (usuário, residência, preferência, categoria, equipamento, simulação, recomendação e feedback) com CHECKs de escalas, medida conforme o recurso e chaves estrangeiras indexadas; Alembic com migração inicial e testes de integração (upgrade, downgrade, sincronia modelo × migração e constraints).
- Núcleo do agente em Python puro (`app/agente/`) com Facade, Strategy, Template Method, Factory Method e Chain of Responsibility; valores em `Decimal`, explicação do motivo de inelegibilidade e contribuição de cada critério; testes de regressão que reproduzem o agente original em R01–R10.
- Documentação de padrões de projeto, ADR 0001 (arquitetura em camadas) e diagrama de classes do núcleo.
- Pipeline de CI no GitHub Actions: pre-commit, backend (ruff, mypy, pytest com Postgres e cobertura), frontend (lint, testes e build) e build das imagens Docker, com filtro por pasta e job agregador `CI concluído`.
- Backend FastAPI: rota `/api/v1/health` com verificação do banco (timeout de conexão), Swagger em `/docs`, CORS restrito e erros no formato RFC 7807 preservando cabeçalhos.
- Configuração 12-factor validada na subida: perfis `dev`, `teste`, `staging` e `producao`; em staging/produção exige variáveis explícitas, senhas fortes e CORS sem localhost ou curinga.
- `.env.example` com todas as variáveis de ambiente.
- Processo de contribuição: `CONTRIBUTING.md`, Definição de Pronto, templates de issue e PR, `CODEOWNERS`.
- `pre-commit` com ruff, gitleaks, mypy, prettier, eslint e validação de Conventional Commits; validação do título do PR no CI; merge somente por squash.
- `.gitattributes` e `.editorconfig` padronizando fim de linha e formatação.
- Licença proprietária.
- `AGENTS.md`, README do produto e diagramas ER e de classes.

## [0.1.0] - 2026-11-15

### Adicionado
- Agente de terminal (`agente_energia.py`) do Trabalho 2 da disciplina UFSM01280: percepção, elegibilidade, utilidade ponderada, recomendações ordenadas e feedback.

[Não lançado]: https://github.com/Joloano/agente-recomendacao-economia/compare/v0.1.0...HEAD
[0.1.0]: https://github.com/Joloano/agente-recomendacao-economia/releases/tag/v0.1.0
