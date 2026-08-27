#!/bin/bash
# Installe la surveillance des services Auris sur le VPS OVH (SCRUM-176)
# Usage : sudo bash install-monitoring-cron.sh

set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

echo "=== Installation de la surveillance Auris ==="

if [ "$(id -u)" -ne 0 ]; then
    echo "✗ Ce script doit être lancé avec sudo : il écrit dans /etc/cron.d"
    exit 1
fi

# ─── Dossiers de travail ───
# monitoring.log  : journal des contrôles
# state           : marqueurs de panne, qui portent le délai de silence entre
#                   deux alertes pour un même service
mkdir -p /var/log/auris
mkdir -p /var/lib/auris/monitoring

# ─── Script de surveillance ───
# Volontairement aucun "chmod +x" ici : le script vit dans le dépôt cloné et
# git suit les permissions. Le rendre exécutable le ferait apparaître comme
# modifié localement, et le "git pull" du déploiement refuserait de l'écraser.
# Le cron l'invoque de toute façon par "bash monitor-services.sh".

# ─── Cron job ───
# Le nom du fichier ne doit pas contenir de point : cron ignore
# silencieusement les fichiers de /etc/cron.d dont le nom ne lui plaît pas.
cp "${SCRIPT_DIR}/auris-monitoring.cron" /etc/cron.d/auris-monitoring
chmod 644 /etc/cron.d/auris-monitoring
chown root:root /etc/cron.d/auris-monitoring

# ─── Rotation du journal ───
# Sans ça le fichier grossit indéfiniment : un contrôle toutes les 5 minutes
# fait environ 300 lignes par jour, et le disque du VPS n'est pas extensible.
cat > /etc/logrotate.d/auris-monitoring <<'EOF'
/var/log/auris/monitoring.log /var/log/auris/monitoring-cron.log {
    weekly
    rotate 4
    compress
    missingok
    notifempty
    copytruncate
}
EOF
chmod 644 /etc/logrotate.d/auris-monitoring

echo "✓ Cron job installé — contrôle des services toutes les 5 minutes"
echo "✓ Journal dans /var/log/auris/monitoring.log"
echo "✓ Rotation hebdomadaire configurée"
echo ""
echo "Pour un contrôle immédiat sans attendre le cron :"
echo "  sudo bash ${SCRIPT_DIR}/monitor-services.sh"
