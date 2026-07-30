# Schéma de base de données — Auris
**Document de référence équipe — Juillet 2026**
**Version 2 — mis à jour suite aux corrections Q2 et Q5 (Enzo, 30/07/2026)**
**À lire AVANT de créer ou modifier un modèle SQLAlchemy**

---

## Changelog

| Version | Date | Auteur | Modification |
|---|---|---|---|
| v1 | 21/07/2026 | Théo | Création initiale |
| v2 | 30/07/2026 | Théo | Ajout `meeting_link` (Q2) + correction `mode` default (Q5) |

---

## Règles fondamentales

1. **Jamais de DELETE physique** — toujours utiliser `deleted_at`
2. **Toujours filtrer** les enregistrements supprimés : `.filter(Model.deleted_at == None)`
3. **Jamais de fichier audio en BDD** — uniquement le `storage_key` OVH
4. **UUID partout** — jamais d'entiers auto-incrémentés
5. **Status meetings** : `pending → recording → processing → completed | failed`
6. **mode meetings** : `dictaphone` ou `video` uniquement
7. **Le webhook Vexa est la seule source de vérité du statut** — ne jamais modifier `status` au lancement du bot

---

## Vue d'ensemble des relations

```
users
├── consents        (1 user → N consents)
└── meetings        (1 user → N meetings)
    └── audio_files     (1 meeting → 1 audio_file)
        └── transcriptions  (1 audio_file → 1 transcription)
            └── summaries       (1 transcription → 1 summary)
```

---

## Schéma SQL complet

```sql
-- ─────────────────────────────────────────────────────
-- TABLE : users
-- Utilisateurs authentifiés via Keycloak
-- ─────────────────────────────────────────────────────
CREATE TABLE users (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    keycloak_id     VARCHAR(255) UNIQUE NOT NULL,
    email           VARCHAR(255) UNIQUE NOT NULL,
    full_name       VARCHAR(255) NOT NULL,
    created_at      TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMP NOT NULL DEFAULT NOW()
);

-- ─────────────────────────────────────────────────────
-- TABLE : consents
-- Consentement RGPD explicite (Art. 7 et Art. 9)
-- ─────────────────────────────────────────────────────
CREATE TABLE consents (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id     UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    meeting_id  UUID,
    given_at    TIMESTAMP NOT NULL DEFAULT NOW(),
    ip_address  VARCHAR(45),
    is_active   BOOLEAN NOT NULL DEFAULT TRUE,
    revoked_at  TIMESTAMP
);

-- ─────────────────────────────────────────────────────
-- TABLE : meetings
-- Unité centrale du produit
-- meeting_link : URL de la réunion vidéo (Google Meet, Teams, Zoom) — nullable pour le mode dictaphone
-- ─────────────────────────────────────────────────────
CREATE TABLE meetings (
    id           UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    owner_id     UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    title        VARCHAR(255) NOT NULL,
    mode         VARCHAR(20) NOT NULL DEFAULT 'dictaphone'
                 CHECK (mode IN ('dictaphone', 'video')),
    status       VARCHAR(20) NOT NULL DEFAULT 'pending'
                 CHECK (status IN ('pending', 'recording', 'processing', 'completed', 'failed')),
    meeting_link VARCHAR(500),                             -- URL visio (mode video uniquement)
    started_at   TIMESTAMP,
    ended_at     TIMESTAMP,
    duration_sec INTEGER,
    created_at   TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at   TIMESTAMP NOT NULL DEFAULT NOW(),
    deleted_at   TIMESTAMP                                -- NULL = actif | non NULL = soft delete RGPD
);

-- ─────────────────────────────────────────────────────
-- TABLE : audio_files
-- Fichier audio stocké sur OVH Object Storage
-- Ne jamais stocker le fichier en BDD — uniquement storage_key
-- ─────────────────────────────────────────────────────
CREATE TABLE audio_files (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    meeting_id      UUID NOT NULL REFERENCES meetings(id) ON DELETE CASCADE,
    storage_key     VARCHAR(512) NOT NULL,         -- chemin OVH : "meetings/uuid/audio.wav"
    file_size_bytes BIGINT,
    duration_sec    INTEGER,
    mime_type       VARCHAR(50) NOT NULL DEFAULT 'audio/wav',
    created_at      TIMESTAMP NOT NULL DEFAULT NOW(),
    deleted_at      TIMESTAMP
);

-- ─────────────────────────────────────────────────────
-- TABLE : transcriptions
-- Résultat Voxtral Mini V2
-- ─────────────────────────────────────────────────────
CREATE TABLE transcriptions (
    id             UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    meeting_id     UUID NOT NULL REFERENCES meetings(id) ON DELETE CASCADE,
    audio_file_id  UUID NOT NULL REFERENCES audio_files(id) ON DELETE CASCADE,
    raw_text       TEXT NOT NULL,                  -- transcription brute
    diarization    JSONB,                          -- labels locuteurs + timestamps
    language       VARCHAR(10) NOT NULL DEFAULT 'fr',
    voxtral_model  VARCHAR(100) NOT NULL DEFAULT 'voxtral-mini-transcribe-v2',
    processing_ms  INTEGER,                        -- temps de traitement mesuré
    created_at     TIMESTAMP NOT NULL DEFAULT NOW(),
    deleted_at     TIMESTAMP
);

-- ─────────────────────────────────────────────────────
-- TABLE : summaries
-- Compte-rendu généré par Mistral Small 4
-- ─────────────────────────────────────────────────────
CREATE TABLE summaries (
    id                UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    meeting_id        UUID NOT NULL REFERENCES meetings(id) ON DELETE CASCADE,
    transcription_id  UUID NOT NULL REFERENCES transcriptions(id) ON DELETE CASCADE,
    content           TEXT NOT NULL,               -- CR structuré complet
    decisions         JSONB,                       -- décisions extraites
    action_items      JSONB,                       -- actions par responsable
    tone              VARCHAR(50),                 -- 'formal' | 'informal' | 'technical'
    theme             VARCHAR(100),                -- thème principal de la réunion
    mistral_model     VARCHAR(100) NOT NULL DEFAULT 'mistral-small-latest',
    tokens_used       INTEGER,
    processing_ms     INTEGER,
    created_at        TIMESTAMP NOT NULL DEFAULT NOW(),
    deleted_at        TIMESTAMP
);
```

