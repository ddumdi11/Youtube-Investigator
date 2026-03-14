"""
Channel Statistics Analyzer
Orchestriert Kanal-Analyse mit Quota-effizientem Playlist-Trick
"""
from datetime import datetime, timedelta
from typing import Optional
import pytz

from src.api.youtube_client import YouTubeClient
from src.quota.tracker import QuotaTracker


class ChannelAnalyzer:
    """
    Analysiert YouTube-Kanäle mit intelligentem Quota-Management
    """

    def __init__(
        self,
        client: Optional[YouTubeClient] = None,
        quota_tracker: Optional[QuotaTracker] = None
    ):
        """
        Initialisiert Channel Analyzer

        Args:
            client: YouTubeClient Instanz (optional)
            quota_tracker: QuotaTracker Instanz (optional)
        """
        self.quota_tracker = quota_tracker or QuotaTracker()
        self.client = client or YouTubeClient(quota_tracker=self.quota_tracker)

    def _filter_videos_by_date(
        self,
        videos: list[dict],
        days: int
    ) -> list[dict]:
        """
        Filtert Videos nach Veröffentlichungsdatum

        Args:
            videos: Liste von Video-Dictionaries
            days: Anzahl Tage zurück

        Returns:
            Gefilterte Liste von Videos
        """
        if days <= 0:
            return videos

        cutoff_date = datetime.now(pytz.UTC) - timedelta(days=days)

        filtered = []
        for video in videos:
            # Parse ISO 8601 Format: 2025-11-15T14:30:00Z
            published = datetime.fromisoformat(
                video['published_at'].replace('Z', '+00:00')
            )

            if published >= cutoff_date:
                filtered.append(video)

        return filtered

    def _calculate_statistics(self, videos: list[dict]) -> dict:
        """
        Berechnet Statistiken für Video-Liste

        Args:
            videos: Liste von Video-Dictionaries

        Returns:
            Dictionary mit Statistiken
        """
        if not videos:
            return {
                'videos_in_period': 0,
                'total_views': 0,
                'total_likes': 0,
                'total_comments': 0,
                'avg_views_per_video': 0,
                'avg_likes_per_video': 0,
                'avg_comments_per_video': 0,
                'median_views': 0,
                'max_views': 0,
                'min_views': 0,
                'engagement_rate': 0.0
            }

        view_counts = [v['view_count'] for v in videos]
        like_counts = [v['like_count'] for v in videos]
        comment_counts = [v['comment_count'] for v in videos]

        total_views = sum(view_counts)
        total_likes = sum(like_counts)
        total_comments = sum(comment_counts)
        count = len(videos)

        # Median berechnen
        sorted_views = sorted(view_counts)
        median_views = sorted_views[count // 2] if count > 0 else 0

        # Engagement Rate: (Likes + Comments) / Views
        engagement_rate = 0.0
        if total_views > 0:
            engagement_rate = (total_likes + total_comments) / total_views

        return {
            'videos_in_period': count,
            'total_views': total_views,
            'total_likes': total_likes,
            'total_comments': total_comments,
            'avg_views_per_video': total_views // count if count > 0 else 0,
            'avg_likes_per_video': total_likes // count if count > 0 else 0,
            'avg_comments_per_video': total_comments // count if count > 0 else 0,
            'median_views': median_views,
            'max_views': max(view_counts) if view_counts else 0,
            'min_views': min(view_counts) if view_counts else 0,
            'engagement_rate': round(engagement_rate * 100, 2)  # Als Prozent
        }

    def analyze_channel(
        self,
        identifier: str,
        lookback_days: int = 90,
        max_videos: Optional[int] = None
    ) -> dict:
        """
        Führt vollständige Kanal-Analyse durch

        Args:
            identifier: Channel-ID, @handle, oder URL
            lookback_days: Zeitraum in Tagen (0 = alle Videos)
            max_videos: Optional - Maximale Anzahl Videos zu analysieren

        Returns:
            Dictionary mit vollständiger Analyse

        Quota-Kosten:
            - Channel-ID Auflösung: 1 Unit (falls @handle)
            - Kanal-Info: 1 Unit
            - Playlist-Items: 1 Unit pro 50 Videos
            - Video-Details: 1 Unit pro 50 Videos
        """
        quota_start = self.quota_tracker.get_used()

        # 1. Channel-ID auflösen
        channel_id = self.client.resolve_channel_id(identifier)

        # 2. Kanal-Metadaten abrufen
        channel_info = self.client.get_channel_info(channel_id)

        # 3. Video-IDs aus Upload-Playlist holen (Playlist-Trick!)
        uploads_playlist_id = channel_info['uploads_playlist_id']
        video_ids = self.client.get_playlist_videos(
            uploads_playlist_id,
            max_results=max_videos
        )

        # 4. Video-Details in Batches abrufen
        all_videos = self.client.get_videos_batch(video_ids)

        # 5. Nach Datum filtern
        filtered_videos = self._filter_videos_by_date(all_videos, lookback_days)

        # 6. Statistiken berechnen
        statistics = self._calculate_statistics(filtered_videos)

        # 7. Zeitraum bestimmen
        if filtered_videos:
            dates = [
                datetime.fromisoformat(v['published_at'].replace('Z', '+00:00'))
                for v in filtered_videos
            ]
            start_date = min(dates).strftime('%Y-%m-%d')
            end_date = max(dates).strftime('%Y-%m-%d')
        else:
            start_date = end_date = None

        # Quota-Verbrauch berechnen
        quota_used = self.quota_tracker.get_used() - quota_start

        return {
            'channel': {
                'id': channel_info['channel_id'],
                'title': channel_info['title'],
                'description': channel_info['description'],
                'created_at': channel_info['created_at'],
                'subscribers': channel_info['subscriber_count'],
                'total_videos': channel_info['video_count'],
                'total_views': channel_info['view_count']
            },
            'analysis_period': {
                'lookback_days': lookback_days,
                'start': start_date,
                'end': end_date,
                'videos_analyzed': len(filtered_videos),
                'videos_total': len(all_videos)
            },
            'videos': filtered_videos,
            'statistics': statistics,
            'meta': {
                'fetched_at': datetime.now(pytz.UTC).isoformat(),
                'quota_used': quota_used,
                'quota_remaining': self.quota_tracker.get_remaining()
            }
        }

    def estimate_quota_cost(
        self,
        identifier: str,
        lookback_days: int = 90,
        max_videos: Optional[int] = None
    ) -> dict:
        """
        Schätzt Quota-Kosten für eine Kanal-Analyse

        Args:
            identifier: Channel-ID, @handle, oder URL
            lookback_days: Zeitraum in Tagen
            max_videos: Optional - Maximale Anzahl Videos

        Returns:
            Dictionary mit Kosten-Schätzung
        """
        # Basis-Kosten
        costs = {
            'channel_id_resolution': 1 if identifier.startswith('@') else 0,
            'channel_info': 1,
            'playlist_items': 0,
            'video_details': 0,
            'total': 0
        }

        # Schätzung basierend auf max_videos oder typischer Kanal-Größe
        estimated_videos = max_videos if max_videos else 500  # Annahme

        # Playlist Items: 1 Unit pro 50 Videos
        costs['playlist_items'] = (estimated_videos + 49) // 50

        # Video Details: 1 Unit pro 50 Videos
        costs['video_details'] = (estimated_videos + 49) // 50

        costs['total'] = sum(costs.values())

        return costs
