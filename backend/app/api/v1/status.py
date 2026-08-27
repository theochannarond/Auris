"""
État des services de la pile Auris (SCRUM-176).

Alimente le tableau de bord d'administration. Les sondes passent par le réseau
Docker et non par le socket du démon : monter /var/run/docker.sock dans le
conteneur du backend reviendrait à lui donner les pleins pouvoirs sur l'hôte,
pour un besoin que de simples requêtes HTTP couvrent très bien.
"""

import asyncio
import time
from datetime import datetime, timezone

import httpx
from fastapi import APIRouter, Depends

from app.core.database import check_db_connection, settings
from app.core.security import get_current_user
from app.services.storage_service import check_ovh_health

router = APIRouter(prefix="/api/v1/status", tags=["status"])

# Délai au-delà duquel un service est déclaré injoignable. Les sondes tournent
# en parallèle : c'est donc aussi le temps d'affichage maximal de la page, qui
# doit rester consultable quand tout est en panne — c'est là qu'on en a besoin.
# Fixé à 5 s et non 3 s après mesure en production : la sonde du stockage OVH
# demande à elle seule 1,7 s, et une marge trop courte la ferait afficher en
# panne au moindre ralentissement du fournisseur.
PROBE_TIMEOUT_SEC = 5.0


def _result(name: str, label: str, status: str, started: float, error: str | None = None) -> dict:
    return {
        "name":       name,
        "label":      label,
        "status":     status,
        "latency_ms": round((time.perf_counter() - started) * 1000),
        "error":      error,
    }


async def _probe_http(name: str, label: str, url: str) -> dict:
    """Sonde HTTP générique : toute réponse hors erreur vaut disponibilité."""
    started = time.perf_counter()
    try:
        async with httpx.AsyncClient(timeout=PROBE_TIMEOUT_SEC) as client:
            response = await client.get(url)
    except Exception as exc:
        return _result(name, label, "down", started, str(exc))

    if response.status_code >= 400:
        return _result(name, label, "down", started, f"HTTP {response.status_code}")

    return _result(name, label, "up", started)


async def _probe_database() -> dict:
    started = time.perf_counter()
    # check_db_connection est synchrone : l'exécuter tel quel bloquerait la
    # boucle d'événements et figerait les autres sondes lancées en parallèle.
    ok = await asyncio.to_thread(check_db_connection)
    if ok:
        return _result("database", "Base PostgreSQL", "up", started)
    return _result("database", "Base PostgreSQL", "down", started, "Connexion impossible")


async def _probe_storage() -> dict:
    started = time.perf_counter()
    health = await check_ovh_health()
    if health["status"] == "ok":
        return _result("storage", "Stockage objet OVH", "up", started)
    return _result("storage", "Stockage objet OVH", "down", started, health.get("error"))


@router.get("/services")
async def services_status(_user: dict = Depends(get_current_user)) -> dict:
    """
    Renvoie l'état de chaque brique de la pile, sondée en direct.

    Route authentifiée : elle expose des noms d'hôte internes et les messages
    d'erreur bruts des dépendances, qui n'ont rien à faire en accès libre.
    """
    started = time.perf_counter()

    # Le backend se déclare disponible sans se sonder lui-même : s'il ne
    # l'était pas, cette réponse n'existerait pas.
    backend = _result("backend", "API FastAPI", "up", started)

    # nginx est sondé pour que le tableau soit complet, mais son résultat est
    # à lire avec réserve : le navigateur passe par nginx pour arriver ici,
    # donc s'il était vraiment tombé, la page ne se serait pas chargée.
    probes = await asyncio.gather(
        _probe_database(),
        _probe_storage(),
        _probe_http("keycloak", "Authentification Keycloak", f"{settings.KEYCLOAK_URL}/health/ready"),
        _probe_http("frontend", "Frontend React", settings.FRONTEND_HEALTH_URL),
        _probe_http("nginx",    "Proxy nginx",    settings.NGINX_HEALTH_URL),
    )

    services = [backend, *probes]

    return {
        "checked_at": datetime.now(timezone.utc).isoformat(),
        "overall":    "ok" if all(s["status"] == "up" for s in services) else "degraded",
        "services":   services,
    }
