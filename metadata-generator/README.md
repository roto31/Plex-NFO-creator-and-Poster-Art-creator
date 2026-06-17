# Plex Metadata Generator with Tunarr/TVDb/TMDb Integration

Automatically generate and manage Plex NFO (metadata) files for your TV show library by integrating with:
- **Tunarr** - Extract program metadata from your Tunarr instance
- **TVDb API** - Comprehensive TV show metadata (recommended)
- **TMDb API** - The Movie Database as fallback
- **Plex API** - Automatic library refresh

## Features

✅ **Multi-source Metadata** - Queries TVDb, TMDb, and Tunarr with intelligent fallback  
✅ **Automatic Scheduling** - Systemd timer or cron-based daily runs  
✅ **Episode-level Metadata** - Generates NFO for every episode  
✅ **Artwork Download** - Automatically downloads and caches posters and banners  
✅ **Plex Integration** - Triggers library refresh automatically  
✅ **Rate Limiting** - Respects API limits; includes intelligent caching  
✅ **Comprehensive Logging** - Full audit trail and error reporting  
✅ **Health Monitoring** - Built-in health check script  

## Quick Start (5 Minutes)

### 1. Get API Keys

- **TVDb**: https://thetvdb.com/dashboard/account/settings/api (free, instant)
- **TMDb**: https://www.themoviedb.org/settings/api (free, instant)
- **Plex Token**: View page source at http://localhost:32400/web/ → search `authenticationToken`

### 2. Install

```bash
# Install dependencies
pip install requests

# Install script
sudo cp plex_metadata_generator.py /usr/local/bin/plex-metadata-generator
sudo chmod +x /usr/local/bin/plex-metadata-generator

# Install systemd files
sudo cp plex-metadata-generator.service /etc/systemd/system/
sudo cp plex-metadata-generator.timer /etc/systemd/system/
sudo systemctl daemon-reload
```

### 3. Configure

```bash
sudo cp plex-metadata-generator.conf /etc/plex-metadata-generator.conf
sudo nano /etc/plex-metadata-generator.conf
```

Fill in (at minimum):
```json
{
  "library_root": "/mnt/media/TV",  // Your TV library path
  "plex": {
    "url": "http://localhost:32400",
    "token": "YOUR_PLEX_TOKEN",
    "library_key": "1"
  },
  "tvdb": {
    "api_key": "YOUR_TVDB_KEY"
  },
  "tmdb": {
    "api_key": "YOUR_TMDB_KEY"
  }
}
```

### 4. Enable Scheduling

```bash
# Start timer (runs daily at 2 AM)
sudo systemctl enable plex-metadata-generator.timer
sudo systemctl start plex-metadata-generator.timer

# Verify
sudo systemctl status plex-metadata-generator.timer
```

### 5. Run First Time

```bash
# Test run (may take 5-30 min depending on library size)
sudo -u plex /usr/local/bin/plex-metadata-generator \
  --config /etc/plex-metadata-generator.conf

# Check logs
sudo tail -f /var/log/plex-metadata-generator.log
```

### 6. Verify in Plex

- Open Plex Web: http://localhost:32400/web/
- Settings → Libraries → TV Shows → **Ensure "Local Media Assets" is top agent**
- Your show metadata should now be populated from NFO files

---

## What Gets Generated

For each show:
```
Show Name/
├── tvshow.nfo          ← Show metadata (title, year, plot, rating, IDs)
├── poster.jpg          ← Show poster
├── Season 1/
│   ├── Episode 1.mkv
│   ├── Episode 1.nfo   ← Episode metadata (title, plot, date, rating)
│   └── ...
└── Season 2/
    └── ...
```

All NFO files are **Plex-compliant XML** with show/episode metadata and pointers to TVDb/TMDb/IMDb IDs.

---

## Scheduling Options

### Systemd Timer (Recommended)

**Daily at 2 AM:**
```bash
sudo systemctl status plex-metadata-generator.timer
sudo journalctl -u plex-metadata-generator -f
```

**Change time:** Edit `/etc/systemd/system/plex-metadata-generator.timer`

### Cron

```bash
sudo crontab -e
# Add: 0 2 * * * /usr/local/bin/plex-metadata-generator-cron
```

---

## Usage

### Run Manually

```bash
# Full library
sudo -u plex /usr/local/bin/plex-metadata-generator --config /etc/plex-metadata-generator.conf

# Specific show
sudo -u plex /usr/local/bin/plex-metadata-generator --config /etc/plex-metadata-generator.conf --show "The Office"

# Debug mode
sudo -u plex /usr/local/bin/plex-metadata-generator --config /etc/plex-metadata-generator.conf --debug
```

### Health Check

```bash
sudo python3 health-check.py
```

Shows:
- Configuration validity
- Systemd/cron status
- Recent logs and errors
- API connectivity
- File permissions
- Disk space

### View Logs

```bash
# Systemd
sudo journalctl -u plex-metadata-generator -f -n 100

# Or direct log file
tail -f /var/log/plex-metadata-generator.log

# View only errors
grep ERROR /var/log/plex-metadata-generator.log
```

---

## Troubleshooting

### NFO Files Not Appearing in Plex

