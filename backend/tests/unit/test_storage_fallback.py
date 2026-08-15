import pytest
import os
from unittest.mock import AsyncMock, patch, MagicMock
from app.services import storage_service
from app.services.storage_service import (
    check_ovh_health,
    upload_audio_file_with_fallback,
    LOCAL_FALLBACK_DIR
)
from app.services.sync_service import sync_local_files_to_ovh

AUDIO = b"fake-audio-content"
OBJECT_KEY = "meetings/uuid-123/recording.wav"

@pytest.fixture(autouse=True)
def mock_settings(monkeypatch):
    monkeypatch.setattr(storage_service.settings, "OVH_ACCESS_KEY", "real-access-key")
    monkeypatch.setattr(storage_service.settings, "OVH_SECRET_KEY", "real-secret-key")
    monkeypatch.setattr(storage_service.settings, "OVH_BUCKET_NAME", "auris-audio")
    monkeypatch.setattr(storage_service.settings, "OVH_ENDPOINT_URL", "https://s3.gra.io.cloud.ovh.net")
    monkeypatch.setattr(storage_service.settings, "OVH_REGION", "gra")

# ─── Tests check_ovh_health ───

@pytest.mark.asyncio
async def test_health_check_credentials_manquants(monkeypatch):
    """Sans credentials OVH — retourne unavailable immédiatement"""
    monkeypatch.setattr(storage_service.settings, "OVH_ACCESS_KEY", "your-ovh-access-key")
    result = await check_ovh_health()
    assert result["status"] == "unavailable"
    assert result["error"] is not None

@pytest.mark.asyncio
async def test_health_check_ovh_accessible():
    """OVH accessible — retourne ok"""
    with patch("app.services.storage_service.check_ovh_health",
               new=AsyncMock(return_value={"status": "ok", "error": None})):
        from app.services.storage_service import check_ovh_health as mocked
        result = await mocked()
    assert result["status"] == "ok"
    assert result["error"] is None

@pytest.mark.asyncio
async def test_health_check_ovh_inaccessible():
    """OVH inaccessible — retourne unavailable avec l'erreur"""
    with patch("app.services.storage_service.check_ovh_health",
               new=AsyncMock(return_value={"status": "unavailable", "error": "Connection refused"})):
        from app.services.storage_service import check_ovh_health as mocked
        result = await mocked()
    assert result["status"] == "unavailable"
    assert result["error"] == "Connection refused"

# ─── Tests upload_audio_file_with_fallback ───

@pytest.mark.asyncio
async def test_upload_vers_ovh_si_disponible(tmp_path):
    """OVH disponible — upload direct sans fallback"""
    with patch("app.services.storage_service.check_ovh_health",
               new=AsyncMock(return_value={"status": "ok", "error": None})):
        with patch("app.services.storage_service.upload_audio_file",
                   new=AsyncMock(return_value=OBJECT_KEY)):
            result = await upload_audio_file_with_fallback(AUDIO, OBJECT_KEY, "audio/wav")

    assert result["storage"] == "ovh"
    assert result["fallback"] is False
    assert result["storage_key"] == OBJECT_KEY

@pytest.mark.asyncio
async def test_fallback_local_si_ovh_indisponible(tmp_path, monkeypatch):
    """OVH indisponible — sauvegarde locale activée"""
    monkeypatch.setattr(storage_service, "LOCAL_FALLBACK_DIR", str(tmp_path))

    with patch("app.services.storage_service.check_ovh_health",
               new=AsyncMock(return_value={"status": "unavailable", "error": "Timeout"})):
        result = await upload_audio_file_with_fallback(AUDIO, OBJECT_KEY, "audio/wav")

    assert result["storage"] == "local"
    assert result["fallback"] is True
    assert os.path.exists(result["storage_key"])

    with open(result["storage_key"], "rb") as f:
        assert f.read() == AUDIO

@pytest.mark.asyncio
async def test_fallback_local_si_upload_ovh_echoue(tmp_path, monkeypatch):
    """OVH disponible mais upload échoue — fallback local activé"""
    monkeypatch.setattr(storage_service, "LOCAL_FALLBACK_DIR", str(tmp_path))

    with patch("app.services.storage_service.check_ovh_health",
               new=AsyncMock(return_value={"status": "ok", "error": None})):
        with patch("app.services.storage_service.upload_audio_file",
                   new=AsyncMock(side_effect=Exception("S3 error"))):
            result = await upload_audio_file_with_fallback(AUDIO, OBJECT_KEY, "audio/wav")

    assert result["storage"] == "local"
    assert result["fallback"] is True

# ─── Tests sync_local_files_to_ovh ───

@pytest.mark.asyncio
async def test_sync_ignoree_si_ovh_indisponible():
    """OVH toujours indisponible — sync ignorée"""
    with patch("app.services.storage_service.check_ovh_health",
               new=AsyncMock(return_value={"status": "unavailable", "error": "Timeout"})):
        from app.services.sync_service import sync_local_files_to_ovh
        result = await sync_local_files_to_ovh()

    assert result["skipped"] == 1
    assert result["synced"] == 0

@pytest.mark.asyncio
async def test_sync_uploade_fichiers_locaux(tmp_path, monkeypatch):
    """OVH disponible — les fichiers locaux sont uploadés et supprimés"""
    monkeypatch.setattr(storage_service, "LOCAL_FALLBACK_DIR", str(tmp_path))

    from app.services import sync_service
    monkeypatch.setattr(sync_service, "LOCAL_FALLBACK_DIR", str(tmp_path))

    test_file = tmp_path / "meetings_uuid-123_recording.wav"
    test_file.write_bytes(AUDIO)

    with patch("app.services.sync_service.check_ovh_health",
               new=AsyncMock(return_value={"status": "ok", "error": None})):
        with patch("app.services.sync_service.upload_audio_file",
                   new=AsyncMock(return_value="ok")):
            from app.services.sync_service import sync_local_files_to_ovh
            result = await sync_local_files_to_ovh()

    assert result["synced"] == 1
    assert result["failed"] == 0
    assert not test_file.exists()