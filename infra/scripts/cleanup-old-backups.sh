#!/bin/bash
# Supprime les backups PostgreSQL de plus de 30 jours sur OVH Object Storage
# Appelé automatiquement par le cron job après chaque backup
# Usage : bash cleanup-old-backups.sh

set -e

BUCKET="${OVH_BACKUP_BUCKET:-auris-backups}"
S3_PREFIX="postgresql"
RETENTION_DAYS=30
LOG_FILE="/var/log/auris/backup.log"

log() {
    echo "[$(date +"%Y-%m-%dT%H:%M:%S")] $1" | tee -a "$LOG_FILE"
}

log "INFO — Nettoyage des backups de plus de ${RETENTION_DAYS} jours..."

# Date limite en secondes depuis epoch
CUTOFF=$(date -d "${RETENTION_DAYS} days ago" +%s)

# Liste tous les fichiers du bucket
aws s3 ls \
    "s3://${BUCKET}/${S3_PREFIX}/" \
    --endpoint-url "${OVH_ENDPOINT_URL}" \
    --region "${OVH_REGION:-gra}" | while read -r line; do

    # Extrait la date et le nom du fichier
    FILE_DATE=$(echo "$line" | awk '{print $1}')
    FILE_NAME=$(echo "$line" | awk '{print $4}')

    if [ -z "$FILE_NAME" ]; then
        continue
    fi

    # Convertit la date en secondes
    FILE_TIMESTAMP=$(date -d "$FILE_DATE" +%s 2>/dev/null || echo 0)

    # Supprime si plus vieux que 30 jours
    if [ "$FILE_TIMESTAMP" -lt "$CUTOFF" ]; then
        aws s3 rm \
            "s3://${BUCKET}/${S3_PREFIX}/${FILE_NAME}" \
            --endpoint-url "${OVH_ENDPOINT_URL}" \
            --region "${OVH_REGION:-gra}"
        log "INFO — Supprimé : ${FILE_NAME}"
    fi
done

log "INFO — Nettoyage terminé"