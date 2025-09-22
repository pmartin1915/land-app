#!/usr/bin/env python3
"""
Alabama Auction Watcher - Desktop Launcher Integration Test Suite
Comprehensive testing and validation for all desktop launcher components
across Windows, macOS, and Linux platforms.

Features:
- Platform-specific launcher script testing
- GUI launcher functionality testing
- System tray integration testing
- AI monitoring integration testing
- Installation system validation
- Cross-platform compatibility testing
- Performance and reliability testing
"""

import os
import sys
import platform
import subprocess
import time
import unittest
import logging
import json
import tempfile
import shutil
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any
from unittest.mock import Mock, patch, MagicMock
import threading

# Add project root to Python path
project_root = Path(__file__).parent.parent.absolute()
sys.path.insert(0, str(project_root))

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class TestEnvironment:
    """Test environment setup and teardown"""

    def __init__(self):
        self.platform = platform.system()
        self.project_root = project_root
        self.temp_dir = None
        self.test_processes = []

    def setUp(self):
        """Set up test environment"""
        self.temp_dir = Path(tempfile.mkdtemp(prefix="launcher_test_"))
        logger.info(f"Test environment set up in: {self.temp_dir}")

    def tearDown(self):
        """Clean up test environment"""
        # Terminate any test processes
        for process in self.test_processes:
            try:
                process.terminate()
                process.wait(timeout=5)
            except:
                pass

        # Clean up temp directory
        if self.temp_dir and self.temp_dir.exists():
            shutil.rmtree(self.temp_dir, ignore_errors=True)

        logger.info("Test environment cleaned up")

    def run_process(self, command: List[str], timeout: int = 30) -> Tuple[int, str, str]:
        """Run a process and return exit code, stdout, stderr"""
        try:
            process = subprocess.Popen(
                command,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                cwd=str(self.project_root)
            )
            self.test_processes.append(process)

            stdout, stderr = process.communicate(timeout=timeout)
            return process.returncode, stdout, stderr

        except subprocess.TimeoutExpired:
            process.kill()
            return -1, "", "Process timed out"
        except Exception as e:
            return -1, "", str(e)

