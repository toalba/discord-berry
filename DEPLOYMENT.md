# Deployment Guide

## Option 1: Systemd Services (empfohlen für einzelnen Server)

### Bot Service (bereits vorhanden)
```bash
sudo cp berry.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable berry.service
sudo systemctl start berry.service
```

### Web Interface Service (NEU)
```bash
sudo cp webui.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable webui.service
sudo systemctl start webui.service
```

### Services verwalten
```bash
# Status prüfen
sudo systemctl status berry.service
sudo systemctl status webui.service

# Logs ansehen
sudo journalctl -u berry.service -f
sudo journalctl -u webui.service -f

# Neustarten
sudo systemctl restart berry.service
sudo systemctl restart webui.service

# Stoppen
sudo systemctl stop berry.service
sudo systemctl stop webui.service
```

## Option 2: Docker Compose (empfohlen für einfaches Deployment)

### Voraussetzungen
```bash
# Docker installieren (falls nicht vorhanden)
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh

# Docker Compose installieren
sudo apt install docker-compose-plugin
```

### Deployment
```bash
cd /root/discord-berry

# Container bauen und starten
docker compose up -d

# Logs ansehen
docker compose logs -f

# Nur Bot-Logs
docker compose logs -f bot

# Nur WebUI-Logs
docker compose logs -f webui
```

### Container Management
```bash
# Status prüfen
docker compose ps

# Neustarten
docker compose restart

# Stoppen
docker compose stop

# Stoppen und Container entfernen
docker compose down

# Komplett neu bauen
docker compose up -d --build

# Einzelnen Service neustarten
docker compose restart bot
docker compose restart webui
```

### Updates durchführen
```bash
# Code aktualisieren
git pull  # oder manuelle Änderungen

# Container neu bauen und starten
docker compose up -d --build
```

## Vergleich der Optionen

### Systemd Services
✅ Einfacher für einzelne Dienste  
✅ Direkte Integration mit System  
✅ Einfacher Zugriff auf Logs via journalctl  
❌ Manuelles Dependency-Management  
❌ Keine Isolation  

### Docker
✅ Komplette Isolation  
✅ Einfaches Deployment auf anderen Servern  
✅ Dependency-Management inklusive  
✅ Beide Services gleichzeitig verwalten  
❌ Zusätzlicher Overhead  
❌ Docker muss installiert sein  

## Production-Setup mit nginx (Optional)

### nginx als Reverse Proxy für WebUI
```nginx
# /etc/nginx/sites-available/berry-webui
server {
    listen 80;
    server_name tournament-config.yourdomain.com;

    location / {
        proxy_pass http://127.0.0.1:5000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

```bash
sudo ln -s /etc/nginx/sites-available/berry-webui /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl reload nginx
```

### SSL mit Let's Encrypt
```bash
sudo apt install certbot python3-certbot-nginx
sudo certbot --nginx -d tournament-config.yourdomain.com
```

## Environment Variables

Stelle sicher, dass `.env` existiert:
```bash
TOKEN=your_discord_bot_token
WEBHOOK=your_discord_webhook_url
```

## Firewall-Konfiguration

### Port 5000 öffnen (für WebUI)
```bash
# ufw
sudo ufw allow 5000/tcp

# iptables
sudo iptables -A INPUT -p tcp --dport 5000 -j ACCEPT
sudo iptables-save > /etc/iptables/rules.v4
```

## Monitoring

### Systemd Services
```bash
# Service-Status im Überblick
systemctl status berry.service webui.service

# Automatischer Restart bei Failure
# (bereits in .service Files konfiguriert mit Restart=always)
```

### Docker
```bash
# Container-Health-Check
docker compose ps

# Resource-Usage
docker stats
```

## Backup

### Wichtige Dateien sichern
```bash
# Config-Backup
cp tournament_config.json tournament_config.json.backup

# Automatisches Backup (Cron)
# /etc/cron.daily/berry-backup
#!/bin/bash
cd /root/discord-berry
cp tournament_config.json /backup/tournament_config_$(date +%Y%m%d).json
find /backup -name "tournament_config_*.json" -mtime +30 -delete
```

## Troubleshooting

### Systemd: Service startet nicht
```bash
# Logs prüfen
sudo journalctl -u webui.service -n 50 --no-pager

# Manuell testen
cd /root/discord-berry
source venv/bin/activate
python webui.py
```

### Docker: Container crasht
```bash
# Logs anzeigen
docker compose logs webui

# Container ohne Daemon-Mode starten
docker compose up webui

# In Container einloggen
docker compose exec webui bash
```

### Port bereits belegt
```bash
# Prüfen welcher Prozess Port 5000 nutzt
sudo lsof -i :5000
sudo netstat -tulpn | grep :5000

# Prozess beenden
sudo kill -9 <PID>
```
