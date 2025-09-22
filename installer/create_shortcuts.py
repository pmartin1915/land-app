#!/usr/bin/env python3
"""
Alabama Auction Watcher - Simple Shortcut Creator
A lightweight, dependency-free shortcut creator that works across platforms
without requiring additional packages like pywin32 or winshell.

This script creates basic shortcuts that can be enhanced later with proper installers.
"""

import os
import sys
import platform
import stat
from pathlib import Path

class SimpleShortcutCreator:
    """Creates basic shortcuts without external dependencies"""

    def __init__(self):
        self.platform = platform.system()
        self.script_dir = Path(__file__).parent.parent.absolute()
        self.app_name = "Alabama Auction Watcher"

    def create_all_shortcuts(self):
        """Create shortcuts for all platforms"""
        print(f"Creating shortcuts for {self.platform}...")

        if self.platform == "Windows":
            return self.create_windows_shortcuts()
        elif self.platform == "Darwin":  # macOS
            return self.create_macos_shortcuts()
        else:  # Linux
            return self.create_linux_shortcuts()

    def create_windows_shortcuts(self):
        """Create Windows shortcuts using VBScript"""
        try:
            desktop = Path.home() / "Desktop"

            shortcuts = [
                {
                    'name': 'Alabama Auction Watcher',
                    'target': str(self.script_dir / "launchers" / "windows" / "launch_main_app.bat"),
                    'description': 'Main interactive dashboard'
                },
                {
                    'name': 'Alabama Auction Watcher API',
                    'target': str(self.script_dir / "launchers" / "windows" / "launch_backend_api.bat"),
                    'description': 'Backend API server'
                },
                {
                    'name': 'Alabama Auction Watcher Enhanced',
                    'target': str(self.script_dir / "launchers" / "windows" / "launch_enhanced_dashboard.bat"),
                    'description': 'Enhanced dashboard with AI monitoring'
                },
                {
                    'name': 'Alabama Auction Watcher Launcher',
                    'target': str(self.script_dir / "launchers" / "windows" / "launch_smart_launcher.bat"),
                    'description': 'Smart GUI launcher'
                }
            ]

            for shortcut in shortcuts:
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
                os.system(f'cscript //nologo "{vbs_file}"')

                # Clean up VBS file
                vbs_file.unlink()

                print(f"  [SUCCESS] Created: {shortcut['name']}")

            return True

        except Exception as e:
            print(f"  [ERROR] Error creating Windows shortcuts: {e}")
            return False

    def create_macos_shortcuts(self):
        """Create macOS shortcuts using AppleScript"""
        try:
            desktop = Path.home() / "Desktop"

            shortcuts = [
                {
                    'name': 'Alabama Auction Watcher',
                    'command': f'bash "{self.script_dir / "launchers" / "macos" / "launch_main_app.command"}"'
                },
                {
                    'name': 'Alabama Auction Watcher API',
                    'command': f'bash "{self.script_dir / "launchers" / "macos" / "launch_backend_api.command"}"'
                },
                {
                    'name': 'Alabama Auction Watcher Enhanced',
                    'command': f'bash "{self.script_dir / "launchers" / "macos" / "launch_enhanced_dashboard.command"}"'
                },
                {
                    'name': 'Alabama Auction Watcher Launcher',
                    'command': f'"{sys.executable}" "{self.script_dir / "launchers" / "cross_platform" / "smart_launcher.py"}"'
                }
            ]

            for shortcut in shortcuts:
                # Create shell script that can be double-clicked
                script_path = desktop / f"{shortcut['name']}.command"

                script_content = f'''#!/bin/bash
cd "{self.script_dir}"
{shortcut['command']}
'''
                with open(script_path, 'w') as f:
                    f.write(script_content)

                # Make executable
                script_path.chmod(script_path.stat().st_mode | stat.S_IEXEC)

                print(f"  [SUCCESS] Created: {shortcut['name']}")

            return True

        except Exception as e:
            print(f"  [ERROR] Error creating macOS shortcuts: {e}")
            return False

    def create_linux_shortcuts(self):
        """Create Linux .desktop files"""
        try:
            desktop = Path.home() / "Desktop"
            apps_dir = Path.home() / ".local" / "share" / "applications"
            apps_dir.mkdir(parents=True, exist_ok=True)

            shortcuts = [
                {
                    'name': 'Alabama Auction Watcher',
                    'exec': f'bash "{self.script_dir / "launchers" / "linux" / "launch_scripts" / "launch_main_app.sh"}"',
                    'comment': 'Main interactive dashboard'
                },
                {
                    'name': 'Alabama Auction Watcher API',
                    'exec': f'bash "{self.script_dir / "launchers" / "linux" / "launch_scripts" / "launch_backend_api.sh"}"',
                    'comment': 'Backend API server'
                },
                {
                    'name': 'Alabama Auction Watcher Enhanced',
                    'exec': f'bash "{self.script_dir / "launchers" / "linux" / "launch_scripts" / "launch_enhanced_dashboard.sh"}"',
                    'comment': 'Enhanced dashboard with AI monitoring'
                },
                {
                    'name': 'Alabama Auction Watcher Launcher',
                    'exec': f'{sys.executable} "{self.script_dir / "launchers" / "cross_platform" / "smart_launcher.py"}"',
                    'comment': 'Smart GUI launcher'
                }
            ]

            for shortcut in shortcuts:
                desktop_content = f'''[Desktop Entry]
Version=1.0
Type=Application
Name={shortcut['name']}
Comment={shortcut['comment']}
Exec={shortcut['exec']}
Icon={self.script_dir}/icons/main_app.ico
Terminal=true
Categories=Office;Finance;Development;
Keywords=auction;property;investment;alabama;
StartupNotify=true
'''

                # Create desktop shortcut
                if desktop.exists():
                    desktop_file = desktop / f"{shortcut['name'].replace(' ', '_')}.desktop"
                    with open(desktop_file, 'w') as f:
                        f.write(desktop_content)
                    desktop_file.chmod(0o755)

                # Create applications menu entry
                apps_file = apps_dir / f"alabama-auction-watcher-{shortcut['name'].replace(' ', '_').lower()}.desktop"
                with open(apps_file, 'w') as f:
                    f.write(desktop_content)
                apps_file.chmod(0o755)

                print(f"  [SUCCESS] Created: {shortcut['name']}")

            return True

        except Exception as e:
            print(f"  [ERROR] Error creating Linux shortcuts: {e}")
            return False

def main():
    """Main entry point"""
    print("Alabama Auction Watcher - Simple Shortcut Creator")
    print("=" * 50)

    creator = SimpleShortcutCreator()

    print(f"Platform: {platform.system()}")
    print(f"Working directory: {creator.script_dir}")
    print()

    if creator.create_all_shortcuts():
        print()
        print("[SUCCESS] Desktop shortcuts created successfully!")
        print()
        print("Available shortcuts:")
        print("  * Alabama Auction Watcher - Main dashboard")
        print("  * Alabama Auction Watcher API - Backend server")
        print("  * Alabama Auction Watcher Enhanced - Full system")
        print("  * Alabama Auction Watcher Launcher - GUI manager")
        print()
        print("You can now double-click these shortcuts to launch the application!")
    else:
        print()
        print("[ERROR] Failed to create some shortcuts")
        print("You can still launch the application manually using the launcher scripts.")

if __name__ == "__main__":
    main()