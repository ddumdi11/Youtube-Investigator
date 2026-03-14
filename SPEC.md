# YouTube Channel Investigator - SPEC

## Projektziel

Eine Python-CLI-App für investigative Analysen von YouTube-Kanälen mit intelligentem Quota-Management. Ermöglicht systematische Datenextraktion für Recherchen wie Kanal-Vergleiche, Reichweiten-Analysen und zeitliche Entwicklungen.

## Beispiel-Use-Case

**Konfliktanalyse Candace Owens vs. TPUSA:**
- Kanal-Metadaten: Erstellungsdatum, Abonnentenzahl
- Video-Performance: Views der letzten 90 Tage
- Vergleichende Statistiken zwischen beiden Kanälen
- Export für weitere Analyse (NotebookLM, Spreadsheets)

---

## YouTube Data API v3 - Technische Grundlagen

### Quota-System
- **Tägliches Limit:** 10.000 Units (kostenlos)
- **Reset:** Mitternacht Pacific Time (PT) = 09:00 Uhr MEZ
- **Kostenpflichtige Erweiterung:** ~$0.005 pro 1.000 zusätzliche Units

### Relevante Endpoints & Kosten

| Endpoint | Quota-Kosten | Zweck |
|----------|--------------|-------|
| `channels.list` | 1 Unit | Kanal-Metadaten (Erstellungsdatum, Subscriber) |
| `search.list` | 100 Units | Video-IDs eines Kanals finden |
| `videos.list` | 1 Unit | Video-Details (Views, Likes, Datum) |
| `playlistItems.list` | 1 Unit | Videos aus Upload-Playlist (effizienter!) |

### Optimierte Abfrage-Strategie

**Ineffizient (teuer):**
```
search.list → 100 Units pro 50 Videos
```

**Effizient (günstig):**
```
channels.list (contentDetails) → Upload-Playlist-ID holen (1 Unit)
playlistItems.list → Video-IDs aus Playlist (1 Unit pro 50 Videos)
videos.list → Details für bis zu 50 Videos (1 Unit)
```

**Kosten-Beispiel für 200 Videos eines Kanals:**
- Ineffizient: 400 Units (4x search.list)
- Effizient: 1 + 4 + 4 = 9 Units

---

## Architektur

```
youtube-investigator/
├── src/
│   ├── __init__.py
│   ├── main.py                 # CLI Entry Point
│   ├── config.py               # Settings, API-Key Management
│   │
│   ├── api/
│   │   ├── __init__.py
│   │   ├── youtube_client.py   # API-Wrapper mit Retry-Logic
│   │   └── endpoints.py        # Endpoint-spezifische Methoden
│   │
│   ├── quota/
│   │   ├── __init__.py
│   │   ├── tracker.py          # Quota-Verbrauch tracken
│   │   ├── calculator.py       # Kosten pro Operation berechnen
│   │   └── scheduler.py        # Reset-Zeit, Warteschlangen-Timing
│   │
│   ├── queue/
│   │   ├── __init__.py
│   │   ├── models.py           # SQLite Models (Job, Channel, Video)
│   │   ├── manager.py          # Queue-Operationen
│   │   └── batch_processor.py  # Batch-Verarbeitung
│   │
│   ├── analysis/
│   │   ├── __init__.py
│   │   ├── channel_stats.py    # Kanal-Analyse
│   │   ├── video_stats.py      # Video-Performance
│   │   └── comparator.py       # Kanal-Vergleiche
│   │
│   └── export/
│       ├── __init__.py
│       ├── csv_export.py
│       ├── json_export.py
│       └── notebooklm_format.py  # Optimiert für NotebookLM-Import
│
├── data/
│   ├── queue.db                # SQLite Queue-Datenbank
│   └── exports/                # Generierte Reports
│
├── tests/
│   └── ...
│
├── .env.example                # API-Key Template
├── requirements.txt
└── README.md
```

---

## Datenmodelle

### SQLite Schema

