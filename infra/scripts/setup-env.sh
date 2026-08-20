#!/bin/bash
# Script de configuration des variables d'environnement sur le VPS OVH
# À exécuter une seule fois après la première connexion SSH
# Usage : bash setup-env.sh

set -e

echo "=== Configuration Auris Production ==="

ENV_FILE="/opt/auris/.env.prod"

# Crée le dossier si nécessaire
mkdir -p /opt/auris

# Crée le fichier .env.prod avec les valeurs saisies interactivement
cat > "$ENV_FILE" << EOF
# ─── PostgreSQL ───
POSTGRES_USER=${POSTGRES_USER}
POSTGRES_PASSWORD=${POSTGRES_PASSWORD}

# ─── Keycloak ───
KEYCLOAK_REALM=${KEYCLOAK_REALM}
KEYCLOAK_CLIENT_ID=${KEYCLOAK_CLIENT_ID}
KEYCLOAK_CLIENT_SECRET=${KEYCLOAK_CLIENT_SECRET}
KEYCLOAK_ADMIN=${KEYCLOAK_ADMIN}
KEYCLOAK_ADMIN_PASSWORD=${KEYCLOAK_ADMIN_PASSWORD}
KC_HOSTNAME=${KC_HOSTNAME}

# ─── Mistral / Voxtral ───
MISTRAL_API_KEY=${MISTRAL_API_KEY}
VOXTRAL_MODEL=${VOXTRAL_MODEL}
VOXTRAL_TIMEOUT_SEC=${VOXTRAL_TIMEOUT_SEC}
MAX_RETRY_COUNT=${MAX_RETRY_COUNT}

# ─── OVH Object Storage ───
OVH_ACCESS_KEY=${OVH_ACCESS_KEY}
OVH_SECRET_KEY=${OVH_SECRET_KEY}
OVH_BUCKET_NAME=${OVH_BUCKET_NAME}
OVH_ENDPOINT_URL=${OVH_ENDPOINT_URL}
OVH_REGION=${OVH_REGION}

# ─── Vexa ───
VEXA_API_KEY=${VEXA_API_KEY}
VEXA_WEBHOOK_SECRET=${VEXA_WEBHOOK_SECRET}

# ─── Frontend ───
VITE_KEYCLOAK_URL=${VITE_KEYCLOAK_URL}
VITE_KEYCLOAK_REALM=${VITE_KEYCLOAK_REALM}
VITE_KEYCLOAK_CLIENT_ID=${VITE_KEYCLOAK_CLIENT_ID}
EOF

# Sécurise le fichier — lisible uniquement par root
chmod 600 "$ENV_FILE"
chown root:root "$ENV_FILE"

echo "✓ Fichier $ENV_FILE créé avec permissions 600"
echo "✓ Configuration terminée"