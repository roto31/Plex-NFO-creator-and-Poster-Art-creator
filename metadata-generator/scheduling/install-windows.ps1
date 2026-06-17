# =============================================================================
#  Plex Metadata Generator — Windows Install Script (PowerShell)
#
#  Installs the script and registers it as a Task Scheduler job that runs
#  daily at 2 AM. Must be run as Administrator once to register the task.
#
#  Usage (PowerShell as Administrator):
#    Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
#    .\install-windows.ps1
# =============================================================================

#Requires -RunAsAdministrator

$ErrorActionPreference = "Stop"

# ── Paths — edit these to match your system ───────────────────────────────────
$PythonExe    = "python"          # or full path: "C:\Python312\python.exe"
$InstallDir   = "C:\Program Files\PlexMetadataGenerator"
$ConfigDir    = "C:\ProgramData\PlexMetadataGenerator"
$LogDir       = "C:\ProgramData\PlexMetadataGenerator\Logs"
$ScriptSrc    = "plex_metadata_generator_extended.py"
$ConfSrc      = "plex-metadata-generator-extended.conf"
$TaskName     = "PlexMetadataGenerator"
$TaskDesc     = "Runs Plex Metadata Generator daily to update NFO files and refresh Plex."

# ── Colour helpers ─────────────────────────────────────────────────────────────
function Write-Info    { Write-Host "→ $args" -ForegroundColor Cyan }
function Write-Success { Write-Host "✓ $args" -ForegroundColor Green }
function Write-Warn    { Write-Host "! $args" -ForegroundColor Yellow }

Write-Host ""
Write-Host "╔══════════════════════════════════════════════════════════════╗" -ForegroundColor White
Write-Host "║       Plex Metadata Generator — Windows Installer            ║" -ForegroundColor White
Write-Host "╚══════════════════════════════════════════════════════════════╝" -ForegroundColor White
Write-Host ""

# ── Pre-flight ────────────────────────────────────────────────────────────────
Write-Info "Checking prerequisites..."

if (-not (Test-Path $ScriptSrc))  { throw "Cannot find $ScriptSrc — run from the same directory." }
if (-not (Test-Path $ConfSrc))    { throw "Cannot find $ConfSrc — run from the same directory." }

try   { & $PythonExe --version | Out-Null }
catch { throw "Python not found. Install from https://www.python.org/downloads/" }

Write-Success "Prerequisites OK"

# ── Create directories ────────────────────────────────────────────────────────
Write-Info "Creating install directories..."
New-Item -ItemType Directory -Force -Path $InstallDir | Out-Null
New-Item -ItemType Directory -Force -Path $ConfigDir  | Out-Null
New-Item -ItemType Directory -Force -Path $LogDir     | Out-Null
Write-Success "Directories created"

# ── Install script ────────────────────────────────────────────────────────────
Write-Info "Installing script to $InstallDir..."
Copy-Item $ScriptSrc -Destination "$InstallDir\plex_metadata_generator_extended.py" -Force
Write-Success "Script installed"

# ── Install config (skip if exists) ──────────────────────────────────────────
$ConfDest = "$ConfigDir\plex-metadata-generator.conf"
if (Test-Path $ConfDest) {
  Write-Warn "Config already exists at $ConfDest — skipping (your settings are safe)"
} else {
  Copy-Item $ConfSrc -Destination $ConfDest -Force
  Write-Success "Config installed — edit $ConfDest with your API keys and paths"
}

# ── Install requests if missing ───────────────────────────────────────────────
Write-Info "Checking Python dependencies..."
$pip = & $PythonExe -m pip show requests 2>&1
if ($LASTEXITCODE -ne 0) {
  Write-Warn "'requests' not found. Installing..."
  & $PythonExe -m pip install requests
}
Write-Success "Python dependencies OK"

# ── Register Task Scheduler job ───────────────────────────────────────────────
Write-Info "Registering Task Scheduler job..."

$Action = New-ScheduledTaskAction `
  -Execute $PythonExe `
  -Argument "`"$InstallDir\plex_metadata_generator_extended.py`" --config `"$ConfDest`" --media-type all >> `"$LogDir\plex-metadata-generator.log`" 2>&1" `
  -WorkingDirectory $InstallDir

# Daily at 2:00 AM; also run if the scheduled time was missed
$Trigger = New-ScheduledTaskTrigger -Daily -At "02:00"
$Trigger.StartBoundary = (Get-Date).Date.AddHours(2).ToString("yyyy-MM-ddTHH:mm:ss")

$Settings = New-ScheduledTaskSettingsSet `
  -MultipleInstances IgnoreNew `
  -StartWhenAvailable `
  -ExecutionTimeLimit (New-TimeSpan -Hours 2) `
  -Priority 7 `
  -RunOnlyIfNetworkAvailable

$Principal = New-ScheduledTaskPrincipal `
  -UserId ([System.Security.Principal.WindowsIdentity]::GetCurrent().Name) `
  -LogonType Interactive `
  -RunLevel Limited

# Remove old task if present
Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false -ErrorAction SilentlyContinue

Register-ScheduledTask `
  -TaskName    $TaskName `
  -Description $TaskDesc `
  -Action      $Action `
  -Trigger     $Trigger `
  -Settings    $Settings `
  -Principal   $Principal | Out-Null

Write-Success "Task registered: $TaskName"

# ── Summary ───────────────────────────────────────────────────────────────────
Write-Host ""
Write-Host "╔══════════════════════════════════════════════════════════════╗" -ForegroundColor Green
Write-Host "║                    Install Complete ✓                        ║" -ForegroundColor Green
Write-Host "╚══════════════════════════════════════════════════════════════╝" -ForegroundColor Green
Write-Host ""
Write-Host "  Script:    $InstallDir\plex_metadata_generator_extended.py"
Write-Host "  Config:    $ConfDest  ← edit this first"
Write-Host "  Logs:      $LogDir\plex-metadata-generator.log"
Write-Host "  Schedule:  Daily at 2:00 AM"
Write-Host ""
Write-Host "  Next steps:"
Write-Host "  1. Edit config:   notepad `"$ConfDest`""
Write-Host "  2. Test run:      $PythonExe `"$InstallDir\plex_metadata_generator_extended.py`" --config `"$ConfDest`" --debug"
Write-Host "  3. Run now:       Start-ScheduledTask -TaskName $TaskName"
Write-Host "  4. View logs:     Get-Content `"$LogDir\plex-metadata-generator.log`" -Tail 50 -Wait"
Write-Host "  5. Uninstall:     Unregister-ScheduledTask -TaskName $TaskName"
Write-Host ""
