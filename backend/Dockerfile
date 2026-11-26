# syntax=docker/dockerfile:1.7

# ---------- Estágio 1: dependências ----------
FROM python:3.12-slim AS dependencias

ENV PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PYTHONDONTWRITEBYTECODE=1

WORKDIR /build
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Só o pyproject primeiro: a camada de dependências fica em cache enquanto ele não mudar.
COPY pyproject.toml ./
RUN mkdir app && touch app/__init__.py \
    && pip install . \
    && pip uninstall -y agente-recomendador

# ---------- Estágio 2: imagem final ----------
FROM python:3.12-slim AS final

LABEL org.opencontainers.image.title="agente-recomendador-api" \
      org.opencontainers.image.description="API REST do agente recomendador de energia e água" \
      org.opencontainers.image.licenses="LicenseRef-Proprietaria"

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH="/opt/venv/bin:$PATH" \
    PORTA=8000

RUN groupadd --system --gid 1001 app \
    && useradd --system --uid 1001 --gid app --no-create-home --shell /usr/sbin/nologin app

COPY --from=dependencias /opt/venv /opt/venv

WORKDIR /app
COPY --chown=app:app alembic.ini ./
COPY --chown=app:app alembic ./alembic
COPY --chown=app:app app ./app
COPY --chown=app:app --chmod=755 docker-entrypoint.sh /usr/local/bin/docker-entrypoint.sh

USER app
EXPOSE 8000

HEALTHCHECK --interval=15s --timeout=5s --start-period=20s --retries=3 \
    CMD python -c "import os, urllib.request; urllib.request.urlopen(f'http://127.0.0.1:{os.environ.get(\"PORTA\", \"8000\")}/api/v1/health', timeout=4)" || exit 1

ENTRYPOINT ["docker-entrypoint.sh"]
CMD ["api"]
