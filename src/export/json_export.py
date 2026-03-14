"""
JSON Export Formatter
Exportiert Analyse-Ergebnisse als strukturiertes JSON
"""
import json
from pathlib import Path
from datetime import datetime
from typing import Optional

from src.config import config


class JSONExporter:
    """
    Formatiert und exportiert Analyse-Daten als JSON
    """

    def __init__(self, export_dir: Optional[Path] = None):
        """
        Initialisiert JSON Exporter

        Args:
            export_dir: Verzeichnis für Exports (optional)
        """
        self.export_dir = export_dir or config.EXPORT_DIR
        self.export_dir.mkdir(parents=True, exist_ok=True)

    def format_analysis(self, analysis: dict, pretty: bool = True) -> str:
        """
        Formatiert Analyse-Daten als JSON-String

        Args:
            analysis: Analyse-Dictionary
            pretty: Pretty-print mit Einrückung

        Returns:
            JSON-String
        """
        if pretty:
            return json.dumps(analysis, indent=2, ensure_ascii=False)
        else:
            return json.dumps(analysis, ensure_ascii=False)

    def export_to_file(
        self,
        analysis: dict,
        filename: Optional[str] = None,
        pretty: bool = True
    ) -> Path:
        """
        Exportiert Analyse als JSON-Datei

        Args:
            analysis: Analyse-Dictionary
            filename: Optional - Dateiname (auto-generiert falls None)
            pretty: Pretty-print mit Einrückung

        Returns:
            Pfad zur exportierten Datei
        """
        # Auto-generate filename
        if not filename:
            channel_id = analysis['channel']['id']
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f"channel_{channel_id}_{timestamp}.json"

        filepath = self.export_dir / filename

        # Export
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(self.format_analysis(analysis, pretty=pretty))

        return filepath

    def create_summary(self, analysis: dict) -> dict:
        """
        Erstellt Zusammenfassung der wichtigsten Metriken

        Args:
            analysis: Vollständige Analyse

        Returns:
            Kompakte Zusammenfassung
        """
        return {
            'channel': {
                'title': analysis['channel']['title'],
                'id': analysis['channel']['id'],
                'subscribers': analysis['channel']['subscribers']
            },
            'period': {
                'days': analysis['analysis_period']['lookback_days'],
                'videos': analysis['statistics']['videos_in_period']
            },
            'performance': {
                'total_views': analysis['statistics']['total_views'],
                'avg_views': analysis['statistics']['avg_views_per_video'],
                'median_views': analysis['statistics']['median_views'],
                'engagement_rate': f"{analysis['statistics']['engagement_rate']}%"
            },
            'quota_used': analysis['meta']['quota_used']
        }
