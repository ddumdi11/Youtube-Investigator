"""
Quota Tracker - Verfolgt YouTube API Quota-Verbrauch
"""
import sqlite3
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional
import pytz

from src.config import config


class QuotaTracker:
    """
    Verwaltet das tägliche YouTube API Quota-Limit
    Speichert Verbrauch in SQLite für Persistenz
    """

    def __init__(self, db_path: Optional[Path] = None):
        """
        Initialisiert den Tracker mit Datenbank-Verbindung

        Args:
            db_path: Pfad zur SQLite Datenbank (optional)
        """
        self.db_path = db_path or config.DB_PATH
        self.daily_limit = config.DAILY_QUOTA_LIMIT
        self.warning_threshold = config.QUOTA_WARNING_THRESHOLD
        self._init_db()

    def _init_db(self) -> None:
        """Erstellt die quota_log Tabelle falls nicht vorhanden"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS quota_log (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    date TEXT NOT NULL UNIQUE,
                    units_used INTEGER DEFAULT 0,
                    units_limit INTEGER DEFAULT 10000,
                    last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            conn.commit()

    def _get_current_date_pt(self) -> str:
        """
        Gibt das aktuelle Datum in Pacific Time zurück (YYYY-MM-DD)
        YouTube API Quota resettet um Mitternacht PT
        """
        pt_tz = pytz.timezone('US/Pacific')
        now_pt = datetime.now(pt_tz)
        return now_pt.strftime('%Y-%m-%d')

    def _get_today_quota(self) -> tuple[int, int]:
        """
        Holt aktuelle Quota-Daten für heute (PT)

        Returns:
            Tuple von (units_used, units_limit)
        """
        today = self._get_current_date_pt()

        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute(
                "SELECT units_used, units_limit FROM quota_log WHERE date = ?",
                (today,)
            )
            row = cursor.fetchone()

            if row:
                return row[0], row[1]
            else:
                # Neuer Tag - erstelle Eintrag
                conn.execute(
                    "INSERT INTO quota_log (date, units_used, units_limit) VALUES (?, 0, ?)",
                    (today, self.daily_limit)
                )
                conn.commit()
                return 0, self.daily_limit

    def get_remaining(self) -> int:
        """
        Gibt verbleibende Quota-Units für heute zurück

        Returns:
            Anzahl verfügbarer Units
        """
        used, limit = self._get_today_quota()
        return max(0, limit - used)

    def get_used(self) -> int:
        """
        Gibt verbrauchte Quota-Units für heute zurück

        Returns:
            Anzahl verbrauchter Units
        """
        used, _ = self._get_today_quota()
        return used

    def can_afford(self, cost: int) -> bool:
        """
        Prüft ob Operation möglich ist ohne Limit zu überschreiten

        Args:
            cost: Quota-Kosten der Operation

        Returns:
            True wenn genug Quota verfügbar, sonst False
        """
        return self.get_remaining() >= cost

    def consume(self, cost: int, operation: str = "") -> None:
        """
        Bucht Quota-Units ab und aktualisiert Datenbank

        Args:
            cost: Anzahl zu buchender Units
            operation: Optional - Beschreibung der Operation für Logging

        Raises:
            ValueError: Wenn nicht genug Quota verfügbar
        """
        if not self.can_afford(cost):
            raise ValueError(
                f"Nicht genug Quota verfügbar! "
                f"Benötigt: {cost}, Verfügbar: {self.get_remaining()}"
            )

        today = self._get_current_date_pt()

        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                """
                UPDATE quota_log
                SET units_used = units_used + ?,
                    last_updated = CURRENT_TIMESTAMP
                WHERE date = ?
                """,
                (cost, today)
            )
            conn.commit()

        # Warnung wenn Threshold überschritten
        used, limit = self._get_today_quota()
        if used / limit >= self.warning_threshold:
            print(
                f"⚠️  Quota-Warnung: {used}/{limit} Units verwendet "
                f"({used/limit*100:.1f}%)"
            )

    def time_until_reset(self) -> timedelta:
        """
        Berechnet Zeit bis zum nächsten Quota-Reset (Mitternacht PT)

        Returns:
            timedelta bis zum Reset
        """
        pt_tz = pytz.timezone('US/Pacific')
        now_pt = datetime.now(pt_tz)

        # Nächste Mitternacht PT
        tomorrow_pt = (now_pt + timedelta(days=1)).replace(
            hour=0, minute=0, second=0, microsecond=0
        )

        return tomorrow_pt - now_pt

    def get_usage_percentage(self) -> float:
        """
        Gibt Quota-Verbrauch als Prozentsatz zurück

        Returns:
            Prozentsatz (0.0 bis 1.0)
        """
        used, limit = self._get_today_quota()
        return used / limit if limit > 0 else 0.0

    def get_status(self) -> dict:
        """
        Gibt vollständigen Status-Report zurück

        Returns:
            Dictionary mit allen Quota-Informationen
        """
        used, limit = self._get_today_quota()
        remaining = limit - used
        percentage = used / limit if limit > 0 else 0.0
        time_to_reset = self.time_until_reset()

        return {
            "date": self._get_current_date_pt(),
            "used": used,
            "limit": limit,
            "remaining": remaining,
            "percentage": percentage,
            "time_until_reset": time_to_reset,
            "warning_threshold": self.warning_threshold,
            "is_warning": percentage >= self.warning_threshold
        }
