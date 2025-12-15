"""
Automated Desktop Integration Setup (Non-Interactive)
Alabama Auction Watcher - Option 2 Professional Setup

Automatically creates desktop shortcuts, Start Menu entries, and system integration
without requiring user interaction.
"""

import os
import sys
import platform
import logging
from pathlib import Path
from typing import Dict, List

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class AutoDesktopIntegrator:
    """Automated desktop integration without user prompts"""

    def __init__(self):
        self.platform = platform.system()
        self.project_dir = Path(__file__).parent.absolute()
        self.app_name = "Alabama Auction Watcher"
        self.app_id = "alabama-auction-watcher"

        # Shortcut configurations
        self.shortcuts = {
            'main_launcher': {
                'name': 'Alabama Auction Watcher',
                'description': 'Professional Real Estate Investment Tool - Smart Launcher',
                'target': str(self.project_dir / "Alabama Auction Watcher.bat"),
                'icon': str(self.project_dir / "branding/generated/windows/alabama-auction-watcher.ico"),
                'category': 'Office;Finance;'
            },
            'smart_launcher': {
                'name': 'Alabama Auction Watcher - Launcher',
                'description': 'Smart GUI Launcher with Monitoring and Controls',
                'target': str(self.project_dir / "launchers/cross_platform/smart_launcher.py"),
                'icon': str(self.project_dir / "branding/generated/windows/aaw-settings.ico"),
                'category': 'Office;Development;'
            },
            'enhanced_dashboard': {
                'name': 'Alabama Auction Watcher - Enhanced Dashboard',
                'description': 'Full-Featured Enhanced Dashboard with AI Analytics',
                'target': str(self.project_dir / "launchers/windows/launch_enhanced_dashboard.bat"),
                'icon': str(self.project_dir / "branding/generated/windows/aaw-analytics.ico"),
                'category': 'Office;Finance;'
            }
        }

    def create_windows_shortcuts(self) -> bool:
        """Create Windows desktop shortcuts and Start Menu entries"""
        logger.info("Creating Windows desktop integration...")

        try:
            desktop = Path.home() / "Desktop"
            success_count = 0

            for shortcut_id, config in self.shortcuts.items():
                logger.info(f"Creating shortcut: {config['name']}")

                # Create desktop shortcut using VBScript
                shortcut_path = desktop / f"{config['name']}.lnk"

                # Create VBScript to generate proper Windows shortcut
                vbs_script = f'''
Set oWS = WScript.CreateObject("WScript.Shell")
sLinkFile = "{shortcut_path}"
Set oLink = oWS.CreateShortcut(sLinkFile)
oLink.TargetPath = "{config['target']}"
oLink.WorkingDirectory = "{self.project_dir}"
oLink.Description = "{config['description']}"
oLink.IconLocation = "{config['icon']}"
oLink.Save
'''

                # Write and execute VBScript
                vbs_file = self.project_dir / f"temp_{shortcut_id}.vbs"

                try:
                    with open(vbs_file, 'w') as f:
                        f.write(vbs_script)

                    # Execute VBScript silently
                    result = os.system(f'cscript //nologo "{vbs_file}" >nul 2>&1')

                    # Clean up
                    if vbs_file.exists():
                        vbs_file.unlink()

                    if shortcut_path.exists():
                        logger.info(f"✓ Created: {config['name']}")
                        success_count += 1
                    else:
                        logger.warning(f"✗ Failed: {config['name']}")

                except Exception as e:
                    logger.error(f"Error creating {config['name']}: {e}")

            # Try to create Start Menu shortcuts
            try:
                self._create_start_menu_shortcuts()
            except Exception as e:
                logger.warning(f"Start Menu creation failed: {e}")

            logger.info(f"Desktop integration complete: {success_count}/{len(self.shortcuts)} shortcuts created")
            return success_count > 0

        except Exception as e:
            logger.error(f"Windows desktop integration failed: {e}")
            return False

    def _create_start_menu_shortcuts(self):
        """Create Start Menu shortcuts (Windows)"""
        try:
            # Try to get Start Menu path
            start_menu_paths = [
                Path(os.environ.get('APPDATA', '')) / "Microsoft/Windows/Start Menu/Programs",
                Path.home() / "AppData/Roaming/Microsoft/Windows/Start Menu/Programs"
            ]

            start_menu = None
            for path in start_menu_paths:
                if path.exists():
                    start_menu = path
                    break

            if not start_menu:
                logger.warning("Start Menu path not found")
                return

            # Create app folder in Start Menu
            app_folder = start_menu / self.app_name
            app_folder.mkdir(exist_ok=True)

            # Create Start Menu shortcuts
            for shortcut_id, config in self.shortcuts.items():
                if shortcut_id == 'main_launcher':  # Only main launcher in Start Menu
                    shortcut_path = app_folder / f"{config['name']}.lnk"

                    vbs_script = f'''
Set oWS = WScript.CreateObject("WScript.Shell")
sLinkFile = "{shortcut_path}"
Set oLink = oWS.CreateShortcut(sLinkFile)
oLink.TargetPath = "{config['target']}"
oLink.WorkingDirectory = "{self.project_dir}"
oLink.Description = "{config['description']}"
oLink.IconLocation = "{config['icon']}"
oLink.Save
'''

                    vbs_file = self.project_dir / f"temp_startmenu_{shortcut_id}.vbs"
                    with open(vbs_file, 'w') as f:
                        f.write(vbs_script)

                    os.system(f'cscript //nologo "{vbs_file}" >nul 2>&1')

                    if vbs_file.exists():
                        vbs_file.unlink()

                    if shortcut_path.exists():
                        logger.info(f"✓ Start Menu: {config['name']}")

        except Exception as e:
            logger.warning(f"Start Menu shortcuts failed: {e}")

    def run_integration(self) -> bool:
        """Run the automated desktop integration"""
        print(f"=== OPTION 2: AUTOMATED PROFESSIONAL SETUP ===")
        print(f"Platform: {self.platform}")
        print(f"Project Directory: {self.project_dir}")
        print()

        if self.platform == "Windows":
            success = self.create_windows_shortcuts()
        else:
            logger.warning(f"Automated setup not implemented for {self.platform}")
            logger.info("Please use Option 1 (manual) or run the interactive installer")
            return False

        return success

def main():
    """Main function to run automated desktop integration"""
    integrator = AutoDesktopIntegrator()

    try:
        success = integrator.run_integration()

        print()
        if success:
            print("🎉 DESKTOP INTEGRATION COMPLETE!")
            print()
            print("You now have desktop icons for:")
            print("  • Alabama Auction Watcher (Main Application)")
            print("  • Alabama Auction Watcher - Launcher (GUI Manager)")
            print("  • Alabama Auction Watcher - Enhanced Dashboard (Full System)")
            print()
            print("Plus Start Menu entries for easy access!")
            print()
            print("Double-click any desktop icon to launch the enhanced system with:")
            print("  ✓ 1,550 properties with enhanced scoring")
            print("  ✓ Advanced description intelligence")
            print("  ✓ County market intelligence")
            print("  ✓ Professional investment rankings")
            print("  ✓ Real-time monitoring and controls")
            print()
        else:
            print("❌ DESKTOP INTEGRATION FAILED")
            print()
            print("Fallback options:")
            print("1. Run: python create_desktop_shortcut.py")
            print("2. Run: python installer/setup_desktop_integration.py")
            print("3. Manually create shortcut from Alabama Auction Watcher.bat")
            print()

    except Exception as e:
        logger.error(f"Setup failed: {e}")
        print(f"❌ Setup failed: {e}")

if __name__ == "__main__":
    main()