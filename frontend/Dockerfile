# syntax=docker/dockerfile:1.7

# Imagens fixadas por digest (build reproduzível). Ficam literais no FROM para o
# Dependabot conseguir atualizá-las (ele não resolve ARG em FROM).

# ---------- Estágio 1: build do Angular ----------
FROM node:24-alpine@sha256:116b800c3754b440ee0aa3ed2f20f5bf3d99a554bfd9adeea09ea8017f6e85f5 AS build

WORKDIR /app
# Dependências primeiro: a camada fica em cache enquanto o lockfile não muda.
COPY package.json package-lock.json ./
RUN --mount=type=cache,target=/root/.npm npm ci --no-audit --no-fund

COPY . .
RUN npx ng build --configuration production

# ---------- Estágio 2: nginx sem root ----------
FROM nginxinc/nginx-unprivileged:1.29-alpine@sha256:0c79d56aee561a1d81c63f00eee5fb5fe29279560cdc55e91425133104c7fbe6 AS final

LABEL org.opencontainers.image.title="agente-recomendador-web" \
      org.opencontainers.image.description="Interface web do agente recomendador de energia e água" \
      org.opencontainers.image.source="https://github.com/Joloano/agente-recomendacao-economia" \
      org.opencontainers.image.licenses="LicenseRef-Proprietaria"

# Endereço do backend usado pelo proxy de /api (no compose, o serviço "api").
# O filtro garante que o envsubst só troque API_UPSTREAM no template.
ENV API_UPSTREAM=http://api:8000 \
    NGINX_ENVSUBST_FILTER=^API_UPSTREAM$

# O template é processado pelo entrypoint oficial (envsubst) ao subir o container.
COPY nginx.conf.template /etc/nginx/templates/default.conf.template
COPY nginx-seguranca.conf /etc/nginx/snippets/seguranca.conf
COPY --from=build /app/dist/agente-web/browser /usr/share/nginx/html

EXPOSE 8080

HEALTHCHECK --interval=15s --timeout=3s --start-period=10s --retries=3 \
    CMD wget -q -O /dev/null http://127.0.0.1:8080/saude || exit 1