---

## Modèles SQLAlchemy complets

### users

```python
# backend/app/models/user.py
from sqlalchemy import Column, String, DateTime
from sqlalchemy.dialects.postgresql import UUID
from datetime import datetime
import uuid
from app.core.database import Base

class User(Base):
    __tablename__ = "users"

    id          = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    keycloak_id = Column(String(255), unique=True, nullable=False)
    email       = Column(String(255), unique=True, nullable=False)
    full_name   = Column(String(255), nullable=False)
    created_at  = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at  = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
```

### consents

```python
# backend/app/models/consent.py
from sqlalchemy import Column, String, DateTime, Boolean
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy import ForeignKey
from datetime import datetime
import uuid
from app.core.database import Base

class Consent(Base):
    __tablename__ = "consents"

    id         = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id    = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    meeting_id = Column(UUID(as_uuid=True), nullable=True)
    given_at   = Column(DateTime, nullable=False, default=datetime.utcnow)
    ip_address = Column(String(45), nullable=True)
    is_active  = Column(Boolean, nullable=False, default=True)
    revoked_at = Column(DateTime, nullable=True)
```

### meetings

```python
# backend/app/models/meeting.py
from sqlalchemy import Column, String, DateTime, ForeignKey, Integer
from sqlalchemy.dialects.postgresql import UUID
from datetime import datetime
import uuid
from app.core.database import Base

class Meeting(Base):
    __tablename__ = "meetings"

    id           = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    owner_id     = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    title        = Column(String(255), nullable=False)
    mode         = Column(String(20), nullable=False, default="dictaphone")  # "dictaphone" | "video"
    status       = Column(String(20), nullable=False, default="pending")     # pending | recording | processing | completed | failed
    meeting_link = Column(String(500), nullable=True)                        # URL visio (mode video uniquement)
    started_at   = Column(DateTime, nullable=True)
    ended_at     = Column(DateTime, nullable=True)
    duration_sec = Column(Integer, nullable=True)
    created_at   = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at   = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
    deleted_at   = Column(DateTime, nullable=True)   # soft delete RGPD — NE JAMAIS SUPPRIMER PHYSIQUEMENT
```

