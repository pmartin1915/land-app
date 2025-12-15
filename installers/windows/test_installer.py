#!/usr/bin/env python3
"""
Windows Installer Test Suite
Validates Windows desktop installation functionality
"""

import os
import sys
import winreg
from pathlib import Path
import subprocess
import json

class WindowsInstallerTester:
    """Test suite for Windows desktop installer"""

    def __init__(self):
        self.app_name = "Alabama Auction Watcher"
        self.install_dir = Path(os.environ.get('PROGRAMFILES', 'C:/Program Files')) / "Alabama Auction Watcher"
        self.test_results = []

    def log_test(self, test_name: str, passed: bool, details: str = ""):
        """Log test result"""
        status = "PASS" if passed else "FAIL"
        self.test_results.append({
            "test": test_name,
            "status": status,
            "details": details
        })
        print(f"[{status}] {test_name}" + (f" - {details}" if details else ""))

    def test_installation_directory(self):
        """Test if installation directory exists"""
        exists = self.install_dir.exists()
        self.log_test("Installation Directory", exists, str(self.install_dir))

        # Test subdirectories
        subdirs = ["Application", "Backend", "Config", "Icons", "Logs"]
        for subdir in subdirs:
            subdir_path = self.install_dir / subdir
            exists = subdir_path.exists()
            self.log_test(f"Subdirectory: {subdir}", exists, str(subdir_path))

    def test_application_files(self):
        """Test if application files were copied correctly"""
        critical_files = [
            "Application/Alabama Auction Watcher.bat",
            "Backend/start_backend_api.py",
            "uninstall.py",
            "installation_info.json"
        ]

        for file_path in critical_files:
            full_path = self.install_dir / file_path
            exists = full_path.exists()
            self.log_test(f"File: {file_path}", exists)

    def test_icon_files(self):
        """Test if icon files are present"""
        icon_files = [
            "alabama-auction-watcher.ico",
            "aaw-backend.ico",
            "aaw-analytics.ico",
            "aaw-health.ico",
            "aaw-settings.ico"
        ]

        icons_dir = self.install_dir / "Icons"
        for icon_file in icon_files:
            icon_path = icons_dir / icon_file
            exists = icon_path.exists()
            self.log_test(f"Icon: {icon_file}", exists)

    def test_desktop_shortcut(self):
        """Test desktop shortcut creation"""
        desktop = Path.home() / "Desktop"
        shortcut_lnk = desktop / f"{self.app_name}.lnk"
        shortcut_bat = desktop / f"{self.app_name}.bat"

        lnk_exists = shortcut_lnk.exists()
        bat_exists = shortcut_bat.exists()

        has_shortcut = lnk_exists or bat_exists
        self.log_test("Desktop Shortcut", has_shortcut,
                     "LNK" if lnk_exists else "BAT" if bat_exists else "None")

    def test_start_menu_shortcuts(self):
        """Test Start Menu shortcut creation"""
        start_menu = Path(os.environ['APPDATA']) / "Microsoft" / "Windows" / "Start Menu" / "Programs"
        app_folder = start_menu / "Alabama Auction Watcher"

        folder_exists = app_folder.exists()
        self.log_test("Start Menu Folder", folder_exists, str(app_folder))

        if folder_exists:
            shortcuts = list(app_folder.glob("*.lnk")) + list(app_folder.glob("*.bat"))
            self.log_test("Start Menu Shortcuts", len(shortcuts) > 0, f"{len(shortcuts)} shortcuts found")

    def test_registry_entries(self):
        """Test Windows registry entries"""
        try:
            # Test application registration
            app_key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Software\AlabamaAuctionWatcher")
            install_path, _ = winreg.QueryValueEx(app_key, "InstallPath")
            winreg.CloseKey(app_key)

            path_correct = Path(install_path) == self.install_dir
            self.log_test("Registry: App Registration", True, f"Path: {install_path}")

        except Exception as e:
            self.log_test("Registry: App Registration", False, str(e))

        try:
            # Test URL protocol
            protocol_key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Software\Classes\aaw")
            protocol_desc, _ = winreg.QueryValueEx(protocol_key, "")
            winreg.CloseKey(protocol_key)

            self.log_test("Registry: URL Protocol", True, protocol_desc)

        except Exception as e:
            self.log_test("Registry: URL Protocol", False, str(e))

    def test_uninstaller(self):
        """Test uninstaller script"""
        uninstaller = self.install_dir / "uninstall.py"
        exists = uninstaller.exists()

        if exists:
            # Test if uninstaller script is valid Python
            try:
                with open(uninstaller, 'r', encoding='utf-8') as f:
                    content = f.read()
                    valid = 'def main()' in content and 'winreg' in content
                    self.log_test("Uninstaller Script", valid, "Valid Python script")
            except Exception as e:
                self.log_test("Uninstaller Script", False, str(e))
        else:
            self.log_test("Uninstaller Script", False, "File not found")

    def test_installation_info(self):
        """Test installation information file"""
        info_file = self.install_dir / "installation_info.json"

        if info_file.exists():
            try:
                with open(info_file, 'r', encoding='utf-8') as f:
                    info = json.load(f)

                required_keys = ["product_name", "version", "install_date", "install_path"]
                has_all_keys = all(key in info for key in required_keys)

                self.log_test("Installation Info", has_all_keys,
                             f"Version: {info.get('version', 'Unknown')}")

            except Exception as e:
                self.log_test("Installation Info", False, str(e))
        else:
            self.log_test("Installation Info", False, "File not found")

    def test_url_protocol_handler(self):
        """Test URL protocol handler functionality"""
        try:
            # Try to query the command handler
            command_key = winreg.OpenKey(winreg.HKEY_CURRENT_USER,
                                        r"Software\Classes\aaw\shell\open\command")
            command, _ = winreg.QueryValueEx(command_key, "")
            winreg.CloseKey(command_key)

            # Check if command points to correct executable
            has_correct_path = str(self.install_dir) in command
            self.log_test("URL Protocol Handler", has_correct_path, command[:50] + "...")

        except Exception as e:
            self.log_test("URL Protocol Handler", False, str(e))

    def run_all_tests(self):
        """Run complete test suite"""
        print("[TARGET] Alabama Auction Watcher - Windows Installer Test Suite")
        print("=" * 60)

        if not self.install_dir.exists():
            print(f"[ERROR] Installation directory not found: {self.install_dir}")
            print("Please run the installer first: python create_windows_installer.py")
            return False

        print(f"[INFO] Testing installation at: {self.install_dir}")
        print()

        # Run all tests
        self.test_installation_directory()
        self.test_application_files()
        self.test_icon_files()
        self.test_desktop_shortcut()
        self.test_start_menu_shortcuts()
        self.test_registry_entries()
        self.test_uninstaller()
        self.test_installation_info()
        self.test_url_protocol_handler()

        # Summary
        passed = sum(1 for result in self.test_results if result["status"] == "PASS")
        total = len(self.test_results)
        success_rate = (passed / total) * 100

        print()
        print("[SUMMARY] Test Results")
        print(f"Passed: {passed}/{total} ({success_rate:.1f}%)")

        if success_rate >= 80:
            print("[SUCCESS] Installation verification completed successfully!")
            return True
        else:
            print("[WARNING] Some installation components failed verification")
            print("Please review failed tests and re-run installer if needed")
            return False

    def generate_test_report(self):
        """Generate detailed test report"""
        report = {
            "test_date": __import__('datetime').datetime.now().isoformat(),
            "installation_path": str(self.install_dir),
            "total_tests": len(self.test_results),
            "passed_tests": sum(1 for r in self.test_results if r["status"] == "PASS"),
            "failed_tests": sum(1 for r in self.test_results if r["status"] == "FAIL"),
            "test_results": self.test_results
        }

        report_file = Path(__file__).parent / "test_report.json"
        with open(report_file, 'w', encoding='utf-8') as f:
            json.dump(report, f, indent=2)

        print(f"[INFO] Test report saved: {report_file}")

def main():
    """Main test execution"""
    tester = WindowsInstallerTester()

    success = tester.run_all_tests()
    tester.generate_test_report()

    if success:
        print("\n[OK] All tests completed successfully!")
        sys.exit(0)
    else:
        print("\n[WARNING] Some tests failed - check results above")
        sys.exit(1)

if __name__ == '__main__':
    main()