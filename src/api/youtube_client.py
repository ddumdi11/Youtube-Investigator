"""
YouTube API Client - Wrapper für YouTube Data API v3
"""
from typing import Optional
import time
import re
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

from src.config import config
from src.quota.tracker import QuotaTracker


class YouTubeClient:
    """
    Wrapper für YouTube Data API v3 mit automatischem Quota-Tracking
    """

    # Quota-Kosten pro Endpoint (laut YouTube API Dokumentation)
    QUOTA_COSTS = {
        'channels.list': 1,
        'videos.list': 1,
        'playlistItems.list': 1,
        'search.list': 100,
    }

    def __init__(
        self,
        api_key: Optional[str] = None,
        quota_tracker: Optional[QuotaTracker] = None
    ):
        """
        Initialisiert YouTube API Client

        Args:
            api_key: YouTube API Key (optional, wird aus config geladen)
            quota_tracker: QuotaTracker Instanz (optional)
        """
        self.api_key = api_key or config.YOUTUBE_API_KEY

        if not self.api_key:
            raise ValueError(
                "YouTube API Key fehlt! "
                "Bitte YOUTUBE_API_KEY in .env setzen."
            )

        self.youtube = build('youtube', 'v3', developerKey=self.api_key)
        self.quota_tracker = quota_tracker or QuotaTracker()
        self.retry_count = config.RETRY_COUNT
        self.retry_delay = config.RETRY_DELAY

    def _execute_with_retry(self, request, operation: str, quota_cost: int):
        """
        Führt API-Request mit Retry-Logic aus

        Args:
            request: YouTube API Request Objekt
            operation: Name der Operation für Logging
            quota_cost: Quota-Kosten der Operation

        Returns:
            API Response

        Raises:
            HttpError: Bei API-Fehlern nach allen Retries
        """
        # Quota-Check vor Request
        if not self.quota_tracker.can_afford(quota_cost):
            raise ValueError(
                f"Nicht genug Quota für {operation}! "
                f"Benötigt: {quota_cost}, "
                f"Verfügbar: {self.quota_tracker.get_remaining()}"
            )

        # API Call mit Retries
        for attempt in range(self.retry_count):
            try:
                response = request.execute()

                # Quota buchen bei Erfolg
                self.quota_tracker.consume(quota_cost, operation)

                return response

            except HttpError as e:
                if e.resp.status in [403, 429]:  # Rate limit oder Quota exceeded
                    if attempt < self.retry_count - 1:
                        wait_time = self.retry_delay * (2 ** attempt)  # Exponential backoff
                        print(f"⏳ Rate limit erreicht, warte {wait_time}s...")
                        time.sleep(wait_time)
                    else:
                        raise
                else:
                    raise

    def get_channel_info(self, channel_id: str) -> dict:
        """
        Holt Kanal-Metadaten

        Args:
            channel_id: YouTube Channel ID

        Returns:
            Dictionary mit Kanal-Informationen
        """
        request = self.youtube.channels().list(
            part='snippet,statistics,contentDetails',
            id=channel_id
        )

        response = self._execute_with_retry(
            request,
            f'channels.list({channel_id})',
            self.QUOTA_COSTS['channels.list']
        )

        if not response.get('items'):
            raise ValueError(f"Kanal {channel_id} nicht gefunden")

        item = response['items'][0]

        return {
            'channel_id': channel_id,
            'title': item['snippet']['title'],
            'description': item['snippet']['description'],
            'created_at': item['snippet']['publishedAt'],
            'subscriber_count': int(item['statistics'].get('subscriberCount', 0)),
            'video_count': int(item['statistics'].get('videoCount', 0)),
            'view_count': int(item['statistics'].get('viewCount', 0)),
            'uploads_playlist_id': item['contentDetails']['relatedPlaylists']['uploads']
        }

    def get_videos_info(self, video_ids: list[str]) -> list[dict]:
        """
        Holt Video-Statistiken (bis zu 50 Videos pro Call)

        Args:
            video_ids: Liste von Video IDs

        Returns:
            Liste von Video-Informationen
        """
        if len(video_ids) > 50:
            raise ValueError("Maximal 50 Video-IDs pro Request erlaubt")

        request = self.youtube.videos().list(
            part='snippet,statistics,contentDetails',
            id=','.join(video_ids)
        )

        response = self._execute_with_retry(
            request,
            f'videos.list({len(video_ids)} videos)',
            self.QUOTA_COSTS['videos.list']
        )

        videos = []
        for item in response.get('items', []):
            videos.append({
                'video_id': item['id'],
                'channel_id': item['snippet']['channelId'],
                'title': item['snippet']['title'],
                'published_at': item['snippet']['publishedAt'],
                'view_count': int(item['statistics'].get('viewCount', 0)),
                'like_count': int(item['statistics'].get('likeCount', 0)),
                'comment_count': int(item['statistics'].get('commentCount', 0)),
                'duration': item['contentDetails']['duration']
            })

        return videos

    def resolve_channel_id(self, identifier: str) -> str:
        """
        Konvertiert Channel-Handle (@username) oder URL zu Channel-ID

        Args:
            identifier: Channel-ID, @handle, oder YouTube URL

        Returns:
            Channel-ID (UC...)

        Raises:
            ValueError: Wenn Kanal nicht gefunden wird
        """
        # Bereits eine Channel-ID (UC...)
        if identifier.startswith('UC'):
            return identifier

        # Handle (@username)
        if identifier.startswith('@'):
            request = self.youtube.channels().list(
                part='id',
                forHandle=identifier[1:]  # Ohne @
            )

            response = self._execute_with_retry(
                request,
                f'channels.list(forHandle={identifier})',
                self.QUOTA_COSTS['channels.list']
            )

            if response.get('items'):
                return response['items'][0]['id']
            else:
                raise ValueError(f"Kanal mit Handle {identifier} nicht gefunden")

        # URL-Parsing
        # Muster: youtube.com/channel/UC..., youtube.com/@handle, youtube.com/c/customname
        url_patterns = [
            r'youtube\.com/channel/(UC[\w-]+)',
            r'youtube\.com/@([\w-]+)',
            r'youtube\.com/c/([\w-]+)',
            r'youtube\.com/user/([\w-]+)',
        ]

        for pattern in url_patterns:
            match = re.search(pattern, identifier)
            if match:
                extracted = match.group(1)
                if extracted.startswith('UC'):
                    return extracted
                else:
                    # Rekursiv mit @ oder custom name
                    return self.resolve_channel_id(f'@{extracted}')

        # Als letztes: Versuche es als Custom URL/Username
        return self.resolve_channel_id(f'@{identifier}')

    def get_playlist_videos(
        self,
        playlist_id: str,
        max_results: Optional[int] = None
    ) -> list[str]:
        """
        Holt alle Video-IDs aus einer Playlist (z.B. uploads)

        Args:
            playlist_id: YouTube Playlist ID
            max_results: Optional - Maximale Anzahl Videos

        Returns:
            Liste von Video-IDs
        """
        video_ids = []
        next_page_token = None

        while True:
            request = self.youtube.playlistItems().list(
                part='contentDetails',
                playlistId=playlist_id,
                maxResults=50,  # API Maximum
                pageToken=next_page_token
            )

            response = self._execute_with_retry(
                request,
                f'playlistItems.list({playlist_id})',
                self.QUOTA_COSTS['playlistItems.list']
            )

            # Video-IDs extrahieren
            for item in response.get('items', []):
                video_ids.append(item['contentDetails']['videoId'])

            # Prüfe ob max_results erreicht
            if max_results and len(video_ids) >= max_results:
                return video_ids[:max_results]

            # Nächste Seite?
            next_page_token = response.get('nextPageToken')
            if not next_page_token:
                break

        return video_ids

    def get_videos_batch(self, video_ids: list[str]) -> list[dict]:
        """
        Holt Video-Statistiken in Batches (50er Gruppen)

        Args:
            video_ids: Liste von Video IDs

        Returns:
            Liste von Video-Informationen
        """
        all_videos = []
        batch_size = 50

        for i in range(0, len(video_ids), batch_size):
            batch = video_ids[i:i + batch_size]
            videos = self.get_videos_info(batch)
            all_videos.extend(videos)

            # Rate limiting
            if i + batch_size < len(video_ids):
                time.sleep(1 / config.REQUESTS_PER_SECOND)

        return all_videos

    def test_connection(self) -> bool:
        """
        Testet ob API-Key funktioniert

        Returns:
            True bei Erfolg, False bei Fehler
        """
        try:
            # Einfacher Test-Request (sehr günstig)
            request = self.youtube.channels().list(
                part='snippet',
                id='UC_x5XG1OV2P6uZZ5FSM9Ttw'  # Google Developers Channel
            )
            request.execute()
            return True
        except Exception as e:
            print(f"[X] API-Verbindung fehlgeschlagen: {e}")
            return False
