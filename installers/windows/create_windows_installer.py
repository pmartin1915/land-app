#!/usr/bin/env python3
"""
Windows Desktop Installer - Self-contained Python solution
Creates desktop integration without requiring WiX or external tools
"""

import os
import sys
import shutil
import winreg
from pathlib import Path
import json
import subprocess

class WindowsDesktopInstaller:
    """Self-contained Windows desktop installer"""

    def __init__(self):
        self.app_name = "Alabama Auction Watcher"
        self.app_version = "1.0.0.0"
        self.publisher = "Alabama Auction Watcher Team"
        self.source_dir = Path(__file__).parent.parent.parent
        self.install_dir = Path(os.environ['PROGRAMFILES']) / "Alabama Auction Watcher"

        # User paths
        self.desktop = Path.home() / "Desktop"
        self.start_menu = Path(os.environ['APPDATA']) / "Microsoft" / "Windows" / "Start Menu" / "Programs"
        self.app_start_menu = self.start_menu / "Alabama Auction Watcher"

    def check_admin_rights(self) -> bool:
        """Check if running with administrator privileges"""
        try:
            # Try to open HKEY_LOCAL_MACHINE for writing
            key = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, "Software", 0, winreg.KEY_WRITE)
            winreg.CloseKey(key)
            return True
        except PermissionError:
            return False

    def request_admin_elevation(self):
        """Request administrator elevation"""
        if not self.check_admin_rights():
            print("[WARNING] Administrator privileges required for system-wide installation")
            print("Please run as administrator or choose user-level installation")

            choice = input("Install for current user only? (y/n): ").lower()
            if choice == 'y':
                # Switch to user-level installation
                self.install_dir = Path.home() / "Alabama Auction Watcher"
                return True
            else:
                print("[ERROR] Installation cancelled - administrator rights required")
                return False
        return True

    def create_installation_directories(self):
        """Create necessary directories"""
        directories = [
            self.install_dir,
            self.install_dir / "Application",
            self.install_dir / "Backend",
            self.install_dir / "Config",
            self.install_dir / "Icons",
            self.install_dir / "Logs",
            self.app_start_menu
        ]

        for directory in directories:
            directory.mkdir(parents=True, exist_ok=True)
            print(f"[INFO] Created directory: {directory}")

    def copy_application_files(self):
        """Copy application files to installation directory"""

        # File mappings: (source, destination)
        file_mappings = [
            # Main application files
            ("Alabama Auction Watcher.bat", "Application/Alabama Auction Watcher.bat"),
            ("streamlit_app", "Application/streamlit_app"),
            ("frontend", "Application/frontend"),
            ("requirements.txt", "Application/requirements.txt"),

            # Backend files
            ("start_backend_api.py", "Backend/start_backend_api.py"),
            ("backend_api", "Backend/backend_api"),

            # Configuration
            ("config", "Config"),

            # Database (if exists)
            ("alabama_auction_watcher.db", "Application/alabama_auction_watcher.db"),

            # Scripts
            ("scripts", "Application/scripts")
        ]

        for source_rel, dest_rel in file_mappings:
            source_path = self.source_dir / source_rel
            dest_path = self.install_dir / dest_rel

            if source_path.exists():
                if source_path.is_file():
                    # Copy single file
                    dest_path.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(source_path, dest_path)
                    print(f"[INFO] Copied: {source_rel}")
                elif source_path.is_dir():
                    # Copy entire directory
                    if dest_path.exists():
                        shutil.rmtree(dest_path)
                    shutil.copytree(source_path, dest_path)
                    print(f"[INFO] Copied directory: {source_rel}")
            else:
                print(f"[WARNING] Source not found: {source_rel}")

        # Copy icons
        icon_source = self.source_dir / "branding" / "generated" / "windows"
        icon_dest = self.install_dir / "Icons"

        if icon_source.exists():
            for icon_file in icon_source.glob("*.ico"):
                shutil.copy2(icon_file, icon_dest / icon_file.name)
                print(f"[INFO] Copied icon: {icon_file.name}")

    def create_desktop_shortcut(self):
        """Create desktop shortcut"""
        try:
            import win32com.client

            shell = win32com.client.Dispatch("WScript.Shell")
            shortcut_path = self.desktop / f"{self.app_name}.lnk"
            shortcut = shell.CreateShortCut(str(shortcut_path))

            shortcut.Targetpath = str(self.install_dir / "Application" / "Alabama Auction Watcher.bat")
            shortcut.WorkingDirectory = str(self.install_dir / "Application")
            shortcut.IconLocation = str(self.install_dir / "Icons" / "alabama-auction-watcher.ico")
            shortcut.Description = "Professional Real Estate Auction Intelligence"

            shortcut.save()
            print(f"[OK] Created desktop shortcut: {shortcut_path}")

        except ImportError:
            # Fallback: Create simple batch file shortcut
            batch_shortcut = self.desktop / f"{self.app_name}.bat"
            with open(batch_shortcut, 'w') as f:
                f.write(f'@echo off\n')
                f.write(f'cd /d "{self.install_dir / "Application"}"\n')
                f.write(f'call "Alabama Auction Watcher.bat"\n')

            print(f"[OK] Created desktop batch shortcut: {batch_shortcut}")

    def create_start_menu_shortcuts(self):
        """Create Start Menu shortcuts"""
        shortcuts = [
            {
                "name": "Alabama Auction Watcher",
                "target": "Application/Alabama Auction Watcher.bat",
                "description": "Launch Alabama Auction Watcher Application",
                "icon": "Icons/alabama-auction-watcher.ico"
            },
            {
                "name": "Backend Service Manager",
                "target": "Backend/start_backend_api.py",
                "description": "Manage Backend Services",
                "icon": "Icons/aaw-backend.ico"
            },
            {
                "name": "Uninstall Alabama Auction Watcher",
                "target": f'"{sys.executable}" "{Path(__file__).parent / "uninstall.py"}"',
                "description": "Remove Alabama Auction Watcher",
                "icon": "Icons/aaw-settings.ico"
            }
        ]

        for shortcut_info in shortcuts:
            try:
                import win32com.client

                shell = win32com.client.Dispatch("WScript.Shell")
                shortcut_path = self.app_start_menu / f"{shortcut_info['name']}.lnk"
                shortcut = shell.CreateShortCut(str(shortcut_path))

                if shortcut_info['target'].endswith('.py'):
                    shortcut.Targetpath = sys.executable
                    shortcut.Arguments = f'"{self.install_dir / shortcut_info["target"]}"'
                else:
                    shortcut.Targetpath = str(self.install_dir / shortcut_info['target'])

                shortcut.WorkingDirectory = str(self.install_dir)
                shortcut.IconLocation = str(self.install_dir / shortcut_info['icon'])
                shortcut.Description = shortcut_info['description']

                shortcut.save()
                print(f"[OK] Created Start Menu shortcut: {shortcut_info['name']}")

            except ImportError:
                # Fallback: Create batch shortcuts
                batch_path = self.app_start_menu / f"{shortcut_info['name']}.bat"
                with open(batch_path, 'w') as f:
                    f.write(f'@echo off\n')
                    f.write(f'cd /d "{self.install_dir}"\n')
                    if shortcut_info['target'].endswith('.py'):
                        f.write(f'python "{shortcut_info["target"]}"\n')
                    else:
                        f.write(f'call "{shortcut_info["target"]}"\n')

                print(f"[OK] Created Start Menu batch: {shortcut_info['name']}")

    def create_registry_entries(self):
        """Create Windows registry entries"""
        try:
            # Application registration
            app_key = winreg.CreateKey(winreg.HKEY_CURRENT_USER,
                                      r"Software\AlabamaAuctionWatcher")

            winreg.SetValueEx(app_key, "InstallPath", 0, winreg.REG_SZ, str(self.install_dir))
            winreg.SetValueEx(app_key, "Version", 0, winreg.REG_SZ, self.app_version)
            winreg.SetValueEx(app_key, "Publisher", 0, winreg.REG_SZ, self.publisher)
            winreg.SetValueEx(app_key, "DisplayName", 0, winreg.REG_SZ, self.app_name)

            winreg.CloseKey(app_key)
            print("[OK] Created application registry entries")

            # URL protocol registration for aaw:// links
            protocol_key = winreg.CreateKey(winreg.HKEY_CURRENT_USER, r"Software\Classes\aaw")
            winreg.SetValueEx(protocol_key, "", 0, winreg.REG_SZ, "Alabama Auction Watcher Protocol")
            winreg.SetValueEx(protocol_key, "URL Protocol", 0, winreg.REG_SZ, "")

            # Default icon
            icon_key = winreg.CreateKey(winreg.HKEY_CURRENT_USER, r"Software\Classes\aaw\DefaultIcon")
            winreg.SetValueEx(icon_key, "", 0, winreg.REG_SZ,
                             str(self.install_dir / "Icons" / "alabama-auction-watcher.ico"))

            # Command handler
            command_key = winreg.CreateKey(winreg.HKEY_CURRENT_USER, r"Software\Classes\aaw\shell\open\command")
            winreg.SetValueEx(command_key, "", 0, winreg.REG_SZ,
                             f'"{self.install_dir / "Application" / "Alabama Auction Watcher.bat"}" "%1"')

            winreg.CloseKey(protocol_key)
            winreg.CloseKey(icon_key)
            winreg.CloseKey(command_key)
            print("[OK] Created URL protocol registry entries")

        except Exception as e:
            print(f"[WARNING] Registry creation failed: {e}")
            print("Some features may not work properly")

    def create_uninstaller(self):
        """Create uninstaller script"""
        uninstaller_content = f'''#!/usr/bin/env python3
"""
Alabama Auction Watcher Uninstaller
"""

import os
import sys
import shutil
import winreg
from pathlib import Path

def remove_files():
    """Remove installation files"""
    install_dir = Path(r"{self.install_dir}")
    if install_dir.exists():
        shutil.rmtree(install_dir, ignore_errors=True)
        print(f"[INFO] Removed installation directory")

def remove_shortcuts():
    """Remove shortcuts"""
    shortcuts = [
        Path.home() / "Desktop" / "{self.app_name}.lnk",
        Path.home() / "Desktop" / "{self.app_name}.bat",
        Path(os.environ['APPDATA']) / "Microsoft" / "Windows" / "Start Menu" / "Programs" / "Alabama Auction Watcher"
    ]

    for shortcut in shortcuts:
        if shortcut.exists():
            if shortcut.is_file():
                shortcut.unlink()
            else:
                shutil.rmtree(shortcut, ignore_errors=True)
            print(f"[INFO] Removed shortcut: {{shortcut.name}}")

def remove_registry():
    """Remove registry entries"""
    try:
        winreg.DeleteKey(winreg.HKEY_CURRENT_USER, r"Software\\AlabamaAuctionWatcher")
        winreg.DeleteKey(winreg.HKEY_CURRENT_USER, r"Software\\Classes\\aaw\\shell\\open\\command")
        winreg.DeleteKey(winreg.HKEY_CURRENT_USER, r"Software\\Classes\\aaw\\shell\\open")
        winreg.DeleteKey(winreg.HKEY_CURRENT_USER, r"Software\\Classes\\aaw\\shell")
        winreg.DeleteKey(winreg.HKEY_CURRENT_USER, r"Software\\Classes\\aaw\\DefaultIcon")
        winreg.DeleteKey(winreg.HKEY_CURRENT_USER, r"Software\\Classes\\aaw")
        print("[INFO] Removed registry entries")
    except:
        print("[WARNING] Some registry entries could not be removed")

def main():
    print("Alabama Auction Watcher Uninstaller")
    print("=" * 40)

    confirm = input("Are you sure you want to uninstall? (y/N): ")
    if confirm.lower() != 'y':
        print("Uninstallation cancelled")
        return

    print("Removing Alabama Auction Watcher...")
    remove_shortcuts()
    remove_registry()
    remove_files()

    print("\\nUninstallation completed successfully!")
    input("Press Enter to exit...")

if __name__ == '__main__':
    main()
'''

        uninstaller_path = self.install_dir / "uninstall.py"
        with open(uninstaller_path, 'w', encoding='utf-8') as f:
            f.write(uninstaller_content)

        print(f"[INFO] Created uninstaller: {uninstaller_path}")

    def create_installation_info(self):
        """Create installation information file"""
        info = {
            "product_name": self.app_name,
            "version": self.app_version,
            "publisher": self.publisher,
            "install_date": __import__('datetime').datetime.now().isoformat(),
            "install_path": str(self.install_dir),
            "installation_type": "Windows Desktop Integration",
            "features_installed": [
                "Desktop shortcut",
                "Start Menu shortcuts",
                "Registry integration",
                "URL protocol handler",
                "Uninstaller"
            ]
        }

        info_file = self.install_dir / "installation_info.json"
        with open(info_file, 'w', encoding='utf-8') as f:
            json.dump(info, f, indent=2)

        print(f"[INFO] Created installation info: {info_file}")

    def install(self) -> bool:
        """Complete installation process"""
        print("[TARGET] Alabama Auction Watcher - Windows Desktop Installer")
        print("=" * 60)

        try:
            # Check permissions
            if not self.request_admin_elevation():
                return False

            print(f"[INFO] Installing to: {self.install_dir}")

            # Create directories
            self.create_installation_directories()

            # Copy files
            print("[INFO] Copying application files...")
            self.copy_application_files()

            # Create shortcuts
            print("[INFO] Creating desktop integration...")
            self.create_desktop_shortcut()
            self.create_start_menu_shortcuts()

            # Registry integration
            print("[INFO] Setting up Windows integration...")
            self.create_registry_entries()

            # Create uninstaller
            self.create_uninstaller()

            # Create installation info
            self.create_installation_info()

            print("\n[SUCCESS] Alabama Auction Watcher installed successfully!")
            print(f"[INFO] Installation location: {self.install_dir}")
            print(f"[INFO] Desktop shortcut created")
            print(f"[INFO] Start Menu shortcuts created")
            print(f"[INFO] URL protocol 'aaw://' registered")
            print(f"[INFO] Uninstaller available in Start Menu")

            return True

        except Exception as e:
            print(f"[ERROR] Installation failed: {e}")
            return False

def main():
    """Main installation function"""
    installer = WindowsDesktopInstaller()

    if installer.install():
        print("\n[OK] Installation completed successfully!")
        input("Press Enter to exit...")
        sys.exit(0)
    else:
        print("\n[ERROR] Installation failed!")
        input("Press Enter to exit...")
        sys.exit(1)

if __name__ == '__main__':
    main()