# Plex Metadata Generator — Installation Guide

> **How it works:** The generator is a Python script that runs once, updates your NFO files, tells Plex to refresh, then exits. It does **not** stay resident in memory. You simply schedule it to run daily using your operating system's built-in task scheduler.

---

## Choose Your Platform

| Platform | Method | Install time |
|---|---|---|
| **macOS** | launchd (LaunchAgent) | ~5 min |
| **Windows** | Task Scheduler | ~5 min |
| **Linux** | systemd timer or cron | ~5 min |
| **Docker** | Docker Compose | [See Appendix](#appendix-docker) |

---

## macOS — launchd (Recommended)

launchd is the native macOS task scheduler. The agent runs as your normal user with no sudo required after install.

### Quick Install (Automated)

```bash
# 1. From the directory where you extracted the zip
chmod +x install-macos.sh
./install-macos.sh

# 2. Edit config with your API keys and paths
sudo nano /usr/local/etc/plex-metadata-generator.conf

# 3. Test run
python3 /usr/local/bin/plex_metadata_generator_extended.py \
  --config /usr/local/etc/plex-metadata-generator.conf --debug
```

That's it. The script will run daily at 2 AM.

### Manual Install

**Step 1 — Install the script**
```bash
sudo cp plex_metadata_generator_extended.py /usr/local/bin/
sudo chmod +x /usr/local/bin/plex_metadata_generator_extended.py
pip3 install --user requests
```

**Step 2 — Install the config**
```bash
sudo cp plex-metadata-generator-extended.conf /usr/local/etc/plex-metadata-generator.conf
sudo chmod 600 /usr/local/etc/plex-metadata-generator.conf
sudo nano /usr/local/etc/plex-metadata-generator.conf
```

**Step 3 — Install the LaunchAgent plist**
```bash
sed "s/YOUR_USERNAME/$USER/g" com.plexmetadata.generator.plist \
  > ~/Library/LaunchAgents/com.plexmetadata.generator.plist
launchctl load ~/Library/LaunchAgents/com.plexmetadata.generator.plist
```

**Step 4 — Verify**
```bash
launchctl list | grep plexmetadata
```

### Managing the Agent

```bash
# Run immediately (without waiting for 2 AM)
launchctl start com.plexmetadata.generator

# Stop a running job
launchctl stop com.plexmetadata.generator

# Disable
launchctl unload ~/Library/LaunchAgents/com.plexmetadata.generator.plist

# Re-enable after editing the plist
launchctl unload ~/Library/LaunchAgents/com.plexmetadata.generator.plist
launchctl load   ~/Library/LaunchAgents/com.plexmetadata.generator.plist

# View logs
tail -f ~/Library/Logs/plex-metadata-generator.log
tail -f ~/Library/Logs/plex-metadata-generator-error.log
```

### Change the Schedule

Edit `~/Library/LaunchAgents/com.plexmetadata.generator.plist`:

```xml
<!-- Daily at 3 AM -->
<key>StartCalendarInterval</key>
<dict>
  <key>Hour</key><integer>3</integer>
  <key>Minute</key><integer>0</integer>
</dict>

<!-- Twice daily — 2 AM and 2 PM -->
<key>StartCalendarInterval</key>
<array>
  <dict><key>Hour</key><integer>2</integer><key>Minute</key><integer>0</integer></dict>
  <dict><key>Hour</key><integer>14</integer><key>Minute</key><integer>0</integer></dict>
</array>
```

After editing: `launchctl unload ... && launchctl load ...`

---

## Windows — Task Scheduler (Recommended)

Task Scheduler is built into every version of Windows. No third-party software required.

### Quick Install (PowerShell — run as Administrator)

```powershell
# Open PowerShell as Administrator, navigate to the extracted folder
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.\install-windows.ps1

# Edit config
notepad "C:\ProgramData\PlexMetadataGenerator\plex-metadata-generator.conf"

# Test run
python "C:\Program Files\PlexMetadataGenerator\plex_metadata_generator_extended.py" `
  --config "C:\ProgramData\PlexMetadataGenerator\plex-metadata-generator.conf" --debug
```

### Manual Install via Task Scheduler UI

1. Open **Task Scheduler** (`Win + R` → `taskschd.msc`)
2. **Action → Import Task...** → select `plex-metadata-generator-windows.xml`
3. **Actions** tab — update paths to match your Python installation
4. **General** tab — set your Windows username under Security options
5. Click **OK**

### Managing the Task

```powershell
# Run immediately
Start-ScheduledTask -TaskName "PlexMetadataGenerator"

# Check last run
Get-ScheduledTaskInfo -TaskName "PlexMetadataGenerator" | Select LastRunTime, LastTaskResult

# Disable / Re-enable
Disable-ScheduledTask -TaskName "PlexMetadataGenerator"
Enable-ScheduledTask  -TaskName "PlexMetadataGenerator"

# Remove
Unregister-ScheduledTask -TaskName "PlexMetadataGenerator" -Confirm:$false

# View logs
Get-Content "C:\ProgramData\PlexMetadataGenerator\Logs\plex-metadata-generator.log" -Tail 50 -Wait
```

---

## Linux — systemd Timer (Recommended)

Modern Linux distros (Ubuntu 16+, Fedora, Arch, Debian 8+) all include systemd. A timer is the native, clean way to schedule a one-shot script.

### Quick Install (Automated)

```bash
chmod +x install-linux.sh
sudo ./install-linux.sh

# Edit config
sudo nano /etc/plex-metadata-generator.conf

# Test run
python3 /usr/local/bin/plex_metadata_generator_extended.py \
  --config /etc/plex-metadata-generator.conf --debug
```

The installer auto-detects systemd vs. non-systemd and picks the right scheduler.

### Manual Install — systemd

```bash
sudo cp plex_metadata_generator_extended.py /usr/local/bin/
sudo chmod +x /usr/local/bin/plex_metadata_generator_extended.py
pip3 install requests

sudo cp plex-metadata-generator-extended.conf /etc/plex-metadata-generator.conf
sudo chmod 600 /etc/plex-metadata-generator.conf
sudo nano /etc/plex-metadata-generator.conf

sudo cp plex-metadata-generator.service /etc/systemd/system/
sudo cp plex-metadata-generator.timer   /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now plex-metadata-generator.timer
```

### Manual Install — cron (non-systemd systems)

```bash
sudo cp plex-metadata-generator-cron /usr/local/bin/
sudo chmod +x /usr/local/bin/plex-metadata-generator-cron

sudo crontab -e
# Add: 0 2 * * * /usr/local/bin/plex-metadata-generator-cron
```

### Managing the systemd Timer

```bash
# Run immediately
sudo systemctl start plex-metadata-generator.service

# Check next run time
sudo systemctl list-timers plex-metadata-generator.timer

# View logs (live)
sudo journalctl -u plex-metadata-generator -f

# Change schedule
sudo nano /etc/systemd/system/plex-metadata-generator.timer
sudo systemctl daemon-reload && sudo systemctl restart plex-metadata-generator.timer
```

---

## First-Run Checklist (All Platforms)

- [ ] Edit the config file and fill in all API keys and paths
- [ ] Run manually with `--debug` and verify output looks correct
- [ ] Confirm `.nfo` files appeared next to your media files
- [ ] In Plex → Settings → Libraries → your library → Edit → Agents: **Local Media Assets** must be #1
- [ ] Trigger a Plex library refresh and confirm metadata appears

---

## Configuration Reference

| Platform | Config path |
|---|---|
| macOS | `/usr/local/etc/plex-metadata-generator.conf` |
| Windows | `C:\ProgramData\PlexMetadataGenerator\plex-metadata-generator.conf` |
| Linux | `/etc/plex-metadata-generator.conf` |

Minimum working config (TV + Music):

```json
{
  "tv_library_root":    "/path/to/TV",
  "music_library_root": "/path/to/Music",

  "plex": {
    "url": "http://localhost:32400",
    "token": "YOUR_PLEX_TOKEN",
    "tv_library_key":    "1",
    "music_library_key": "2"
  },

  "tunarr":  { "db_path": "/path/to/tunarr.db" },
  "tvdb":    { "api_key": "YOUR_TVDB_KEY",  "enabled": true },
  "tmdb":    { "api_key": "YOUR_TMDB_KEY",  "enabled": true },

  "spotify": {
    "client_id":     "YOUR_SPOTIFY_CLIENT_ID",
    "client_secret": "YOUR_SPOTIFY_CLIENT_SECRET",
    "enabled": true
  },

  "musicbrainz": { "contact": "your@email.com", "enabled": true },

  "metadata_priority": {
    "tv":    ["tvdb", "tmdb", "tunarr"],
    "music": ["spotify", "musicbrainz"]
  }
}
```

### How to Get Your Plex Token

```bash
# macOS / Linux
curl -s "http://localhost:32400/web/" | grep -oP 'authenticationToken="\K[^"]*'
```

Or open `http://localhost:32400/web` in your browser → Developer Tools → Network tab → reload → look for `X-Plex-Token` in any request header.

---

## API Keys

| Service | URL | Notes |
|---|---|---|
| TVDb | https://thetvdb.com/dashboard/account/settings/api | Free, required for TV |
| TMDb | https://www.themoviedb.org/settings/api | Free, TV fallback |
| Spotify | https://developer.spotify.com/dashboard | Free, music metadata |
| MusicBrainz | No key needed | Just set `contact` to your email |

---

## Troubleshooting

**NFO files not appearing in Plex**
- Check files exist: `find /your/tv/path -name "*.nfo" | head`
- Plex → Settings → Libraries → Edit → Agents → **Local Media Assets** must be #1
- Manually refresh: Settings → Troubleshooting → Clean Bundles, then refresh the library

**API errors on first run**
```bash
# Test TVDb
curl -X POST https://api4.thetvdb.com/v4/login \
  -H "Content-Type: application/json" -d '{"apikey":"YOUR_KEY"}'

# Test Plex
curl -H "X-Plex-Token: YOUR_TOKEN" http://localhost:32400/library/sections
```

**macOS: plist not loading**
```bash
plutil -lint ~/Library/LaunchAgents/com.plexmetadata.generator.plist
```

**Linux: permission errors**
```bash
sudo systemctl cat plex-metadata-generator.service | grep User
sudo chown -R YOUR_USER /path/to/media /var/log/plex-metadata-generator
```

---

## Appendix: Docker

> Docker is available for users who prefer containerised deployments — NAS devices, home servers, or environments where Python isn't installed natively. For a Mac, Windows PC, or standard Linux box, the native methods above are simpler and have less overhead.

### Setup

```bash
cp plex-metadata-generator-extended.conf plex-metadata-generator.conf
nano plex-metadata-generator.conf   # fill in your values

docker compose up -d

# Run immediately
docker compose exec plex-metadata-generator \
  python3 /app/plex_metadata_generator_extended.py --debug

# Logs
docker compose logs -f
```

See `docker-compose.yml` and `Dockerfile` in the package for the full configuration.

---

*v1.1.0 — supports TV (TVDb/TMDb/Tunarr) and Music (Spotify/MusicBrainz)*
