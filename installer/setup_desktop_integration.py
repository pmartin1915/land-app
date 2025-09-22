#!/usr/bin/env python3
"""
Alabama Auction Watcher Desktop Integration Setup
Automated installer for creating desktop shortcuts, start menu entries,
and system integration across Windows, macOS, and Linux platforms.

Features:
- Cross-platform desktop shortcut creation
- Start menu/Applications folder integration
- File association setup (optional)
- Auto-startup configuration
- Uninstallation support
- Registry integration (Windows)
- Launch Services integration (macOS)
- FreeDesktop integration (Linux)
"""

import os
import sys
import platform
import shutil
import json
import logging
from pathlib import Path
from typing import Dict, List, Optional, Tuple
import subprocess

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class DesktopIntegrationInstaller:
    """Handles desktop integration installation across platforms"""

    def __init__(self):
        self.platform = platform.system()
        self.script_dir = Path(__file__).parent.parent.absolute()
        self.app_name = "Alabama Auction Watcher"
        self.app_id = "alabama-auction-watcher"

        # Installation configuration
        self.config = {
            'app_name': self.app_name,
            'app_id': self.app_id,
            'version': '1.0.0',
            'description': 'Interactive dashboard for analyzing Alabama tax delinquent property auctions',
            'author': 'Alabama Auction Watcher Team',
            'website': 'https://github.com/yourusername/alabama-auction-watcher',
            'install_date': None,
            'shortcuts': {
                'main_app': {
                    'name': 'Alabama Auction Watcher',
                    'description': 'Main interactive dashboard',
                    'icon': 'main_app.ico'
                },
                'backend_api': {
                    'name': 'Alabama Auction Watcher API',
                    'description': 'Backend API server',
                    'icon': 'backend_api.ico'
                },
                'enhanced_dashboard': {
                    'name': 'Alabama Auction Watcher Enhanced',
                    'description': 'Enhanced dashboard with AI monitoring',
                    'icon': 'enhanced_dashboard.ico'
                },
                'health_check': {
                    'name': 'Alabama Auction Watcher Health Check',
                    'description': 'System health diagnostics',
                    'icon': 'health_check.ico'
                },
                'smart_launcher': {
                    'name': 'Alabama Auction Watcher Launcher',
                    'description': 'Smart GUI launcher and system manager',
                    'icon': 'main_app.ico'
                }
            }
        }

    def install(self, create_desktop_shortcuts: bool = True,
                create_start_menu: bool = True,
                create_file_associations: bool = False,
                enable_auto_startup: bool = False) -> bool:
        """Main installation method"""
        try:
            logger.info(f"Starting desktop integration installation on {self.platform}")

            # Create installation record
            self.config['install_date'] = self._get_current_timestamp()

            success = True

            if create_desktop_shortcuts:
                success &= self._create_desktop_shortcuts()

            if create_start_menu:
                success &= self._create_start_menu_entries()

            if create_file_associations:
                success &= self._create_file_associations()

            if enable_auto_startup:
                success &= self._setup_auto_startup()

            # Save installation configuration
            success &= self._save_installation_config()

            if success:
                logger.info("Desktop integration installation completed successfully")
                return True
            else:
                logger.error("Desktop integration installation completed with errors")
                return False

        except Exception as e:
            logger.error(f"Installation failed: {e}")
            return False

    def uninstall(self) -> bool:
        """Remove all desktop integration"""
        try:
            logger.info("Starting desktop integration uninstallation")

            success = True
            success &= self._remove_desktop_shortcuts()
            success &= self._remove_start_menu_entries()
            success &= self._remove_file_associations()
            success &= self._remove_auto_startup()
            success &= self._cleanup_installation_files()

            if success:
                logger.info("Desktop integration uninstallation completed successfully")
            else:
                logger.error("Desktop integration uninstallation completed with errors")

            return success

        except Exception as e:
            logger.error(f"Uninstallation failed: {e}")
            return False

    # Platform-specific desktop shortcut creation
    def _create_desktop_shortcuts(self) -> bool:
        """Create desktop shortcuts for all platforms"""
        try:
            if self.platform == "Windows":
                return self._create_windows_shortcuts()
            elif self.platform == "Darwin":  # macOS
                return self._create_macos_shortcuts()
            else:  # Linux
                return self._create_linux_shortcuts()
        except Exception as e:
            logger.error(f"Error creating desktop shortcuts: {e}")
            return False

    def _create_windows_shortcuts(self) -> bool:
        """Create Windows desktop shortcuts and start menu entries"""
        try:
            import winshell
            from win32com.client import Dispatch

            desktop = winshell.desktop()
            start_menu = winshell.start_menu()

            shell = Dispatch('WScript.Shell')

            success = True

            for shortcut_id, shortcut_config in self.config['shortcuts'].items():
                try:
                    # Desktop shortcut
                    desktop_path = os.path.join(desktop, f"{shortcut_config['name']}.lnk")
                    shortcut = shell.CreateShortCut(desktop_path)

                    if shortcut_id == 'smart_launcher':
                        # Smart launcher uses Python to run the GUI
                        shortcut.Targetpath = sys.executable
                        shortcut.Arguments = str(self.script_dir / "launchers" / "cross_platform" / "smart_launcher.py")
                    else:
                        # Other shortcuts use batch files
                        if shortcut_id == 'main_app':
                            target = self.script_dir / "launchers" / "windows" / "launch_main_app.bat"
                        elif shortcut_id == 'backend_api':
                            target = self.script_dir / "launchers" / "windows" / "launch_backend_api.bat"
                        elif shortcut_id == 'enhanced_dashboard':
                            target = self.script_dir / "launchers" / "windows" / "launch_enhanced_dashboard.bat"
                        elif shortcut_id == 'health_check':
                            target = self.script_dir / "launchers" / "windows" / "health_check.bat"

                        shortcut.Targetpath = str(target)

                    shortcut.WorkingDirectory = str(self.script_dir)
                    shortcut.Description = shortcut_config['description']

                    # Set icon if available
                    icon_path = self.script_dir / "icons" / shortcut_config['icon']
                    if icon_path.exists():
                        shortcut.IconLocation = str(icon_path)

                    shortcut.save()

                    # Start menu shortcut
                    start_menu_path = os.path.join(start_menu, "Programs", self.app_name)
                    os.makedirs(start_menu_path, exist_ok=True)

                    start_shortcut_path = os.path.join(start_menu_path, f"{shortcut_config['name']}.lnk")
                    start_shortcut = shell.CreateShortCut(start_shortcut_path)
                    start_shortcut.Targetpath = shortcut.Targetpath
                    start_shortcut.Arguments = shortcut.Arguments
                    start_shortcut.WorkingDirectory = shortcut.WorkingDirectory
                    start_shortcut.Description = shortcut.Description
                    start_shortcut.IconLocation = shortcut.IconLocation
                    start_shortcut.save()

                    logger.info(f"Created Windows shortcut: {shortcut_config['name']}")

                except Exception as e:
                    logger.error(f"Error creating Windows shortcut {shortcut_config['name']}: {e}")
                    success = False

            return success

        except ImportError:
            logger.warning("Windows shortcut creation requires pywin32 and winshell packages")
            logger.info("Install with: pip install -r requirements-windows.txt")
            logger.info("Falling back to VBScript method...")
            return self._create_windows_shortcuts_fallback()

    def _create_windows_shortcuts_fallback(self) -> bool:
        """Fallback Windows shortcut creation using VBScript (no external dependencies)"""
        try:
            logger.info("Using VBScript fallback method for Windows shortcuts")

            desktop = Path.home() / "Desktop"

            shortcuts = []
            for shortcut_id, shortcut_config in self.config['shortcuts'].items():
                if shortcut_id == 'smart_launcher':
                    # Use batch file for smart launcher
                    target = str(self.script_dir / "launchers" / "windows" / "launch_smart_launcher.bat")
                else:
                    # Use appropriate batch files for other shortcuts
                    if shortcut_id == 'main_app':
                        target = str(self.script_dir / "launchers" / "windows" / "launch_main_app.bat")
                    elif shortcut_id == 'backend_api':
                        target = str(self.script_dir / "launchers" / "windows" / "launch_backend_api.bat")
                    elif shortcut_id == 'enhanced_dashboard':
                        target = str(self.script_dir / "launchers" / "windows" / "launch_enhanced_dashboard.bat")
                    elif shortcut_id == 'health_check':
                        target = str(self.script_dir / "launchers" / "windows" / "health_check.bat")
                    else:
                        continue

                shortcuts.append({
                    'name': shortcut_config['name'],
                    'target': target,
                    'description': shortcut_config['description']
                })

            success = True
            for shortcut in shortcuts:
                try:
                    vbs_content = f'''
Set oWS = WScript.CreateObject("WScript.Shell")
sLinkFile = "{desktop / (shortcut['name'] + '.lnk')}"
Set oLink = oWS.CreateShortcut(sLinkFile)
oLink.TargetPath = "{shortcut['target']}"
oLink.WorkingDirectory = "{self.script_dir}"
oLink.Description = "{shortcut['description']}"
oLink.Save
'''
                    # Create temporary VBS file
                    vbs_file = self.script_dir / f"temp_shortcut_{shortcut['name'].replace(' ', '_')}.vbs"
                    with open(vbs_file, 'w') as f:
                        f.write(vbs_content)

                    # Execute VBS file
                    import subprocess
                    result = subprocess.run(['cscript', '//nologo', str(vbs_file)],
                                          capture_output=True, text=True)

                    # Clean up VBS file
                    vbs_file.unlink()

                    if result.returncode == 0:
                        logger.info(f"Created desktop shortcut (VBScript): {shortcut['name']}")
                    else:
                        logger.error(f"Failed to create shortcut: {shortcut['name']} - {result.stderr}")
                        success = False

                except Exception as e:
                    logger.error(f"Error creating VBScript shortcut {shortcut['name']}: {e}")
                    success = False

            if success:
                logger.info("VBScript fallback completed successfully - desktop shortcuts created")
                logger.warning("Start Menu integration not available without winshell package")

            return success

        except Exception as e:
            logger.error(f"VBScript fallback failed: {e}")
            return False

    def _create_macos_shortcuts(self) -> bool:
        """Create macOS application shortcuts and dock entries"""
        try:
            # For macOS, we create .app bundles and add to Applications
            applications_dir = Path.home() / "Applications"
            applications_dir.mkdir(exist_ok=True)

            success = True

            for shortcut_id, shortcut_config in self.config['shortcuts'].items():
                try:
                    app_name = f"{shortcut_config['name']}.app"
                    app_path = applications_dir / app_name

                    # Create .app bundle structure
                    contents_dir = app_path / "Contents"
                    macos_dir = contents_dir / "MacOS"
                    resources_dir = contents_dir / "Resources"

                    for dir_path in [app_path, contents_dir, macos_dir, resources_dir]:
                        dir_path.mkdir(parents=True, exist_ok=True)

                    # Create Info.plist
                    plist_content = f'''<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>CFBundleExecutable</key>
    <string>{shortcut_id}_launcher</string>
    <key>CFBundleIdentifier</key>
    <string>com.alabamaauctionwatcher.{shortcut_id}</string>
    <key>CFBundleName</key>
    <string>{shortcut_config['name']}</string>
    <key>CFBundleVersion</key>
    <string>{self.config['version']}</string>
    <key>CFBundleShortVersionString</key>
    <string>{self.config['version']}</string>
    <key>CFBundlePackageType</key>
    <string>APPL</string>
    <key>CFBundleSignature</key>
    <string>ALAU</string>
</dict>
</plist>'''

                    with open(contents_dir / "Info.plist", 'w') as f:
                        f.write(plist_content)

                    # Create launcher script
                    launcher_script = macos_dir / f"{shortcut_id}_launcher"

                    if shortcut_id == 'smart_launcher':
                        script_content = f'''#!/bin/bash
cd "{self.script_dir}"
{sys.executable} "launchers/cross_platform/smart_launcher.py"
'''
                    else:
                        if shortcut_id == 'main_app':
                            command_file = "launch_main_app.command"
                        elif shortcut_id == 'backend_api':
                            command_file = "launch_backend_api.command"
                        elif shortcut_id == 'enhanced_dashboard':
                            command_file = "launch_enhanced_dashboard.command"
                        elif shortcut_id == 'health_check':
                            command_file = "health_check.command"  # We'd need to create this
                        else:
                            command_file = "launch_main_app.command"

                        script_content = f'''#!/bin/bash
cd "{self.script_dir}"
bash "launchers/macos/{command_file}"
'''

                    with open(launcher_script, 'w') as f:
                        f.write(script_content)

                    # Make launcher executable
                    launcher_script.chmod(0o755)

                    logger.info(f"Created macOS app: {shortcut_config['name']}")

                except Exception as e:
                    logger.error(f"Error creating macOS app {shortcut_config['name']}: {e}")
                    success = False

            return success

        except Exception as e:
            logger.error(f"Error creating macOS shortcuts: {e}")
            return False

    def _create_linux_shortcuts(self) -> bool:
        """Create Linux .desktop files and application menu entries"""
        try:
            # Desktop directory
            desktop_dir = Path.home() / "Desktop"
            # Applications directory
            apps_dir = Path.home() / ".local" / "share" / "applications"
            apps_dir.mkdir(parents=True, exist_ok=True)

            success = True

            for shortcut_id, shortcut_config in self.config['shortcuts'].items():
                try:
                    desktop_filename = f"{self.app_id}-{shortcut_id}.desktop"

                    if shortcut_id == 'smart_launcher':
                        exec_command = f'{sys.executable} "{self.script_dir}/launchers/cross_platform/smart_launcher.py"'
                    else:
                        if shortcut_id == 'main_app':
                            script_file = "launch_main_app.sh"
                        elif shortcut_id == 'backend_api':
                            script_file = "launch_backend_api.sh"
                        elif shortcut_id == 'enhanced_dashboard':
                            script_file = "launch_enhanced_dashboard.sh"
                        elif shortcut_id == 'health_check':
                            script_file = "health_check.sh"
                        else:
                            script_file = "launch_main_app.sh"

                        exec_command = f'bash "{self.script_dir}/launchers/linux/launch_scripts/{script_file}"'

                    desktop_content = f'''[Desktop Entry]
Version=1.0
Type=Application
Name={shortcut_config['name']}
Comment={shortcut_config['description']}
Exec={exec_command}
Icon={self.script_dir}/icons/{shortcut_config['icon']}
Terminal=true
Categories=Office;Finance;Development;
Keywords=auction;property;investment;alabama;
StartupNotify=true
'''

                    # Create desktop shortcut
                    if desktop_dir.exists():
                        desktop_file = desktop_dir / desktop_filename
                        with open(desktop_file, 'w') as f:
                            f.write(desktop_content)
                        desktop_file.chmod(0o755)

                    # Create applications menu entry
                    apps_file = apps_dir / desktop_filename
                    with open(apps_file, 'w') as f:
                        f.write(desktop_content)
                    apps_file.chmod(0o755)

                    logger.info(f"Created Linux desktop file: {shortcut_config['name']}")

                except Exception as e:
                    logger.error(f"Error creating Linux desktop file {shortcut_config['name']}: {e}")
                    success = False

            # Update desktop database
            try:
                subprocess.run(["update-desktop-database", str(apps_dir)], check=False)
            except FileNotFoundError:
                pass  # update-desktop-database might not be available

            return success

        except Exception as e:
            logger.error(f"Error creating Linux shortcuts: {e}")
            return False

    # Start menu/Applications folder integration
    def _create_start_menu_entries(self) -> bool:
        """Create start menu entries (handled in platform-specific methods)"""
        # This is handled within the platform-specific shortcut creation methods
        return True

    # File associations
    def _create_file_associations(self) -> bool:
        """Create file associations for .csv files (optional)"""
        try:
            if self.platform == "Windows":
                return self._create_windows_file_associations()
            elif self.platform == "Darwin":  # macOS
                return self._create_macos_file_associations()
            else:  # Linux
                return self._create_linux_file_associations()
        except Exception as e:
            logger.error(f"Error creating file associations: {e}")
            return False

    def _create_windows_file_associations(self) -> bool:
        """Create Windows registry entries for file associations"""
        # This would require registry modification - implement if needed
        logger.info("Windows file associations not implemented")
        return True

    def _create_macos_file_associations(self) -> bool:
        """Create macOS file associations"""
        # This would require modifying Info.plist files - implement if needed
        logger.info("macOS file associations not implemented")
        return True

    def _create_linux_file_associations(self) -> bool:
        """Create Linux MIME type associations"""
        # This would require creating .desktop MIME entries - implement if needed
        logger.info("Linux file associations not implemented")
        return True

    # Auto-startup configuration
    def _setup_auto_startup(self) -> bool:
        """Setup auto-startup for the system tray"""
        try:
            if self.platform == "Windows":
                return self._setup_windows_auto_startup()
            elif self.platform == "Darwin":  # macOS
                return self._setup_macos_auto_startup()
            else:  # Linux
                return self._setup_linux_auto_startup()
        except Exception as e:
            logger.error(f"Error setting up auto-startup: {e}")
            return False

    def _setup_windows_auto_startup(self) -> bool:
        """Setup Windows auto-startup via registry"""
        try:
            import winreg as reg

            key_path = r"SOFTWARE\Microsoft\Windows\CurrentVersion\Run"
            key = reg.OpenKey(reg.HKEY_CURRENT_USER, key_path, 0, reg.KEY_SET_VALUE)

            startup_command = f'"{sys.executable}" "{self.script_dir}/launchers/cross_platform/system_tray.py"'
            reg.SetValueEx(key, self.app_id, 0, reg.REG_SZ, startup_command)
            reg.CloseKey(key)

            logger.info("Windows auto-startup configured")
            return True

        except ImportError:
            logger.error("Windows auto-startup requires winreg module")
            return False
        except Exception as e:
            logger.error(f"Error setting up Windows auto-startup: {e}")
            return False

    def _setup_macos_auto_startup(self) -> bool:
        """Setup macOS auto-startup via launchd"""
        try:
            launchagents_dir = Path.home() / "Library" / "LaunchAgents"
            launchagents_dir.mkdir(parents=True, exist_ok=True)

            plist_file = launchagents_dir / f"com.alabamaauctionwatcher.systemtray.plist"

            plist_content = f'''<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.alabamaauctionwatcher.systemtray</string>
    <key>ProgramArguments</key>
    <array>
        <string>{sys.executable}</string>
        <string>{self.script_dir}/launchers/cross_platform/system_tray.py</string>
    </array>
    <key>RunAtLoad</key>
    <true/>
    <key>KeepAlive</key>
    <false/>
</dict>
</plist>'''

            with open(plist_file, 'w') as f:
                f.write(plist_content)

            logger.info("macOS auto-startup configured")
            return True

        except Exception as e:
            logger.error(f"Error setting up macOS auto-startup: {e}")
            return False

    def _setup_linux_auto_startup(self) -> bool:
        """Setup Linux auto-startup via .desktop autostart"""
        try:
            autostart_dir = Path.home() / ".config" / "autostart"
            autostart_dir.mkdir(parents=True, exist_ok=True)

            desktop_file = autostart_dir / f"{self.app_id}-systemtray.desktop"

            desktop_content = f'''[Desktop Entry]
Type=Application
Name=Alabama Auction Watcher System Tray
Comment=System tray for Alabama Auction Watcher
Exec={sys.executable} "{self.script_dir}/launchers/cross_platform/system_tray.py"
Icon={self.script_dir}/icons/main_app.ico
Hidden=false
NoDisplay=false
X-GNOME-Autostart-enabled=true
StartupNotify=false
'''

            with open(desktop_file, 'w') as f:
                f.write(desktop_content)

            desktop_file.chmod(0o755)

            logger.info("Linux auto-startup configured")
            return True

        except Exception as e:
            logger.error(f"Error setting up Linux auto-startup: {e}")
            return False

    # Cleanup and uninstallation methods
    def _remove_desktop_shortcuts(self) -> bool:
        """Remove desktop shortcuts"""
        success = True
        try:
            if self.platform == "Windows":
                success = self._remove_windows_shortcuts()
            elif self.platform == "Darwin":  # macOS
                success = self._remove_macos_shortcuts()
            else:  # Linux
                success = self._remove_linux_shortcuts()
        except Exception as e:
            logger.error(f"Error removing desktop shortcuts: {e}")
            success = False
        return success

    def _remove_windows_shortcuts(self) -> bool:
        """Remove Windows shortcuts"""
        try:
            import winshell

            desktop = winshell.desktop()
            start_menu = winshell.start_menu()

            success = True

            # Remove desktop shortcuts
            for shortcut_config in self.config['shortcuts'].values():
                shortcut_path = os.path.join(desktop, f"{shortcut_config['name']}.lnk")
                if os.path.exists(shortcut_path):
                    os.remove(shortcut_path)

            # Remove start menu folder
            start_menu_path = os.path.join(start_menu, "Programs", self.app_name)
            if os.path.exists(start_menu_path):
                shutil.rmtree(start_menu_path)

            return success

        except ImportError:
            logger.error("Windows shortcut removal requires winshell package")
            return False

    def _remove_macos_shortcuts(self) -> bool:
        """Remove macOS .app bundles"""
        try:
            applications_dir = Path.home() / "Applications"
            success = True

            for shortcut_config in self.config['shortcuts'].values():
                app_path = applications_dir / f"{shortcut_config['name']}.app"
                if app_path.exists():
                    shutil.rmtree(app_path)

            return success

        except Exception as e:
            logger.error(f"Error removing macOS shortcuts: {e}")
            return False

    def _remove_linux_shortcuts(self) -> bool:
        """Remove Linux .desktop files"""
        try:
            desktop_dir = Path.home() / "Desktop"
            apps_dir = Path.home() / ".local" / "share" / "applications"

            success = True

            for shortcut_id in self.config['shortcuts'].keys():
                desktop_filename = f"{self.app_id}-{shortcut_id}.desktop"

                # Remove from desktop
                desktop_file = desktop_dir / desktop_filename
                if desktop_file.exists():
                    desktop_file.unlink()

                # Remove from applications
                apps_file = apps_dir / desktop_filename
                if apps_file.exists():
                    apps_file.unlink()

            return success

        except Exception as e:
            logger.error(f"Error removing Linux shortcuts: {e}")
            return False

    def _remove_start_menu_entries(self) -> bool:
        """Remove start menu entries (handled in platform-specific methods)"""
        return True

    def _remove_file_associations(self) -> bool:
        """Remove file associations"""
        # Implementation would depend on how associations were created
        return True

    def _remove_auto_startup(self) -> bool:
        """Remove auto-startup configuration"""
        try:
            if self.platform == "Windows":
                return self._remove_windows_auto_startup()
            elif self.platform == "Darwin":  # macOS
                return self._remove_macos_auto_startup()
            else:  # Linux
                return self._remove_linux_auto_startup()
        except Exception as e:
            logger.error(f"Error removing auto-startup: {e}")
            return False

    def _remove_windows_auto_startup(self) -> bool:
        """Remove Windows auto-startup"""
        try:
            import winreg as reg

            key_path = r"SOFTWARE\Microsoft\Windows\CurrentVersion\Run"
            key = reg.OpenKey(reg.HKEY_CURRENT_USER, key_path, 0, reg.KEY_SET_VALUE)

            try:
                reg.DeleteValue(key, self.app_id)
            except FileNotFoundError:
                pass  # Already removed

            reg.CloseKey(key)
            return True

        except Exception as e:
            logger.error(f"Error removing Windows auto-startup: {e}")
            return False

    def _remove_macos_auto_startup(self) -> bool:
        """Remove macOS auto-startup"""
        try:
            plist_file = Path.home() / "Library" / "LaunchAgents" / "com.alabamaauctionwatcher.systemtray.plist"
            if plist_file.exists():
                plist_file.unlink()
            return True

        except Exception as e:
            logger.error(f"Error removing macOS auto-startup: {e}")
            return False

    def _remove_linux_auto_startup(self) -> bool:
        """Remove Linux auto-startup"""
        try:
            desktop_file = Path.home() / ".config" / "autostart" / f"{self.app_id}-systemtray.desktop"
            if desktop_file.exists():
                desktop_file.unlink()
            return True

        except Exception as e:
            logger.error(f"Error removing Linux auto-startup: {e}")
            return False

    def _cleanup_installation_files(self) -> bool:
        """Clean up installation configuration files"""
        try:
            config_file = self.script_dir / "installer" / "installation_config.json"
            if config_file.exists():
                config_file.unlink()
            return True

        except Exception as e:
            logger.error(f"Error cleaning up installation files: {e}")
            return False

    # Utility methods
    def _save_installation_config(self) -> bool:
        """Save installation configuration for later uninstallation"""
        try:
            config_file = self.script_dir / "installer" / "installation_config.json"
            with open(config_file, 'w') as f:
                json.dump(self.config, f, indent=2)
            return True

        except Exception as e:
            logger.error(f"Error saving installation config: {e}")
            return False

    def _get_current_timestamp(self) -> str:
        """Get current timestamp as ISO string"""
        from datetime import datetime
        return datetime.now().isoformat()

    def check_installation_status(self) -> Dict:
        """Check current installation status"""
        try:
            config_file = self.script_dir / "installer" / "installation_config.json"
            if config_file.exists():
                with open(config_file, 'r') as f:
                    return json.load(f)
            else:
                return {"installed": False}

        except Exception as e:
            logger.error(f"Error checking installation status: {e}")
            return {"installed": False, "error": str(e)}

