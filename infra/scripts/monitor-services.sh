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

# ─── Variables ───
SERVICES=(auris_db auris_backend auris_frontend auris_keycloak auris_nginx)

LOG_FILE="${MONITORING_LOG_FILE:-/var/log/auris/monitoring.log}"
STATE_DIR="${MONITORING_STATE_DIR:-/var/lib/auris/monitoring}"

# Une panne qui dure ne doit pas produire une alerte toutes les 5 minutes.
# La première part immédiatement, les suivantes seulement après ce délai.
ALERT_COOLDOWN_MIN="${ALERT_COOLDOWN_MIN:-60}"

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

# Point d'entrée unique de l'émission des alertes. Le canal réel (email) est
# branché ici par le ticket suivant de SCRUM-176 ; pour l'instant tout part
# dans le journal, ce qui suffit à valider la détection.
send_alert() {
    local subject="$1"
    local body="$2"

    log "ALERTE — $subject"
    printf '%s\n' "$body" >> "$LOG_FILE"
}

notify_failure() {
    local service="$1"
    local state="$2"
    local marker="${STATE_DIR}/${service}.down"

    if should_alert "$marker"; then
        send_alert \
            "Auris — service indisponible : ${service} (${state})" \
            "$(printf 'Service   : %s\nÉtat      : %s\nHorodatage: %s\nServeur   : %s\n\n%s' \
                "$service" "$state" "$(date --iso-8601=seconds)" "$(hostname)" \
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
                rm -f "$marker"
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
            notify_failure "$service" "$state"
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
