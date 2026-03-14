"""
Configuration Management für YouTube Investigator
Lädt API-Keys und Settings aus .env Datei
"""
import os
from pathlib import Path
from dotenv import load_dotenv

# Projekt-Root ermitteln
PROJECT_ROOT = Path(__file__).parent.parent

# .env Datei laden
load_dotenv(PROJECT_ROOT / ".env")


class Config:
    """
    Zentrale Konfiguration für das Projekt
    """

    # YouTube API
    YOUTUBE_API_KEY = os.getenv("YOUTUBE_API_KEY")

    # Quota Settings
    DAILY_QUOTA_LIMIT = 10_000
    QUOTA_WARNING_THRESHOLD = 0.80  # Warnung bei 80%

    # Datenbank
    DB_PATH = PROJECT_ROOT / "data" / "queue.db"

    # Export
    EXPORT_DIR = PROJECT_ROOT / "data" / "exports"

    # API Rate Limiting
    REQUESTS_PER_SECOND = 3.0
    RETRY_COUNT = 3
    RETRY_DELAY = 2  # Sekunden

    # Batch Processing
    DEFAULT_BATCH_SIZE = 50  # Max Items pro API Call
    DEFAULT_LOOKBACK_DAYS = 90

    @classmethod
    def validate(cls) -> bool:
        """
        Prüft ob alle erforderlichen Konfigurationen vorhanden sind
        """
        if not cls.YOUTUBE_API_KEY:
            raise ValueError(
                "YOUTUBE_API_KEY nicht gefunden!\n"
                "Bitte .env Datei erstellen und API-Key hinzufügen.\n"
                "Beispiel: cp .env.example .env"
            )

        # Verzeichnisse erstellen falls nicht vorhanden
        cls.DB_PATH.parent.mkdir(parents=True, exist_ok=True)
        cls.EXPORT_DIR.mkdir(parents=True, exist_ok=True)

        return True


# Singleton-Instanz
config = Config()
