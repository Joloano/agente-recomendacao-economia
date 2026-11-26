# Changelog

Todas as mudanças relevantes deste projeto são registradas aqui.
O formato segue o [Keep a Changelog](https://keepachangelog.com/pt-BR/1.1.0/) e o projeto usa [SemVer](https://semver.org/lang/pt-BR/).

## [Não lançado]

### Alterado
- Repositório reorganizado em monorepo: `backend/`, `frontend/`, `docs/` e `legado/` (agente de terminal original, agora executável de qualquer pasta).

### Adicionado
- Gestão de usuários pelo admin (`/admin/usuarios`): lista paginada com busca e filtros, criação (inclusive de admins), edição parcial, promoção, ativação e exclusão, sempre mantendo ao menos um admin ativo (com trava contra corrida). Perfil próprio (`/usuarios/eu`): editar nome e e-mail e trocar a senha. Paginação padrão `Pagina[T]` para todas as listas.
- Serviço de e-mail transacional (padrão Adapter): SMTP (inclusive relay de SES, Brevo e Resend) e envio em memória para testes; modelos HTML e texto em português (boas-vindas, verificação, recuperação de senha, alertas) com Jinja2 e escape automático; guia de SPF, DKIM e DMARC em `docs/email.md`.
- Autenticação: cadastro de cliente, login OAuth2 com JWT, `/auth/eu`, senhas argon2id com política mínima, dependências `usuario_atual`/`exigir_admin` e `garantir_acesso` (cliente só vê o que é seu, com 404; admin vê tudo).
- Imagem Docker da interface: build do Angular em Node 24 e nginx sem root, com proxy de `/api` (DNS dinâmico, `X-Forwarded-*` à prova de falsificação), fallback da SPA, cabeçalhos de segurança (CSP só com `self`), gzip e cache imutável só para arquivos com hash.
- `docker-compose.yml` com banco, migração única, API e web endurecidos (sem privilégios extras, só leitura, logs com rotação) e `docker-compose.override.yml` de desenvolvimento com hot reload da API, Mailpit e pgAdmin opcional.
- Frontend Angular 22 com Angular Material 3: layout responsivo (barra superior, menu lateral que esconde itens de admin, atalho para o conteúdo), tema energia/água, `pt-BR`, `ApiService` que traduz erros RFC 7807, sessão com sinais, proxy de desenvolvimento, ESLint, Prettier e Vitest.
- Imagem Docker da API: multi-stage, base fixada por digest, dependências com hashes (`requirements-lock.txt`), usuário sem privilégios e código só leitura, `HEALTHCHECK` de liveness e entrypoint que migra (com advisory lock entre réplicas) e sobe o Uvicorn.
- Rota `/api/v1/health/live` (liveness sem banco) e Dependabot para a imagem base, dependências Python e Actions (sem versões maiores do Postgres e do TypeScript, que exigem migração planejada).
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
