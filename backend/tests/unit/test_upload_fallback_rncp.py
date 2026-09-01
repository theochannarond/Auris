import pytest
import os
from unittest.mock import AsyncMock, patch
from app.services import storage_service
from app.services.storage_service import upload_audio_file_with_fallback

"""
Tests unitaires — upload_audio_file_with_fallback
==================================================

Cette fonction est le cœur de la résilience d'Auris face aux pannes OVH.
Elle garantit qu'aucun fichier audio n'est jamais perdu, même si OVH
Object Storage est temporairement indisponible.

Logique métier testée :
  1. OVH disponible  → upload direct sur OVH (cas nominal)
  2. OVH indisponible → sauvegarde locale dans /tmp/auris_fallback (fallback)
  3. OVH disponible mais upload échoue → fallback activé (résilience)

Concepts utilisés :
  - pytest.fixture    : prépare l'environnement de test (dossier temporaire)
  - unittest.mock     : simule OVH sans faire de vrais appels réseau
  - AsyncMock         : mock pour les fonctions async (await)
  - patch             : remplace temporairement une fonction par un mock
  - monkeypatch       : modifie une variable d'environnement pour le test
"""

AUDIO_CONTENT = b"fake-audio-content-wav"
OBJECT_KEY    = "meetings/uuid-123/recording.wav"
CONTENT_TYPE  = "audio/wav"


@pytest.fixture(autouse=True)
def mock_settings(monkeypatch):
    """
    Injecte de fausses credentials OVH pour que is_storage_configured()
    retourne True — sans ça, check_ovh_health() retourne 'unavailable'
    immédiatement sans même tenter la connexion.
    """
    monkeypatch.setattr(storage_service.settings, "OVH_ACCESS_KEY", "real-key")
    monkeypatch.setattr(storage_service.settings, "OVH_SECRET_KEY", "real-secret")
    monkeypatch.setattr(storage_service.settings, "OVH_BUCKET_NAME", "auris-audio")
    monkeypatch.setattr(storage_service.settings, "OVH_ENDPOINT_URL", "https://s3.gra.io.cloud.ovh.net")
    monkeypatch.setattr(storage_service.settings, "OVH_REGION", "gra")


# ─── Cas 1 — OVH disponible ───────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_upload_vers_ovh_quand_disponible():
    """
    Cas nominal : OVH répond correctement.
    Le fichier doit être uploadé sur OVH, pas en local.
    Le résultat doit indiquer storage="ovh" et fallback=False.
    """
    with patch("app.services.storage_service.check_ovh_health",
               new=AsyncMock(return_value={"status": "ok", "error": None})):
        with patch("app.services.storage_service.upload_audio_file",
                   new=AsyncMock(return_value=OBJECT_KEY)):

            result = await upload_audio_file_with_fallback(
                AUDIO_CONTENT, OBJECT_KEY, CONTENT_TYPE
            )

    assert result["storage"]     == "ovh"
    assert result["fallback"]    is False
    assert result["storage_key"] == OBJECT_KEY


# ─── Cas 2 — OVH indisponible → fallback local ────────────────────────────────

@pytest.mark.asyncio
async def test_fallback_local_quand_ovh_indisponible(tmp_path, monkeypatch):
    """
    Cas de panne OVH : check_ovh_health retourne 'unavailable'.
    Le fichier doit être sauvegardé localement dans LOCAL_FALLBACK_DIR.
    Le résultat doit indiquer storage="local" et fallback=True.
    Le contenu du fichier local doit être identique à l'original.
    """
    monkeypatch.setattr(storage_service, "LOCAL_FALLBACK_DIR", str(tmp_path))

    with patch("app.services.storage_service.check_ovh_health",
               new=AsyncMock(return_value={"status": "unavailable", "error": "Connection refused"})):

        result = await upload_audio_file_with_fallback(
            AUDIO_CONTENT, OBJECT_KEY, CONTENT_TYPE
        )

    assert result["storage"]  == "local"
    assert result["fallback"] is True
    assert os.path.exists(result["storage_key"])

    # Vérifie que le contenu sauvegardé est intact
    with open(result["storage_key"], "rb") as f:
        assert f.read() == AUDIO_CONTENT


# ─── Cas 3 — OVH disponible mais upload échoue ────────────────────────────────

@pytest.mark.asyncio
async def test_fallback_local_si_upload_ovh_echoue(tmp_path, monkeypatch):
    """
    Cas de défaillance partielle : OVH répond au health check
    mais l'upload lui-même échoue (timeout, erreur S3...).
    Le fallback local doit être activé automatiquement.
    Aucune exception ne doit remonter à l'appelant.
    """
    monkeypatch.setattr(storage_service, "LOCAL_FALLBACK_DIR", str(tmp_path))

    with patch("app.services.storage_service.check_ovh_health",
               new=AsyncMock(return_value={"status": "ok", "error": None})):
        with patch("app.services.storage_service.upload_audio_file",
                   new=AsyncMock(side_effect=Exception("S3 upload timeout"))):

            result = await upload_audio_file_with_fallback(
                AUDIO_CONTENT, OBJECT_KEY, CONTENT_TYPE
            )

    assert result["storage"]  == "local"
    assert result["fallback"] is True
    assert os.path.exists(result["storage_key"])


# ─── Cas 4 — OVH disponible, upload ne doit pas sauvegarder en local ──────────

@pytest.mark.asyncio
async def test_pas_de_fichier_local_quand_ovh_reussit(tmp_path, monkeypatch):
    """
    Vérifie qu'en cas de succès OVH, aucun fichier local n'est créé.
    Le dossier de fallback doit rester vide.
    """
    monkeypatch.setattr(storage_service, "LOCAL_FALLBACK_DIR", str(tmp_path))

    with patch("app.services.storage_service.check_ovh_health",
               new=AsyncMock(return_value={"status": "ok", "error": None})):
        with patch("app.services.storage_service.upload_audio_file",
                   new=AsyncMock(return_value=OBJECT_KEY)):

            await upload_audio_file_with_fallback(
                AUDIO_CONTENT, OBJECT_KEY, CONTENT_TYPE
            )

    # Aucun fichier ne doit avoir été créé localement
    assert list(tmp_path.iterdir()) == []