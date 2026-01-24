# Discord-Berry AI Coding Agent Instructions

## Project Overview
Discord bot für World of Warships Turniere mit Pick & Ban-System. Der Bot koordiniert Map-Auswahl und -Verbote zwischen Team-Captains über Discord-DMs. Unterstützt flexible Tournament-Konfigurationen über Webinterface.

## Architecture & Core Components

### Bot Structure (`src/bot.py`)
- **Blarry**: Hauptklasse (extends `discord.ext.commands.Bot`)
  - Verwaltet aktive Pick&Ban-Sitzungen in `self.pick_bans` Liste
  - Globale Command-Sync bei Bot-Start (`setup_hook`)
  - Cleanup-Logik für graceful shutdown (löscht Messages, schließt aiohttp-Sessions)
  - Autocomplete für Tournament/Stage-Auswahl aus `tournament_config.json`

### State Management (`src/pickandban.py`)
- **PickandBan**: Zustandsmaschine für jede Turnier-Match-Session
  - Verwendet UUID zur eindeutigen Identifikation (`self.uid`)
  - Lädt Tournament-Config dynamisch via `tournament_id` und `stage_name`
  - Drei parallele Embeds: Original-Interaction + DMs zu beiden Team-Reps
  - Stage-basierter Workflow: Map-Ban → Map-Pick → Spawn-Pick → Ship-Ban (config-basiert)
  - `current_picker` rotiert zwischen `rep_a.id` und `rep_b.id`

### Tournament Configuration System
- **tournament_config.json**: Zentrale Konfigurationsdatei
  - Mehrere Tournaments mit eigenem Mappool und Stages
  - Stage-Konfiguration: `map_bans`, `map_picks`, `ship_bans`, `has_tiebreaker`, `tiebreaker_maps`
  - Bot lädt Config bei jedem `/pick_ban` Command neu (hot-reload)
- **webui.py**: Flask-basiertes Webinterface (Port 5000)
  - CRUD-Operationen für Tournaments und Stages
  - Mappool-Management
  - REST-API für Config-Updates

### Discord UI Pattern
Alle UI-Komponenten folgen diesem Muster:
```python
# View hält Select/Buttons, wird als Message mit view= Parameter gesendet
# Callback überprüft interaction.user.id gegen erlaubte Picker
# Nach Aktion: view.delete() + nächstes UI senden + update_embed()
```

### Critical Data Flow
1. `/pick_ban` Command mit `tournament_id` + `stage_name` → PickandBan-Instanz → `client.add_pb(pb)`
2. `start_rep_conversation()` sendet DMs mit initialen Views (Map-Ban oder Map-Pick, je nach Config)
3. User-Interaktionen triggern Callbacks → State-Update → `update_embed()` für alle 3 Embeds
4. `/remove_pb` Command → `client.remove_pb(uuid)` → Cleanup aller Messages

## Configuration Files

### Environment Variables (`.env`)
```bash
TOKEN=<discord_bot_token>
WEBHOOK=<discord_webhook_url_for_logging>
# DC-GUILD removed in multi-server migration
```

### Data Files
- **tournament_config.json**: Tournament-Konfigurationen mit Stages und Mappools (siehe `WEBUI_README.md`)
- **mappool.json**: Legacy fallback, wird nicht mehr aktiv genutzt
- **mappool_epi.json**: Alternative Map-Pool-Konfiguration (veraltet)

## Development Workflows

### Running the Bot
```bash
source venv/bin/activate
python src/bot.py
```

### Running Web Interface
```bash
source venv/bin/activate
python webui.py
# Access at http://localhost:5000
```

### Deployment (systemd service)
```bash
sudo systemctl start berry.service
sudo systemctl status berry.service
sudo journalctl -u berry.service -f  # Logs
```
Service-Config: `berry.service` (WorkingDir=/root/discord-berry/)

### Dependencies
```bash
pip install -r requirements.txt
# Core: discord.py 2.5.2, aiohttp 3.11.13, python-dotenv 1.0.1, Flask 3.1.0
```

## Project-Specific Conventions

### Team Name Extraction
Teams werden aus Discord-Nicknames extrahiert: `[CLANTAG] Name` → `CLANTAG`
```python
def get_clantag(self, rep_name: str):
    return rep_name.split("[")[1].split("]")[0]
```

### Error Handling Pattern
- Verwende `asyncio.gather(..., return_exceptions=True)` für parallele Discord-API-Calls
- Logge Exceptions über `WebhookLogger` statt raise
- Graceful degradation: Ignoriere `discord.NotFound` bei Message-Deletion

### Permissions
- Commands nutzen `@app_commands.default_permissions(manage_guild=True)`
- Keine hartcodierten Role-IDs (wurde in multi-server migration entfernt)

### Logging (`src/log_webhook.py`)
- **WebhookLogger**: Lazy-initialized aiohttp.ClientSession
- Immer `await logger.log()` für wichtige Events (Fehler, P&B-Start/Ende)
- ACHTUNG: Hardcoded Webhook-URL in Code überschreibt Konstruktor-Parameter

## Tournament Configuration System Details

### Stage Config Schema
```python
{
  "map_bans": 1,        # Maps die jedes Team bannen darf
  "map_picks": 1,       # Maps die jedes Team pickt (mit Spawn-Auswahl)
  "ship_bans": 3,       # Ships die jedes Team bannen muss (Modal-Input)
  "has_tiebreaker": true,
  "tiebreaker_maps": ["Riposte", "Ocean"]  # Random pick bei Tiebreaker
}
```

### Workflow-Logik
- `map_bans == 0`: Starte direkt mit Map-Picks
- Nach allen Map-Picks: Tiebreaker (falls `has_tiebreaker == true`)
- `ship_bans == 0`: Keine Ship-Ban-Phase, Embed wird grün
- Embed zeigt "Banned Ships" Field nur wenn `ship_bans > 0`

## Known Issues & Gotchas

1. **Global Command Sync**: Kann bis zu 1 Stunde dauern (siehe `MULTI_SERVER_MIGRATION.md`)
2. **View Timeouts**: Alle Views haben `timeout=60000` (16.7 Stunden) - keine Auto-Cleanup
3. **Embed Update Race Conditions**: `update_embed()` nutzt gather() mit return_exceptions
4. **Turn Validation**: `current_picker` wird in Callbacks geprüft - wichtig bei Spawn/Map-Picks
5. **toornament_api.py**: Enthält Test-Code, keine aktive Integration in Bot
6. **Config Hot-Reload**: Bot lädt `tournament_config.json` bei jedem `/pick_ban` - kein Restart nötig

## Testing Entry Points
- `/pick_ban rep_a:@User1 rep_b:@User2 tournament_id:example_tournament stage_name:"KO Stage"` - Startet neue Session
- `/remove_pb uuid:<uuid>` - Löscht laufende Session
- `?berry` - Legacy Message-Command (nur Test-Response)
- Webinterface: http://localhost:5000 - Tournament-Konfiguration

## Multi-Server Support (seit Migration)
- Bot funktioniert auf mehreren Servern gleichzeitig
- Permissions pro Server über Discord Server Settings → Integrations konfigurierbar
- Keine guild-spezifische Konfiguration im Code nötig
