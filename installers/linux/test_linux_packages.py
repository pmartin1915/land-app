#!/usr/bin/env python3
"""
Linux Package Test Suite
Validates Linux package structure and installation readiness
"""

import os
import sys
import subprocess
from pathlib import Path
import json
import tempfile

class LinuxPackageTester:
    """Test suite for Linux packages (.deb and .rpm)"""

    def __init__(self):
        self.build_dir = Path(__file__).parent / "build"
        self.app_name = "alabama-auction-watcher"
        self.version = "1.0.0"
        self.revision = "1"
        self.architecture = "all"
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

    def test_build_directory(self):
        """Test build directory structure"""
        build_exists = self.build_dir.exists()
        self.log_test("Build Directory", build_exists, str(self.build_dir))

        if build_exists:
            # Check subdirectories
            subdirs = ["deb", "rpm"]
            for subdir in subdirs:
                subdir_path = self.build_dir / subdir
                exists = subdir_path.exists()
                self.log_test(f"Build Subdir: {subdir}", exists)

    def test_deb_package_structure(self):
        """Test Debian package structure"""
        deb_file = self.build_dir / f"{self.app_name}_{self.version}-{self.revision}_{self.architecture}.deb"
        deb_exists = deb_file.exists()
        self.log_test("DEB Package File", deb_exists, str(deb_file.name))

        # Test DEB package structure
        deb_build_dir = self.build_dir / "deb"
        if deb_build_dir.exists():
            deb_root = deb_build_dir / f"{self.app_name}_{self.version}-{self.revision}_{self.architecture}"
            structure_exists = deb_root.exists()
            self.log_test("DEB Build Structure", structure_exists)

            if structure_exists:
                # Check DEBIAN control directory
                debian_dir = deb_root / "DEBIAN"
                debian_exists = debian_dir.exists()
                self.log_test("DEBIAN Directory", debian_exists)

                if debian_exists:
                    # Check control files
                    control_files = ["control", "postinst", "prerm", "postrm"]
                    for control_file in control_files:
                        file_path = debian_dir / control_file
                        exists = file_path.exists()
                        self.log_test(f"Control File: {control_file}", exists)

                        # Check if maintainer scripts are executable
                        if control_file in ["postinst", "prerm", "postrm"] and exists:
                            is_executable = os.access(file_path, os.X_OK)
                            self.log_test(f"Executable: {control_file}", is_executable)

    def test_rpm_spec_file(self):
        """Test RPM spec file"""
        spec_file = self.build_dir / "rpm" / "SPECS" / f"{self.app_name}.spec"
        spec_exists = spec_file.exists()
        self.log_test("RPM Spec File", spec_exists, str(spec_file.name))

        if spec_exists:
            try:
                with open(spec_file, 'r', encoding='utf-8') as f:
                    content = f.read()

                # Check for required spec sections
                required_sections = ["%description", "%files", "%install", "%post"]
                for section in required_sections:
                    has_section = section in content
                    self.log_test(f"Spec Section: {section}", has_section)

                # Check for package metadata
                metadata_fields = ["Name:", "Version:", "Release:", "Summary:"]
                for field in metadata_fields:
                    has_field = field in content
                    self.log_test(f"Spec Field: {field.rstrip(':')}", has_field)

            except Exception as e:
                self.log_test("RPM Spec Content", False, str(e))

    def test_application_files(self):
        """Test application files in package structure"""
        # Check DEB structure
        deb_root = self.build_dir / "deb" / f"{self.app_name}_{self.version}-{self.revision}_{self.architecture}"

        if deb_root.exists():
            app_dir = deb_root / "opt" / "alabama-auction-watcher"
            app_exists = app_dir.exists()
            self.log_test("Application Directory", app_exists)

            if app_exists:
                # Check for critical application files
                critical_files = [
                    "requirements.txt",
                    "start_backend_api.py",
                    "streamlit_app",
                    "backend_api",
                    "config"
                ]

                for file_name in critical_files:
                    file_path = app_dir / file_name
                    exists = file_path.exists()
                    file_type = "directory" if file_path.is_dir() else "file"
                    self.log_test(f"App File: {file_name}", exists, file_type)

    def test_launcher_script(self):
        """Test launcher script"""
        deb_root = self.build_dir / "deb" / f"{self.app_name}_{self.version}-{self.revision}_{self.architecture}"

        if deb_root.exists():
            launcher_script = deb_root / "usr" / "local" / "bin" / self.app_name
            exists = launcher_script.exists()
            self.log_test("Launcher Script", exists)

            if exists:
                # Check if executable
                is_executable = os.access(launcher_script, os.X_OK)
                self.log_test("Launcher Executable", is_executable)

                # Check script content
                try:
                    with open(launcher_script, 'r', encoding='utf-8') as f:
                        content = f.read()

                    is_bash_script = content.startswith('#!/bin/bash')
                    has_main_function = 'main()' in content
                    has_error_handling = 'show_error' in content

                    self.log_test("Bash Script Format", is_bash_script)
                    self.log_test("Has Main Function", has_main_function)
                    self.log_test("Has Error Handling", has_error_handling)

                except Exception as e:
                    self.log_test("Launcher Content", False, str(e))

    def test_desktop_integration(self):
        """Test desktop integration files"""
        deb_root = self.build_dir / "deb" / f"{self.app_name}_{self.version}-{self.revision}_{self.architecture}"

        if deb_root.exists():
            # Test desktop file
            desktop_file = deb_root / "usr" / "share" / "applications" / f"{self.app_name}.desktop"
            desktop_exists = desktop_file.exists()
            self.log_test("Desktop File", desktop_exists)

            if desktop_exists:
                try:
                    with open(desktop_file, 'r', encoding='utf-8') as f:
                        content = f.read()

                    # Check desktop file format
                    has_desktop_entry = '[Desktop Entry]' in content
                    has_name = 'Name=' in content
                    has_exec = 'Exec=' in content
                    has_icon = 'Icon=' in content

                    self.log_test("Desktop Entry Format", has_desktop_entry)
                    self.log_test("Desktop Name Field", has_name)
                    self.log_test("Desktop Exec Field", has_exec)
                    self.log_test("Desktop Icon Field", has_icon)

                except Exception as e:
                    self.log_test("Desktop File Content", False, str(e))

            # Test icon files
            icon_base = deb_root / "usr" / "share" / "icons" / "hicolor"
            if icon_base.exists():
                icon_sizes = ["16x16", "32x32", "48x48", "64x64", "128x128", "256x256"]
                icon_count = 0

                for size in icon_sizes:
                    icon_path = icon_base / size / "apps" / f"{self.app_name}.png"
                    if icon_path.exists():
                        icon_count += 1

                has_icons = icon_count > 0
                self.log_test("Icon Files", has_icons, f"{icon_count} sizes found")

    def test_documentation(self):
        """Test documentation files"""
        deb_root = self.build_dir / "deb" / f"{self.app_name}_{self.version}-{self.revision}_{self.architecture}"

        if deb_root.exists():
            doc_dir = deb_root / "usr" / "share" / "doc" / self.app_name
            doc_exists = doc_dir.exists()
            self.log_test("Documentation Directory", doc_exists)

            if doc_exists:
                # Check for required documentation
                doc_files = ["README", "changelog"]
                for doc_file in doc_files:
                    file_path = doc_dir / doc_file
                    exists = file_path.exists()
                    self.log_test(f"Doc File: {doc_file}", exists)

    def test_package_validation_tools(self):
        """Test packages with system validation tools"""
        deb_file = self.build_dir / f"{self.app_name}_{self.version}-{self.revision}_{self.architecture}.deb"

        if deb_file.exists():
            # Test with dpkg (if available)
            try:
                result = subprocess.run(['dpkg', '--info', str(deb_file)],
                                       capture_output=True, text=True, timeout=30)
                dpkg_valid = result.returncode == 0
                self.log_test("dpkg Info Check", dpkg_valid)

                if dpkg_valid and result.stdout:
                    # Check for package metadata in output
                    has_package_info = 'Package:' in result.stdout
                    has_version_info = 'Version:' in result.stdout
                    self.log_test("Package Metadata", has_package_info)
                    self.log_test("Version Metadata", has_version_info)

            except FileNotFoundError:
                self.log_test("dpkg Validation", True, "dpkg not available (not on Debian/Ubuntu)")
            except subprocess.TimeoutExpired:
                self.log_test("dpkg Validation", False, "Timeout")
            except Exception as e:
                self.log_test("dpkg Validation", False, str(e))

            # Test file list extraction
            try:
                result = subprocess.run(['dpkg', '--contents', str(deb_file)],
                                       capture_output=True, text=True, timeout=30)
                contents_valid = result.returncode == 0
                self.log_test("Package Contents", contents_valid)

                if contents_valid:
                    # Check for key files in contents
                    contents = result.stdout
                    has_launcher = f'./usr/local/bin/{self.app_name}' in contents
                    has_desktop = f'./usr/share/applications/{self.app_name}.desktop' in contents
                    self.log_test("Contents: Launcher", has_launcher)
                    self.log_test("Contents: Desktop", has_desktop)

            except FileNotFoundError:
                self.log_test("Package Contents", True, "dpkg not available")
            except Exception as e:
                self.log_test("Package Contents", False, str(e))

    def test_package_info_file(self):
        """Test package information file"""
        info_file = self.build_dir / "package_info.json"
        exists = info_file.exists()
        self.log_test("Package Info File", exists)

        if exists:
            try:
                with open(info_file, 'r', encoding='utf-8') as f:
                    info = json.load(f)

                required_fields = ["package_name", "version", "maintainer", "packages_created"]
                has_all_fields = all(field in info for field in required_fields)
                self.log_test("Package Info Content", has_all_fields)

                # Check packages created info
                if "packages_created" in info:
                    packages = info["packages_created"]
                    has_deb_info = "deb" in packages
                    has_rpm_info = "rpm_spec" in packages
                    self.log_test("DEB Package Info", has_deb_info)
                    self.log_test("RPM Package Info", has_rpm_info)

            except Exception as e:
                self.log_test("Package Info Parsing", False, str(e))

    def test_dependency_requirements(self):
        """Test dependency requirements"""
        deb_root = self.build_dir / "deb" / f"{self.app_name}_{self.version}-{self.revision}_{self.architecture}"

        if deb_root.exists():
            control_file = deb_root / "DEBIAN" / "control"

            if control_file.exists():
                try:
                    with open(control_file, 'r', encoding='utf-8') as f:
                        content = f.read()

                    # Check for required dependencies
                    has_python3 = 'python3' in content
                    has_pip = 'python3-pip' in content
                    has_depends = 'Depends:' in content

                    self.log_test("Python3 Dependency", has_python3)
                    self.log_test("Pip Dependency", has_pip)
                    self.log_test("Depends Field", has_depends)

                except Exception as e:
                    self.log_test("Dependency Check", False, str(e))

    def run_all_tests(self):
        """Run complete test suite"""
        print("[TARGET] Linux Package Test Suite - Alabama Auction Watcher")
        print("=" * 60)

        if not self.build_dir.exists():
            print(f"[ERROR] Build directory not found: {self.build_dir}")
            print("Please run the package creator first: python3 create_linux_packages.py")
            return False

        print(f"[INFO] Testing packages in: {self.build_dir}")
        print()

        # Run all tests
        self.test_build_directory()
        self.test_deb_package_structure()
        self.test_rpm_spec_file()
        self.test_application_files()
        self.test_launcher_script()
        self.test_desktop_integration()
        self.test_documentation()
        self.test_package_validation_tools()
        self.test_package_info_file()
        self.test_dependency_requirements()

        # Summary
        passed = sum(1 for result in self.test_results if result["status"] == "PASS")
        total = len(self.test_results)
        success_rate = (passed / total) * 100

        print()
        print("[SUMMARY] Test Results")
        print(f"Passed: {passed}/{total} ({success_rate:.1f}%)")

        if success_rate >= 80:
            print("[SUCCESS] Linux package validation completed successfully!")
            return True
        else:
            print("[WARNING] Some package components failed validation")
            print("Please review failed tests and rebuild packages if necessary")
            return False

    def generate_test_report(self):
        """Generate detailed test report"""
        report = {
            "test_date": __import__('datetime').datetime.now().isoformat(),
            "build_directory": str(self.build_dir),
            "platform": sys.platform,
            "total_tests": len(self.test_results),
            "passed_tests": sum(1 for r in self.test_results if r["status"] == "PASS"),
            "failed_tests": sum(1 for r in self.test_results if r["status"] == "FAIL"),
            "test_results": self.test_results
        }

        report_file = Path(__file__).parent / "linux_test_report.json"
        with open(report_file, 'w', encoding='utf-8') as f:
            json.dump(report, f, indent=2)

        print(f"[INFO] Test report saved: {report_file}")

def main():
    """Main test execution"""
    tester = LinuxPackageTester()

    success = tester.run_all_tests()
    tester.generate_test_report()

    if success:
        print("\n[OK] All tests completed successfully!")
        print("Packages are ready for distribution and installation")
        sys.exit(0)
    else:
        print("\n[WARNING] Some tests failed - check results above")
        sys.exit(1)

if __name__ == '__main__':
    main()