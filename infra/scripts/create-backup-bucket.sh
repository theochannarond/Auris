#!/bin/bash
# Crée le bucket OVH Object Storage dédié aux backups PostgreSQL
# À exécuter une seule fois lors de la mise en production
# Usage : bash create-backup-bucket.sh

set -e

echo "=== Création bucket OVH backups ==="

# Vérifie que les credentials sont disponibles
if [ -z "$OVH_ACCESS_KEY" ] || [ -z "$OVH_SECRET_KEY" ]; then
    echo "✗ OVH_ACCESS_KEY et OVH_SECRET_KEY requis"
    exit 1
fi

BUCKET="${OVH_BACKUP_BUCKET:-auris-backups}"

# Crée le bucket
aws s3 mb \
    "s3://${BUCKET}" \
    --endpoint-url "${OVH_ENDPOINT_URL}" \
    --region "${OVH_REGION:-gra}"

echo "✓ Bucket ${BUCKET} créé sur OVH Object Storage"
echo "✓ Région : ${OVH_REGION:-gra}"