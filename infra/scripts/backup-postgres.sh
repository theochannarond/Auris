#!/bin/bash
# Script de sauvegarde PostgreSQL quotidienne
# Dump la base auris et l'uploade sur OVH Object Storage
# Usage : bash backup-postgres.sh
# Appelé automatiquement par le cron job (SCRUM-253)

set -e

# ─── Variables ───
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
BACKUP_FILE="auris_backup_${TIMESTAMP}.sql.gz"
BACKUP_DIR="/tmp/auris_backups"
S3_BUCKET="${OVH_BACKUP_BUCKET:-auris-backups}"
S3_PREFIX="postgresql"
LOG_FILE="/var/log/auris/backup.log"

# ─── Fonctions ───
log() {
    echo "[$(date +"%Y-%m-%dT%H:%M:%S")] $1" | tee -a "$LOG_FILE"
}

# ─── Préparation ───
mkdir -p "$BACKUP_DIR"
mkdir -p "$(dirname "$LOG_FILE")"

log "INFO — Démarrage sauvegarde PostgreSQL"

# ─── Dump PostgreSQL ───
log "INFO — Dump de la base auris..."
PGPASSWORD="$POSTGRES_PASSWORD" pg_dump \
    -h "${POSTGRES_HOST:-db}" \
    -U "${POSTGRES_USER:-auris}" \
    -d "${POSTGRES_DB:-auris}" \
    --no-owner \
    --no-acl \
    | gzip > "${BACKUP_DIR}/${BACKUP_FILE}"

BACKUP_SIZE=$(du -sh "${BACKUP_DIR}/${BACKUP_FILE}" | cut -f1)
log "INFO — Dump terminé — taille : ${BACKUP_SIZE}"

# ─── Upload OVH Object Storage ───
log "INFO — Upload vers OVH Object Storage..."
aws s3 cp \
    "${BACKUP_DIR}/${BACKUP_FILE}" \
    "s3://${S3_BUCKET}/${S3_PREFIX}/${BACKUP_FILE}" \
    --endpoint-url "${OVH_ENDPOINT_URL}" \
    --region "${OVH_REGION:-gra}"

log "INFO — Upload réussi : s3://${S3_BUCKET}/${S3_PREFIX}/${BACKUP_FILE}"

# ─── Nettoyage local ───
rm -f "${BACKUP_DIR}/${BACKUP_FILE}"
log "INFO — Fichier local supprimé"

log "INFO — Sauvegarde terminée avec succès"