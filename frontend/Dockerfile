# syntax=docker/dockerfile:1

# ─── Étape 1 : construction du bundle ───
FROM node:22-alpine AS build

WORKDIR /app

# Vite lit les variables VITE_* au moment du BUILD et écrit leurs valeurs en
# dur dans les fichiers JS générés. Les fournir au démarrage du conteneur
# n'aurait aucun effet — elles doivent arriver ici, en arguments de build.
ARG VITE_KEYCLOAK_URL
ARG VITE_KEYCLOAK_REALM
ARG VITE_KEYCLOAK_CLIENT_ID
ENV VITE_KEYCLOAK_URL=${VITE_KEYCLOAK_URL} \
    VITE_KEYCLOAK_REALM=${VITE_KEYCLOAK_REALM} \
    VITE_KEYCLOAK_CLIENT_ID=${VITE_KEYCLOAK_CLIENT_ID}

# Même version de Node que la CI, et npm ci plutôt que npm install pour
# installer exactement les versions du package-lock.json
COPY package.json package-lock.json ./
RUN npm ci

COPY . .
RUN npm run build

# ─── Étape 2 : service des fichiers statiques ───
# Plus de serveur de développement en production : nginx sert le contenu de
# dist/, sans Node ni sources dans l'image finale.
FROM nginx:alpine

COPY --from=build /app/dist /usr/share/nginx/html

# React Router gère les routes côté navigateur. Sans ce try_files, un
# rafraîchissement sur /meetings/42 chercherait un fichier de ce nom sur le
# disque et renverrait 404 au lieu de l'application.
COPY <<'EOF' /etc/nginx/conf.d/default.conf
server {
    listen 80;
    server_name _;

    root /usr/share/nginx/html;
    index index.html;

    location / {
        try_files $uri $uri/ /index.html;
    }
}
EOF

EXPOSE 80
