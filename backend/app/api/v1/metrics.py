from typing import Optional

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func
from app.core.database import get_db
from app.core.security import get_current_user
from app.models.transcription import Transcription
from app.models.summary import Summary
from app.models.audio_file import AudioFile
from app.schemas.metrics import MetricsResponse, OperationMetrics

router = APIRouter(prefix="/api/v1", tags=["metrics"])


def _percentile_95(values: list[float]) -> Optional[float]:
    """Calcule le p95 depuis une liste de valeurs."""
    if not values:
        return None
    sorted_vals = sorted(values)
    idx = int(len(sorted_vals) * 0.95)
    return sorted_vals[min(idx, len(sorted_vals) - 1)]


@router.get("/metrics", response_model=MetricsResponse)
async def get_metrics(
    db:           Session = Depends(get_db),
    current_user: dict    = Depends(get_current_user)
):
    """
    Retourne les latences moyennes et p95 mesurées sur les opérations clés.

    SLO cibles :
      - Transcription Voxtral : < 2 min (120 000 ms)
      - Résumé Mistral        : < 10 s  (10 000 ms)
      - Upload OVH            : < 30 s  (30 000 ms)
    """
    # ── Transcription ──
    transcription_rows = db.query(Transcription.processing_ms).filter(
        Transcription.status == "completed",
        Transcription.processing_ms.isnot(None)
    ).all()
    transcription_values = [r[0] for r in transcription_rows]
    avg_transcription = round(sum(transcription_values) / len(transcription_values), 2) if transcription_values else None
    p95_transcription = _percentile_95(transcription_values)

    # ── Résumé ──
    summary_rows = db.query(Summary.processing_ms).filter(
        Summary.processing_ms.isnot(None)
    ).all()
    summary_values = [r[0] for r in summary_rows]
    avg_summary = round(sum(summary_values) / len(summary_values), 2) if summary_values else None
    p95_summary = _percentile_95(summary_values)

    # ── Upload OVH ──
    upload_rows = db.query(AudioFile.upload_ms).filter(
        AudioFile.upload_ms.isnot(None)
    ).all()
    upload_values = [r[0] for r in upload_rows]
    avg_upload = round(sum(upload_values) / len(upload_values), 2) if upload_values else None
    p95_upload = _percentile_95(upload_values)

    SLO_TRANSCRIPTION_MS = 120_000
    SLO_SUMMARY_MS       = 10_000
    SLO_UPLOAD_MS        = 30_000

    return MetricsResponse(
        transcription=OperationMetrics(
            avg_ms        = avg_transcription,
            p95_ms        = p95_transcription,
            sample_size   = len(transcription_values),
            slo_target_ms = SLO_TRANSCRIPTION_MS,
            slo_validated = avg_transcription < SLO_TRANSCRIPTION_MS if avg_transcription else None,
        ),
        summary=OperationMetrics(
            avg_ms        = avg_summary,
            p95_ms        = p95_summary,
            sample_size   = len(summary_values),
            slo_target_ms = SLO_SUMMARY_MS,
            slo_validated = avg_summary < SLO_SUMMARY_MS if avg_summary else None,
        ),
        upload=OperationMetrics(
            avg_ms        = avg_upload,
            p95_ms        = p95_upload,
            sample_size   = len(upload_values),
            slo_target_ms = SLO_UPLOAD_MS,
            slo_validated = avg_upload < SLO_UPLOAD_MS if avg_upload else None,
        ),
    )