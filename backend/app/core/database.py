from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, DeclarativeBase
from pydantic_settings import BaseSettings

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
    # Sondes internes du tableau de bord d'administration (SCRUM-176). Ces
    # noms d'hôte sont ceux du réseau Docker : ils ne résolvent que depuis un
    # conteneur de la pile, jamais depuis l'extérieur.
    FRONTEND_HEALTH_URL:  str = "http://frontend:80/"
    NGINX_HEALTH_URL:     str = "http://nginx:80/nginx-health"

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