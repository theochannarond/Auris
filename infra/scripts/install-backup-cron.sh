#!/bin/bash
# Installe le cron job de backup sur le VPS OVH
# Usage : bash install-backup-cron.sh

set -e

echo "=== Installation cron job backup Auris ==="

# Copie le script de backup
mkdir -p /opt/auris/scripts
cp backup-postgres.sh /opt/auris/scripts/
chmod +x /opt/auris/scripts/backup-postgres.sh

# Crée le dossier de logs
mkdir -p /var/log/auris

# Installe le cron job
cp auris-backup.cron /etc/cron.d/auris-backup
chmod 644 /etc/cron.d/auris-backup

echo "✓ Cron job installé — sauvegarde quotidienne à 2h00"
echo "✓ Logs dans /var/log/auris/backup.log"