#!/usr/bin/env bash
# =============================================================================
#  Plex Metadata Generator — Linux Install Script
#
#  Installs the script and sets up either a systemd timer (recommended)
#  or a cron job. Works on Debian/Ubuntu, RHEL/Fedora, and Arch.
#
#  Usage:
#    chmod +x install-linux.sh
#    sudo ./install-linux.sh
# =============================================================================

set -euo pipefail

RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'
BLUE='\033[0;34m'; NC='\033[0m'
info()    { echo -e "${BLUE}→${NC} $*"; }
success() { echo -e "${GREEN}✓${NC} $*"; }
warn()    { echo -e "${YELLOW}!${NC} $*"; }
error()   { echo -e "${RED}✗${NC} $*"; exit 1; }

[[ $EUID -eq 0 ]] || error "Run as root: sudo ./install-linux.sh"

SCRIPT_SRC="plex_metadata_generator_extended.py"
CONF_SRC="plex-metadata-generator-extended.conf"
SERVICE_SRC="plex-metadata-generator.service"
TIMER_SRC="plex-metadata-generator.timer"
CRON_SRC="plex-metadata-generator-cron"

SCRIPT_DEST="/usr/local/bin/plex_metadata_generator_extended.py"
CONF_DEST="/etc/plex-metadata-generator.conf"
LOG_DIR="/var/log/plex-metadata-generator"

echo ""
echo "╔══════════════════════════════════════════════════════════════╗"
echo "║        Plex Metadata Generator — Linux Installer             ║"
echo "╚══════════════════════════════════════════════════════════════╝"
echo ""

# ── Detect scheduling method ──────────────────────────────────────────────────
if command -v systemctl &>/dev/null && systemctl --version &>/dev/null 2>&1; then
  SCHEDULER="systemd"
  info "Detected systemd — will install timer"
else
  SCHEDULER="cron"
  warn "systemd not found — will install cron job"
fi

# ── Pre-flight ────────────────────────────────────────────────────────────────
info "Checking prerequisites..."
[[ -f "$SCRIPT_SRC" ]] || error "Cannot find $SCRIPT_SRC — run from the same directory."
[[ -f "$CONF_SRC" ]]   || error "Cannot find $CONF_SRC — run from the same directory."
python3 --version &>/dev/null || error "python3 not found. Install via your package manager."
python3 -c "import requests" 2>/dev/null || {
  warn "'requests' not found. Installing..."
  pip3 install requests
}
success "Prerequisites OK"

# ── Install script ────────────────────────────────────────────────────────────
info "Installing script to $SCRIPT_DEST..."
cp "$SCRIPT_SRC" "$SCRIPT_DEST"
chmod +x "$SCRIPT_DEST"
success "Script installed"

# ── Install config ────────────────────────────────────────────────────────────
if [[ -f "$CONF_DEST" ]]; then
  warn "Config already exists at $CONF_DEST — skipping (your settings are safe)"
else
  cp "$CONF_SRC" "$CONF_DEST"
  chmod 600 "$CONF_DEST"
  success "Config installed — edit $CONF_DEST with your API keys and paths"
fi

# ── Create log directory ──────────────────────────────────────────────────────
mkdir -p "$LOG_DIR"
success "Log directory: $LOG_DIR"

# ── Scheduling ────────────────────────────────────────────────────────────────
if [[ "$SCHEDULER" == "systemd" ]]; then
  info "Installing systemd service and timer..."
  [[ -f "$SERVICE_SRC" ]] || error "Cannot find $SERVICE_SRC"
  [[ -f "$TIMER_SRC" ]]   || error "Cannot find $TIMER_SRC"

  # Patch User= in service file to current sudo user (or plex if exists)
  RUN_USER="${SUDO_USER:-$(id -un)}"
  id plex &>/dev/null && RUN_USER="plex"

  sed "s/^User=.*/User=$RUN_USER/" "$SERVICE_SRC" > /etc/systemd/system/plex-metadata-generator.service
  cp "$TIMER_SRC" /etc/systemd/system/plex-metadata-generator.timer

  systemctl daemon-reload
  systemctl enable --now plex-metadata-generator.timer
  success "systemd timer enabled and started"

  echo ""
  info "Verify:"
  echo "  systemctl list-timers plex-metadata-generator.timer"
  echo "  journalctl -u plex-metadata-generator -f"

else
  info "Installing cron job..."
  [[ -f "$CRON_SRC" ]] || error "Cannot find $CRON_SRC"
  cp "$CRON_SRC" /usr/local/bin/plex-metadata-generator-cron
  chmod +x /usr/local/bin/plex-metadata-generator-cron

  CRON_LINE="0 2 * * * /usr/local/bin/plex-metadata-generator-cron"
  ( crontab -l 2>/dev/null | grep -v plex-metadata-generator; echo "$CRON_LINE" ) | crontab -
  success "Cron job installed (daily at 2 AM)"

  echo ""
  info "Verify:"
  echo "  crontab -l | grep plex"
  echo "  tail -f $LOG_DIR/cron-\$(date +%Y%m%d).log"
fi

# ── Summary ───────────────────────────────────────────────────────────────────
echo ""
echo "╔══════════════════════════════════════════════════════════════╗"
echo "║                    Install Complete ✓                        ║"
echo "╚══════════════════════════════════════════════════════════════╝"
echo ""
echo "  Script:   $SCRIPT_DEST"
echo "  Config:   $CONF_DEST  ← edit this first"
echo "  Logs:     $LOG_DIR"
echo "  Schedule: Daily at 2:00 AM ($SCHEDULER)"
echo ""
echo "  Next steps:"
echo "  1. Edit config:  nano $CONF_DEST"
echo "  2. Test run:     python3 $SCRIPT_DEST --config $CONF_DEST --debug"
if [[ "$SCHEDULER" == "systemd" ]]; then
echo "  3. Run now:      systemctl start plex-metadata-generator.service"
echo "  4. View logs:    journalctl -u plex-metadata-generator -f"
else
echo "  3. Run now:      /usr/local/bin/plex-metadata-generator-cron"
echo "  4. View logs:    tail -f $LOG_DIR/cron-\$(date +%Y%m%d).log"
fi
echo ""
