from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
import time
import logging
import os
from app.core.database import check_db_connection
from app.core.logging_config import setup_logging
from app.api.v1.auth import router as auth_router
from app.api.v1.meetings import router as meetings_router
from app.api.v1.webhooks import router as webhooks_router
from app.api.v1.transcriptions import router as transcriptions_router
from app.api.v1.summaries import router as summaries_router
from app.api.v1.metrics import router as metrics_router
from app.api.v1.status import router as status_router
from app.services.storage_service import check_ovh_health

# Configure les logs JSON dès le démarrage
setup_logging(level=os.getenv("LOG_LEVEL", "INFO"))
logger = logging.getLogger("auris.requests")


app = FastAPI(
    title="Auris API",
    description="Assistant de réunion intelligent — API REST",
    version="1.0.0"
)


@app.middleware("http")
async def log_requests(request: Request, call_next):
    """
    Logue chaque requête HTTP avec méthode, chemin, statut et durée.
    Le user_id est extrait du token si présent — jamais le token lui-même.
    """
    start = time.perf_counter()
    response = await call_next(request)
    duration_ms = round((time.perf_counter() - start) * 1000, 2)

    # Extrait le user_id depuis le header Authorization sans logger le token
    user_id = None
    auth_header = request.headers.get("authorization", "")
    if auth_header.startswith("Bearer "):
        try:
            from jose import jwt as jose_jwt
            token = auth_header.split(" ")[1]
            payload = jose_jwt.get_unverified_claims(token)
            user_id = payload.get("sub")
        except Exception:
            pass

    logger.info(
        f"{request.method} {request.url.path}",
        extra={
            "method":      request.method,
            "path":        request.url.path,
            "status_code": response.status_code,
            "duration_ms": duration_ms,
            "user_id":     user_id,
        }
    )
    return response

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router)
app.include_router(meetings_router)
app.include_router(webhooks_router)
app.include_router(transcriptions_router)
app.include_router(summaries_router)
app.include_router(metrics_router)
app.include_router(status_router)


@app.get("/health")
async def health_check():
    db_ok      = check_db_connection()
    ovh_health = await check_ovh_health()
    return {
        "status":   "ok" if db_ok else "error",
        "service":  "auris-backend",
        "database": "connected" if db_ok else "unreachable",
        "storage":  ovh_health["status"],
    }

@app.get("/health/db")
def health_check_db():
    db_ok = check_db_connection()
    return {
        "status":   "ok" if db_ok else "error",
        "database": "connected" if db_ok else "unreachable"
    }

@app.get("/health/storage")
async def health_check_storage():
    ovh_health = await check_ovh_health()
    return {
        "status":  ovh_health["status"],
        "storage": "ovh",
        "error":   ovh_health.get("error")
    }