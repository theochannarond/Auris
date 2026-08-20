#!/bin/bash
# Vérifie qu'aucun secret n'apparaît dans le repository GitHub
# À exécuter en local avant chaque push important
# Usage : bash infra/scripts/check-secrets-in-repo.sh

set -e

echo "=== Audit sécurité — repository GitHub ==="

SECRETS_FOUND=0

# Patterns de secrets à ne jamais commiter
PATTERNS=(
    "MISTRAL_API_KEY=\"[A-Za-z0-9]"
    "OVH_ACCESS_KEY=\"[A-Za-z0-9]"
    "OVH_SECRET_KEY=\"[A-Za-z0-9]"
    "POSTGRES_PASSWORD=\"[A-Za-z0-9]"
    "KEYCLOAK_CLIENT_SECRET=\"[A-Za-z0-9]"
    "KEYCLOAK_ADMIN_PASSWORD=\"[A-Za-z0-9]"
    "VEXA_API_KEY=\"[A-Za-z0-9]"
    "VEXA_WEBHOOK_SECRET=\"[A-Za-z0-9]"
)

# Fichiers à exclure de la vérification
EXCLUDE_PATTERNS=(
    "*.example"
    ".env.example"
    "*.md"
    "check-secrets-in-repo.sh"
)

echo "→ Scan des fichiers trackés par Git..."

for pattern in "${PATTERNS[@]}"; do
    # Cherche dans tous les fichiers trackés
    result=$(git grep -l -E "$pattern" 2>/dev/null || true)
    if [ -n "$result" ]; then
        echo "  ✗ SECRET TROUVÉ : pattern '$pattern' dans :"
        echo "$result" | sed 's/^/    - /'
        SECRETS_FOUND=1
    fi
done

echo ""
echo "→ Vérification des fichiers .env..."

# Vérifie que les .env ne sont pas trackés
ENV_FILES=$(git ls-files "**/.env" ".env" 2>/dev/null || true)
if [ -n "$ENV_FILES" ]; then
    echo "  ✗ Fichiers .env trackés par Git :"
    echo "$ENV_FILES" | sed 's/^/    - /'
    SECRETS_FOUND=1
fi

echo ""
if [ $SECRETS_FOUND -eq 0 ]; then
    echo "✓ Aucun secret détecté dans le repository"
    exit 0
else
    echo "✗ Des secrets ont été trouvés — retirez-les avant de pusher"
    exit 1
fi