#!/bin/sh
# Ponto de entrada do container da API.
#   api       → aplica as migrações (se MIGRAR_AO_SUBIR=true) e sobe o Uvicorn
#   migrar    → só aplica as migrações
#   qualquer outro comando é executado como está (ex.: `python -m app.seed`)
set -eu

migrar() {
    echo "Aplicando migrações do banco..."
    alembic upgrade head
}

case "${1:-api}" in
    api)
        if [ "${MIGRAR_AO_SUBIR:-true}" = "true" ]; then
            migrar
        fi
        exec uvicorn app.main:app \
            --host 0.0.0.0 \
            --port "${PORTA:-8000}" \
            --workers "${WORKERS:-2}" \
            --proxy-headers \
            --forwarded-allow-ips "${IPS_PROXY_CONFIAVEIS:-127.0.0.1}" \
            --no-server-header
        ;;
    migrar)
        migrar
        ;;
    *)
        exec "$@"
        ;;
esac
