from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, DeclarativeBase
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    DATABASE_URL: str = "postgresql://user:password@localhost:5432/auris"
    KEYCLOAK_URL: str = "http://localhost:8080"
    KEYCLOAK_REALM: str = "auris"
    KEYCLOAK_CLIENT_ID: str = "auris-backend"
    KEYCLOAK_CLIENT_SECRET: str = "your-secret"
    OVH_ACCESS_KEY: str = "your-ovh-access-key"
    OVH_SECRET_KEY: str = "your-ovh-secret-key"
    OVH_BUCKET_NAME: str = "auris-audio"
    OVH_ENDPOINT_URL: str = "https://s3.gra.io.cloud.ovh.net"
    OVH_REGION: str = "gra"

    class Config:
        env_file = ".env"

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