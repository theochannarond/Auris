from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, DeclarativeBase
from pydantic_settings import BaseSettings
import logging
import time
from sqlalchemy import event
from sqlalchemy.engine import Engine



class Settings(BaseSettings):
    DATABASE_URL:         str = "postgresql://user:password@localhost:5432/auris"
    KEYCLOAK_URL:         str = "http://localhost:8080"
    KEYCLOAK_REALM:       str = "auris"
    KEYCLOAK_CLIENT_ID:   str = "auris-backend"
    KEYCLOAK_CLIENT_SECRET: str = "your-secret"
    VEXA_API_KEY:         str = ""
    OVH_ACCESS_KEY:       str = "your-ovh-access-key"
    OVH_SECRET_KEY:       str = "your-ovh-secret-key"
    OVH_BUCKET_NAME:      str = "auris-audio"
    OVH_ENDPOINT_URL:     str = "https://s3.gra.io.cloud.ovh.net"
    OVH_REGION:           str = "gra"
    VEXA_WEBHOOK_SECRET:  str = "your-vexa-webhook-secret"
    MISTRAL_API_KEY:      str = ""
    MISTRAL_API_URL:      str = "https://api.mistral.ai/v1"
    VOXTRAL_MODEL:        str = "voxtral-mini-latest"
    VOXTRAL_TIMEOUT_SEC:  float = 300.0
    MAX_RETRY_COUNT: int = 3

    class Config:
        env_file = ".env"
        extra = "ignore"

settings = Settings()

engine = create_engine(settings.DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

class Base(DeclarativeBase):
    pass

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def check_db_connection():
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return True
    except Exception:
        return False

# Logger dédié aux requêtes SQL lentes
slow_query_logger = logging.getLogger("auris.slow_queries")

# Se déclenche juste AVANT chaque requête SQL exécutée
@event.listens_for(Engine, "before_cursor_execute")
def before_cursor_execute(conn, cursor, statement, parameters, context, executemany):
    # On note l'heure de départ, pour pouvoir calculer la durée après
    conn.info.setdefault("query_start_time", []).append(time.perf_counter())

# Se déclenche juste APRÈS chaque requête SQL exécutée
@event.listens_for(Engine, "after_cursor_execute")
def after_cursor_execute(conn, cursor, statement, parameters, context, executemany):
    # Calcule combien de temps la requête a pris, en millisecondes
    total_ms = round(
        (time.perf_counter() - conn.info["query_start_time"].pop(-1)) * 1000, 2
    )
    # Si la requête a pris plus de 100ms, on la considère "lente" et on log un avertissement
    if total_ms > 100:
        slow_query_logger.warning(
            f"Slow query detected ({total_ms}ms)",
            extra={"duration_ms": total_ms, "query": statement[:200]}
        )