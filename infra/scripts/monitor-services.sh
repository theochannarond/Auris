#!/bin/bash
# Surveillance des conteneurs Docker Auris (SCRUM-176)
# Contrôle l'état de chaque service et journalise toute indisponibilité.
# Usage : bash monitor-services.sh
# Appelé automatiquement toutes les 5 minutes par /etc/cron.d/auris-monitoring
#
# Code de retour : 0 si tout va bien, 1 si au moins un service est en panne.
# C'est ce qui permet au test de simulation de panne de se prononcer.

# Pas de "set -e" ici, contrairement aux autres scripts du dossier : un service
# en panne fait forcément échouer une commande, or c'est précisément le cas
# qu'on veut traiter. Le script doit continuer et contrôler les suivants.
set -uo pipefail

# ─── Configuration ───
# Destinataire et relais SMTP des alertes. Ce fichier contient un mot de passe
# et n'est donc pas versionné : voir .env.monitoring.example à la racine du
# dépôt. "set -a" exporte les variables lues, ce dont msmtp a besoin plus bas
# pour récupérer le mot de passe par l'environnement plutôt qu'en argument.
MONITORING_ENV_FILE="${MONITORING_ENV_FILE:-/opt/auris/.env.monitoring}"

if [ -f "$MONITORING_ENV_FILE" ]; then
    set -a
    # shellcheck source=/dev/null
    . "$MONITORING_ENV_FILE"
    set +a
fi

# ─── Variables ───
# Liste des conteneurs surveillés, surchargeable par MONITORING_SERVICES (noms
# séparés par des espaces). Sert au test de simulation de panne, qui vise un
# conteneur jetable : éprouver la chaîne d'alerte ne doit pas exiger de
# couper un service réel.
if [ -n "${MONITORING_SERVICES:-}" ]; then
    read -r -a SERVICES <<< "$MONITORING_SERVICES"
else
    SERVICES=(auris_db auris_backend auris_frontend auris_keycloak auris_nginx)
fi

LOG_FILE="${MONITORING_LOG_FILE:-/var/log/auris/monitoring.log}"
STATE_DIR="${MONITORING_STATE_DIR:-/var/lib/auris/monitoring}"

# Valeurs par défaut appliquées après la lecture du fichier de configuration,
# pour que celui-ci puisse les remplacer.
ALERT_EMAIL_TO="${ALERT_EMAIL_TO:-}"
ALERT_EMAIL_FROM="${ALERT_EMAIL_FROM:-auris-monitoring@$(hostname -f 2>/dev/null || hostname)}"
SMTP_HOST="${SMTP_HOST:-}"
SMTP_PORT="${SMTP_PORT:-587}"
SMTP_USER="${SMTP_USER:-}"
SMTP_PASSWORD="${SMTP_PASSWORD:-}"

# Une panne qui dure ne doit pas produire une alerte toutes les 5 minutes.
# La première part immédiatement, les suivantes seulement après ce délai.
ALERT_COOLDOWN_MIN="${ALERT_COOLDOWN_MIN:-60}"

# Redémarrage automatique des services en panne. Docker relance déjà seul un
# conteneur qui s'arrête (restart: always dans docker-compose.prod.yml), mais
# il ne fait rien d'un conteneur qui tourne sans plus répondre : c'est ce trou
# que la surveillance comble.
AUTO_RESTART="${AUTO_RESTART:-true}"

# Délai avant de retenter un redémarrage. Garde-fou contre l'acharnement : un
# service qui retombe aussitôt a un problème que le redémarrage ne résout pas,
# et le relancer toutes les 5 minutes n'ajouterait que du bruit et des coupures.
RESTART_COOLDOWN_MIN="${RESTART_COOLDOWN_MIN:-15}"

# ─── Fonctions ───
log() {
    echo "[$(date +"%Y-%m-%dT%H:%M:%S")] $1" | tee -a "$LOG_FILE"
}

# Renvoie l'état d'un conteneur en un seul mot :
#   healthy | unhealthy | starting  — conteneur doté d'une sonde
#   running | stopped               — conteneur sans sonde déclarée
#   absent                          — conteneur inexistant (jamais lancé,
#                                     supprimé, ou renommé)
container_state() {
    local name="$1" state

    # Sur un conteneur inconnu, "docker inspect" écrit une ligne vide sur la
    # sortie standard avant d'échouer : se fier au seul code de retour
    # donnerait un état "\nabsent". On nettoie donc, et on traite toute
    # réponse vide comme un conteneur absent.
    state=$(docker inspect --format \
        '{{- if .State.Health -}}{{- .State.Health.Status -}}{{- else if .State.Running -}}running{{- else -}}stopped{{- end -}}' \
        "$name" 2>/dev/null | tr -d '[:space:]')

    if [ -z "$state" ]; then
        echo "absent"
    else
        echo "$state"
    fi
}

