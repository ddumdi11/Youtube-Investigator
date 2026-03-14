# YouTube Channel Investigator

Eine Python-CLI-App für investigative Analysen von YouTube-Kanälen mit intelligentem Quota-Management.

## Status: Phase 2 - Channel Analyzer ✓

Phase 1 & 2 sind abgeschlossen! Folgende Features sind implementiert:

### Phase 1 (MVP)
- ✅ YouTube API Client mit Authentifizierung
- ✅ Quota Tracker mit SQLite-Persistenz
- ✅ Funktionierende CLI mit Click
- ✅ `yt-investigate quota status` Befehl

### Phase 2 (Channel Analyzer)
- ✅ Channel-ID Resolver (@handle, URLs, IDs)
- ✅ Playlist-Trick für effiziente Video-Abfrage
- ✅ Batch Video Processing
- ✅ Zeitraum-Filter (letzte X Tage)
- ✅ Statistik-Berechnungen (Views, Engagement, etc.)
- ✅ JSON Export
- ✅ `yt-investigate channel` Befehl
- ✅ `yt-investigate quota estimate` Befehl

## Installation

### 1. Repository klonen und Setup

```bash
# In das Projekt-Verzeichnis wechseln
cd Youtube_Investigator

# Virtual Environment ist bereits erstellt
# Falls nicht: py -m venv venv

# Dependencies installieren (im venv)
venv/Scripts/python.exe -m pip install -e .
```

### 2. YouTube API Key einrichten

