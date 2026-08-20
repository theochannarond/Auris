#!/bin/bash
# Vérifie qu'aucun secret n'apparaît dans les logs Docker
# À exécuter sur le VPS après déploiement
# Usage : bash check-secrets-in-logs.sh

set -e

echo "=== Audit sécurité — logs Docker ==="

SECRETS_FOUND=0

# Liste des patterns à rechercher
PATTERNS=(
    "MISTRAL_API_KEY"
    "POSTGRES_PASSWORD"
    "KEYCLOAK_CLIENT_SECRET"
    "KEYCLOAK_ADMIN_PASSWORD"
    "OVH_ACCESS_KEY"
    "OVH_SECRET_KEY"
    "VEXA_API_KEY"
    "VEXA_WEBHOOK_SECRET"
)

CONTAINERS=(
    "auris_backend"
    "auris_frontend"
    "auris_keycloak"
    "auris_nginx"
    "auris_db"
)

for container in "${CONTAINERS[@]}"; do
    echo ""
    echo "→ Vérification de $container..."

    # Vérifie que le container existe
    if ! docker ps -a --format '{{.Names}}' | grep -q "^${container}$"; then
        echo "  ⚠ Container $container non trouvé — ignoré"
        continue
    fi

    for pattern in "${PATTERNS[@]}"; do
        if docker logs "$container" 2>&1 | grep -q "$pattern"; then
            echo "  ✗ SECRET TROUVÉ : $pattern dans $container"
            SECRETS_FOUND=1
        fi
    done
done

echo ""
if [ $SECRETS_FOUND -eq 0 ]; then
    echo "✓ Aucun secret détecté dans les logs Docker"
    exit 0
else
    echo "✗ Des secrets ont été trouvés dans les logs — corrigez avant de continuer"
    exit 1
fi