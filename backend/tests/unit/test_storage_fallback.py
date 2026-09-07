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
  4. OVH disponible → aucun fichier local ne doit être créé
  5. OVH indisponible ET fallback local KO → échec explicite, jamais silencieux

Concepts utilisés :
  - pytest.fixture    : prépare l'environnement de test (dossier temporaire)
  - unittest.mock     : simule OVH sans faire de vrais appels réseau
  - AsyncMock         : mock pour les fonctions async (await)
  - monkeypatch       : modifie une variable d'environnement pour le test,
                        annulé automatiquement à la fin de chaque test
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


def mock_ovh(monkeypatch, *, health_status="ok", health_error=None,
             upload_return=None, upload_exception=None):
    """
    Helper factorisant le mock de check_ovh_health + upload_audio_file.

    Remplace les blocs `with patch(...)` dupliqués dans chaque test :
    un seul appel paramétré configure le comportement OVH attendu pour
    le scénario testé. monkeypatch annule automatiquement ces mocks
    à la fin de chaque test, comme pour les autres fixtures.
    """
    monkeypatch.setattr(
        storage_service, "check_ovh_health",
        AsyncMock(return_value={"status": health_status, "error": health_error}),
    )
    if upload_exception is not None:
        monkeypatch.setattr(
            storage_service, "upload_audio_file",
            AsyncMock(side_effect=upload_exception),
        )
    else:
        monkeypatch.setattr(
            storage_service, "upload_audio_file",
            AsyncMock(return_value=upload_return),
        )


# ─── Cas 1 — OVH disponible ───────────────────────────────────────────────────
@pytest.mark.asyncio
async def test_upload_vers_ovh_quand_disponible(monkeypatch):
    """
    Cas nominal : OVH répond correctement.
    Le fichier doit être uploadé sur OVH, pas en local.
    Le résultat doit indiquer storage="ovh" et fallback=False.
    """
    mock_ovh(monkeypatch, health_status="ok", upload_return=OBJECT_KEY)

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
    mock_ovh(monkeypatch, health_status="unavailable", health_error="Connection refused")

    result = await upload_audio_file_with_fallback(
        AUDIO_CONTENT, OBJECT_KEY, CONTENT_TYPE
    )

    assert result["storage"]  == "local"
    assert result["fallback"] is True
    assert os.path.exists(result["storage_key"])
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
    mock_ovh(monkeypatch, health_status="ok", upload_exception=Exception("S3 upload timeout"))

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
    mock_ovh(monkeypatch, health_status="ok", upload_return=OBJECT_KEY)

    await upload_audio_file_with_fallback(AUDIO_CONTENT, OBJECT_KEY, CONTENT_TYPE)

    assert list(tmp_path.iterdir()) == []


# ─── Cas 5 — OVH indisponible ET fallback local KO ────────────────────────────
@pytest.mark.asyncio
async def test_echoue_explicitement_si_ovh_et_fallback_local_ko(tmp_path, monkeypatch):
    """
    Pire cas de résilience : OVH est indisponible ET l'écriture locale
    échoue aussi (disque plein, permissions refusées).
    La fonction ne doit jamais échouer en silence ni renvoyer un résultat
    trompeur (ex. fallback=True sans fichier réellement écrit) : elle doit
    laisser remonter une exception explicite à l'appelant.

    NOTE : adapte la cible du patch ci-dessous à l'implémentation réelle
    de l'écriture locale (ex. `storage_service.open`, ou
    `pathlib.Path.write_bytes` si le code utilise l'API pathlib).
    """
    monkeypatch.setattr(storage_service, "LOCAL_FALLBACK_DIR", str(tmp_path))
    mock_ovh(monkeypatch, health_status="unavailable", health_error="Connection refused")

    def raise_disk_full(*args, **kwargs):
        raise OSError("No space left on device")

    monkeypatch.setattr(storage_service, "open", raise_disk_full, raising=False)

    with pytest.raises(Exception):
        await upload_audio_file_with_fallback(AUDIO_CONTENT, OBJECT_KEY, CONTENT_TYPE)