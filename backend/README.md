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

## Autenticação

| Rota | O quê |
|---|---|
| `POST /api/v1/auth/registrar` | Cria uma conta de **cliente** (o papel nunca vem do corpo) |
| `POST /api/v1/auth/login` | OAuth2 *password* (`username` = e-mail) → token JWT de acesso |
| `GET /api/v1/auth/eu` | Usuário autenticado |

- Senhas com argon2id; política de no mínimo 10 caracteres, sem regras de composição forçadas
  (NIST SP 800-63B), não igual ao e-mail.
- JWT com algoritmo fixo, `iss`, `aud`, `exp` obrigatório e `jti`. O papel é lido do banco a cada
  requisição: desativar ou rebaixar alguém vale na hora.
- Login inválido, e-mail inexistente e conta inativa dão a mesma resposta (401), com tempo parecido.
- Limite de tentativas (429 + `Retry-After`): login com 5 por e-mail+IP, 30 por e-mail e 50 por IP
  a cada 15 min; 10 cadastros por IP por hora. A tentativa é reservada antes do argon2 e a
  contagem fica no banco (`tentativa_acesso`, só HMAC). Atrás de um proxy TLS, configure o
  `real_ip` no nginx (#63) para o IP do cliente não virar o do proxy.
- Nas rotas, use `UsuarioDep` (autenticado), `AdminDep` (só admin) e `garantir_acesso(usuario,
  dono_id, "Recurso")`. Cliente que tenta acessar dado de outra pessoa recebe **404**, para não
  revelar que o dado existe.

## Verificação de e-mail, troca de e-mail e recuperação de senha

| Rota | O quê |
|---|---|
| `POST /api/v1/auth/verificacao/solicitar` | Reenvia o link de confirmação (do e-mail atual ou do pendente; 3 por hora) |
| `POST /api/v1/auth/verificacao/confirmar` | `{token}`: confirma o e-mail atual ou efetiva a troca pendente |
| `POST /api/v1/auth/senha/esqueci` | Sempre 202 e sem consultar a conta na requisição; 3 por e-mail e 20 por IP por hora |
| `POST /api/v1/auth/senha/redefinir` | `{token, nova_senha}`: troca a senha, derruba as sessões e avisa por e-mail |
| `PATCH /api/v1/usuarios/eu` com `email` | Exige `senha_atual`; o novo e-mail fica **pendente** até ser confirmado |
| `POST /api/v1/usuarios/eu/senha` | Troca a senha, derruba as outras sessões e devolve um token novo |

- Links com o token no **fragmento** (`/redefinir-senha#token=...`): o navegador nunca o envia
  ao servidor, então ele não aparece em logs nem no Referer.
- Tokens de 256 bits, de uso único, presos ao endereço para o qual foram enviados (24 h para
  verificação e 30 min para recuperação). Só o hash SHA-256 fica no banco, e um pedido novo
  invalida o link anterior.
- **Versão das credenciais**: trocar ou redefinir a senha, ou efetivar uma troca de e-mail, sobe
  `versao_credenciais`. Os tokens de acesso com versão antiga recebem 401, e os links pendentes
  são invalidados.
- Pedido de troca de e-mail: o endereço atual é avisado e o novo recebe a confirmação.
- `email_verificado_em` é informativo por enquanto (não bloqueia login nem ações).

## Usuários

| Rota | Quem | O quê |
|---|---|---|
| `GET /api/v1/admin/usuarios?busca=&papel=&ativo=&pagina=&tamanho=` | admin | Lista paginada (`itens`, `total`, `pagina`, `tamanho`) |
| `POST /api/v1/admin/usuarios` | admin | Cria usuário, inclusive admin |
| `GET`/`PATCH`/`DELETE /api/v1/admin/usuarios/{id}` | admin | Detalhe, edição parcial (nome, e-mail, papel, ativo) e exclusão |
| `GET`/`PATCH /api/v1/usuarios/eu` | qualquer usuário | Ver e editar nome e e-mail |
| `POST /api/v1/usuarios/eu/senha` | qualquer usuário | Trocar a senha (exige a atual) |

O sistema nunca fica sem admin ativo: rebaixar, desativar ou excluir o último admin dá 409. As
linhas dos admins são travadas (`SELECT ... FOR UPDATE`) para duas requisições simultâneas não
contornarem a regra.

## Docker

```bash
docker build -t agente-api backend/
docker run --env-file .env -p 8000:8000 agente-api          # migra e sobe a API
docker run --env-file .env agente-api migrar                # só migra
docker run --env-file .env agente-api python -m app.seed    # qualquer outro comando
```

A imagem é multi-stage, com base fixada por digest e dependências instaladas de
`requirements-lock.txt` com hashes. Roda como usuário sem privilégios (uid 1001), com o código só
leitura e sem pip na imagem final. Pode rodar com `--read-only --tmpfs /tmp`.

- `HEALTHCHECK` usa `/api/v1/health/live` (não depende do banco); `/api/v1/health` é a readiness.
- As migrações rodam ao subir (`MIGRAR_AO_SUBIR`); várias réplicas podem subir juntas, pois um
  advisory lock do PostgreSQL deixa só uma migrar.

Ao mudar dependências no `pyproject.toml`, regenere o lockfile com o comando do cabeçalho de
`requirements-lock.txt` (o CI confere).

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
