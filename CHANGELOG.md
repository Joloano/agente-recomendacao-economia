# Changelog

Todas as mudanças relevantes deste projeto são registradas aqui.
O formato segue o [Keep a Changelog](https://keepachangelog.com/pt-BR/1.1.0/) e o projeto usa [SemVer](https://semver.org/lang/pt-BR/).

## [Não lançado]

### Alterado
- Repositório reorganizado em monorepo: `backend/`, `frontend/`, `docs/` e `legado/` (agente de terminal original, agora executável de qualquer pasta).

### Adicionado
- `.env.example` com todas as variáveis de ambiente.
- Processo de contribuição: `CONTRIBUTING.md`, Definição de Pronto, templates de issue e PR, `CODEOWNERS`.
- `pre-commit` com ruff, gitleaks, mypy, prettier, eslint e validação de Conventional Commits; validação do título do PR no CI; merge somente por squash.
- `.gitattributes` e `.editorconfig` padronizando fim de linha e formatação.
- Licença proprietária.
- `AGENTS.md`, README do produto e diagramas ER e de classes.

## [0.1.0] - 2026-11-15

### Adicionado
- Agente de terminal (`agente_energia.py`) do Trabalho 2 da disciplina UFSM01280: percepção, elegibilidade, utilidade ponderada, recomendações ordenadas e feedback.

[Não lançado]: https://github.com/Joloano/agente-recomendacao-energia/compare/v0.1.0...HEAD
[0.1.0]: https://github.com/Joloano/agente-recomendacao-energia/releases/tag/v0.1.0
