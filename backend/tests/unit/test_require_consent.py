import pytest
from fastapi import HTTPException
from app.api.v1.auth import require_consent, consents_store


@pytest.fixture(autouse=True)
def clean_consents_store():
    """Vide le store avant et après chaque test, pour ne pas polluer les autres tests"""
    consents_store.clear()
    yield
    consents_store.clear()


def test_require_consent_bloque_sans_consentement():
    """Aucun consentement enregistré -> lève une 403"""
    current_user = {"id": "user-sans-consentement"}

    with pytest.raises(HTTPException) as exc_info:
        require_consent(current_user=current_user)

    assert exc_info.value.status_code == 403
    assert "Consentement RGPD requis" in exc_info.value.detail


def test_require_consent_bloque_si_consentement_inactif():
    """Consentement existant mais is_active=False -> lève une 403"""
    user_id = "user-consentement-revoque"
    consents_store[user_id] = {
        "id": "consent-1",
        "user_id": user_id,
        "is_active": False
    }
    current_user = {"id": user_id}

    with pytest.raises(HTTPException) as exc_info:
        require_consent(current_user=current_user)

    assert exc_info.value.status_code == 403


def test_require_consent_autorise_si_consentement_actif():
    """Consentement existant et actif -> retourne le consentement, pas d'erreur"""
    user_id = "user-avec-consentement"
    consents_store[user_id] = {
        "id": "consent-2",
        "user_id": user_id,
        "is_active": True
    }
    current_user = {"id": user_id}

    result = require_consent(current_user=current_user)

    assert result["is_active"] is True
    assert result["user_id"] == user_id