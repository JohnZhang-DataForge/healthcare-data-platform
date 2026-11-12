# Context: pinned upstream OHDSI/Atlas3 v3.0.0 commit
# f775da50dfcd8b7fa5c57abc2e2654650d37ee4b. Never build from a floating branch.
FROM node:20-alpine AS build
WORKDIR /app
COPY package*.json ./
RUN npm ci
COPY . .
# Guard against stale report errors when switching from empty Drug Era to populated Person.
RUN npm run test:unit:run -- tests/unit/stores/datasources.spec.ts
RUN npm run build

FROM caddy:2-alpine
LABEL org.opencontainers.image.source="https://github.com/JohnZhang-DataForge/healthcare-data-platform"
LABEL org.opencontainers.image.title="Healthcare ATLAS3 UI"
LABEL org.opencontainers.image.version="3.0.0"
COPY --from=build /app/dist /srv/atlas
COPY docker/config-local.json /srv/atlas/config-local.json
# /etc/caddy/Caddyfile is injected by the version-controlled K8s ConfigMap.
EXPOSE 8080
