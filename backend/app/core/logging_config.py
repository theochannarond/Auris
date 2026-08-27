import logging
import json
import sys
from datetime import datetime, timezone


class JSONFormatter(logging.Formatter):
    """
    Formate chaque entrée de log en JSON sur une seule ligne.
    Parsable par tout agrégateur de logs (Loki, Datadog, CloudWatch…).
    Les données sensibles (tokens, mots de passe) ne doivent JAMAIS
    être passées en argument de log — c'est la responsabilité de l'appelant.
    """

    SENSITIVE_PATTERNS = [
        "password", "token", "secret", "api_key",
        "access_key", "authorization", "credential"
    ]

    def format(self, record: logging.LogRecord) -> str:
        message = record.getMessage()

        # Détecte une fuite de données sensibles et la masque
        msg_lower = message.lower()
        for pattern in self.SENSITIVE_PATTERNS:
            if pattern in msg_lower:
                message = "[REDACTED — sensitive data detected in log]"
                break

        log_entry: dict = {
            "timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "level":     record.levelname,
            "logger":    record.name,
            "message":   message,
        }

        # Champs optionnels enrichis par l'appelant via extra={}
        for field in ("user_id", "method", "path", "status_code", "duration_ms", "meeting_id"):
            if hasattr(record, field):
                log_entry[field] = getattr(record, field)

        if record.exc_info:
            log_entry["exception"] = self.formatException(record.exc_info)

        return json.dumps(log_entry, ensure_ascii=False)


def setup_logging(level: str = "INFO") -> None:
    """
    Configure le logger racine en JSON sur stdout.
    À appeler une seule fois au démarrage de l'application (dans main.py).

    Niveaux disponibles :
      DEBUG   — détails techniques (dev uniquement)
      INFO    — flux normal (requêtes, actions utilisateur)
      WARNING — anomalies non bloquantes (retry, fallback)
      ERROR   — erreurs récupérées (transcription échouée, OVH indispo)
    """
    numeric_level = getattr(logging, level.upper(), logging.INFO)

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(JSONFormatter())

    root = logging.getLogger()
    root.handlers = [handler]
    root.setLevel(numeric_level)

    # Réduit le bruit des bibliothèques tierces
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)