"""
Tests du réessai Mistral et du déblocage d'une réunion après un échec.

Ces tests existent à cause d'un incident réel : un 429 « Rate limit exceeded »
de Mistral rendait une réunion **définitivement** ingénérable.

Deux défauts se combinaient. La ligne `summaries` est créée AVANT l'appel à
Mistral ; en cas d'échec, l'ancienne version y écrivait le message d'erreur.
La ligne n'étant alors plus vide, le contrôle d'idempotence la prenait pour un
résumé valide et la renvoyait à chaque nouveau clic, sans jamais relancer la
génération — pendant que l'utilisateur voyait la réponse brute de Mistral
affichée comme si c'était son compte rendu.

À noter : transcription et résumé passent par la même clé et le même hôte,
donc par le même quota de débit. Générer un résumé juste après une
transcription suffit à déclencher le 429.
"""

import uuid
import pytest
from unittest.mock import AsyncMock, patch

from app.services import mistral_service
from app.services.mistral_service import (
    generate_summary_with_backoff,
    MistralSummaryError,
)
from app.models.summary import Summary

TEXTE = "Bonjour, ceci est la transcription de la réunion."

RESUME_OK = {
    "content":       "Compte rendu de la réunion.",
    "decisions":     ["Décision A"],
    "action_items":  ["Action B"],
    "tone":          "formal",
    "theme":         "Revue de sprint",
    "tokens_used":   120,
    "processing_ms": 900,
}


@pytest.fixture(autouse=True)
def reglages(monkeypatch):
    monkeypatch.setattr(mistral_service.settings, "MISTRAL_API_KEY", "test-key")
    monkeypatch.setattr(mistral_service.settings, "MAX_RETRY_COUNT", 3)
    # Neutralise les temporisations : les tests ne doivent pas dormir 7 secondes.
    monkeypatch.setattr(mistral_service.asyncio, "sleep", AsyncMock())


# ─── Le réessai ───

@pytest.mark.asyncio
async def test_reussite_au_premier_essai():
    with patch.object(mistral_service, "generate_summary",
                      new=AsyncMock(return_value=RESUME_OK)) as appel:
        result = await generate_summary_with_backoff(TEXTE)

    assert result["content"] == RESUME_OK["content"]
    assert appel.await_count == 1


@pytest.mark.asyncio
async def test_429_est_reessaye_puis_reussit():
    """Le cas de l'incident : un 429 passager ne doit plus être définitif."""
    erreur_429 = MistralSummaryError(
        'Mistral a répondu 429 : {"message":"Rate limit exceeded"}', 120
    )
    appel = AsyncMock(side_effect=[erreur_429, erreur_429, RESUME_OK])

    with patch.object(mistral_service, "generate_summary", new=appel):
        result = await generate_summary_with_backoff(TEXTE)

    assert result["content"] == RESUME_OK["content"]
    assert appel.await_count == 3


@pytest.mark.asyncio
async def test_429_persistant_finit_par_lever():
    """Après MAX_RETRY_COUNT tentatives, l'erreur remonte."""
    erreur_429 = MistralSummaryError("Mistral a répondu 429 : Rate limit exceeded", 120)
    appel = AsyncMock(side_effect=erreur_429)

    with patch.object(mistral_service, "generate_summary", new=appel):
        with pytest.raises(MistralSummaryError):
            await generate_summary_with_backoff(TEXTE)

    assert appel.await_count == 4          # 1 essai + 3 réessais


@pytest.mark.asyncio
async def test_erreur_definitive_non_reessayee():
    """Une clé absente échouera pareil à chaque tentative : inutile d'insister."""
    appel = AsyncMock(side_effect=MistralSummaryError("Clé API Mistral manquante"))

    with patch.object(mistral_service, "generate_summary", new=appel):
        with pytest.raises(MistralSummaryError):
            await generate_summary_with_backoff(TEXTE)

    assert appel.await_count == 1


# ─── Le déblocage de la réunion ───

def _transcription_prete(db, test_transcription):
    test_transcription.status   = "completed"
    test_transcription.raw_text = TEXTE
    db.commit()


def test_echec_laisse_la_reunion_generable(client, db, test_meeting, test_transcription):
    """
    Cœur de la correction. Après un échec, aucun résumé exploitable ne doit
    subsister : une nouvelle demande doit repartir, pas renvoyer le raté.
    """
    _transcription_prete(db, test_transcription)

    # Une tentative précédente a échoué : la ligne a été écartée.
    rate = Summary(
        id=uuid.uuid4(),
        meeting_id=test_meeting.id,
        transcription_id=test_transcription.id,
        content="",
    )
    db.add(rate)
    db.commit()
    from datetime import datetime
    rate.deleted_at = datetime.utcnow()
    db.commit()

    with patch("app.api.v1.summaries.run_summary", new=AsyncMock()):
        res = client.post("/api/v1/summaries", json={"meeting_id": str(test_meeting.id)})

    assert res.status_code == 202
    assert res.json()["id"] != str(rate.id)     # une nouvelle génération, pas l'ancienne


def test_ligne_vide_est_reutilisee_et_relance(client, db, test_meeting, test_transcription):
    """
    Un résumé vide encore actif ne doit pas être pris pour un résumé valide :
    on relance, en réutilisant la ligne plutôt qu'en empilant les doublons.
    """
    _transcription_prete(db, test_transcription)

    vide = Summary(
        id=uuid.uuid4(),
        meeting_id=test_meeting.id,
        transcription_id=test_transcription.id,
        content="",
    )
    db.add(vide)
    db.commit()

    with patch("app.api.v1.summaries.run_summary", new=AsyncMock()) as relance:
        res = client.post("/api/v1/summaries", json={"meeting_id": str(test_meeting.id)})

    assert res.status_code == 202
    assert res.json()["id"] == str(vide.id)     # même ligne réutilisée
    relance.assert_called_once()

    actifs = db.query(Summary).filter(
        Summary.meeting_id == test_meeting.id,
        Summary.deleted_at == None
    ).count()
    assert actifs == 1                          # aucun doublon empilé


def test_resume_abouti_n_est_pas_regenere(client, db, test_meeting, test_transcription):
    """L'idempotence reste vraie quand le résumé existe vraiment."""
    _transcription_prete(db, test_transcription)

    abouti = Summary(
        id=uuid.uuid4(),
        meeting_id=test_meeting.id,
        transcription_id=test_transcription.id,
        content="Un vrai compte rendu.",
    )
    db.add(abouti)
    db.commit()

    with patch("app.api.v1.summaries.run_summary", new=AsyncMock()) as relance:
        res = client.post("/api/v1/summaries", json={"meeting_id": str(test_meeting.id)})

    assert res.json()["id"] == str(abouti.id)
    relance.assert_not_called()                 # Mistral n'est pas rappelé pour rien