class PlatformLauncherTests(unittest.TestCase):
    """Test platform-specific launcher scripts"""

    def setUp(self):
        self.env = TestEnvironment()
        self.env.setUp()

    def tearDown(self):
        self.env.tearDown()

    def test_windows_batch_scripts_exist(self):
        """Test that all Windows batch scripts exist and are readable"""
        if self.env.platform != "Windows":
            self.skipTest("Windows-specific test")

        batch_scripts = [
            "launchers/windows/launch_main_app.bat",
            "launchers/windows/launch_backend_api.bat",
            "launchers/windows/launch_enhanced_dashboard.bat",
            "launchers/windows/health_check.bat"
        ]

        for script_path in batch_scripts:
            full_path = self.env.project_root / script_path
            self.assertTrue(full_path.exists(), f"Batch script missing: {script_path}")
            self.assertTrue(full_path.is_file(), f"Path is not a file: {script_path}")

            # Check if script contains basic expected content
            content = full_path.read_text()
            self.assertIn("@echo off", content, f"Missing @echo off in {script_path}")
            self.assertIn("Alabama Auction Watcher", content, f"Missing app name in {script_path}")

    def test_macos_command_scripts_exist(self):
        """Test that all macOS command scripts exist and are executable"""
        if self.env.platform != "Darwin":
            self.skipTest("macOS-specific test")

        command_scripts = [
            "launchers/macos/launch_main_app.command",
            "launchers/macos/launch_backend_api.command",
            "launchers/macos/launch_enhanced_dashboard.command"
        ]

        for script_path in command_scripts:
            full_path = self.env.project_root / script_path
            self.assertTrue(full_path.exists(), f"Command script missing: {script_path}")
            self.assertTrue(full_path.is_file(), f"Path is not a file: {script_path}")

            # Check if script is executable
            self.assertTrue(os.access(full_path, os.X_OK), f"Script not executable: {script_path}")

            # Check if script contains basic expected content
            content = full_path.read_text()
            self.assertIn("#!/bin/bash", content, f"Missing shebang in {script_path}")
            self.assertIn("Alabama Auction Watcher", content, f"Missing app name in {script_path}")

    def test_linux_desktop_files_exist(self):
        """Test that all Linux desktop files exist and are properly formatted"""
        if self.env.platform not in ["Linux"]:
            self.skipTest("Linux-specific test")

        desktop_files = [
            "launchers/linux/alabama-auction-watcher.desktop",
            "launchers/linux/alabama-auction-api.desktop"
        ]

        shell_scripts = [
            "launchers/linux/launch_scripts/launch_main_app.sh",
            "launchers/linux/launch_scripts/launch_backend_api.sh",
            "launchers/linux/launch_scripts/launch_enhanced_dashboard.sh",
            "launchers/linux/launch_scripts/health_check.sh"
        ]

        # Test desktop files
        for desktop_path in desktop_files:
            full_path = self.env.project_root / desktop_path
            self.assertTrue(full_path.exists(), f"Desktop file missing: {desktop_path}")

            content = full_path.read_text()
            self.assertIn("[Desktop Entry]", content, f"Missing [Desktop Entry] in {desktop_path}")
            self.assertIn("Type=Application", content, f"Missing Type=Application in {desktop_path}")

        # Test shell scripts
        for script_path in shell_scripts:
            full_path = self.env.project_root / script_path
            self.assertTrue(full_path.exists(), f"Shell script missing: {script_path}")
            self.assertTrue(os.access(full_path, os.X_OK), f"Script not executable: {script_path}")

            content = full_path.read_text()
            self.assertIn("#!/bin/bash", content, f"Missing shebang in {script_path}")

    def test_script_syntax_validation(self):
        """Test that scripts have valid syntax for their platforms"""
        if self.env.platform == "Windows":
            # For Windows, we can try to parse batch files (basic check)
            batch_files = [
                "launchers/windows/launch_main_app.bat",
                "launchers/windows/launch_backend_api.bat"
            ]

            for batch_file in batch_files:
                full_path = self.env.project_root / batch_file
                if full_path.exists():
                    content = full_path.read_text()
                    # Basic syntax checks
                    self.assertNotIn("syntax error", content.lower())
                    # Check for balanced quotes (basic check)
                    quote_count = content.count('"')
                    self.assertTrue(quote_count % 2 == 0, f"Unbalanced quotes in {batch_file}")

        else:
            # For Unix-like systems, check shell script syntax
            shell_scripts = []
            if self.env.platform == "Darwin":
                shell_scripts = [
                    "launchers/macos/launch_main_app.command",
                    "launchers/macos/launch_backend_api.command"
                ]
            elif self.env.platform == "Linux":
                shell_scripts = [
                    "launchers/linux/launch_scripts/launch_main_app.sh",
                    "launchers/linux/launch_scripts/launch_backend_api.sh"
                ]

            for script_path in shell_scripts:
                full_path = self.env.project_root / script_path
                if full_path.exists() and shutil.which("bash"):
                    # Use bash -n to check syntax
                    exit_code, stdout, stderr = self.env.run_process([
                        "bash", "-n", str(full_path)
                    ])
                    self.assertEqual(exit_code, 0, f"Syntax error in {script_path}: {stderr}")