### audio_files

```python
# backend/app/models/audio_file.py
from sqlalchemy import Column, String, DateTime, Integer, BigInteger
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy import ForeignKey
from datetime import datetime
import uuid
from app.core.database import Base

class AudioFile(Base):
    __tablename__ = "audio_files"

    id              = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    meeting_id      = Column(UUID(as_uuid=True), ForeignKey("meetings.id", ondelete="CASCADE"), nullable=False)
    storage_key     = Column(String(512), nullable=False)   # chemin OVH : "meetings/uuid/audio.wav"
    file_size_bytes = Column(BigInteger, nullable=True)
    duration_sec    = Column(Integer, nullable=True)
    mime_type       = Column(String(50), nullable=False, default="audio/wav")
    created_at      = Column(DateTime, nullable=False, default=datetime.utcnow)
    deleted_at      = Column(DateTime, nullable=True)
```

### transcriptions

```python
# backend/app/models/transcription.py
from sqlalchemy import Column, String, DateTime, Integer, Text
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy import ForeignKey
from datetime import datetime
import uuid
from app.core.database import Base

class Transcription(Base):
    __tablename__ = "transcriptions"

    id             = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    meeting_id     = Column(UUID(as_uuid=True), ForeignKey("meetings.id", ondelete="CASCADE"), nullable=False)
    audio_file_id  = Column(UUID(as_uuid=True), ForeignKey("audio_files.id", ondelete="CASCADE"), nullable=False)
    raw_text       = Column(Text, nullable=False)
    diarization    = Column(JSONB, nullable=True)   # labels locuteurs + timestamps
    language       = Column(String(10), nullable=False, default="fr")
    voxtral_model  = Column(String(100), nullable=False, default="voxtral-mini-transcribe-v2")
    processing_ms  = Column(Integer, nullable=True)
    created_at     = Column(DateTime, nullable=False, default=datetime.utcnow)
    deleted_at     = Column(DateTime, nullable=True)
```

### summaries

```python
# backend/app/models/summary.py
from sqlalchemy import Column, String, DateTime, Integer, Text
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy import ForeignKey
from datetime import datetime
import uuid
from app.core.database import Base

class Summary(Base):
    __tablename__ = "summaries"

    id               = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    meeting_id       = Column(UUID(as_uuid=True), ForeignKey("meetings.id", ondelete="CASCADE"), nullable=False)
    transcription_id = Column(UUID(as_uuid=True), ForeignKey("transcriptions.id", ondelete="CASCADE"), nullable=False)
    content          = Column(Text, nullable=False)
    decisions        = Column(JSONB, nullable=True)
    action_items     = Column(JSONB, nullable=True)
    tone             = Column(String(50), nullable=True)
    theme            = Column(String(100), nullable=True)
    mistral_model    = Column(String(100), nullable=False, default="mistral-small-latest")
    tokens_used      = Column(Integer, nullable=True)
    processing_ms    = Column(Integer, nullable=True)
    created_at       = Column(DateTime, nullable=False, default=datetime.utcnow)
    deleted_at       = Column(DateTime, nullable=True)
```

---

## Schémas Pydantic complets

### users

```python
# backend/app/schemas/user.py
from pydantic import BaseModel, EmailStr
from uuid import UUID
from datetime import datetime

class UserBase(BaseModel):
    email:     EmailStr
    full_name: str

class UserCreate(UserBase):
    keycloak_id: str

class UserResponse(UserBase):
    id:          UUID
    keycloak_id: str
    created_at:  datetime
    updated_at:  datetime

    class Config:
        from_attributes = True
```

### consents

```python
# backend/app/schemas/consent.py
from pydantic import BaseModel
from uuid import UUID
from datetime import datetime
from typing import Optional

class ConsentCreate(BaseModel):
    meeting_id: Optional[UUID] = None

class ConsentResponse(BaseModel):
    id:         UUID
    user_id:    UUID
    meeting_id: Optional[UUID] = None
    given_at:   datetime
    ip_address: Optional[str] = None
    is_active:  bool
    revoked_at: Optional[datetime] = None

    class Config:
        from_attributes = True
```

