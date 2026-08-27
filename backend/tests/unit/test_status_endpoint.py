"""
Tests de l'état des services exposé au tableau de bord d'administration
(SCRUM-176).

Les sondes sont remplacées par des doublures : le test doit se prononcer sur
la logique d'agrégation, pas sur la disponibilité réelle de Keycloak ou d'OVH,
qui ne tournent pas dans l'intégration continue.
"""

import pytest
from fastapi.testclient import TestClient

from unittest.mock import patch

from app.api.v1 import status as status_module
from app.main import app

SERVICE_NAMES = {"backend", "database", "storage", "keycloak", "frontend", "nginx"}


class _FakeResponse:
    def __init__(self, status_code: int):
        self.status_code = status_code


class _FakeClient:
    """Doublure de httpx.AsyncClient : renvoie une réponse figée, ou lève."""

    def __init__(self, response=None, error=None):
        self._response = response
        self._error = error

    async def __aenter__(self):
        return self

    async def __aexit__(self, *_):
        return False

    async def get(self, _url):
        if self._error:
            raise self._error
        return self._response


def _fake_client_factory(response=None, error=None):
    def factory(*_args, **_kwargs):
        return _FakeClient(response, error)
    return factory


def _service(name: str, status: str) -> dict:
    return {
        "name":       name,
        "label":      name,
        "status":     status,
        "latency_ms": 1,
        "error":      None if status == "up" else "injoignable",
    }


def _async(value):
    """Emballe une valeur figée dans une coroutine, pour remplacer une sonde."""
    async def _coroutine(*_args, **_kwargs):
        return value
    return _coroutine


# ─── Sondes HTTP ───

@pytest.mark.asyncio
async def test_sonde_http_service_disponible():
    """Réponse 200 — le service est déclaré disponible, sans erreur"""
    with patch.object(status_module.httpx, "AsyncClient",
                      _fake_client_factory(_FakeResponse(200))):
        result = await status_module._probe_http("keycloak", "Keycloak", "http://x/health")

    assert result["status"] == "up"
    assert result["error"] is None
    assert result["latency_ms"] >= 0


@pytest.mark.asyncio
async def test_sonde_http_erreur_serveur():
    """Réponse 503 — le service répond mais va mal : c'est une panne"""
    with patch.object(status_module.httpx, "AsyncClient",
                      _fake_client_factory(_FakeResponse(503))):
        result = await status_module._probe_http("frontend", "Frontend", "http://x/")

    assert result["status"] == "down"
    assert result["error"] == "HTTP 503"


@pytest.mark.asyncio
async def test_sonde_http_service_injoignable():
    """Connexion impossible — la cause remonte dans le détail de l'alerte"""
    with patch.object(status_module.httpx, "AsyncClient",
                      _fake_client_factory(error=ConnectionError("connexion refusée"))):
        result = await status_module._probe_http("nginx", "Proxy", "http://x/nginx-health")

    assert result["status"] == "down"
    assert "connexion refusée" in result["error"]


# ─── Sonde base de données ───

@pytest.mark.asyncio
async def test_sonde_base_de_donnees_en_panne():
    with patch.object(status_module, "check_db_connection", lambda: False):
        result = await status_module._probe_database()

    assert result["status"] == "down"
    assert result["error"] is not None


@pytest.mark.asyncio
async def test_sonde_base_de_donnees_disponible():
    with patch.object(status_module, "check_db_connection", lambda: True):
        result = await status_module._probe_database()

    assert result["status"] == "up"


# ─── Endpoint ───

def test_endpoint_liste_tous_les_services(client):
    """Les six briques de la pile sont rapportées, backend compris"""
    async def sonde_ok(name, label, url):
        return _service(name, "up")

    with patch.object(status_module, "_probe_http", sonde_ok), \
         patch.object(status_module, "_probe_database", _async(_service("database", "up"))), \
         patch.object(status_module, "_probe_storage", _async(_service("storage", "up"))):
        response = client.get("/api/v1/status/services")

    assert response.status_code == 200
    body = response.json()

    assert {s["name"] for s in body["services"]} == SERVICE_NAMES
    assert body["overall"] == "ok"
    assert body["checked_at"]


def test_endpoint_signale_une_pile_degradee(client):
    """Un seul service en panne suffit à dégrader l'état global"""
    async def sonde_ok(name, label, url):
        return _service(name, "up")

    with patch.object(status_module, "_probe_http", sonde_ok), \
         patch.object(status_module, "_probe_database", _async(_service("database", "down"))), \
         patch.object(status_module, "_probe_storage", _async(_service("storage", "up"))):
        response = client.get("/api/v1/status/services")

    assert response.status_code == 200
    body = response.json()

    assert body["overall"] == "degraded"

    en_panne = [s for s in body["services"] if s["status"] == "down"]
    assert len(en_panne) == 1
    assert en_panne[0]["name"] == "database"
    # Le détail doit remonter jusqu'à l'écran : une pastille rouge sans cause
    # n'aide personne à diagnostiquer.
    assert en_panne[0]["error"]


def test_endpoint_backend_toujours_disponible(client):
    """Le backend se déclare disponible : s'il ne l'était pas, pas de réponse"""
    async def sonde_ko(name, label, url):
        return _service(name, "down")

    with patch.object(status_module, "_probe_http", sonde_ko), \
         patch.object(status_module, "_probe_database", _async(_service("database", "down"))), \
         patch.object(status_module, "_probe_storage", _async(_service("storage", "down"))):
        response = client.get("/api/v1/status/services")

    body = response.json()
    backend = next(s for s in body["services"] if s["name"] == "backend")

    assert backend["status"] == "up"
    assert body["overall"] == "degraded"


def test_endpoint_refuse_les_visiteurs_non_authentifies():
    """La route expose des noms d'hôte internes : elle ne doit pas être ouverte"""
    # TestClient monté sans la surcharge d'authentification du fixture "client".
    with TestClient(app) as anonyme:
        response = anonyme.get("/api/v1/status/services")

    assert response.status_code in (401, 403)