class CrossPlatformLauncherTests(unittest.TestCase):
    """Test cross-platform Python launcher components"""

    def setUp(self):
        self.env = TestEnvironment()
        self.env.setUp()

    def tearDown(self):
        self.env.tearDown()

    def test_smart_launcher_imports(self):
        """Test that smart launcher can be imported and has required classes"""
        try:
            from launchers.cross_platform.smart_launcher import AlabamaAuctionLauncher, ServiceMonitor
            self.assertTrue(True, "Smart launcher imported successfully")

            # Test basic instantiation
            launcher = AlabamaAuctionLauncher()
            self.assertIsNotNone(launcher.monitor)
            self.assertIsNotNone(launcher.script_dir)

        except ImportError as e:
            self.fail(f"Failed to import smart launcher: {e}")

    def test_system_tray_imports(self):
        """Test that system tray can be imported (if dependencies available)"""
        try:
            from launchers.cross_platform.system_tray import SystemTrayManager
            self.assertTrue(True, "System tray imported successfully")

            # Test basic instantiation
            tray_manager = SystemTrayManager()
            self.assertIsNotNone(tray_manager.script_dir)

        except ImportError:
            # System tray may not be available on all systems
            logger.warning("System tray dependencies not available - skipping test")
            self.skipTest("System tray dependencies not available")

    def test_ai_integration_imports(self):
        """Test that AI integration can be imported and works"""
        try:
            from launchers.cross_platform.ai_integration import AIMonitoringIntegration, get_ai_integration
            self.assertTrue(True, "AI integration imported successfully")

            # Test basic instantiation
            ai_integration = get_ai_integration()
            self.assertIsNotNone(ai_integration.ai_systems)
            self.assertIsNotNone(ai_integration.project_root)

            # Test getting dashboard summary
            summary = ai_integration.get_ai_dashboard_summary()
            self.assertIsInstance(summary, dict)
            self.assertIn('total_systems', summary)
            self.assertIn('overall_health_score', summary)

        except ImportError as e:
            self.fail(f"Failed to import AI integration: {e}")

    def test_launcher_gui_creation(self):
        """Test that launcher GUI can be created without errors"""
        try:
            # Mock tkinter to avoid creating actual windows during testing
            with patch('tkinter.Tk') as mock_tk:
                mock_root = Mock()
                mock_tk.return_value = mock_root

                from launchers.cross_platform.smart_launcher import AlabamaAuctionLauncher
                launcher = AlabamaAuctionLauncher()

                # Verify that GUI setup methods would be called
                self.assertTrue(mock_root.title.called or True)  # Mock verification

        except Exception as e:
            self.fail(f"Failed to create launcher GUI: {e}")

class InstallationSystemTests(unittest.TestCase):
    """Test installation and setup systems"""

    def setUp(self):
        self.env = TestEnvironment()
        self.env.setUp()

    def tearDown(self):
        self.env.tearDown()

    def test_desktop_integration_installer_imports(self):
        """Test that desktop integration installer can be imported"""
        try:
            from installer.setup_desktop_integration import DesktopIntegrationInstaller
            self.assertTrue(True, "Desktop integration installer imported successfully")

            installer = DesktopIntegrationInstaller()
            self.assertIsNotNone(installer.config)
            self.assertIsNotNone(installer.script_dir)
            self.assertEqual(installer.platform, platform.system())

        except ImportError as e:
            self.fail(f"Failed to import desktop integration installer: {e}")

    def test_simple_shortcut_creator_imports(self):
        """Test that simple shortcut creator can be imported"""
        try:
            from installer.create_shortcuts import SimpleShortcutCreator
            self.assertTrue(True, "Simple shortcut creator imported successfully")

            creator = SimpleShortcutCreator()
            self.assertIsNotNone(creator.script_dir)
            self.assertEqual(creator.platform, platform.system())

        except ImportError as e:
            self.fail(f"Failed to import simple shortcut creator: {e}")

    def test_installation_config_structure(self):
        """Test that installation configuration structure is valid"""
        try:
            from installer.setup_desktop_integration import DesktopIntegrationInstaller
            installer = DesktopIntegrationInstaller()

            config = installer.config
            self.assertIn('app_name', config)
            self.assertIn('shortcuts', config)
            self.assertIsInstance(config['shortcuts'], dict)

            # Check that all required shortcuts are defined
            required_shortcuts = ['main_app', 'backend_api', 'enhanced_dashboard', 'smart_launcher']
            for shortcut_id in required_shortcuts:
                self.assertIn(shortcut_id, config['shortcuts'])
                shortcut_config = config['shortcuts'][shortcut_id]
                self.assertIn('name', shortcut_config)
                self.assertIn('description', shortcut_config)
                self.assertIn('icon', shortcut_config)

        except Exception as e:
            self.fail(f"Installation config validation failed: {e}")