```sql
-- Analyse-Jobs in der Warteschlange
CREATE TABLE jobs (
    id INTEGER PRIMARY KEY,
    job_type TEXT NOT NULL,           -- 'channel_meta', 'channel_videos', 'video_stats'
    target_id TEXT NOT NULL,          -- Channel-ID oder Video-ID
    status TEXT DEFAULT 'pending',    -- 'pending', 'processing', 'completed', 'failed'
    priority INTEGER DEFAULT 0,
    estimated_quota INTEGER,
    actual_quota INTEGER,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    processed_at TIMESTAMP,
    error_message TEXT
);

-- Gecachte Kanal-Daten
CREATE TABLE channels (
    channel_id TEXT PRIMARY KEY,
    title TEXT,
    description TEXT,
    created_at TEXT,                  -- ISO-Datum der Kanal-Erstellung
    subscriber_count INTEGER,
    video_count INTEGER,
    view_count INTEGER,               -- Gesamt-Views
    uploads_playlist_id TEXT,
    fetched_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Gecachte Video-Daten
CREATE TABLE videos (
    video_id TEXT PRIMARY KEY,
    channel_id TEXT,
    title TEXT,
    published_at TEXT,
    view_count INTEGER,
    like_count INTEGER,
    comment_count INTEGER,
    duration TEXT,                    -- ISO 8601 Duration
    fetched_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (channel_id) REFERENCES channels(channel_id)
);

-- Quota-Tracking
CREATE TABLE quota_log (
    id INTEGER PRIMARY KEY,
    date TEXT NOT NULL,               -- YYYY-MM-DD in PT
    units_used INTEGER DEFAULT 0,
    units_limit INTEGER DEFAULT 10000,
    last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

---

## Core Features

### 1. Quota Manager

```python
class QuotaManager:
    """
    Zentrale Quota-Verwaltung mit Echtzeit-Tracking
    """
    
    DAILY_LIMIT = 10_000
    WARNING_THRESHOLD = 0.80  # Warnung bei 80%
    
    def get_remaining(self) -> int:
        """Verbleibende Units für heute (PT)"""
        
    def can_afford(self, cost: int) -> bool:
        """Prüft ob Operation möglich ohne Limit zu überschreiten"""
        
    def consume(self, cost: int, operation: str) -> None:
        """Bucht Units und loggt Operation"""
        
    def time_until_reset(self) -> timedelta:
        """Zeit bis Mitternacht PT"""
        
    def estimate_job_cost(self, job: Job) -> int:
        """Schätzt Quota-Kosten für einen Job"""
```

### 2. Queue Manager

```python
class QueueManager:
    """
    Warteschlangen-Verwaltung mit Prioritäten
    """
    
    def add_channel_analysis(
        self, 
        channel_id: str, 
        include_videos: bool = True,
        video_lookback_days: int = 90,
        priority: int = 0
    ) -> Job:
        """Fügt Kanal-Analyse zur Queue hinzu"""
        
    def add_video_batch(
        self, 
        video_ids: list[str],
        priority: int = 0
    ) -> list[Job]:
        """Fügt Video-Batch zur Queue hinzu"""
        
    def get_next_batch(self, max_quota: int) -> list[Job]:
        """Holt nächste Jobs die ins Budget passen"""
        
    def process_queue(
        self,
        batch_size: int = 50,
        stop_at_threshold: bool = True
    ) -> ProcessingResult:
        """Verarbeitet Queue bis Quota erschöpft oder Threshold erreicht"""
```

### 3. Batch Processor

```python
class BatchProcessor:
    """
    Effiziente Batch-Verarbeitung mit Rate-Limiting
    """
    
    def __init__(
        self,
        batch_size: int = 50,           # Max Videos pro API-Call
        requests_per_second: float = 3,  # Rate Limit
        retry_count: int = 3
    ):
        pass
    
    def process_channel(self, channel_id: str) -> ChannelResult:
        """
        Vollständige Kanal-Analyse:
        1. Kanal-Metadaten
        2. Upload-Playlist-ID
        3. Video-IDs der letzten X Tage
        4. Video-Statistiken in Batches
        """
        
    def process_videos(self, video_ids: list[str]) -> list[VideoResult]:
        """Batch-Verarbeitung von Video-IDs"""
```

---

## CLI Interface

```bash
# Basis-Kommandos
yt-investigate channel <CHANNEL_ID_OR_URL> [--days 90] [--export csv|json]
yt-investigate compare <CHANNEL_1> <CHANNEL_2> [--days 90]
yt-investigate video <VIDEO_ID_OR_URL>
yt-investigate batch <FILE_WITH_IDS>

