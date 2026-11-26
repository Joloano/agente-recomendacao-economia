# Backend

API REST em Python (FastAPI). Visão geral e convenções no [AGENTS.md](../AGENTS.md).

## Desenvolvimento local

```bash
cd backend
python -m venv .venv
.venv/Scripts/activate        # Windows  (Linux/macOS: source .venv/bin/activate)
pip install -e ".[dev]"
cp ../.env.example ../.env    # lido da raiz do repositório; fora do Docker use POSTGRES_HOST=localhost
uvicorn app.main:app --reload
```

Swagger em http://localhost:8000/docs · saúde em http://localhost:8000/api/v1/health

## Banco e migrações

```bash
alembic upgrade head                                # aplica as migrações
alembic revision --autogenerate -m "descrição"       # gera migração a partir dos modelos
alembic downgrade -1                                # desfaz a última
alembic check                                       # falha se modelos e migrações divergirem
```

Regras: nunca `create_all` em produção; enums são texto com `CHECK` (sem `ALTER TYPE`);
nomes de constraints seguem a convenção de `app/modelos/base.py`.

## Qualidade

```bash
pytest            # testes + cobertura (mínimo 80%)
# testes de integração com Postgres real (pulados sem a variável):
TESTE_BANCO_URL=postgresql+psycopg://agente:agente@localhost:5432/agente_teste pytest tests/integracao
ruff check .      # lint
ruff format .     # formatação
mypy app tests    # tipos (modo estrito)
```

## Estrutura

| Pasta | Responsabilidade |
|---|---|
| `app/api/v1/` | Rotas HTTP (finas: validam entrada e chamam serviços) |
| `app/core/` | Configuração, banco, erros (RFC 7807) e segurança |
| `app/agente/` | Núcleo do agente (domínio puro, sem banco) |
| `app/modelos/` | Tabelas SQLAlchemy |
| `alembic/` | Migrações |
| `tests/` | Testes com pytest |

Erros seguem o formato `application/problem+json` (RFC 7807), com `detail` em português
e, em erros de validação, a lista `erros` com `campo` e `mensagem`.
