import pytest
from fastapi import HTTPException
from datetime import datetime
from app.api.v1.auth import require_consent
from app.models.consent import Consent


def test_require_consent_bloque_sans_consentement(db, test_user):
    """Aucun consentement en base pour cet utilisateur -> lève une 403"""
    # On simule un utilisateur connecté, sans jamais créer de Consent pour lui
    current_user = {"id": test_user.keycloak_id}

    # On s'attend à ce que ça lève une erreur HTTPException
    with pytest.raises(HTTPException) as exc_info:
        require_consent(db=db, current_user=current_user)

    # On vérifie que c'est bien une 403, avec le bon message
    assert exc_info.value.status_code == 403
    assert "Consentement RGPD requis" in exc_info.value.detail


def test_require_consent_bloque_si_consentement_inactif(db, test_user):
    """Consentement existant en base mais is_active=False -> lève une 403"""
    # On crée un vrai Consent en base, mais désactivé
    consent = Consent(
        user_id=test_user.id,
        given_at=datetime.utcnow(),
        ip_address="127.0.0.1",
        is_active=False
    )
    db.add(consent)
    db.commit()

    current_user = {"id": test_user.keycloak_id}

    # Même si un Consent existe, is_active=False doit quand même bloquer
    with pytest.raises(HTTPException) as exc_info:
        require_consent(db=db, current_user=current_user)

    assert exc_info.value.status_code == 403


def test_require_consent_autorise_si_consentement_actif(db, test_user):
    """Consentement existant en base et actif -> retourne le consentement, pas d'erreur"""
    # On crée un vrai Consent en base, actif cette fois
    consent = Consent(
        user_id=test_user.id,
        given_at=datetime.utcnow(),
        ip_address="127.0.0.1",
        is_active=True
    )
    db.add(consent)
    db.commit()

    current_user = {"id": test_user.keycloak_id}

    # Cette fois, pas d'erreur — on récupère directement le résultat
    result = require_consent(db=db, current_user=current_user)

    # On vérifie que c'est bien le bon consentement qui est renvoyé
    assert result.is_active is True
    assert result.user_id == test_user.id