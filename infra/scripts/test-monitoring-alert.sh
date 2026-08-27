#!/bin/bash
# Test de bout en bout de la chaîne de surveillance (SCRUM-176)
# Usage : sudo bash test-monitoring-alert.sh
#
# Simule la panne d'un service, puis vérifie que la surveillance la détecte,
# émet une alerte contenant le nom du service, l'horodatage et le détail de
# l'erreur, et redémarre le conteneur.
#
# Le test travaille sur un conteneur jetable (auris_test_dummy) et non sur un
# service réel : éprouver la chaîne d'alerte ne doit pas couper la production.
# Il écrit par ailleurs dans ses propres fichiers temporaires, pour ne pas
# polluer le journal de surveillance ni y laisser des marqueurs qui feraient
# taire une véritable alerte ensuite.

set -uo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
MONITOR="${SCRIPT_DIR}/monitor-services.sh"

DUMMY="auris_test_dummy"
WORK_DIR="$(mktemp -d)"
TEST_LOG="${WORK_DIR}/monitoring.log"
TEST_STATE="${WORK_DIR}/state"

passed=0
failed=0

# ─── Fonctions ───
ok()   { echo "  ✓ $1"; passed=$((passed + 1)); }
ko()   { echo "  ✗ $1"; failed=$((failed + 1)); }

assert_contains() {
    local haystack="$1" needle="$2" label="$3"
    if printf '%s' "$haystack" | grep -qF "$needle"; then
        ok "$label"
    else
        ko "$label — motif introuvable : ${needle}"
    fi
}

assert_matches() {
    local haystack="$1" pattern="$2" label="$3"
    if printf '%s' "$haystack" | grep -qE "$pattern"; then
        ok "$label"
    else
        ko "$label — motif introuvable : ${pattern}"
    fi
}

# Exécute la surveillance sur le seul conteneur jetable, dans son bac à sable.
# Renvoie le code de retour du script et laisse sa sortie dans $TEST_LOG.
run_monitor() {
    local auto_restart="$1"
    : > "$TEST_LOG"
    MONITORING_SERVICES="$DUMMY" \
    MONITORING_LOG_FILE="$TEST_LOG" \
    MONITORING_STATE_DIR="$TEST_STATE" \
    AUTO_RESTART="$auto_restart" \
    RESTART_COOLDOWN_MIN=0 \
        bash "$MONITOR" > /dev/null 2>&1
}

cleanup() {
    docker rm -f "$DUMMY" > /dev/null 2>&1
    rm -rf "$WORK_DIR"
}
trap cleanup EXIT

# ─── Préparation ───
echo "=== Test de la chaîne d'alerte Auris ==="
echo ""

if [ "$(id -u)" -ne 0 ]; then
    echo "✗ Ce script doit être lancé avec sudo : il pilote Docker"
    exit 1
fi

mkdir -p "$TEST_STATE"

# Un conteneur qui ne fait rien d'autre que rester en vie. Sans port publié :
# il ne peut entrer en conflit avec aucun service réel.
docker rm -f "$DUMMY" > /dev/null 2>&1
if ! docker run -d --name "$DUMMY" --restart no nginx:alpine > /dev/null 2>&1; then
    echo "✗ Impossible de créer le conteneur de test"
    exit 1
fi
echo "Conteneur de test ${DUMMY} créé."
echo ""

# ─── Étape 1 : service sain ───
echo "Étape 1 — service en fonctionnement"
run_monitor "false"
code=$?
log=$(cat "$TEST_LOG")

if [ "$code" -eq 0 ]; then
    ok "code de retour 0"
else
    ko "code de retour attendu 0, obtenu ${code}"
fi
assert_contains "$log" "les 1 services sont disponibles" "aucune panne signalée"
if printf '%s' "$log" | grep -q "ALERTE"; then
    ko "aucune alerte ne devait être émise"
else
    ok "aucune alerte émise"
fi
echo ""

# ─── Étape 2 : panne détectée et alerte émise ───
# AUTO_RESTART désactivé à dessein : on isole ici la détection et l'alerte du
# redémarrage, qui est éprouvé séparément à l'étape 3.
echo "Étape 2 — service arrêté manuellement, alerte attendue"
docker stop "$DUMMY" > /dev/null 2>&1
run_monitor "false"
code=$?
log=$(cat "$TEST_LOG")

if [ "$code" -eq 1 ]; then
    ok "code de retour 1"
else
    ko "code de retour attendu 1, obtenu ${code}"
fi

assert_contains "$log" "ALERTE"                       "une alerte a été émise"
assert_contains "$log" "$DUMMY"                       "l'alerte nomme le service"
assert_contains "$log" "stopped"                      "l'alerte donne l'état du service"
assert_matches  "$log" "[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}" \
                                                      "l'alerte porte un horodatage"
assert_contains "$log" "Dernières lignes du journal"  "l'alerte joint le détail de l'erreur"
assert_contains "$log" "Redémarrage automatique désactivé" \
                                                      "l'alerte indique l'action entreprise"

# L'envoi effectif dépend de la configuration SMTP : son absence n'invalide
# pas la détection, mais elle doit être signalée sans ambiguïté.
if printf '%s' "$log" | grep -q "Alerte envoyée à"; then
    ok "alerte transmise par email"
elif printf '%s' "$log" | grep -q "AVERTISSEMENT — alerte non envoyée"; then
    echo "  ⚠ email non configuré sur ce serveur — envoi non éprouvé"
else
    ko "l'envoi de l'email a échoué"
fi
echo ""

# ─── Étape 3 : redémarrage automatique ───
echo "Étape 3 — redémarrage automatique du service en panne"
rm -f "${TEST_STATE}/${DUMMY}".*
run_monitor "true"
log=$(cat "$TEST_LOG")

assert_contains "$log" "redémarré automatiquement" "le redémarrage a été déclenché"

state=$(docker inspect --format '{{.State.Running}}' "$DUMMY" 2>/dev/null)
if [ "$state" = "true" ]; then
    ok "le conteneur tourne de nouveau"
else
    ko "le conteneur devait être relancé, état obtenu : ${state}"
fi
echo ""

# ─── Étape 4 : rétablissement signalé ───
echo "Étape 4 — retour à la normale"
run_monitor "false"
code=$?
log=$(cat "$TEST_LOG")

if [ "$code" -eq 0 ]; then
    ok "code de retour 0"
else
    ko "code de retour attendu 0, obtenu ${code}"
fi
assert_contains "$log" "de nouveau disponible" "le rétablissement est signalé"
echo ""

# ─── Bilan ───
echo "=== Bilan : ${passed} réussite(s), ${failed} échec(s) ==="

if [ "$failed" -gt 0 ]; then
    echo ""
    echo "Journal complet de la dernière étape :"
    cat "$TEST_LOG"
    exit 1
fi

echo "La chaîne de surveillance est opérationnelle."
exit 0
