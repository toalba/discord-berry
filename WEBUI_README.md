# Tournament Configuration Web Interface

## Überblick

Das Webinterface ermöglicht die flexible Konfiguration von Turnieren mit verschiedenen Stages und individuellen Regeln pro Stage.

## Webinterface starten

```bash
source venv/bin/activate
python webui.py
```

Das Interface ist dann unter http://localhost:5000 erreichbar.

## Features

### Tournament Management
- Erstellen mehrerer Tournaments mit eindeutiger ID
- Jedes Tournament hat eigenen Mappool und Stage-Konfigurationen
- Löschen einzelner Tournaments

### Mappool-Konfiguration
- Maps zum Pool hinzufügen/entfernen
- Einfache Tag-basierte Verwaltung

### Stage-Konfiguration
Jede Stage kann individuell konfiguriert werden:
- **Map Bans**: Anzahl Maps die jedes Team bannen darf
- **Map Picks**: Anzahl Maps die jedes Team pickt
- **Ship Bans**: Anzahl Ships die jedes Team bannen muss
- **Tiebreaker**: Optional mit konfigurierbaren Tiebreaker-Maps

### Beispiel-Tournament

Die Datei `tournament_config.json` enthält bereits ein Beispiel-Tournament mit 4 Stages:

```
Group
  └─ 1 Ship Ban each

2nd Group Stage
  └─ 1 Map pick each
  └─ Tiebreaker (Riposte, Ocean)
  └─ 2 Ship bans each

KO Stage
  └─ 1 Map pick each
  └─ Tiebreaker (Riposte, Ocean)
  └─ 3 Ship bans each

Final
  └─ 1 Map ban each
  └─ 2 Map picks each
  └─ Tiebreaker (Riposte, Ocean)
  └─ 4 Ship bans each
```

## Bot-Integration

### Pick&Ban Command

Der `/pick_ban` Command verwendet jetzt Autocomplete für Tournament und Stage-Auswahl:

```
/pick_ban rep_a:@Captain1 rep_b:@Captain2 tournament_id:example_tournament stage_name:"KO Stage"
```

### Workflow

1. Webinterface: Tournament und Stages konfigurieren
2. Discord: `/pick_ban` Command mit gewünschtem Tournament/Stage ausführen
3. Bot folgt automatisch den konfigurierten Regeln für diese Stage

## Konfigurationsdatei

`tournament_config.json` wird automatisch beim Speichern aktualisiert. Format:

```json
{
  "tournaments": [
    {
      "id": "tournament_id",
      "name": "Tournament Name",
      "mappool": ["Map1", "Map2", ...],
      "stages": {
        "Stage Name": {
          "map_bans": 0,
          "map_picks": 1,
          "ship_bans": 2,
          "has_tiebreaker": true,
          "tiebreaker_maps": ["Map1", "Map2"]
        }
      }
    }
  ]
}
```

## Production Deployment

Für Production-Einsatz sollte ein WSGI-Server wie Gunicorn verwendet werden:

```bash
pip install gunicorn
gunicorn -w 4 -b 0.0.0.0:5000 webui:app
```

Oder als systemd service mit nginx als Reverse Proxy.

## Hinweise

- Der Bot liest die Config bei jedem `/pick_ban` Command neu ein
- Änderungen im Webinterface werden sofort aktiv
- Tournament-IDs müssen eindeutig sein (lowercase, keine Leerzeichen)
- Stage-Namen sind frei wählbar und werden im Bot angezeigt
