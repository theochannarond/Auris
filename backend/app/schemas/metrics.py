from pydantic import BaseModel
from typing import Optional


class OperationMetrics(BaseModel):
    avg_ms:        Optional[float]
    p95_ms:        Optional[float]
    sample_size:   int
    slo_target_ms: int
    slo_validated: Optional[bool]


class MetricsResponse(BaseModel):
    transcription: OperationMetrics
    summary:       OperationMetrics
    upload:        OperationMetrics