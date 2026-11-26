# Backend

API REST em Python (FastAPI). Visão geral e convenções no [AGENTS.md](../AGENTS.md).

## Desenvolvimento local

```bash
cd backend
python -m venv .venv
.venv/Scripts/activate        # Windows  (Linux/macOS: source .venv/bin/activate)
pip install -e ".[dev]"
cp ../.env.example ../.env    # ajuste POSTGRES_HOST=localhost fora do Docker
uvicorn app.main:app --reload
```

Swagger em http://localhost:8000/docs · saúde em http://localhost:8000/api/v1/health

## Qualidade

```bash
pytest            # testes + cobertura (mínimo 80%)
ruff check .      # lint
ruff format .     # formatação
mypy app tests    # tipos (modo estrito)
```

## Estrutura

| Pasta | Responsabilidade |
|---|---|
| `app/api/v1/` | Rotas HTTP (finas: validam entrada e chamam serviços) |
| `app/core/` | Configuração, banco, erros (RFC 7807) e segurança |
| `tests/` | Testes com pytest |

Erros seguem o formato `application/problem+json` (RFC 7807), com `detail` em português
e, em erros de validação, a lista `erros` com `campo` e `mensagem`.
