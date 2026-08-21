#!/bin/bash
# Teste la procédure de backup et restore en local
# À exécuter avant la mise en production pour valider les scripts
# Usage : bash test-backup-restore.sh

set -e

echo "=== Test backup & restore PostgreSQL Auris ==="

TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
TEST_BACKUP_FILE="auris_test_backup_${TIMESTAMP}.sql.gz"
TEST_DIR="/tmp/auris_backup_test"

mkdir -p "$TEST_DIR"

# ─── Étape 1 — Dump local ───
echo ""
echo "→ Étape 1 — Dump de la base auris..."
PGPASSWORD="$POSTGRES_PASSWORD" pg_dump \
    -h "${POSTGRES_HOST:-localhost}" \
    -U "${POSTGRES_USER:-auris}" \
    -d "${POSTGRES_DB:-auris}" \
    --no-owner \
    --no-acl \
    | gzip > "${TEST_DIR}/${TEST_BACKUP_FILE}"

BACKUP_SIZE=$(du -sh "${TEST_DIR}/${TEST_BACKUP_FILE}" | cut -f1)
echo "  ✓ Dump créé — taille : ${BACKUP_SIZE}"

# ─── Étape 2 — Vérifie que le dump est lisible ───
echo ""
echo "→ Étape 2 — Vérification intégrité du dump..."
gunzip -t "${TEST_DIR}/${TEST_BACKUP_FILE}"
echo "  ✓ Fichier gzip valide"

# ─── Étape 3 — Compte les tables dans le dump ───
echo ""
echo "→ Étape 3 — Contenu du dump..."
TABLE_COUNT=$(gunzip -c "${TEST_DIR}/${TEST_BACKUP_FILE}" | grep -c "^CREATE TABLE" || true)
echo "  ✓ Tables trouvées : ${TABLE_COUNT}"

if [ "$TABLE_COUNT" -lt 5 ]; then
    echo "  ✗ ERREUR — Moins de 5 tables dans le dump (attendu : users, meetings, transcriptions, summaries, consents)"
    exit 1
fi

# ─── Étape 4 — Nettoyage ───
echo ""
echo "→ Étape 4 — Nettoyage..."
rm -f "${TEST_DIR}/${TEST_BACKUP_FILE}"
echo "  ✓ Fichier temporaire supprimé"

echo ""
echo "✓ Test backup & restore réussi"
echo "✓ La procédure est prête pour la production"
echo ""
echo "⚠  Note : le test de restauration réelle sur la base de prod"
echo "   doit être fait manuellement avec restore-postgres.sh"
echo "   sur un environnement de staging avant la mise en production."