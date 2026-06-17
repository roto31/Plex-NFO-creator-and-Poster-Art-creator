#!/usr/bin/env bash
# =============================================================================
#  Plex Metadata Generator — macOS Install Script
#
#  Installs the script and registers it as a launchd agent so it runs
#  daily at 2 AM as your normal user. No sudo required after install.
#
#  Usage:
#    chmod +x install-macos.sh
#    ./install-macos.sh
# =============================================================================

set -euo pipefail

RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'
BLUE='\033[0;34m'; NC='\033[0m'
info()    { echo -e "${BLUE}→${NC} $*"; }
success() { echo -e "${GREEN}✓${NC} $*"; }
warn()    { echo -e "${YELLOW}!${NC} $*"; }
error()   { echo -e "${RED}✗${NC} $*"; exit 1; }

SCRIPT_SRC="plex_metadata_generator_extended.py"
SCRIPT_DEST="/usr/local/bin/plex_metadata_generator_extended.py"
CONF_SRC="plex-metadata-generator-extended.conf"
CONF_DEST="/usr/local/etc/plex-metadata-generator.conf"
PLIST_SRC="com.plexmetadata.generator.plist"
PLIST_DEST="$HOME/Library/LaunchAgents/com.plexmetadata.generator.plist"
LOG_DIR="$HOME/Library/Logs"
LABEL="com.plexmetadata.generator"

echo ""
echo "╔══════════════════════════════════════════════════════════════╗"
echo "║        Plex Metadata Generator — macOS Installer             ║"
echo "╚══════════════════════════════════════════════════════════════╝"
echo ""

info "Checking prerequisites..."
[[ -f "$SCRIPT_SRC" ]] || error "Cannot find $SCRIPT_SRC — run this from the same directory."
[[ -f "$CONF_SRC" ]]   || error "Cannot find $CONF_SRC — run this from the same directory."
[[ -f "$PLIST_SRC" ]]  || error "Cannot find $PLIST_SRC — run this from the same directory."
python3 --version &>/dev/null || error "python3 not found. Install via: brew install python"
python3 -c "import requests" 2>/dev/null || {
  warn "'requests' not found. Installing..."
  pip3 install --user requests
}
success "Prerequisites OK"

info "Installing script to $SCRIPT_DEST..."
sudo cp "$SCRIPT_SRC" "$SCRIPT_DEST"
sudo chmod +x "$SCRIPT_DEST"
success "Script installed"

if [[ -f "$CONF_DEST" ]]; then
  warn "Config already exists at $CONF_DEST — skipping (your settings are safe)"
else
  info "Installing config to $CONF_DEST..."
  sudo cp "$CONF_SRC" "$CONF_DEST"
  sudo chmod 600 "$CONF_DEST"
  success "Config installed — edit it with your API keys and paths"
fi

info "Configuring plist for user: $USER..."
sed "s|YOUR_USERNAME|$USER|g" "$PLIST_SRC" > "$PLIST_DEST"
chmod 644 "$PLIST_DEST"
success "Plist written to $PLIST_DEST"

info "Registering with launchd..."
launchctl unload "$PLIST_DEST" 2>/dev/null || true
launchctl load   "$PLIST_DEST"
success "launchd agent loaded"

echo ""
echo "╔══════════════════════════════════════════════════════════════╗"
echo "║                    Install Complete ✓                        ║"
echo "╚══════════════════════════════════════════════════════════════╝"
echo ""
echo "  Script:   $SCRIPT_DEST"
echo "  Config:   $CONF_DEST  ← edit this first"
echo "  Plist:    $PLIST_DEST"
echo "  Logs:     $LOG_DIR/plex-metadata-generator.log"
echo "  Schedule: Daily at 2:00 AM"
echo ""
echo "  Next steps:"
echo "  1. Edit config:   sudo nano $CONF_DEST"
echo "  2. Test run:      python3 $SCRIPT_DEST --config $CONF_DEST --debug"
echo "  3. Run now:       launchctl start $LABEL"
echo "  4. View logs:     tail -f $LOG_DIR/plex-metadata-generator.log"
echo "  5. Uninstall:     launchctl unload $PLIST_DEST && rm $PLIST_DEST"
echo ""