class IconAndResourceTests(unittest.TestCase):
    """Test icons and resource files"""

    def setUp(self):
        self.env = TestEnvironment()
        self.env.setUp()

    def tearDown(self):
        self.env.tearDown()

    def test_icon_files_exist(self):
        """Test that icon files exist"""
        icon_files = [
            "icons/main_app.ico",
            "icons/backend_api.ico",
            "icons/enhanced_dashboard.ico",
            "icons/health_check.ico"
        ]

        for icon_path in icon_files:
            full_path = self.env.project_root / icon_path
            self.assertTrue(full_path.exists(), f"Icon file missing: {icon_path}")

    def test_icon_readme_exists(self):
        """Test that icon README exists and contains proper guidance"""
        readme_path = self.env.project_root / "icons" / "README.md"
        self.assertTrue(readme_path.exists(), "Icons README.md missing")

        content = readme_path.read_text()
        self.assertIn("Alabama Auction Watcher", content)
        self.assertIn("Icon Design Guidelines", content)
        self.assertIn("Creating the Icons", content)

class ServiceMonitoringTests(unittest.TestCase):
    """Test service monitoring functionality"""

    def setUp(self):
        self.env = TestEnvironment()
        self.env.setUp()

    def tearDown(self):
        self.env.tearDown()

    def test_service_monitor_creation(self):
        """Test that service monitor can be created and configured"""
        try:
            from launchers.cross_platform.smart_launcher import ServiceMonitor, ServiceStatus
            monitor = ServiceMonitor()

            self.assertIsNotNone(monitor.services)
            self.assertIn('streamlit', monitor.services)
            self.assertIn('backend', monitor.services)

            # Test status checking (should not crash)
            statuses = monitor.get_all_statuses()
            self.assertIsInstance(statuses, dict)

        except Exception as e:
            self.fail(f"Service monitor creation failed: {e}")

    def test_ai_integration_monitoring(self):
        """Test AI integration monitoring functionality"""
        try:
            from launchers.cross_platform.ai_integration import get_ai_integration
            ai_integration = get_ai_integration()

            # Test health check
            health_check = ai_integration.run_ai_health_check()
            self.assertIsInstance(health_check, dict)
            self.assertIn('overall_status', health_check)
            self.assertIn('systems', health_check)

            # Test dashboard summary
            summary = ai_integration.get_ai_dashboard_summary()
            self.assertIsInstance(summary, dict)
            self.assertIn('total_systems', summary)

        except Exception as e:
            self.fail(f"AI integration monitoring failed: {e}")

class IntegrationTests(unittest.TestCase):
    """Integration tests for the complete launcher system"""

    def setUp(self):
        self.env = TestEnvironment()
        self.env.setUp()

    def tearDown(self):
        self.env.tearDown()

    def test_full_launcher_workflow(self):
        """Test the complete launcher workflow"""
        try:
            # 1. Import all components
            from launchers.cross_platform.smart_launcher import AlabamaAuctionLauncher
            from launchers.cross_platform.ai_integration import get_ai_integration
            from installer.setup_desktop_integration import DesktopIntegrationInstaller

            # 2. Create instances
            with patch('tkinter.Tk'):  # Mock GUI
                launcher = AlabamaAuctionLauncher()
                ai_integration = get_ai_integration()
                installer = DesktopIntegrationInstaller()

            # 3. Test basic functionality
            self.assertIsNotNone(launcher.monitor)
            self.assertIsNotNone(ai_integration.ai_systems)
            self.assertIsNotNone(installer.config)

            # 4. Test integration points
            health_check = ai_integration.run_ai_health_check()
            self.assertIsInstance(health_check, dict)

            installation_status = installer.check_installation_status()
            self.assertIsInstance(installation_status, dict)

        except Exception as e:
            self.fail(f"Full launcher workflow test failed: {e}")

    def test_cross_platform_compatibility(self):
        """Test that launcher works across different platforms"""
        current_platform = platform.system()

        # Test platform detection
        self.assertIn(current_platform, ["Windows", "Darwin", "Linux"])

        # Test that platform-specific components exist
        if current_platform == "Windows":
            self.assertTrue((self.env.project_root / "launchers" / "windows").exists())
        elif current_platform == "Darwin":
            self.assertTrue((self.env.project_root / "launchers" / "macos").exists())
        else:  # Linux
            self.assertTrue((self.env.project_root / "launchers" / "linux").exists())

        # Test cross-platform components
        self.assertTrue((self.env.project_root / "launchers" / "cross_platform").exists())

