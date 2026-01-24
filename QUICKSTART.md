# Quick Start Guide - Tournament Configuration

## 🚀 Schnellstart

### 1. Webinterface starten
```bash
cd /root/discord-berry
source venv/bin/activate
python webui.py
```
→ Öffne http://localhost:5000 im Browser

### 2. Erstes Tournament erstellen

**Im Webinterface:**
1. Klick auf "Neues Tournament erstellen"
2. ID eingeben (z.B. `spring_2026`)
3. Name eingeben (z.B. "Spring Championship 2026")
4. Tournament öffnet sich automatisch

### 3. Mappool konfigurieren

**Im Tournament:**
1. Map-Name in Textfeld eingeben (z.B. "Sleeping Giant")
2. "Map hinzufügen" klicken
3. Wiederholen für alle Maps

**Beispiel-Mappool:**
- Sleeping Giant
- North
- Islands of Ice
- Warriors Path
- Tears of the Desert
- Shards
- Riposte
- Ocean

### 4. Stage konfigurieren

**Beispiel: "KO Stage"**
```
Stage Name: KO Stage
Map Bans: 0
Map Picks: 1
Ship Bans: 3
☑ Tiebreaker aktivieren
Tiebreaker Maps: Riposte, Ocean
```

**Was bedeutet das:**
- Kein Map-Ban, direkt Map-Picks
- Jedes Team pickt 1 Map (+ Spawn)
- Nach 2 Map-Picks wird Tiebreaker gezogen
- Jedes Team bannt 3 Ships (Modal-Input)

### 5. Bot Command verwenden

**In Discord:**
```
/pick_ban 
  rep_a: @Captain1
  rep_b: @Captain2
  tournament_id: spring_2026
  stage_name: KO Stage
```

Bot verwendet automatisch die konfigurierten Regeln! 🎉

## 📋 Typische Stage-Konfigurationen

### Nur Ship Bans (Group Stage)
```
map_bans: 0
map_picks: 0
ship_bans: 1
has_tiebreaker: false
```

### Standard (KO Stage)
```
map_bans: 0
map_picks: 1
ship_bans: 3
has_tiebreaker: true
tiebreaker_maps: Riposte, Ocean
```

### Final (Extended)
```
map_bans: 1
map_picks: 2
ship_bans: 4
has_tiebreaker: true
tiebreaker_maps: Riposte, Ocean
```

## 🔄 Workflow

```
Webinterface                Discord Bot
    │                           │
    ├─ Tournament erstellen     │
    ├─ Mappool setzen          │
    ├─ Stages konfigurieren    │
    │                           │
    ▼                           ▼
Config gespeichert ──────→ /pick_ban Command
tournament_config.json  ←── liest Config
    │                           │
    │                           ├─ DMs an Captains
    │                           ├─ Map Ban/Pick
    │                           ├─ Spawn Select
    │                           └─ Ship Bans
    ▼                           ▼
Änderung möglich        Session läuft
(Hot-Reload)            (folgt Config)
```

## 💡 Tipps

- **Config wird live geladen**: Änderungen sofort wirksam bei neuem `/pick_ban`
- **Stage-Namen frei wählbar**: Werden im Bot-Embed angezeigt
- **Tournament-ID wichtig**: Muss im `/pick_ban` Command exakt übereinstimmen
- **Tiebreaker-Maps**: Werden aus nicht-gebannten Maps random gezogen
- **Ship Bans = 0**: Überspringt Ship-Ban-Phase, Embed wird sofort grün

## 🛠️ Troubleshooting

**Command zeigt keine Tournaments:**
- Tournament-ID korrekt? (lowercase, keine Leerzeichen)
- `tournament_config.json` existiert?
- Bot neu starten falls Commands nicht syncen

**Stages werden nicht angezeigt:**
- Zuerst Tournament auswählen
- Autocomplete funktioniert nur mit gültiger Tournament-ID

**Map fehlt im Pick:**
- Mappool in Tournament-Config prüfen
- Map könnte bereits gebannt sein
