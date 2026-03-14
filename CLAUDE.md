# YouTube Channel Investigator

## Projektübersicht

Python-CLI-App für investigative YouTube-Kanal-Analysen mit intelligentem Quota-Management. Ermöglicht systematische Datenextraktion für Recherchen (Kanal-Vergleiche, Reichweiten-Analysen, zeitliche Entwicklungen).

**Detaillierte Spezifikation:** siehe `SPEC.md`

## Technische Kernentscheidungen

### YouTube API Optimierung
- **Nutze den Playlist-Trick:** Statt `search.list` (100 Units) → `playlistItems.list` (1 Unit) via Upload-Playlist
- Batch-Requests: Max 50 Video-IDs pro `videos.list` Call
- Quota-Budget: 10.000 Units/Tag, Reset um 09:00 MEZ (Mitternacht PT)

### Stack
- Python 3.11+
- `google-api-python-client` für YouTube API
- `click` für CLI
- `rich` für Terminal-UI und Progress
- `sqlite3` für Queue und Cache (kein ORM nötig)
- `python-dotenv` für API-Key

### Architektur-Prinzipien
- Quota-Verbrauch vor jedem API-Call prüfen und tracken
- Alle API-Responses in SQLite cachen
- Batch-Processing mit konfigurierbarer Größe
- Graceful degradation bei Quota-Erschöpfung

## Entwicklungshinweise

### API-Key
```bash
# .env Datei im Projektroot
YOUTUBE_API_KEY=AIza...
```

### Wichtige Quota-Kosten
| Endpoint | Cost |
|----------|------|
| channels.list | 1 |
| playlistItems.list | 1 |
| videos.list | 1 |
| search.list | 100 ⚠️ vermeiden! |

### PT-Timezone für Reset
```python
from datetime import datetime
import pytz
pt = pytz.timezone('US/Pacific')
now_pt = datetime.now(pt)
```

## CLI-Zielstruktur

```bash
yt-investigate channel <ID> [--days 90] [--export json|csv]
yt-investigate compare <CH1> <CH2>
yt-investigate quota status
yt-investigate queue process [--batch-size 50]
```

## Implementierungsreihenfolge

1. **Config & API-Client** - YouTube-Verbindung mit Auth
2. **Quota-Tracker** - SQLite-basiertes Tracking
3. **Channel-Fetcher** - Einzelkanal-Abfrage (Playlist-Trick)
4. **CLI Grundgerüst** - click-basiert
5. **Queue-System** - Job-Warteschlange
6. **Export-Formate** - JSON, CSV, NotebookLM-MD

## Testdaten

```
Candace Owens: @RealCandaceO oder UC...
TPUSA: @TurningPointUSA oder UC...
```

Channel-IDs können aus URLs extrahiert oder via `channels.list(forUsername=...)` aufgelöst werden.