1. Verify NFO files were created:
```bash
find /mnt/media/TV -name "*.nfo" | head -10
```

2. Check Local Media Agent is prioritized:
   - Plex → Settings → Libraries → TV Shows → Agents
   - Drag "Local Media Assets" to **top**

3. Manually refresh library:
```bash
curl -X POST -H "X-Plex-Token: YOUR_TOKEN" \
  http://localhost:32400/library/sections/1/refresh
```

### API Key Issues

Test connectivity:
```bash
# TVDb
curl -X POST https://api4.thetvdb.com/v4/login \
  -H "Content-Type: application/json" \
  -d '{"apikey":"YOUR_KEY"}'

# TMDb
curl "https://api.themoviedb.org/3/search/tv?api_key=YOUR_KEY&query=test"
```

### Permissions Errors

```bash
# Create plex user if missing
sudo useradd -r -s /bin/false plex 2>/dev/null || true

# Fix permissions
sudo chown -R plex:plex /mnt/media/TV
sudo chown -R plex:plex /var/cache/plex-metadata
sudo chown -R plex:plex /var/log/plex-metadata-generator
```

### Script Not Running

```bash
# Check timer is enabled
sudo systemctl is-enabled plex-metadata-generator.timer
# Should output: enabled

# Check timer is active
sudo systemctl is-active plex-metadata-generator.timer
# Should output: active

# View timer schedule
sudo systemctl list-timers plex-metadata-generator.timer
```

---

## Configuration Reference

Full config structure:

```json
{
  "library_root": "/mnt/media/TV",
  "cache_dir": "/var/cache/plex-metadata",
  
  "plex": {
    "url": "http://localhost:32400",
    "token": "YOUR_PLEX_TOKEN",
    "library_key": "1"
  },
  
  "tunarr": {
    "db_path": "/opt/tunarr/cache/tunarr.db"
  },
  
  "tvdb": {
    "api_key": "YOUR_TVDB_KEY",
    "enabled": true
  },
  
  "tmdb": {
    "api_key": "YOUR_TMDB_KEY",
    "enabled": true
  },
  
  "metadata_priority": ["tvdb", "tmdb", "tunarr"]
}
```

**Key Notes:**
- `library_root` - Path to your Plex TV library
- `plex.library_key` - Check Settings → Library → (right-click show) → "Get Info" → URL contains `/library/sections/X/`
- `metadata_priority` - Order to search for metadata
- API keys get ~99% of shows (very comprehensive)

---

## Performance

- **First run:** 5-30 minutes (depends on library size and API response)
- **Subsequent runs:** 2-10 minutes (cached artwork, incremental)
- **Memory:** ~50-100 MB during full scan
- **Disk:** ~10-50 MB for NFO files + artwork cache
- **Network:** Rate-limited to respect API terms (~1-2 requests/sec)

---

## File Structure

```
├── plex_metadata_generator.py      ← Main script
├── plex-metadata-generator.conf    ← Configuration
├── plex-metadata-generator.service ← Systemd service
├── plex-metadata-generator.timer   ← Systemd timer
├── plex-metadata-generator-cron    ← Cron alternative
├── health-check.py                 ← Monitoring script
├── INSTALL.md                      ← Detailed install guide
└── README.md                       ← This file
```

---

## Integration Examples

### With Homelab Infrastructure

This integrates seamlessly with:
- **Tunarr** - Pulls show metadata from your custom channels
- **Plex** - Automatic library refresh and metadata application
- **TVDb/TMDb** - Professional TV show databases
- **Docker** - Can run in container with volumes mounted

### With Jamf (macOS Management)

Deploy as LaunchAgent on managed Macs:
```bash
# /Library/LaunchAgents/com.plex.metadata-generator.plist
# Requires: /usr/local/bin/plex-metadata-generator installed
```

### With Kubernetes

Deploy as CronJob in Kubernetes cluster with PVC for library access.

---

## Contributing

This tool is published under GitHub: [roto31/plex-metadata-generator](https://github.com/roto31/plex-metadata-generator)

Issues, PRs, and suggestions welcome.

---

## License

Released for personal/non-commercial use with Plex Media Server.

---

## Support

### Debug a Single Run

```bash
sudo -u plex /usr/local/bin/plex-metadata-generator \
  --config /etc/plex-metadata-generator.conf \
  --show "Show Name" \
  --debug 2>&1 | tee /tmp/debug.log
```

### Monitor in Real-Time

```bash
# Open two terminals

# Terminal 1: Watch logs
sudo tail -f /var/log/plex-metadata-generator.log

# Terminal 2: Trigger manual run
sudo -u plex /usr/local/bin/plex-metadata-generator --config /etc/plex-metadata-generator.conf
```

### Get Help

1. Run `health-check.py` to diagnose
2. Check logs: `tail -f /var/log/plex-metadata-generator.log`
3. Verify config: `python3 -m json.tool < /etc/plex-metadata-generator.conf`
4. Test API keys manually (see Troubleshooting)

---

## Version History

**v1.0.0** - Initial Release
- Tunarr, TVDb, TMDb integration
- Systemd timer + cron scheduling
- Episode-level metadata
- Artwork caching
- Health monitoring

---

**Last Updated:** June 2026  
**Author:** Chris Ruter (@roto31)
