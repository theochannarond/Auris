import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.core.database import Base
from app.models.user import User
from app.models.consent import Consent
from app.models.meeting import Meeting
from app.models.audio_file import AudioFile
from app.models.transcription import Transcription
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

@pytest.fixture
def test_audio_file(db, test_meeting):
    audio_file = AudioFile(
        id=uuid.uuid4(),
        meeting_id=test_meeting.id,
        storage_key=f"{test_meeting.id}/recording.wav",
        file_size_bytes=1024,
        mime_type="audio/wav"
    )
    db.add(audio_file)
    db.commit()
    db.refresh(audio_file)
    return audio_file

@pytest.fixture
def test_transcription(db, test_meeting, test_audio_file):
    transcription = Transcription(
        id=uuid.uuid4(),
        meeting_id=test_meeting.id,
        audio_file_id=test_audio_file.id,
        status="pending"
    )
    db.add(transcription)
    db.commit()
    db.refresh(transcription)
    return transcription