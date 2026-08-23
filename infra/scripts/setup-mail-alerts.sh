#!/bin/bash
# Installe le canal d'alerte email de la surveillance Auris (SCRUM-176)
# Usage : sudo bash setup-mail-alerts.sh
#
# Le VPS n'héberge pas de serveur mail, et OVH bloque fréquemment le port 25
# en sortie. On installe donc msmtp, un simple client SMTP, qui relaie les
# alertes par un compte authentifié en 587.

set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
REPO_DIR="$(cd "${SCRIPT_DIR}/../.." && pwd)"

ENV_FILE="/opt/auris/.env.monitoring"
ENV_EXAMPLE="${REPO_DIR}/.env.monitoring.example"

echo "=== Installation des alertes email Auris ==="

if [ "$(id -u)" -ne 0 ]; then
    echo "✗ Ce script doit être lancé avec sudo"
    exit 1
fi

# ─── Client SMTP ───
if command -v msmtp > /dev/null 2>&1; then
    echo "✓ msmtp déjà installé ($(msmtp --version | head -n 1))"
else
    echo "→ Installation de msmtp..."
    apt-get update -qq
    apt-get install -y msmtp
    echo "✓ msmtp installé"
fi

# ─── Fichier de configuration ───
# On ne réécrit jamais un fichier existant : il contient le mot de passe
# d'application, et l'écraser demanderait de le ressaisir.
if [ -f "$ENV_FILE" ]; then
    echo "✓ ${ENV_FILE} existe déjà, laissé intact"
else
    if [ ! -f "$ENV_EXAMPLE" ]; then
        echo "✗ Modèle introuvable : ${ENV_EXAMPLE}"
        exit 1
    fi
    cp "$ENV_EXAMPLE" "$ENV_FILE"
    echo "✓ ${ENV_FILE} créé à partir du modèle"
fi

# Le fichier porte un mot de passe : lisible par root seul, dans tous les cas,
# y compris s'il préexistait avec des droits trop larges.
chown root:root "$ENV_FILE"
chmod 600 "$ENV_FILE"
echo "✓ Droits restreints à root (600)"

# ─── Suite ───
# Détecte si le modèle est resté tel quel, pour ne pas laisser croire que
# les alertes sont opérationnelles alors qu'elles partiraient dans le vide.
if grep -qE "alerte@exemple\.fr|mot-de-passe-de-la-boite" "$ENV_FILE"; then
    echo ""
    echo "⚠ La configuration contient encore les valeurs d'exemple."
    echo ""
    echo "  1. Créez la boîte d'envoi dans l'espace client OVH :"
    echo "       Web Cloud → Emails → aurishetic.fr → Comptes de messagerie"
    echo "     Une boîte dédiée, pas une adresse personnelle : le mot de passe"
    echo "     stocké sur ce serveur ne doit ouvrir qu'une messagerie vide."
    echo "  2. Renseignez le fichier :"
    echo "       sudo nano ${ENV_FILE}"
    echo "  3. Envoyez une alerte de test :"
    echo "       sudo bash ${SCRIPT_DIR}/monitor-services.sh --test-alert"
    exit 0
fi

echo ""
echo "→ Envoi d'une alerte de test..."
bash "${SCRIPT_DIR}/monitor-services.sh" --test-alert

echo ""
echo "✓ Terminé — vérifiez la réception, et le journal en cas d'échec :"
echo "    sudo tail -n 30 /var/log/auris/monitoring.log"