### meetings

```python
# backend/app/schemas/meeting.py
from pydantic import BaseModel
from uuid import UUID
from datetime import datetime
from typing import Optional

class MeetingCreate(BaseModel):
    title:        str
    mode:         str = "dictaphone"           # dictaphone | video
    meeting_link: Optional[str] = None         # URL visio (mode video uniquement)

class MeetingResponse(BaseModel):
    id:           UUID
    owner_id:     UUID
    title:        str
    mode:         str
    status:       str
    meeting_link: Optional[str] = None         # URL visio (mode video uniquement)
    started_at:   Optional[datetime] = None
    ended_at:     Optional[datetime] = None
    duration_sec: Optional[int] = None
    created_at:   datetime
    updated_at:   datetime

    class Config:
        from_attributes = True

class MeetingStatusResponse(BaseModel):
    """Schéma retourné par GET /api/v1/meetings/{id}/status (SCRUM-83 T3)"""
    id:     UUID
    status: str

    class Config:
        from_attributes = True
```

### audio_files

```python
# backend/app/schemas/audio_file.py
from pydantic import BaseModel
from uuid import UUID
from datetime import datetime
from typing import Optional

class AudioFileResponse(BaseModel):
    id:              UUID
    meeting_id:      UUID
    storage_key:     str
    file_size_bytes: Optional[int] = None
    duration_sec:    Optional[int] = None
    mime_type:       str
    created_at:      datetime

    class Config:
        from_attributes = True
```

### transcriptions

```python
# backend/app/schemas/transcription.py
from pydantic import BaseModel
from uuid import UUID
from datetime import datetime
from typing import Optional, Any

class TranscriptionResponse(BaseModel):
    id:            UUID
    meeting_id:    UUID
    audio_file_id: UUID
    raw_text:      str
    diarization:   Optional[Any] = None
    language:      str
    voxtral_model: str
    processing_ms: Optional[int] = None
    created_at:    datetime

    class Config:
        from_attributes = True
```

### summaries

```python
# backend/app/schemas/summary.py
from pydantic import BaseModel
from uuid import UUID
from datetime import datetime
from typing import Optional, Any

class SummaryResponse(BaseModel):
    id:               UUID
    meeting_id:       UUID
    transcription_id: UUID
    content:          str
    decisions:        Optional[Any] = None
    action_items:     Optional[Any] = None
    tone:             Optional[str] = None
    theme:            Optional[str] = None
    mistral_model:    str
    tokens_used:      Optional[int] = None
    processing_ms:    Optional[int] = None
    created_at:       datetime

    class Config:
        from_attributes = True
```

---

## Règles de suppression RGPD (Art. 17)

Quand un utilisateur demande la suppression de ses données :

```python
from datetime import datetime

def soft_delete_meeting(meeting_id: UUID, db: Session):
    now = datetime.utcnow()

    # 1. Soft delete de la réunion
    meeting = db.query(Meeting).filter(Meeting.id == meeting_id).first()
    meeting.deleted_at = now

    # 2. Soft delete des fichiers audio
    db.query(AudioFile).filter(AudioFile.meeting_id == meeting_id).update({"deleted_at": now})

    # 3. Soft delete des transcriptions
    db.query(Transcription).filter(Transcription.meeting_id == meeting_id).update({"deleted_at": now})

    # 4. Soft delete des résumés
    db.query(Summary).filter(Summary.meeting_id == meeting_id).update({"deleted_at": now})

    db.commit()
    # TODO Sprint 9 : supprimer le fichier audio sur OVH Object Storage
    # TODO Sprint 9 : propager la suppression à Gladia et Mistral via leurs DPA
```

---

## Checklist avant de créer une migration Alembic

- [ ] Le modèle est dans `backend/app/models/`
- [ ] Le modèle importe `Base` depuis `app.core.database`
- [ ] Le modèle est importé dans `backend/alembic/env.py`
- [ ] `deleted_at` est présent si la table contient des données utilisateur
- [ ] La migration est générée avec `alembic revision --autogenerate -m "description"`
- [ ] La migration est appliquée avec `alembic upgrade head`
- [ ] La migration est committée avec `feat(db) : description [SCRUM-XX]`
