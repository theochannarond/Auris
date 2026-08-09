from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.database import check_db_connection
from app.api.v1.auth import router as auth_router
from app.api.v1.meetings import router as meetings_router
from app.api.v1.webhooks import router as webhooks_router
from app.api.v1.transcriptions import router as transcriptions_router
from app.api.v1.summaries import router as summaries_router



app = FastAPI(
    title="Auris API",
    description="Assistant de réunion intelligent — API REST",
    version="1.0.0"
)

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

@app.get("/health")
def health_check():
    return {"status": "ok", "service": "auris-backend"}


@app.get("/health/db")
def health_check_db():
    db_ok = check_db_connection()
    return {
        "status": "ok" if db_ok else "error",
        "database": "connected" if db_ok else "unreachable"
    }