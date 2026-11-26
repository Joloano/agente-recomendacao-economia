#!/bin/sh
# Ponto de entrada do container da API.
#   api       → aplica as migrações (se MIGRAR_AO_SUBIR=true) e sobe o Uvicorn
#   migrar    → só aplica as migrações (ex.: serviço único antes das réplicas)
#   qualquer outro comando é executado como está (ex.: `python -m app.seed`)
#
# Várias réplicas podem migrar ao mesmo tempo com segurança: o alembic/env.py usa um
# advisory lock do PostgreSQL, então só uma aplica e as outras esperam.
#
# IPS_PROXY_CONFIAVEIS: IP ou CIDR do proxy reverso (ex.: 172.18.0.0/16 na rede do compose).
# Nunca use * com a porta 8000 exposta: qualquer cliente poderia falsificar IP e protocolo.
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
            --timeout-graceful-shutdown "${TEMPO_DESLIGAMENTO_S:-30}" \
            --no-server-header
        ;;
    migrar)
        migrar
        ;;
    *)
        exec "$@"
        ;;
esac
