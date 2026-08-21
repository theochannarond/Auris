#!/bin/bash
# Script de restauration PostgreSQL depuis un backup OVH Object Storage
# Usage : bash restore-postgres.sh [nom_du_fichier_backup]
# Exemple : bash restore-postgres.sh auris_backup_20260820_020000.sql.gz
# Sans argument : restaure le backup le plus récent

set -e

BUCKET="${OVH_BACKUP_BUCKET:-auris-backups}"
S3_PREFIX="postgresql"
RESTORE_DIR="/tmp/auris_restore"
LOG_FILE="/var/log/auris/restore.log"

log() {
    echo "[$(date +"%Y-%m-%dT%H:%M:%S")] $1" | tee -a "$LOG_FILE"
}

mkdir -p "$RESTORE_DIR"
mkdir -p "$(dirname "$LOG_FILE")"

log "INFO — Démarrage restauration PostgreSQL"

# ─── Sélection du backup ───
if [ -n "$1" ]; then
    BACKUP_FILE="$1"
    log "INFO — Backup sélectionné manuellement : ${BACKUP_FILE}"
else
    # Récupère le backup le plus récent
    log "INFO — Recherche du backup le plus récent..."
    BACKUP_FILE=$(aws s3 ls \
        "s3://${BUCKET}/${S3_PREFIX}/" \
        --endpoint-url "${OVH_ENDPOINT_URL}" \
        --region "${OVH_REGION:-gra}" \
        | sort | tail -n 1 | awk '{print $4}')

    if [ -z "$BACKUP_FILE" ]; then
        log "ERROR — Aucun backup trouvé dans s3://${BUCKET}/${S3_PREFIX}/"
        exit 1
    fi
    log "INFO — Backup le plus récent : ${BACKUP_FILE}"
fi

# ─── Confirmation ───
echo ""
echo "⚠️  ATTENTION — Cette opération va écraser la base de données actuelle !"
echo "   Backup à restaurer : ${BACKUP_FILE}"
echo "   Base cible         : ${POSTGRES_DB:-auris}"
echo ""
read -p "Confirmer la restauration ? (oui/non) : " CONFIRM
if [ "$CONFIRM" != "oui" ]; then
    log "INFO — Restauration annulée par l'utilisateur"
    exit 0
fi

# ─── Téléchargement depuis OVH ───
log "INFO — Téléchargement depuis OVH Object Storage..."
aws s3 cp \
    "s3://${BUCKET}/${S3_PREFIX}/${BACKUP_FILE}" \
    "${RESTORE_DIR}/${BACKUP_FILE}" \
    --endpoint-url "${OVH_ENDPOINT_URL}" \
    --region "${OVH_REGION:-gra}"

log "INFO — Téléchargement terminé"

# ─── Restauration PostgreSQL ───
log "INFO — Restauration de la base ${POSTGRES_DB:-auris}..."

# Termine les connexions actives
PGPASSWORD="$POSTGRES_PASSWORD" psql \
    -h "${POSTGRES_HOST:-db}" \
    -U "${POSTGRES_USER:-auris}" \
    -d postgres \
    -c "SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname = '${POSTGRES_DB:-auris}' AND pid <> pg_backend_pid();"

# Restaure depuis le dump compressé
gunzip -c "${RESTORE_DIR}/${BACKUP_FILE}" | PGPASSWORD="$POSTGRES_PASSWORD" psql \
    -h "${POSTGRES_HOST:-db}" \
    -U "${POSTGRES_USER:-auris}" \
    -d "${POSTGRES_DB:-auris}"

log "INFO — Restauration terminée avec succès"

# ─── Nettoyage ───
rm -f "${RESTORE_DIR}/${BACKUP_FILE}"
log "INFO — Fichier temporaire supprimé"

echo ""
echo "✓ Base de données restaurée depuis ${BACKUP_FILE}"