#!/usr/bin/env bash
# SCRUM-249 — Renouvelle les certificats Let's Encrypt et recharge nginx
# UNIQUEMENT si un renouvellement a réellement eu lieu (--deploy-hook ne
# s'exécute pas si les certificats sont encore valides plus de 30 jours).
# Prévu pour être appelé automatiquement par cron (voir auris-ssl-renewal.cron).
#
# À exécuter sur le serveur OVH — nécessite que Certbot soit déjà installé
# (SCRUM-246) et un premier certificat déjà généré (SCRUM-248).

set -euo pipefail

# TODO(SCRUM-170) : ajuster ce chemin à l'emplacement réel du repo sur le
# serveur, une fois provisionné (même hypothèse que le job de déploiement
# CI — infra/SCRUM-158-cicd-pipeline).
COMPOSE_FILE="/opt/auris/infra/docker-compose.prod.yml"

sudo certbot renew \
  --webroot -w /var/www/certbot \
  --deploy-hook "docker compose -f ${COMPOSE_FILE} exec -T nginx nginx -s reload"
