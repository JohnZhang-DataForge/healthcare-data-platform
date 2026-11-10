# Context: pinned upstream OHDSI/Atlas3 v3.0.0 commit
# f775da50dfcd8b7fa5c57abc2e2654650d37ee4b. Never build from a floating branch.
FROM node:20-alpine AS build
WORKDIR /app
COPY package*.json ./
RUN npm ci
COPY . .
RUN npm run build

FROM caddy:2-alpine
COPY --from=build /app/dist /srv/atlas
COPY docker/config-local.json /srv/atlas/config-local.json
# /etc/caddy/Caddyfile is injected by the version-controlled K8s ConfigMap.
EXPOSE 8080