1. Gehe zur [Google Cloud Console](https://console.cloud.google.com/)
2. Erstelle ein neues Projekt (oder wähle ein bestehendes)
3. Aktiviere die **YouTube Data API v3**
4. Erstelle einen API-Key (Credentials → Create Credentials → API Key)
5. Erstelle eine `.env` Datei im Projekt-Root:

```bash
cp .env.example .env
```

6. Füge deinen API-Key in die `.env` Datei ein:

```
YOUTUBE_API_KEY=AIza...dein-key-hier
```

## Verwendung

### Kanal analysieren (NEU in Phase 2!)

```bash
# Mit Channel-Handle (@username)
venv/Scripts/yt-investigate.exe channel @RealCandaceO

# Mit Zeitraum-Filter
venv/Scripts/yt-investigate.exe channel @TurningPointUSA --days 30

# Mit Export zu JSON-Datei
venv/Scripts/yt-investigate.exe channel @RealCandaceO --export json

# Mit begrenzter Anzahl Videos (für Tests)
venv/Scripts/yt-investigate.exe channel @RealCandaceO --max-videos 50
```

**Ausgabe:**
- Kanal-Metadaten (Abonnenten, Gesamt-Videos, etc.)
- Video-Statistiken im Zeitraum
- Durchschnittliche Views, Median, Max/Min
- Engagement Rate (Likes + Comments / Views)
- JSON-Zusammenfassung
- Quota-Verbrauch

**Identifier-Formate:**
- `@username` - Channel-Handle (z.B. @RealCandaceO)
- `UCxxx...` - Channel-ID
- `https://youtube.com/@username` - YouTube URL
- `https://youtube.com/channel/UCxxx...` - Channel URL

### Quota-Kosten schätzen

```bash
venv/Scripts/yt-investigate.exe quota estimate @RealCandaceO
venv/Scripts/yt-investigate.exe quota estimate @TurningPointUSA --max-videos 100
```

Zeigt voraussichtliche Quota-Kosten bevor die Analyse gestartet wird.

### Quota Status anzeigen

```bash
venv/Scripts/yt-investigate.exe quota status
```

Zeigt den aktuellen Quota-Verbrauch:
- Verbrauchte Units heute
- Verbleibende Units
- Zeit bis zum Reset (Mitternacht Pacific Time)
- Farbcodierte Warnung bei hohem Verbrauch

### API-Verbindung testen

```bash
venv/Scripts/yt-investigate.exe test
```

Testet:
- Konfiguration (API-Key vorhanden)
- YouTube API Verbindung
- Quota-Tracker Funktionalität

### Hilfe anzeigen

```bash
venv/Scripts/yt-investigate.exe --help
venv/Scripts/yt-investigate.exe channel --help
venv/Scripts/yt-investigate.exe quota --help
```

## Projektstruktur

```
youtube-investigator/
├── src/
│   ├── main.py                 # CLI Entry Point
│   ├── config.py               # Konfiguration & API-Key Management
│   ├── api/
│   │   ├── youtube_client.py   # YouTube API Wrapper (Phase 1 & 2)
│   │   └── __init__.py
│   ├── quota/
│   │   ├── tracker.py          # Quota-Tracking mit SQLite
│   │   └── __init__.py
│   ├── analysis/
│   │   ├── channel_stats.py    # Kanal-Analyse (Phase 2)
│   │   └── __init__.py
│   └── export/
│       ├── json_export.py      # JSON Export (Phase 2)
│       └── __init__.py
├── data/
│   ├── queue.db                # SQLite Datenbank (automatisch erstellt)
│   └── exports/                # JSON Exports
├── venv/                       # Virtual Environment
├── .env                        # API-Keys (nicht in Git!)
├── .env.example                # Template für .env
├── requirements.txt            # Python Dependencies
├── setup.py                    # Package Setup
└── README.md                   # Diese Datei
```

## Quota-System verstehen

YouTube API v3 hat ein tägliches Quota-Limit:
- **Limit:** 10.000 Units pro Tag (kostenlos)
- **Reset:** Mitternacht Pacific Time (PT) = 09:00 Uhr MEZ
- **Warnung:** Bei 80% Verbrauch (8.000 Units)

### Quota-Kosten pro Endpoint

| Endpoint | Kosten | Verwendung |
|----------|--------|------------|
| `channels.list` | 1 Unit | Kanal-Metadaten |
| `videos.list` | 1 Unit | Video-Details |
| `playlistItems.list` | 1 Unit | Videos aus Playlist |
| `search.list` | 100 Units | Video-Suche (teuer!) |

### Der Playlist-Trick (Quota-Optimierung)

Unser Tool verwendet einen intelligenten Ansatz, um Quota-Kosten zu minimieren:

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

**Kosten-Beispiel für 200 Videos:**
- ❌ Ineffizient: 400 Units (4x search.list)
- ✅ Effizient: 1 + 4 + 4 = **9 Units** (44x günstiger!)

## Beispiel-Analyse

### Candace Owens Kanal

```bash
yt-investigate channel @RealCandaceO --days 90
```

**Typische Ausgabe:**
- Kanal-Info: 5.65M Abonnenten, 1234 Videos
- Videos im Zeitraum: 45 Videos
- Gesamt-Views (90 Tage): 48M
- Durchschnitt: 1.07M Views/Video
- Engagement Rate: 4.2%
- **Quota verwendet: ~9 Units** (für 45 Videos)

### Vergleich zweier Kanäle

```bash
yt-investigate channel @RealCandaceO --days 90 --export json
yt-investigate channel @TurningPointUSA --days 90 --export json
```

Beide Analysen zusammen: ~18 Units (unter 0.2% des Tages-Limits!)

## Nächste Schritte (Phase 3)

Die folgenden Features sind geplant für Phase 3:

- [ ] Job Queue System mit SQLite
- [ ] Kanal-Vergleiche (direkt im CLI)
- [ ] CSV Export
- [ ] NotebookLM-Format Export
- [ ] Video-Trending-Analyse

Siehe [YouTube-Investigator-SPEC.md](YouTube-Investigator-SPEC.md) für die vollständige Roadmap.

## Entwicklung

### Projekt im Development-Modus installieren

```bash
venv/Scripts/python.exe -m pip install -e .
```

Dies installiert das Package im "editable" Modus - Änderungen am Code sind sofort verfügbar.

### Tests ausführen

```bash
venv/Scripts/yt-investigate.exe test
```

## Technologie-Stack

- **Python 3.11+**
- **Click** - CLI Framework
- **Rich** - Terminal UI & Formatierung
- **google-api-python-client** - YouTube API Client
- **SQLite** - Datenbank für Quota-Tracking & Queue
- **python-dotenv** - Environment Variables
- **pytz** - Timezone-Handling (Pacific Time)

## Troubleshooting

### "YOUTUBE_API_KEY nicht gefunden"

Stelle sicher, dass:
1. Die `.env` Datei im Projekt-Root existiert
2. Der API-Key korrekt in der `.env` Datei steht
3. Der API-Key mit `YOUTUBE_API_KEY=` beginnt (kein Leerzeichen!)

### Unicode-Fehler auf Windows

Die App verwendet ASCII-Zeichen statt Emojis, um Kompatibilität mit Windows-Terminals zu gewährleisten.

### API-Quota überschritten

Wenn du das Tages-Limit erreichst:
1. Warte bis Mitternacht PT (09:00 MEZ)
2. Oder aktiviere kostenpflichtige Quota-Erweiterung in Google Cloud Console

## Lizenz

Dieses Projekt ist für Recherche- und Analyse-Zwecke gedacht. Bitte beachte die YouTube API Terms of Service.

## Autor

YouTube Investigator Team

---

**Hinweis:** Dies ist Phase 1 (MVP). Weitere Features folgen in den nächsten Phasen!
