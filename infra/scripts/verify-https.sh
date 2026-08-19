#!/usr/bin/env bash
# SCRUM-250 — Vérifie que HTTPS fonctionne correctement sur les 3 services
# proxifiés par nginx. À lancer depuis n'importe quelle machine une fois le
# serveur OVH en place (pas besoin d'être exécuté sur le serveur lui-même).
#
# Usage : ./verify-https.sh auris.example.com

set -euo pipefail

DOMAIN="${1:?Usage: $0 <domaine>}"

check() {
    local description="$1"
    local url="$2"
    local expected_status="$3"

    status=$(curl -s -o /dev/null -w "%{http_code}" --max-time 10 "$url" || echo "000")

    if [ "$status" = "$expected_status" ]; then
        echo "OK   ($status) $description"
    else
        echo "FAIL (attendu $expected_status, reçu $status) $description"
    fi
}

echo "Vérification HTTPS pour $DOMAIN"
echo "--------------------------------"

# Frontend — la page d'accueil doit répondre normalement
check "Frontend (/)" "https://$DOMAIN/" 200

# Backend — un endpoint protégé sans token renvoie 403 (comportement par
# défaut de HTTPBearer en FastAPI quand l'en-tête Authorization est absent —
# pas 401, qu'on aurait pu attendre). Peu importe le code exact ici : ça
# prouve surtout que nginx a bien atteint FastAPI, pas juste qu'il n'y a
# personne (ce qui donnerait 502/504, ou le HTML du frontend si mal routé).
check "Backend (/api/v1/meetings)" "https://$DOMAIN/api/v1/meetings" 403

# Keycloak — endpoint public standard de découverte OIDC, sans authentification
check "Keycloak (/auth/realms/auris/.well-known/openid-configuration)" \
    "https://$DOMAIN/auth/realms/auris/.well-known/openid-configuration" 200

echo ""
echo "Certificat SSL :"
echo | openssl s_client -connect "$DOMAIN:443" -servername "$DOMAIN" 2>/dev/null \
    | openssl x509 -noout -dates -subject