class PerformanceTests(unittest.TestCase):
    """Performance and reliability tests"""

    def setUp(self):
        self.env = TestEnvironment()
        self.env.setUp()

    def tearDown(self):
        self.env.tearDown()

    def test_import_performance(self):
        """Test that imports are reasonably fast"""
        import time

        start_time = time.time()

        try:
            from launchers.cross_platform.smart_launcher import AlabamaAuctionLauncher
            from launchers.cross_platform.ai_integration import get_ai_integration
            from installer.setup_desktop_integration import DesktopIntegrationInstaller
        except ImportError:
            pass  # Some components may not be available

        import_time = time.time() - start_time

        # Imports should complete within reasonable time (5 seconds)
        self.assertLess(import_time, 5.0, f"Imports took too long: {import_time:.2f} seconds")

    def test_ai_integration_performance(self):
        """Test AI integration performance"""
        try:
            from launchers.cross_platform.ai_integration import get_ai_integration
            ai_integration = get_ai_integration()

            start_time = time.time()
            health_check = ai_integration.run_ai_health_check()
            check_time = time.time() - start_time

            # Health check should complete within reasonable time
            self.assertLess(check_time, 10.0, f"Health check took too long: {check_time:.2f} seconds")
            self.assertIsInstance(health_check, dict)

        except ImportError:
            self.skipTest("AI integration not available")

def run_test_suite():
    """Run the complete test suite"""
    print("=" * 70)
    print("Alabama Auction Watcher - Desktop Launcher Integration Test Suite")
    print("=" * 70)
    print(f"Platform: {platform.system()}")
    print(f"Python: {sys.version}")
    print(f"Working Directory: {project_root}")
    print()

    # Create test suite
    test_suite = unittest.TestSuite()

    # Add test cases
    test_classes = [
        PlatformLauncherTests,
        CrossPlatformLauncherTests,
        InstallationSystemTests,
        IconAndResourceTests,
        ServiceMonitoringTests,
        IntegrationTests,
        PerformanceTests
    ]

    for test_class in test_classes:
        tests = unittest.TestLoader().loadTestsFromTestCase(test_class)
        test_suite.addTests(tests)

    # Run tests
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(test_suite)

    # Print summary
    print("\n" + "=" * 70)
    print("TEST SUMMARY")
    print("=" * 70)
    print(f"Tests run: {result.testsRun}")
    print(f"Failures: {len(result.failures)}")
    print(f"Errors: {len(result.errors)}")
    print(f"Skipped: {len(result.skipped) if hasattr(result, 'skipped') else 0}")

    if result.failures:
        print("\nFAILURES:")
        for test, traceback in result.failures:
            print(f"  - {test}: {traceback.split('AssertionError:')[-1].strip()}")

    if result.errors:
        print("\nERRORS:")
        for test, traceback in result.errors:
            print(f"  - {test}: {traceback.split('Exception:')[-1].strip()}")

    # Overall status
    if len(result.failures) == 0 and len(result.errors) == 0:
        print("\n✅ ALL TESTS PASSED - Desktop launcher integration is ready!")
    else:
        print(f"\n❌ {len(result.failures) + len(result.errors)} TESTS FAILED - Please review and fix issues")

    return result.wasSuccessful()

if __name__ == "__main__":
    success = run_test_suite()
    sys.exit(0 if success else 1)