# Détail de la panne, destiné au corps de l'alerte : la sortie des dernières
# exécutions de la sonde si le conteneur en a une, complétée par la fin de son
# journal. Sans ce contexte l'alerte dirait seulement "c'est cassé".
failure_details() {
    local name="$1" state="$2"
    local probe logs

    # Sans conteneur, ni sonde ni journal à consulter : inutile d'interroger
    # Docker pour ne récupérer que son message d'erreur de connexion.
    if [ "$state" = "absent" ]; then
        printf "Aucun conteneur nommé %s sur ce serveur : il n'a jamais été créé, il a été supprimé, ou la pile tourne sous d'autres noms.\n" "$name"
        return
    fi

    probe=$(docker inspect --format \
        '{{- if .State.Health -}}{{- range .State.Health.Log -}}{{- .Output -}}{{- end -}}{{- end -}}' \
        "$name" 2>/dev/null | tail -n 3)

    logs=$(docker logs --tail 10 "$name" 2>&1 | tail -n 10)

    if [ -n "$probe" ]; then
        printf 'Sortie de la sonde :\n%s\n\nDernières lignes du journal :\n%s\n' "$probe" "$logs"
    else
        printf 'Aucune sonde déclarée pour ce conteneur.\n\nDernières lignes du journal :\n%s\n' "$logs"
    fi
}

# Décide s'il faut émettre une alerte pour ce service : oui à la première
# détection, puis seulement une fois le délai de silence écoulé.
should_alert() {
    local marker="$1"

    [ -f "$marker" ] || return 0

    local marker_age_min
    marker_age_min=$(( ( $(date +%s) - $(stat -c %Y "$marker") ) / 60 ))
    [ "$marker_age_min" -ge "$ALERT_COOLDOWN_MIN" ]
}

# Les sujets contiennent des accents. Les transmettre bruts produirait un
# en-tête Subject non conforme, que certains serveurs réécrivent en charabia :
# on les encode selon la RFC 2047.
encode_subject() {
    printf '=?UTF-8?B?%s?=' "$(printf '%s' "$1" | base64 -w 0)"
}

# Point d'entrée unique de l'émission des alertes : tout part dans le journal,
# puis par email si la configuration est en place.
#
# Le VPS n'héberge pas de serveur mail et OVH bloque souvent le port 25 en
# sortie : on passe par un relais authentifié en 587, via msmtp. Le mot de
# passe transite par l'environnement (--passwordeval) et non par la ligne de
# commande, qui serait lisible de tous dans la sortie de "ps".
send_alert() {
    local subject="$1"
    local body="$2"

    log "ALERTE — $subject"
    printf '%s\n' "$body" >> "$LOG_FILE"

    # Absence de configuration : on le signale une fois par alerte plutôt que
    # d'échouer, pour que la surveillance reste utilisable via le seul journal.
    if [ -z "$ALERT_EMAIL_TO" ] || [ -z "$SMTP_HOST" ] || [ -z "$SMTP_USER" ]; then
        log "AVERTISSEMENT — alerte non envoyée par email : ${MONITORING_ENV_FILE} absent ou incomplet"
        return
    fi

    if ! command -v msmtp > /dev/null 2>&1; then
        log "AVERTISSEMENT — alerte non envoyée par email : msmtp n'est pas installé (voir setup-mail-alerts.sh)"
        return
    fi

    if printf 'From: %s\nTo: %s\nSubject: %s\nDate: %s\nContent-Type: text/plain; charset=UTF-8\nContent-Transfer-Encoding: 8bit\n\n%s\n' \
            "$ALERT_EMAIL_FROM" \
            "$ALERT_EMAIL_TO" \
            "$(encode_subject "$subject")" \
            "$(date -R)" \
            "$body" \
        | msmtp \
            --host="$SMTP_HOST" \
            --port="$SMTP_PORT" \
            --auth=on \
            --user="$SMTP_USER" \
            --passwordeval='printenv SMTP_PASSWORD' \
            --tls=on \
            --tls-starttls=on \
            --from="$ALERT_EMAIL_FROM" \
            --read-recipients \
            >> "$LOG_FILE" 2>&1
    then
        log "INFO — Alerte envoyée à ${ALERT_EMAIL_TO}"
    else
        log "ERREUR — Échec de l'envoi de l'alerte email, détail msmtp ci-dessus"
    fi
}

