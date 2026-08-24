# syntax=docker/dockerfile:1

# ─── Étape commune : dépendances ───
# Même version de Node que la CI, et npm ci plutôt que npm install pour
# installer exactement les versions du package-lock.json
FROM node:22-alpine AS deps

WORKDIR /app

COPY package.json package-lock.json ./
RUN npm ci

# ─── Étape de développement ───
# Cible utilisée par infra/docker-compose.yml (target: dev). Sans elle, le
# compose de développement construisait l'image de production : nginx servait
# un bundle figé sur le port 80, alors que le compose publie le 5173 et monte
# les sources depuis l'hôte. Résultat, localhost:5173 ne répondait pas et le
# rechargement à chaud ne fonctionnait plus.
#
# --host 0.0.0.0 est indispensable : par défaut Vite n'écoute que sur la
# boucle locale du conteneur, donc reste injoignable depuis la machine hôte.
FROM deps AS dev

COPY . .

EXPOSE 5173
CMD ["npm", "run", "dev", "--", "--host", "0.0.0.0"]

# ─── Étape de construction du bundle ───
FROM deps AS build

# Vite lit les variables VITE_* au moment du BUILD et écrit leurs valeurs en
# dur dans les fichiers JS générés. Les fournir au démarrage du conteneur
# n'aurait aucun effet — elles doivent arriver ici, en arguments de build.
ARG VITE_KEYCLOAK_URL
ARG VITE_KEYCLOAK_REALM
ARG VITE_KEYCLOAK_CLIENT_ID
ENV VITE_KEYCLOAK_URL=${VITE_KEYCLOAK_URL} \
    VITE_KEYCLOAK_REALM=${VITE_KEYCLOAK_REALM} \
    VITE_KEYCLOAK_CLIENT_ID=${VITE_KEYCLOAK_CLIENT_ID}

COPY . .
RUN npm run build

# ─── Étape finale : service des fichiers statiques ───
# Dernière étape du fichier, donc celle produite par défaut : un "docker build"
# sans --target donne bien l'image de production. Plus de serveur de
# développement ici, nginx sert le contenu de dist/, sans Node ni sources.
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