def main():
    """Main entry point for the installer"""
    installer = DesktopIntegrationInstaller()

    if len(sys.argv) > 1 and sys.argv[1] == "uninstall":
        print("Uninstalling Alabama Auction Watcher desktop integration...")
        success = installer.uninstall()
        if success:
            print("✅ Uninstallation completed successfully")
        else:
            print("❌ Uninstallation completed with errors")
    else:
        print("Installing Alabama Auction Watcher desktop integration...")
        print(f"Platform: {platform.system()}")
        print(f"Installation directory: {installer.script_dir}")
        print()

        # Get user preferences
        create_desktop = input("Create desktop shortcuts? (Y/n): ").lower() != 'n'
        create_start_menu = input("Create start menu/applications entries? (Y/n): ").lower() != 'n'
        enable_auto_startup = input("Enable auto-startup for system tray? (y/N): ").lower() == 'y'

        success = installer.install(
            create_desktop_shortcuts=create_desktop,
            create_start_menu=create_start_menu,
            enable_auto_startup=enable_auto_startup
        )

        if success:
            print("[SUCCESS] Installation completed successfully")
            print()
            print("Desktop shortcuts have been created for:")
            for shortcut_config in installer.config['shortcuts'].values():
                print(f"  - {shortcut_config['name']}")
            print()
            print("You can now launch Alabama Auction Watcher from your desktop or start menu!")
        else:
            print("[ERROR] Installation completed with errors")

if __name__ == "__main__":
    main()