# Tente de relancer un service en panne et décrit ce qui a été fait, en une
# phrase destinée au corps de l'alerte.
#
# Les traces vont volontairement sur la sortie d'erreur : l'appelant capture la
# sortie standard de cette fonction, et une ligne de journal s'y retrouverait
# collée au milieu du message envoyé par email.
attempt_restart() {
    local service="$1" state="$2"
    local marker="${STATE_DIR}/${service}.restart"

    if [ "$AUTO_RESTART" != "true" ]; then
        echo "Redémarrage automatique désactivé (AUTO_RESTART=${AUTO_RESTART})."
        return
    fi

    if [ "$state" = "absent" ]; then
        echo "Aucun conteneur à redémarrer : il n'existe pas sur ce serveur."
        return
    fi

    if [ -f "$marker" ]; then
        local restart_age_min
        restart_age_min=$(( ( $(date +%s) - $(stat -c %Y "$marker") ) / 60 ))
        if [ "$restart_age_min" -lt "$RESTART_COOLDOWN_MIN" ]; then
            echo "Redémarrage déjà tenté il y a ${restart_age_min} min et le service est retombé : nouvelle tentative différée, une intervention manuelle est probablement nécessaire."
            return
        fi
    fi

    date +%s > "$marker"

    if docker restart "$service" > /dev/null 2>&1; then
        log "INFO — ${service} redémarré automatiquement" >&2
        echo "Redémarrage automatique déclenché à $(date --iso-8601=seconds). Le prochain contrôle, dans 5 minutes, dira s'il a suffi."
    else
        log "ERREUR — échec du redémarrage automatique de ${service}" >&2
        echo "Redémarrage automatique tenté, mais la commande docker restart a échoué."
    fi
}

notify_failure() {
    local service="$1"
    local state="$2"
    local restart_outcome="$3"
    local marker="${STATE_DIR}/${service}.down"

    if should_alert "$marker"; then
        send_alert \
            "Auris — service indisponible : ${service} (${state})" \
            "$(printf 'Service   : %s\nÉtat      : %s\nHorodatage: %s\nServeur   : %s\n\nAction    : %s\n\n%s' \
                "$service" "$state" "$(date --iso-8601=seconds)" "$(hostname)" \
                "$restart_outcome" \
                "$(failure_details "$service" "$state")")"
        # Le marqueur est réécrit à chaque alerte émise : sa date de
        # modification sert de point de départ au délai de silence.
        date +%s > "$marker"
    else
        log "INFO — $service toujours en panne, alerte tue (délai de silence de ${ALERT_COOLDOWN_MIN} min)"
    fi
}

notify_recovery() {
    local service="$1"

    send_alert \
        "Auris — service rétabli : ${service}" \
        "$(printf 'Service   : %s\nHorodatage: %s\nServeur   : %s\n' \
            "$service" "$(date --iso-8601=seconds)" "$(hostname)")"
}

# ─── Préparation ───
mkdir -p "$(dirname "$LOG_FILE")" "$STATE_DIR"

# ─── Mode test ───
# "monitor-services.sh --test-alert" émet une alerte factice par le canal
# réel. C'est la façon de valider la configuration SMTP sans avoir à mettre
# un service en panne, et ça exerce exactement le code utilisé en production.
if [ "${1:-}" = "--test-alert" ]; then
    send_alert \
        "Auris — test de la chaîne d'alerte" \
        "$(printf 'Message de test émis manuellement, aucun service n%sest en panne.\n\nHorodatage: %s\nServeur   : %s\n' \
            "'" "$(date --iso-8601=seconds)" "$(hostname)")"
    exit 0
fi

# ─── Contrôle des services ───
failed=0

for service in "${SERVICES[@]}"; do
    state=$(container_state "$service")
    marker="${STATE_DIR}/${service}.down"

    case "$state" in
        healthy|running)
            # Un marqueur présent signifie que ce service était en panne au
            # tour précédent : on signale le rétablissement et on l'efface.
            if [ -f "$marker" ]; then
                log "INFO — ${service} de nouveau disponible (état : ${state})"
                notify_recovery "$service"
                # Le marqueur de redémarrage part avec : une panne ultérieure,
                # sans rapport avec celle-ci, doit pouvoir être traitée tout de
                # suite plutôt que d'attendre la fin d'un délai déjà obsolète.
                rm -f "$marker" "${STATE_DIR}/${service}.restart"
            fi
            ;;

        starting)
            # Le conteneur vient de démarrer et sa sonde n'a pas encore rendu
            # son verdict. Ce n'est pas une panne : on repasse dans 5 minutes.
            log "INFO — ${service} en cours de démarrage, contrôle reporté"
            ;;

        *)
            failed=$((failed + 1))
            log "ERREUR — ${service} indisponible (état : ${state})"
            # On tente la remise en service avant d'alerter, pour que le mail
            # dise à la fois ce qui ne va pas et ce qui a déjà été entrepris.
            restart_outcome=$(attempt_restart "$service" "$state")
            notify_failure "$service" "$state" "$restart_outcome"
            ;;
    esac
done

# ─── Bilan ───
# Une seule ligne par exécution quand tout va bien : à raison d'un contrôle
# toutes les 5 minutes, journaliser chaque service ferait grossir le fichier
# pour rien.
if [ "$failed" -eq 0 ]; then
    log "INFO — Contrôle terminé, les ${#SERVICES[@]} services sont disponibles"
    exit 0
fi

log "ERREUR — Contrôle terminé, ${failed} service(s) en panne sur ${#SERVICES[@]}"
exit 1
