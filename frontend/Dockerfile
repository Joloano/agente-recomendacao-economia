# syntax=docker/dockerfile:1.7

# Imagens fixadas por digest (build reproduzível). Ficam literais no FROM para o
# Dependabot conseguir atualizá-las (ele não resolve ARG em FROM).

# ---------- Estágio 1: build do Angular ----------
FROM node:26-alpine@sha256:6bd9ab43c0ec0190ca7b2d193906cb8b7edf6e7f4afa43ddeccd6452710bffb5 AS build

WORKDIR /app
# Dependências primeiro: a camada fica em cache enquanto o lockfile não muda.
COPY package.json package-lock.json ./
RUN --mount=type=cache,target=/root/.npm npm ci --no-audit --no-fund

COPY . .
RUN npx ng build --configuration production

# ---------- Estágio 2: nginx sem root ----------
FROM nginxinc/nginx-unprivileged:1.31-alpine@sha256:b5047b9b76845eac124358373c6852377c52e4b05834a47647e955dd91cb8f1e AS final

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
