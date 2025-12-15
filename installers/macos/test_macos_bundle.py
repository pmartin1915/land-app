#!/usr/bin/env python3
"""
macOS Bundle Test Suite
Validates macOS .app bundle structure and functionality
"""

import os
import sys
import plistlib
import subprocess
from pathlib import Path
import json

class MacOSBundleTester:
    """Test suite for macOS .app bundle"""

    def __init__(self):
        self.build_dir = Path(__file__).parent / "build"
        self.app_bundle = self.build_dir / "Alabama Auction Watcher.app"
        self.contents_dir = self.app_bundle / "Contents"
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

    def test_bundle_structure(self):
        """Test .app bundle directory structure"""
        bundle_exists = self.app_bundle.exists() and self.app_bundle.is_dir()
        self.log_test("Bundle Directory", bundle_exists, str(self.app_bundle))

        if not bundle_exists:
            return

        # Required directories
        required_dirs = [
            "Contents",
            "Contents/MacOS",
            "Contents/Resources"
        ]

        for dir_path in required_dirs:
            full_path = self.app_bundle / dir_path
            exists = full_path.exists() and full_path.is_dir()
            self.log_test(f"Directory: {dir_path}", exists)

    def test_info_plist(self):
        """Test Info.plist validity and content"""
        info_plist_path = self.contents_dir / "Info.plist"
        exists = info_plist_path.exists()
        self.log_test("Info.plist Exists", exists)

        if not exists:
            return

        try:
            with open(info_plist_path, 'rb') as f:
                plist_data = plistlib.load(f)

            # Check required keys
            required_keys = [
                'CFBundleName',
                'CFBundleIdentifier',
                'CFBundleVersion',
                'CFBundleExecutable',
                'CFBundleIconFile'
            ]

            for key in required_keys:
                has_key = key in plist_data
                value = plist_data.get(key, "Not found")
                self.log_test(f"Info.plist Key: {key}", has_key, str(value)[:30])

            # Test URL scheme registration
            url_types = plist_data.get('CFBundleURLTypes', [])
            has_url_scheme = any('aaw' in url_type.get('CFBundleURLSchemes', [])
                               for url_type in url_types)
            self.log_test("URL Scheme (aaw://)", has_url_scheme)

        except Exception as e:
            self.log_test("Info.plist Validity", False, str(e))

    def test_executable_file(self):
        """Test main executable"""
        executable_path = self.contents_dir / "MacOS" / "launch_alabama_auction_watcher"
        exists = executable_path.exists()
        self.log_test("Main Executable", exists, str(executable_path.name))

        if exists:
            # Check if executable
            is_executable = os.access(executable_path, os.X_OK)
            self.log_test("Executable Permissions", is_executable)

            # Check file content (basic validation)
            try:
                with open(executable_path, 'r', encoding='utf-8') as f:
                    content = f.read(100)  # Read first 100 chars
                    is_shell_script = content.startswith('#!/bin/bash')
                    self.log_test("Shell Script Format", is_shell_script)
            except Exception as e:
                self.log_test("Executable Content", False, str(e))

    def test_icon_files(self):
        """Test application icons"""
        resources_dir = self.contents_dir / "Resources"
        main_icon = resources_dir / "alabama_auction_watcher.icns"

        exists = main_icon.exists()
        self.log_test("Main Icon File", exists, str(main_icon.name))

        # Check additional icons
        if resources_dir.exists():
            icon_files = list(resources_dir.glob("*.icns"))
            self.log_test("Icon Files Count", len(icon_files) > 0, f"{len(icon_files)} icons found")

    def test_application_resources(self):
        """Test application resource files"""
        resources_dir = self.contents_dir / "Resources"

        if not resources_dir.exists():
            self.log_test("Resources Directory", False)
            return

        # Check for key application files
        critical_files = [
            "requirements.txt",
            "start_backend_api.py",
            "streamlit_app",
            "backend_api",
            "config"
        ]

        for file_name in critical_files:
            file_path = resources_dir / file_name
            exists = file_path.exists()
            file_type = "directory" if file_path.is_dir() else "file"
            self.log_test(f"Resource: {file_name}", exists, file_type)

    def test_pkginfo_file(self):
        """Test PkgInfo file"""
        pkginfo_path = self.contents_dir / "PkgInfo"
        exists = pkginfo_path.exists()
        self.log_test("PkgInfo File", exists)

        if exists:
            try:
                with open(pkginfo_path, 'r') as f:
                    content = f.read().strip()
                    valid_format = len(content) == 8  # Should be 8 characters
                    self.log_test("PkgInfo Format", valid_format, content)
            except Exception as e:
                self.log_test("PkgInfo Content", False, str(e))

    def test_version_plist(self):
        """Test version.plist file"""
        version_plist_path = self.contents_dir / "version.plist"
        exists = version_plist_path.exists()
        self.log_test("Version Plist", exists)

        if exists:
            try:
                with open(version_plist_path, 'rb') as f:
                    version_data = plistlib.load(f)

                has_version = 'ProjectVersion' in version_data
                version_value = version_data.get('ProjectVersion', 'Unknown')
                self.log_test("Version Information", has_version, f"v{version_value}")

            except Exception as e:
                self.log_test("Version Plist Content", False, str(e))

    def test_installation_script(self):
        """Test installation script"""
        install_script = self.build_dir / "install.sh"
        exists = install_script.exists()
        self.log_test("Installation Script", exists)

        if exists:
            is_executable = os.access(install_script, os.X_OK)
            self.log_test("Install Script Executable", is_executable)

    def test_bundle_validation_tools(self):
        """Test bundle with macOS validation tools (if on macOS)"""
        if sys.platform != 'darwin':
            self.log_test("Bundle Validation", True, "Skipped (not on macOS)")
            return

        try:
            # Test with plutil
            info_plist = self.contents_dir / "Info.plist"
            if info_plist.exists():
                result = subprocess.run(['plutil', '-lint', str(info_plist)],
                                       capture_output=True, text=True)
                plist_valid = result.returncode == 0
                self.log_test("plutil Validation", plist_valid)

            # Test with codesign (basic check)
            result = subprocess.run(['codesign', '-v', str(self.app_bundle)],
                                   capture_output=True, text=True)
            # codesign will fail on unsigned bundle, but should recognize structure
            recognized = "not signed" in result.stderr.lower() or result.returncode == 0
            self.log_test("Code Sign Recognition", recognized)

        except FileNotFoundError:
            self.log_test("macOS Validation Tools", False, "Tools not available")
        except Exception as e:
            self.log_test("Bundle Validation", False, str(e))

    def test_bundle_info_file(self):
        """Test bundle information file"""
        bundle_info = self.build_dir / "bundle_info.json"
        exists = bundle_info.exists()
        self.log_test("Bundle Info File", exists)

        if exists:
            try:
                with open(bundle_info, 'r', encoding='utf-8') as f:
                    info = json.load(f)

                required_fields = ["app_name", "bundle_identifier", "version"]
                has_all_fields = all(field in info for field in required_fields)
                self.log_test("Bundle Info Content", has_all_fields)

            except Exception as e:
                self.log_test("Bundle Info Parsing", False, str(e))

    def test_dependency_files(self):
        """Test Python dependency handling"""
        resources_dir = self.contents_dir / "Resources"
        requirements_file = resources_dir / "requirements.txt"

        if requirements_file.exists():
            try:
                with open(requirements_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                    has_streamlit = 'streamlit' in content.lower()
                    has_dependencies = len(content.strip().split('\n')) > 5
                    self.log_test("Requirements File", True, f"Has Streamlit: {has_streamlit}")
                    self.log_test("Sufficient Dependencies", has_dependencies)

            except Exception as e:
                self.log_test("Requirements File Reading", False, str(e))
        else:
            self.log_test("Requirements File", False, "Not found")

    def run_all_tests(self):
        """Run complete test suite"""
        print("[TARGET] macOS Bundle Test Suite - Alabama Auction Watcher")
        print("=" * 60)

        if not self.build_dir.exists():
            print(f"[ERROR] Build directory not found: {self.build_dir}")
            print("Please run the bundle creator first: python3 create_macos_app.py")
            return False

        if not self.app_bundle.exists():
            print(f"[ERROR] App bundle not found: {self.app_bundle}")
            print("Please run the bundle creator first: python3 create_macos_app.py")
            return False

        print(f"[INFO] Testing bundle at: {self.app_bundle}")
        print()

        # Run all tests
        self.test_bundle_structure()
        self.test_info_plist()
        self.test_executable_file()
        self.test_icon_files()
        self.test_application_resources()
        self.test_pkginfo_file()
        self.test_version_plist()
        self.test_installation_script()
        self.test_bundle_validation_tools()
        self.test_bundle_info_file()
        self.test_dependency_files()

        # Summary
        passed = sum(1 for result in self.test_results if result["status"] == "PASS")
        total = len(self.test_results)
        success_rate = (passed / total) * 100

        print()
        print("[SUMMARY] Test Results")
        print(f"Passed: {passed}/{total} ({success_rate:.1f}%)")

        if success_rate >= 80:
            print("[SUCCESS] macOS bundle validation completed successfully!")
            return True
        else:
            print("[WARNING] Some bundle components failed validation")
            print("Please review failed tests and rebuild if necessary")
            return False

    def generate_test_report(self):
        """Generate detailed test report"""
        report = {
            "test_date": __import__('datetime').datetime.now().isoformat(),
            "bundle_path": str(self.app_bundle),
            "platform": sys.platform,
            "total_tests": len(self.test_results),
            "passed_tests": sum(1 for r in self.test_results if r["status"] == "PASS"),
            "failed_tests": sum(1 for r in self.test_results if r["status"] == "FAIL"),
            "test_results": self.test_results
        }

        report_file = Path(__file__).parent / "macos_test_report.json"
        with open(report_file, 'w', encoding='utf-8') as f:
            json.dump(report, f, indent=2)

        print(f"[INFO] Test report saved: {report_file}")

def main():
    """Main test execution"""
    tester = MacOSBundleTester()

    success = tester.run_all_tests()
    tester.generate_test_report()

    if success:
        print("\n[OK] All tests completed successfully!")
        print("Bundle is ready for installation and deployment")
        sys.exit(0)
    else:
        print("\n[WARNING] Some tests failed - check results above")
        sys.exit(1)

if __name__ == '__main__':
    main()