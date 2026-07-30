import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.core.database import Base
from app.models.user import User
from app.models.consent import Consent
from app.models.meeting import Meeting
from app.models.audio_file import AudioFile
import uuid

SQLALCHEMY_TEST_URL = "sqlite:///./test.db"

engine = create_engine(
    SQLALCHEMY_TEST_URL,
    connect_args={"check_same_thread": False}
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

@pytest.fixture(scope="function")
def db():
    Base.metadata.create_all(bind=engine)
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(bind=engine)

@pytest.fixture
def test_user(db):
    user = User(
        id=uuid.uuid4(),
        keycloak_id="test-keycloak-id",
        email="test@auris.fr",
        full_name="Test User"
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user

@pytest.fixture
def test_meeting(db, test_user):
    meeting = Meeting(
        id=uuid.uuid4(),
        owner_id=test_user.id,
        title="Réunion test",
        mode="video",
        status="pending"
    )
    db.add(meeting)
    db.commit()
    db.refresh(meeting)
    return meeting