# Queue-Management
yt-investigate queue add <CHANNEL_ID> [--priority high|normal|low]
yt-investigate queue list
yt-investigate queue process [--batch-size 50] [--stop-at 80%]
yt-investigate queue clear

# Quota-Status
yt-investigate quota status
yt-investigate quota history [--days 7]
yt-investigate quota estimate <CHANNEL_ID>

# Export
yt-investigate export <CHANNEL_ID> --format notebooklm
yt-investigate export compare <CH1> <CH2> --format csv
```

---

## Output-Formate

### Channel Report (JSON)

```json
{
  "channel": {
    "id": "UC...",
    "title": "Candace Owens",
    "created_at": "2015-09-22",
    "subscribers": 5650000,
    "total_videos": 1234,
    "total_views": 890000000
  },
  "analysis_period": {
    "start": "2025-09-01",
    "end": "2025-12-01",
    "days": 90
  },
  "videos": [
    {
      "id": "abc123",
      "title": "...",
      "published_at": "2025-11-15",
      "views": 2100000,
      "likes": 95000,
      "comments": 12000
    }
  ],
  "statistics": {
    "videos_in_period": 45,
    "total_views": 48000000,
    "avg_views_per_video": 1066667,
    "median_views": 890000,
    "max_views": 2100000,
    "min_views": 320000
  },
  "fetched_at": "2025-12-07T14:30:00Z",
  "quota_used": 47
}
```

### Comparison Report (CSV)

```csv
metric,candace_owens,tpusa,difference,ratio
channel_created,2015-09-22,2012-12-01,-,-
subscribers,5650000,4700000,+950000,1.20
videos_90d,45,120,-75,0.38
total_views_90d,48000000,93600000,-45600000,0.51
avg_views_per_video,1066667,780000,+286667,1.37
median_views,890000,450000,+440000,1.98
engagement_rate,4.2%,2.1%,+2.1%,2.00
```

### NotebookLM-Format (Markdown)

```markdown
# YouTube Channel Analysis: Candace Owens

## Channel Overview
- **Created:** September 22, 2015
- **Subscribers:** 5.65 million
- **Analysis Period:** September 1 - December 1, 2025

## Performance Summary (Last 90 Days)
The channel published 45 videos with a combined 48 million views.
Average views per video: 1.07 million. Highest performing video 
reached 2.1 million views.

## Video Performance Data
[Structured table of all videos with dates, views, engagement]

## Comparative Context
[If comparison data available]
```

---

## Implementierungs-Phasen

### Phase 1: Core (MVP)
- [ ] YouTube API Client mit Auth
- [ ] Quota Tracker (SQLite)
- [ ] Einzelne Kanal-Abfrage
- [ ] JSON Export

### Phase 2: Queue System
- [ ] Job Queue mit SQLite
- [ ] Batch Processing
- [ ] Quota-Warnings
- [ ] CLI Interface

### Phase 3: Analysis & Export
- [ ] Kanal-Vergleiche
- [ ] Zeitraum-Filter
- [ ] CSV Export
- [ ] NotebookLM Format

### Phase 4: Polish
- [ ] Rate Limiting
- [ ] Retry Logic
- [ ] Progress Bars
- [ ] Caching

---

## Setup-Anforderungen

### API-Key einrichten

1. Google Cloud Console → Neues Projekt
2. YouTube Data API v3 aktivieren
3. API-Key erstellen (keine OAuth nötig für öffentliche Daten)
4. Key in `.env` speichern:
   ```
   YOUTUBE_API_KEY=AIza...
   ```

### Dependencies

```
google-api-python-client>=2.0
python-dotenv>=1.0
click>=8.0          # CLI Framework
rich>=13.0          # Terminal UI, Progress Bars
sqlite-utils>=3.0   # SQLite Helper
httpx>=0.25         # Async HTTP (optional)
```

---

## Notizen

- **Caching:** Kanal-Metadaten ändern sich selten → Cache 24h
- **Video-Stats:** Views ändern sich → Cache max 1h für neue Videos
- **Playlist-Trick:** `uploads` Playlist ist günstiger als Search
- **Batch-Limit:** Max 50 Video-IDs pro `videos.list` Request
- **PT-Timezone:** `pytz.timezone('US/Pacific')` für Reset-Berechnung
