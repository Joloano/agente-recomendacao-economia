# syntax=docker/dockerfile:1.7

# Base fixada por digest (build reproduzível). O Dependabot atualiza o digest e o lockfile
# (por isso a imagem fica literal no FROM); o rebuild traz correções de segurança do SO.

# ---------- Estágio 1: dependências ----------
FROM python:3.12-slim@sha256:191083cdf6c7bda8c76158983163ead5d5cf7b77cf3033e805bb0f5296f51b4b AS dependencias

ENV PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PYTHONDONTWRITEBYTECODE=1

RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Versões exatas e hashes conferidos; a camada só é refeita quando o lockfile muda.
COPY requirements-lock.txt /tmp/requirements-lock.txt
RUN pip install --require-hashes --no-deps -r /tmp/requirements-lock.txt \
    && pip uninstall -y pip

# ---------- Estágio 2: imagem final ----------
FROM python:3.12-slim@sha256:191083cdf6c7bda8c76158983163ead5d5cf7b77cf3033e805bb0f5296f51b4b AS final

LABEL org.opencontainers.image.title="agente-recomendador-api" \
      org.opencontainers.image.description="API REST do agente recomendador de energia e água" \
      org.opencontainers.image.source="https://github.com/Joloano/agente-recomendacao-economia" \
      org.opencontainers.image.licenses="LicenseRef-Proprietaria"

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH="/opt/venv/bin:$PATH" \
    PORTA=8000

RUN groupadd --system --gid 1001 app \
    && useradd --system --uid 1001 --gid app --no-create-home --shell /usr/sbin/nologin app

COPY --from=dependencias /opt/venv /opt/venv

# Código pertence ao root e é só leitura para o usuário da aplicação.
WORKDIR /app
COPY alembic.ini ./
COPY alembic ./alembic
COPY app ./app
COPY --chmod=755 docker-entrypoint.sh /usr/local/bin/docker-entrypoint.sh

USER app
EXPOSE 8000

# Liveness: não depende do banco, para uma falha externa não causar reinícios em loop.
HEALTHCHECK --interval=15s --timeout=5s --start-period=60s --retries=3 \
    CMD python -c "import os, urllib.request; urllib.request.urlopen(f'http://127.0.0.1:{os.environ.get(\"PORTA\", \"8000\")}/api/v1/health/live', timeout=4)" || exit 1

ENTRYPOINT ["docker-entrypoint.sh"]
CMD ["api"]
