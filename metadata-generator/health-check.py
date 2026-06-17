#!/usr/bin/env python3
"""
Health check and monitoring script for Plex Metadata Generator
Monitors status, logs, and provides diagnostic information
"""

import os
import sys
import json
import subprocess
import re
from datetime import datetime, timedelta
from pathlib import Path


class HealthChecker:
    """Monitor health of metadata generator"""
    
    def __init__(self):
        self.config_path = '/etc/plex-metadata-generator.conf'
        self.log_path = '/var/log/plex-metadata-generator.log'
        self.lock_file = '/var/run/plex-metadata-generator.lock'
        self.cache_dir = '/var/cache/plex-metadata'
        self.status_checks = []
    
    def check_configuration(self) -> bool:
        """Verify configuration file exists and is valid"""
        print("[*] Checking configuration...")
        
        if not Path(self.config_path).exists():
            print(f"  ❌ Config file not found: {self.config_path}")
            return False
        
        try:
            with open(self.config_path) as f:
                config = json.load(f)
            
            # Accept either old flat 'library_root' or new split keys
            has_library = (
                'library_root' in config
                or 'tv_library_root' in config
                or 'movies_library_root' in config
            )
            required_keys = ['plex', 'tvdb', 'tmdb']
            missing = [k for k in required_keys if k not in config]
            if not has_library:
                missing.append('tv_library_root (or library_root)')

            if missing:
                print(f"  ⚠️  Missing config keys: {missing}")
                return False

            # Warn (not error) if FanArt.tv key absent — clearart/disc/logo will be skipped
            if not config.get('fanart_tv', {}).get('api_key'):
                print("  ⚠️  fanart_tv.api_key not set — clearart, disc, and logo artwork will be skipped")
            else:
                print("  ✅ FanArt.tv key configured")
            
            # Check for placeholder values
            if 'YOUR_' in json.dumps(config):
                print("  ⚠️  Config contains placeholder API keys (YOUR_*_HERE)")
                return False
            
            print("  ✅ Configuration valid")
            return True
        except json.JSONDecodeError as e:
            print(f"  ❌ Invalid JSON: {e}")
            return False
    
    def check_systemd_timer(self) -> dict:
        """Check systemd timer status"""
        print("[*] Checking systemd timer...")
        
        result = {
            'enabled': False,
            'active': False,
            'last_trigger': None,
            'next_trigger': None,
        }
        
        try:
            # Check if timer is enabled
            enabled = subprocess.run(
                ['systemctl', 'is-enabled', 'plex-metadata-generator.timer'],
                capture_output=True,
                text=True
            )
            result['enabled'] = enabled.returncode == 0
            
            # Check if timer is active
            active = subprocess.run(
                ['systemctl', 'is-active', 'plex-metadata-generator.timer'],
                capture_output=True,
                text=True
            )
            result['active'] = active.returncode == 0
            
            # Get timer info
            list_output = subprocess.run(
                ['systemctl', 'list-timers', 'plex-metadata-generator.timer'],
                capture_output=True,
                text=True
            )
            
            for line in list_output.stdout.split('\n'):
                if 'plex-metadata-generator.timer' in line:
                    # Parse systemctl output (format varies)
                    parts = line.split()
                    if len(parts) >= 3:
                        result['next_trigger'] = parts[0]
            
            # Get last trigger time
            status = subprocess.run(
                ['systemctl', 'status', 'plex-metadata-generator.service'],
                capture_output=True,
                text=True
            )
            
            if 'Active' in status.stdout:
                # Extract time from status output
                active_line = [l for l in status.stdout.split('\n') if 'Active' in l][0]
                if 'since' in active_line:
                    result['last_trigger'] = active_line.split('since')[-1].strip()
            
            if result['active']:
                print(f"  ✅ Timer is active and enabled")
            else:
                print(f"  ⚠️  Timer is not active")
                
            return result
        except Exception as e:
            print(f"  ⚠️  Could not check systemd timer: {e}")
            return result
    
    def check_cron(self) -> bool:
        """Check if cron job is configured"""
        print("[*] Checking cron job...")
        
        try:
            result = subprocess.run(
                ['sudo', 'crontab', '-l'],
                capture_output=True,
                text=True
            )
            
            if 'plex-metadata-generator' in result.stdout:
                print("  ✅ Cron job is configured")
                
                # Show the cron job
                for line in result.stdout.split('\n'):
                    if 'plex-metadata-generator' in line:
                        print(f"     {line}")
                
                return True
            else:
                print("  ⚠️  No cron job found")
                return False
        except Exception as e:
            print(f"  ⚠️  Could not check cron: {e}")
            return False
    
    def check_logs(self) -> dict:
        """Analyze recent logs"""
        print("[*] Checking logs...")
        
        result = {
            'log_exists': False,
            'recent_entries': 0,
            'errors': 0,
            'warnings': 0,
            'last_run': None,
            'last_success': None,
        }
        
        if not Path(self.log_path).exists():
            print(f"  ⚠️  Log file not found: {self.log_path}")
            return result
        
        result['log_exists'] = True
        
        try:
            with open(self.log_path) as f:
                lines = f.readlines()
            
            # Get last 100 lines
            recent = lines[-100:]
            result['recent_entries'] = len(recent)
            
            errors = [l for l in recent if 'ERROR' in l]
            warnings = [l for l in recent if 'WARNING' in l]
            success = [l for l in recent if 'complete' in l.lower()]
            
            result['errors'] = len(errors)
            result['warnings'] = len(warnings)
            
            if success:
                result['last_success'] = success[-1].split(' - ')[0]
            
            if lines:
                result['last_run'] = lines[-1].split(' - ')[0]
            
            print(f"  ✅ Log file found")
            print(f"     Recent entries: {result['recent_entries']}")
            print(f"     Errors: {result['errors']}")
            print(f"     Warnings: {result['warnings']}")
            
            if result['errors'] > 0:
                print(f"\n     Recent errors:")
                for error in errors[-3:]:
                    print(f"     {error.strip()}")
            
            return result
        except Exception as e:
            print(f"  ❌ Error reading logs: {e}")
            return result
    
    def check_api_connectivity(self) -> dict:
        """Test API connectivity"""
        print("[*] Checking API connectivity...")
        
        result = {
            'tunarr': False,
            'tvdb': False,
            'tmdb': False,
            'fanart_tv': False,
            'plex': False,
        }
        
        try:
            config = json.load(open(self.config_path))
        except:
            print("  ⚠️  Could not load configuration")
            return result
        
        # Test Tunarr
        try:
            db_path = config.get('tunarr', {}).get('db_path')
            if db_path and Path(db_path).exists():
                result['tunarr'] = True
                print(f"  ✅ Tunarr DB accessible")
            else:
                print(f"  ⚠️  Tunarr DB not found at {db_path}")
        except Exception as e:
            print(f"  ❌ Tunarr check failed: {e}")
        
        # Test TVDb
        try:
            import requests
            tvdb_key = config.get('tvdb', {}).get('api_key')
            if tvdb_key and 'YOUR_' not in tvdb_key:
                r = requests.post(
                    'https://api4.thetvdb.com/v4/login',
                    json={'apikey': tvdb_key},
                    timeout=5
                )
                if r.status_code == 200:
                    result['tvdb'] = True
                    print(f"  ✅ TVDb API accessible")
                else:
                    print(f"  ❌ TVDb API returned {r.status_code}")
            else:
                print(f"  ⚠️  TVDb API key not configured")
        except Exception as e:
            print(f"  ❌ TVDb check failed: {e}")
        
        # Test TMDb
        try:
            tmdb_key = config.get('tmdb', {}).get('api_key')
            if tmdb_key and 'YOUR_' not in tmdb_key:
                r = requests.get(
                    f'https://api.themoviedb.org/3/search/tv?api_key={tmdb_key}&query=test',
                    timeout=5
                )
                if r.status_code == 200:
                    result['tmdb'] = True
                    print(f"  ✅ TMDb API accessible")
                else:
                    print(f"  ❌ TMDb API returned {r.status_code}")
            else:
                print(f"  ⚠️  TMDb API key not configured")
        except Exception as e:
            print(f"  ❌ TMDb check failed: {e}")
        
        # Test FanArt.tv
        try:
            fanart_key = config.get('fanart_tv', {}).get('api_key')
            if fanart_key and 'YOUR_' not in fanart_key:
                r = requests.get(
                    f'https://webservice.fanart.tv/v3/movies/550?api_key={fanart_key}',
                    timeout=5
                )
                if r.status_code == 200:
                    result['fanart_tv'] = True
                    print(f"  ✅ FanArt.tv API accessible")
                else:
                    print(f"  ❌ FanArt.tv API returned {r.status_code}")
            else:
                print(f"  ⚠️  FanArt.tv API key not configured (clearart/disc/logo will be skipped)")
        except Exception as e:
            print(f"  ❌ FanArt.tv check failed: {e}")

        # Test Plex
        try:
            plex_url = config.get('plex', {}).get('url', 'http://localhost:32400')
            plex_token = config.get('plex', {}).get('token')
            if plex_token and 'YOUR_' not in plex_token:
                r = requests.get(
                    f'{plex_url}/library/sections',
                    headers={'X-Plex-Token': plex_token},
                    timeout=5
                )
                if r.status_code == 200:
                    result['plex'] = True
                    print(f"  ✅ Plex API accessible")
                else:
                    print(f"  ❌ Plex API returned {r.status_code}")
            else:
                print(f"  ⚠️  Plex token not configured")
        except Exception as e:
            print(f"  ❌ Plex check failed: {e}")

        # Test local MusicBrainz DB (if configured)
        try:
            mb_db_cfg = config.get('musicbrainz_db', {})
            if mb_db_cfg.get('host') or mb_db_cfg.get('dbname'):
                if mb_db_cfg.get('skip') is True:
                    print(f"  ℹ️  Local MusicBrainz DB configured but skip=true — using REST API")
                else:
                    try:
                        import psycopg2  # noqa: PLC0415
                        conn = psycopg2.connect(
                            host=mb_db_cfg.get('host', 'localhost'),
                            port=int(mb_db_cfg.get('port', 5432)),
                            dbname=mb_db_cfg.get('dbname', 'musicbrainz'),
                            user=mb_db_cfg.get('user', 'musicbrainz'),
                            password=mb_db_cfg.get('password', ''),
                            connect_timeout=5,
                        )
                        schema = mb_db_cfg.get('schema', 'musicbrainz')
                        with conn.cursor() as cur:
                            cur.execute(f"SELECT COUNT(*) FROM {schema}.artist")
                            artist_count = cur.fetchone()[0]
                        conn.close()
                        result['musicbrainz_local_db'] = True
                        print(f"  ✅ Local MusicBrainz DB accessible ({artist_count:,} artists)")
                    except ImportError:
                        print(f"  ⚠️  Local MusicBrainz DB configured but psycopg2 not installed\n"
                              f"      Install with: pip install psycopg2-binary")
                    except Exception as e:
                        print(f"  ❌ Local MusicBrainz DB connection failed: {e}")
            else:
                print(f"  ℹ️  Local MusicBrainz DB not configured — using REST API")
        except Exception as e:
            print(f"  ❌ MusicBrainz DB check failed: {e}")

        # Test OpenSubtitles (if configured)
        try:
            sub_cfg = config.get('subtitles', {})
            if sub_cfg.get('enabled'):
                os_key = sub_cfg.get('opensubtitles', {}).get('api_key', '')
                sd_key = sub_cfg.get('subdl', {})
                if os_key and 'YOUR_' not in os_key:
                    r = requests.get(
                        'https://api.opensubtitles.com/api/v1/infos/user',
                        headers={'Api-Key': os_key},
                        timeout=5
                    )
                    if r.status_code in (200, 401):  # 401 = valid key, just not logged in
                        result['opensubtitles'] = True
                        print(f"  ✅ OpenSubtitles API reachable")
                    else:
                        print(f"  ❌ OpenSubtitles API returned {r.status_code}")
                elif not os_key and not sd_key:
                    print(f"  ⚠️  subtitles.enabled=true but no provider keys configured")
                else:
                    print(f"  ⚠️  OpenSubtitles API key not configured — Subdl only")

                # Check ffmpeg availability for embedding
                import shutil as _shutil
                if sub_cfg.get('embed_in_file', True):
                    if _shutil.which('ffmpeg'):
                        print(f"  ✅ ffmpeg found (subtitle embedding available)")
                    else:
                        print(f"  ⚠️  ffmpeg not found — subtitle embedding disabled, sidecar only")
            else:
                print(f"  ℹ️  Subtitles disabled (subtitles.enabled=false)")
        except Exception as e:
            print(f"  ❌ Subtitle check failed: {e}")

        return result
    
    def check_permissions(self) -> bool:
        """Check file permissions"""
        print("[*] Checking permissions...")

        paths = [
            '/var/cache/plex-metadata',
            '/var/log/plex-metadata-generator',
            '/etc/plex-metadata-generator.conf',
        ]

        # Add library roots from config if available
        try:
            config = json.load(open(self.config_path))
            for key in ('library_root', 'tv_library_root', 'movies_library_root', 'music_library_root'):
                v = config.get(key)
                if v:
                    paths.append(v)
        except Exception:
            paths.append('/mnt/media/TV')
        
        all_ok = True
        for path in paths:
            p = Path(path)
            
            if not p.exists():
                print(f"  ⚠️  Does not exist: {path}")
                continue
            
            # Check if readable/writable by current user
            try:
                if p.is_file():
                    with open(p) as f:
                        pass
                else:
                    list(p.iterdir())
                print(f"  ✅ Accessible: {path}")
            except PermissionError:
                print(f"  ❌ Permission denied: {path}")
                all_ok = False
        
        return all_ok
    
    def check_disk_space(self) -> dict:
        """Check available disk space"""
        print("[*] Checking disk space...")
        
        result = {
            'library': None,
            'cache': None,
            'logs': None,
        }
        
        try:
            import shutil
            
            # Library space
            lib_stat = shutil.disk_usage('/mnt/media')
            result['library'] = {
                'total': lib_stat.total,
                'used': lib_stat.used,
                'free': lib_stat.free,
                'percent': (lib_stat.used / lib_stat.total) * 100
            }
            print(f"  Library: {result['library']['percent']:.1f}% used")
            
            # Cache space
            cache_stat = shutil.disk_usage('/var/cache')
            result['cache'] = {
                'total': cache_stat.total,
                'used': cache_stat.used,
                'free': cache_stat.free,
            }
            
            # Log space
            log_stat = shutil.disk_usage('/var/log')
            result['logs'] = {
                'total': log_stat.total,
                'used': log_stat.used,
                'free': log_stat.free,
            }
            
            return result
        except Exception as e:
            print(f"  ⚠️  Could not check disk space: {e}")
            return result
    
    def run_all_checks(self) -> dict:
        """Run all health checks"""
        print("=" * 60)
        print("Plex Metadata Generator - Health Check")
        print(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("=" * 60)
        print()
        
        results = {
            'configuration': self.check_configuration(),
            'systemd': self.check_systemd_timer(),
            'cron': self.check_cron(),
            'logs': self.check_logs(),
            'api': self.check_api_connectivity(),
            'permissions': self.check_permissions(),
            'disk': self.check_disk_space(),
        }
        
        print()
        print("=" * 60)
        print("Health Check Summary")
        print("=" * 60)
        
        # Overall status
        critical_issues = []
        if not results['configuration']:
            critical_issues.append("Configuration invalid or missing")
        if not results['permissions']:
            critical_issues.append("Permission issues detected")
        
        if critical_issues:
            print("❌ CRITICAL ISSUES DETECTED:")
            for issue in critical_issues:
                print(f"   - {issue}")
        else:
            print("✅ No critical issues detected")
        
        print()
        return results


if __name__ == '__main__':
    checker = HealthChecker()
    results = checker.run_all_checks()
