"""
Quick Desktop Shortcut Creator for Alabama Auction Watcher
Simple script to create a desktop shortcut manually (Option 1)
"""

import os
import shutil
from pathlib import Path

def create_desktop_shortcut():
    """Create a desktop shortcut for Alabama Auction Watcher"""

    print("=== OPTION 1: MANUAL DESKTOP SHORTCUT CREATION ===")
    print()

    # Get paths
    project_dir = Path(__file__).parent.absolute()
    desktop = Path.home() / "Desktop"

    bat_file = project_dir / "Alabama Auction Watcher.bat"
    icon_file = project_dir / "branding" / "generated" / "windows" / "alabama-auction-watcher.ico"

    # Check if files exist
    print(f"Project directory: {project_dir}")
    print(f"Desktop directory: {desktop}")
    print(f"Launcher file: {bat_file} ({'EXISTS' if bat_file.exists() else 'MISSING'})")
    print(f"Icon file: {icon_file} ({'EXISTS' if icon_file.exists() else 'MISSING'})")
    print()

    if not bat_file.exists():
        print("ERROR: Alabama Auction Watcher.bat not found!")
        return False

    # Try to create VBScript to make proper shortcut with icon
    desktop_shortcut = desktop / "Alabama Auction Watcher.lnk"

    print("Creating desktop shortcut with professional icon...")

    # Create VBScript to generate proper Windows shortcut
    vbs_script = f'''
Set oWS = WScript.CreateObject("WScript.Shell")
sLinkFile = "{desktop_shortcut}"
Set oLink = oWS.CreateShortcut(sLinkFile)
oLink.TargetPath = "{bat_file}"
oLink.WorkingDirectory = "{project_dir}"
oLink.Description = "Alabama Auction Watcher - Professional Real Estate Investment Tool"
oLink.IconLocation = "{icon_file}"
oLink.Save
'''

    # Write and execute VBScript
    vbs_file = project_dir / "temp_shortcut_creator.vbs"

    try:
        with open(vbs_file, 'w') as f:
            f.write(vbs_script)

        # Execute VBScript
        os.system(f'cscript //nologo "{vbs_file}"')

        # Clean up
        vbs_file.unlink()

        if desktop_shortcut.exists():
            print(f"SUCCESS: Desktop shortcut created at:")
            print(f"  {desktop_shortcut}")
            print()
            print("You can now:")
            print("  1. Double-click the 'Alabama Auction Watcher' icon on your desktop")
            print("  2. It will launch the Smart GUI Launcher")
            print("  3. Access your enhanced system with 1,550 ranked properties")
            print()
            return True
        else:
            print("WARNING: Shortcut creation may have failed")
            return False

    except Exception as e:
        print(f"Error creating shortcut: {e}")
        return False

if __name__ == "__main__":
    success = create_desktop_shortcut()
    if not success:
        print()
        print("FALLBACK OPTION:")
        print("1. Right-click 'Alabama Auction Watcher.bat' in project folder")
        print("2. Select 'Create shortcut'")
        print("3. Drag the shortcut to your Desktop")
        print("4. Right-click shortcut → Properties → Change Icon")
        print("5. Browse to: branding/generated/windows/alabama-auction-watcher.ico")
        print()

    input("Press Enter to continue...")