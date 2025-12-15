#!/usr/bin/env python3
"""
Alabama Auction Watcher - Update Manager
Enterprise-grade automatic update system with version checking and secure deployment
"""

import os
import sys
import json
import hashlib
import urllib.request
import urllib.parse
import shutil
import tempfile
import subprocess
from pathlib import Path
from typing import Dict, List, Optional, Tuple
import threading
import time
import ssl
from datetime import datetime, timedelta

class UpdateManager:
    """Professional update management system"""

    def __init__(self, config_file: Optional[Path] = None):
        # Application information
        self.app_name = "Alabama Auction Watcher"
        self.current_version = "1.0.0"
        self.app_dir = Path(__file__).parent.parent

        # Update configuration
        self.config_file = config_file or (self.app_dir / "config" / "update_config.json")
        self.config = self.load_configuration()

        # Update server settings
        self.update_server = self.config.get("update_server", "https://updates.alabamaauctionwatcher.com")
        self.check_interval = self.config.get("check_interval_hours", 24)  # 24 hours
        self.auto_update = self.config.get("auto_update", False)
        self.beta_channel = self.config.get("beta_channel", False)

        # Local paths
        self.update_cache_dir = self.app_dir / "cache" / "updates"
        self.backup_dir = self.app_dir / "backups"
        self.update_log = self.app_dir / "logs" / "update.log"

        # Create necessary directories
        self.update_cache_dir.mkdir(parents=True, exist_ok=True)
        self.backup_dir.mkdir(parents=True, exist_ok=True)
        self.update_log.parent.mkdir(parents=True, exist_ok=True)

        # Update state
        self.last_check = self.load_last_check_time()
        self.available_update = None
        self.update_in_progress = False

    def load_configuration(self) -> Dict:
        """Load update configuration"""
        default_config = {
            "update_server": "https://updates.alabamaauctionwatcher.com",
            "check_interval_hours": 24,
            "auto_update": False,
            "beta_channel": False,
            "backup_count": 3,
            "enterprise_mode": False,
            "allowed_update_window": {
                "start_hour": 2,
                "end_hour": 6
            },
            "notification_preferences": {
                "show_desktop_notifications": True,
                "email_notifications": False,
                "admin_email": ""
            }
        }

        if self.config_file.exists():
            try:
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    user_config = json.load(f)
                    # Merge with defaults
                    default_config.update(user_config)
            except Exception as e:
                self.log_message(f"ERROR: Failed to load config: {e}")

        return default_config

    def save_configuration(self):
        """Save current configuration"""
        try:
            self.config_file.parent.mkdir(parents=True, exist_ok=True)
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(self.config, f, indent=2)
        except Exception as e:
            self.log_message(f"ERROR: Failed to save config: {e}")

    def log_message(self, message: str):
        """Log update messages"""
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        log_entry = f"[{timestamp}] {message}\n"

        print(log_entry.strip())  # Console output

        try:
            with open(self.update_log, 'a', encoding='utf-8') as f:
                f.write(log_entry)
        except Exception:
            pass  # Don't fail if logging fails

    def load_last_check_time(self) -> Optional[datetime]:
        """Load last update check time"""
        check_file = self.update_cache_dir / "last_check.json"

        if check_file.exists():
            try:
                with open(check_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    return datetime.fromisoformat(data['last_check'])
            except Exception:
                pass

        return None

    def save_last_check_time(self):
        """Save last update check time"""
        check_file = self.update_cache_dir / "last_check.json"

        try:
            with open(check_file, 'w', encoding='utf-8') as f:
                json.dump({
                    'last_check': datetime.now().isoformat(),
                    'version_checked': self.current_version
                }, f, indent=2)
        except Exception as e:
            self.log_message(f"ERROR: Failed to save check time: {e}")

    def should_check_for_updates(self) -> bool:
        """Determine if we should check for updates"""
        if self.last_check is None:
            return True

        time_since_check = datetime.now() - self.last_check
        return time_since_check > timedelta(hours=self.check_interval)

    def get_version_info_url(self) -> str:
        """Get version information URL"""
        channel = "beta" if self.beta_channel else "stable"
        platform = self.get_platform_name()
        return f"{self.update_server}/api/v1/version/{channel}/{platform}"

    def get_platform_name(self) -> str:
        """Get current platform name"""
        if sys.platform.startswith('win'):
            return 'windows'
        elif sys.platform == 'darwin':
            return 'macos'
        else:
            return 'linux'

    def compare_versions(self, version1: str, version2: str) -> int:
        """Compare two version strings
        Returns: -1 if version1 < version2, 0 if equal, 1 if version1 > version2
        """
        def version_tuple(version):
            return tuple(map(int, version.split('.')))

        v1 = version_tuple(version1)
        v2 = version_tuple(version2)

        if v1 < v2:
            return -1
        elif v1 > v2:
            return 1
        else:
            return 0

    def check_for_updates(self) -> Optional[Dict]:
        """Check for available updates"""
        self.log_message("Checking for updates...")

        try:
            # Create SSL context for secure connections
            context = ssl.create_default_context()

            # Get version information
            version_url = self.get_version_info_url()
            self.log_message(f"Checking: {version_url}")

            request = urllib.request.Request(version_url)
            request.add_header('User-Agent', f'AlabamaAuctionWatcher/{self.current_version}')

            with urllib.request.urlopen(request, context=context, timeout=30) as response:
                if response.status != 200:
                    self.log_message(f"ERROR: Server returned status {response.status}")
                    return None

                data = json.loads(response.read().decode('utf-8'))

            # Parse response
            latest_version = data.get('version')
            download_url = data.get('download_url')
            changelog = data.get('changelog', '')
            checksum = data.get('sha256_checksum')
            file_size = data.get('file_size', 0)
            release_date = data.get('release_date')
            critical_update = data.get('critical', False)

            if not latest_version or not download_url:
                self.log_message("ERROR: Invalid response from update server")
                return None

            # Compare versions
            comparison = self.compare_versions(self.current_version, latest_version)

            if comparison < 0:  # New version available
                update_info = {
                    'version': latest_version,
                    'download_url': download_url,
                    'changelog': changelog,
                    'checksum': checksum,
                    'file_size': file_size,
                    'release_date': release_date,
                    'critical': critical_update,
                    'platform': self.get_platform_name()
                }

                self.log_message(f"Update available: {latest_version} (current: {self.current_version})")
                self.available_update = update_info
                self.save_last_check_time()
                return update_info

            else:
                self.log_message("Application is up to date")
                self.save_last_check_time()
                return None

        except urllib.error.HTTPError as e:
            self.log_message(f"ERROR: HTTP {e.code} - {e.reason}")
            return None
        except urllib.error.URLError as e:
            self.log_message(f"ERROR: Network error - {e.reason}")
            return None
        except json.JSONDecodeError as e:
            self.log_message(f"ERROR: Invalid JSON response - {e}")
            return None
        except Exception as e:
            self.log_message(f"ERROR: Update check failed - {e}")
            return None

    def download_update(self, update_info: Dict) -> Optional[Path]:
        """Download update package"""
        self.log_message(f"Downloading update {update_info['version']}...")

        try:
            download_url = update_info['download_url']
            file_size = update_info.get('file_size', 0)
            expected_checksum = update_info.get('checksum')

            # Generate local filename
            url_path = urllib.parse.urlparse(download_url).path
            filename = Path(url_path).name or f"update_{update_info['version']}.pkg"
            local_path = self.update_cache_dir / filename

            # Create progress callback
            def progress_callback(downloaded: int, total: int):
                if total > 0:
                    percent = (downloaded / total) * 100
                    self.log_message(f"Download progress: {percent:.1f}% ({downloaded}/{total} bytes)")

            # Download file with progress tracking
            context = ssl.create_default_context()
            request = urllib.request.Request(download_url)
            request.add_header('User-Agent', f'AlabamaAuctionWatcher/{self.current_version}')

            with urllib.request.urlopen(request, context=context, timeout=60) as response:
                total_size = int(response.headers.get('Content-Length', 0)) or file_size
                downloaded = 0

                with open(local_path, 'wb') as f:
                    while True:
                        chunk = response.read(8192)  # 8KB chunks
                        if not chunk:
                            break

                        f.write(chunk)
                        downloaded += len(chunk)

                        # Report progress every 1MB
                        if downloaded % (1024 * 1024) == 0:
                            progress_callback(downloaded, total_size)

            self.log_message(f"Download completed: {local_path}")

            # Verify checksum if provided
            if expected_checksum:
                if self.verify_file_checksum(local_path, expected_checksum):
                    self.log_message("Checksum verification passed")
                else:
                    self.log_message("ERROR: Checksum verification failed")
                    local_path.unlink()  # Delete corrupted file
                    return None

            return local_path

        except Exception as e:
            self.log_message(f"ERROR: Download failed - {e}")
            return None

    def verify_file_checksum(self, file_path: Path, expected_checksum: str) -> bool:
        """Verify file SHA-256 checksum"""
        try:
            hash_sha256 = hashlib.sha256()
            with open(file_path, 'rb') as f:
                for chunk in iter(lambda: f.read(4096), b""):
                    hash_sha256.update(chunk)

            actual_checksum = hash_sha256.hexdigest()
            return actual_checksum.lower() == expected_checksum.lower()

        except Exception as e:
            self.log_message(f"ERROR: Checksum verification failed - {e}")
            return False

    def create_backup(self) -> Optional[Path]:
        """Create backup of current installation"""
        self.log_message("Creating installation backup...")

        try:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            backup_name = f"backup_{self.current_version}_{timestamp}"
            backup_path = self.backup_dir / backup_name

            # Create backup archive
            if sys.platform.startswith('win'):
                # Windows: Use built-in tools or Python zipfile
                import zipfile
                zip_path = self.backup_dir / f"{backup_name}.zip"

                with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
                    for root, dirs, files in os.walk(self.app_dir):
                        # Skip backup and cache directories
                        if 'backups' in Path(root).parts or 'cache' in Path(root).parts:
                            continue

                        for file in files:
                            file_path = Path(root) / file
                            archive_name = file_path.relative_to(self.app_dir)
                            zipf.write(file_path, archive_name)

                self.log_message(f"Backup created: {zip_path}")
                return zip_path

            else:
                # Unix-like: Use tar
                tar_path = self.backup_dir / f"{backup_name}.tar.gz"
                cmd = [
                    'tar', '-czf', str(tar_path),
                    '--exclude=backups',
                    '--exclude=cache',
                    '--exclude=logs',
                    '-C', str(self.app_dir.parent),
                    self.app_dir.name
                ]

                result = subprocess.run(cmd, capture_output=True, text=True)
                if result.returncode == 0:
                    self.log_message(f"Backup created: {tar_path}")
                    return tar_path
                else:
                    self.log_message(f"ERROR: Backup failed - {result.stderr}")
                    return None

        except Exception as e:
            self.log_message(f"ERROR: Backup creation failed - {e}")
            return None

    def apply_update(self, update_package: Path, backup_path: Optional[Path] = None) -> bool:
        """Apply downloaded update"""
        self.log_message(f"Applying update from {update_package}")
        self.update_in_progress = True

        try:
            platform = self.get_platform_name()

            if platform == 'windows':
                return self.apply_windows_update(update_package)
            elif platform == 'macos':
                return self.apply_macos_update(update_package)
            else:  # Linux
                return self.apply_linux_update(update_package)

        except Exception as e:
            self.log_message(f"ERROR: Update application failed - {e}")
            return False
        finally:
            self.update_in_progress = False

    def apply_windows_update(self, update_package: Path) -> bool:
        """Apply Windows update"""
        try:
            # For .msi packages
            if update_package.suffix.lower() == '.msi':
                cmd = [
                    'msiexec', '/i', str(update_package),
                    '/quiet', '/norestart',
                    f'INSTALLLOCATION={self.app_dir}'
                ]

                result = subprocess.run(cmd, capture_output=True, text=True)
                success = result.returncode == 0

                if success:
                    self.log_message("Windows update completed successfully")
                else:
                    self.log_message(f"Windows update failed: {result.stderr}")

                return success

            else:
                self.log_message(f"ERROR: Unsupported update package format: {update_package.suffix}")
                return False

        except Exception as e:
            self.log_message(f"ERROR: Windows update failed - {e}")
            return False

    def apply_macos_update(self, update_package: Path) -> bool:
        """Apply macOS update"""
        try:
            # For .pkg packages
            if update_package.suffix.lower() == '.pkg':
                cmd = [
                    'sudo', 'installer',
                    '-package', str(update_package),
                    '-target', '/'
                ]

                result = subprocess.run(cmd, capture_output=True, text=True)
                success = result.returncode == 0

                if success:
                    self.log_message("macOS update completed successfully")
                else:
                    self.log_message(f"macOS update failed: {result.stderr}")

                return success

            else:
                self.log_message(f"ERROR: Unsupported update package format: {update_package.suffix}")
                return False

        except Exception as e:
            self.log_message(f"ERROR: macOS update failed - {e}")
            return False

    def apply_linux_update(self, update_package: Path) -> bool:
        """Apply Linux update"""
        try:
            # For .deb packages
            if update_package.suffix.lower() == '.deb':
                cmd = ['sudo', 'dpkg', '-i', str(update_package)]
                result = subprocess.run(cmd, capture_output=True, text=True)

                if result.returncode != 0:
                    # Try to fix dependencies
                    self.log_message("Fixing dependencies...")
                    subprocess.run(['sudo', 'apt-get', 'install', '-f'], capture_output=True)

                success = result.returncode == 0

            # For .rpm packages
            elif update_package.suffix.lower() == '.rpm':
                cmd = ['sudo', 'rpm', '-U', str(update_package)]
                result = subprocess.run(cmd, capture_output=True, text=True)
                success = result.returncode == 0

            else:
                self.log_message(f"ERROR: Unsupported update package format: {update_package.suffix}")
                return False

            if success:
                self.log_message("Linux update completed successfully")
            else:
                self.log_message(f"Linux update failed: {result.stderr}")

            return success

        except Exception as e:
            self.log_message(f"ERROR: Linux update failed - {e}")
            return False

    def cleanup_old_backups(self):
        """Clean up old backup files"""
        max_backups = self.config.get("backup_count", 3)

        try:
            # Get all backup files
            backup_files = []
            for pattern in ['backup_*.zip', 'backup_*.tar.gz']:
                backup_files.extend(self.backup_dir.glob(pattern))

            # Sort by modification time (newest first)
            backup_files.sort(key=lambda x: x.stat().st_mtime, reverse=True)

            # Remove excess backups
            for backup_file in backup_files[max_backups:]:
                backup_file.unlink()
                self.log_message(f"Removed old backup: {backup_file.name}")

        except Exception as e:
            self.log_message(f"ERROR: Backup cleanup failed - {e}")

    def is_update_window_open(self) -> bool:
        """Check if we're in the allowed update window"""
        if not self.config.get("enterprise_mode", False):
            return True  # No restrictions in non-enterprise mode

        now = datetime.now()
        window = self.config.get("allowed_update_window", {"start_hour": 2, "end_hour": 6})
        start_hour = window["start_hour"]
        end_hour = window["end_hour"]

        current_hour = now.hour

        if start_hour <= end_hour:
            return start_hour <= current_hour <= end_hour
        else:  # Window crosses midnight
            return current_hour >= start_hour or current_hour <= end_hour

    def update_workflow(self) -> Dict:
        """Complete update workflow"""
        result = {
            "success": False,
            "update_available": False,
            "update_applied": False,
            "version_before": self.current_version,
            "version_after": self.current_version,
            "message": "",
            "error": None
        }

        try:
            # Check if update is needed
            if not self.should_check_for_updates():
                result["message"] = "Update check not due yet"
                return result

            # Check for updates
            update_info = self.check_for_updates()
            if not update_info:
                result["message"] = "No updates available"
                result["success"] = True
                return result

            result["update_available"] = True
            result["message"] = f"Update available: {update_info['version']}"

            # Check if we should auto-update
            if not self.auto_update:
                result["message"] += " (auto-update disabled)"
                result["success"] = True
                return result

            # Check update window for enterprise mode
            if not self.is_update_window_open():
                result["message"] += " (outside update window)"
                result["success"] = True
                return result

            # Download update
            self.log_message("Starting automatic update process...")
            update_package = self.download_update(update_info)
            if not update_package:
                result["error"] = "Failed to download update"
                return result

            # Create backup
            backup_path = self.create_backup()
            if not backup_path:
                result["error"] = "Failed to create backup"
                return result

            # Apply update
            if self.apply_update(update_package, backup_path):
                result["success"] = True
                result["update_applied"] = True
                result["version_after"] = update_info["version"]
                result["message"] = f"Successfully updated to {update_info['version']}"

                # Cleanup
                self.cleanup_old_backups()
                update_package.unlink()  # Remove downloaded package

            else:
                result["error"] = "Failed to apply update"

        except Exception as e:
            result["error"] = f"Update workflow failed: {e}"
            self.log_message(f"ERROR: {result['error']}")

        return result

def main():
    """Main update manager execution"""
    import argparse

    parser = argparse.ArgumentParser(description='Alabama Auction Watcher Update Manager')
    parser.add_argument('--check', action='store_true', help='Check for updates')
    parser.add_argument('--apply', action='store_true', help='Apply available updates')
    parser.add_argument('--force', action='store_true', help='Force update check')
    parser.add_argument('--config', type=Path, help='Configuration file path')
    parser.add_argument('--daemon', action='store_true', help='Run as background daemon')

    args = parser.parse_args()

    updater = UpdateManager(args.config)

    if args.daemon:
        updater.log_message("Starting update daemon...")
        while True:
            result = updater.update_workflow()
            if result.get("error"):
                updater.log_message(f"Update daemon error: {result['error']}")

            # Sleep for check interval
            time.sleep(updater.check_interval * 3600)  # Convert hours to seconds

    elif args.check or args.force:
        if args.force:
            updater.last_check = None  # Force check

        update_info = updater.check_for_updates()
        if update_info:
            print(f"Update available: {update_info['version']}")
            print(f"Current version: {updater.current_version}")
            print(f"Release date: {update_info.get('release_date', 'Unknown')}")
            print(f"Critical: {update_info.get('critical', False)}")
            if update_info.get('changelog'):
                print(f"Changelog:\n{update_info['changelog']}")
        else:
            print("No updates available")

    elif args.apply:
        result = updater.update_workflow()
        print(f"Update result: {result['message']}")
        if result.get("error"):
            print(f"Error: {result['error']}")
            sys.exit(1)

    else:
        result = updater.update_workflow()
        print(json.dumps(result, indent=2))

if __name__ == '__main__':
    main()