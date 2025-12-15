#!/usr/bin/env python3
"""
macOS Application Bundle Creator
Creates professional .app bundle and PKG installer for Alabama Auction Watcher
"""

import os
import sys
import shutil
import plistlib
import subprocess
from pathlib import Path
import json
import tempfile

class MacOSAppBundleCreator:
    """Professional macOS .app bundle and PKG installer creator"""

    def __init__(self):
        self.app_name = "Alabama Auction Watcher"
        self.bundle_identifier = "com.alabamaauctionwatcher.app"
        self.version = "1.0.0"
        self.build_number = "1"

        # Source directory (auction root)
        self.source_dir = Path(__file__).parent.parent.parent

        # Build directories
        self.build_dir = Path(__file__).parent / "build"
        self.app_bundle_dir = self.build_dir / f"{self.app_name}.app"
        self.contents_dir = self.app_bundle_dir / "Contents"
        self.macos_dir = self.contents_dir / "MacOS"
        self.resources_dir = self.contents_dir / "Resources"
        self.frameworks_dir = self.contents_dir / "Frameworks"

    def create_bundle_structure(self):
        """Create macOS .app bundle directory structure"""
        print("[INFO] Creating macOS .app bundle structure...")

        # Remove existing bundle
        if self.app_bundle_dir.exists():
            shutil.rmtree(self.app_bundle_dir)

        # Create standard .app structure
        directories = [
            self.contents_dir,
            self.macos_dir,
            self.resources_dir,
            self.frameworks_dir
        ]

        for directory in directories:
            directory.mkdir(parents=True, exist_ok=True)
            print(f"[INFO] Created: {directory.relative_to(self.build_dir)}")

    def create_info_plist(self):
        """Create Info.plist with application metadata"""
        print("[INFO] Creating Info.plist...")

        info_plist = {
            'CFBundleName': self.app_name,
            'CFBundleDisplayName': self.app_name,
            'CFBundleIdentifier': self.bundle_identifier,
            'CFBundleVersion': self.build_number,
            'CFBundleShortVersionString': self.version,
            'CFBundlePackageType': 'APPL',
            'CFBundleSignature': 'AAAW',
            'CFBundleExecutable': 'launch_alabama_auction_watcher',
            'CFBundleIconFile': 'alabama_auction_watcher.icns',
            'LSMinimumSystemVersion': '10.14.0',
            'LSApplicationCategoryType': 'public.app-category.business',
            'NSHighResolutionCapable': True,
            'NSSupportsAutomaticGraphicsSwitching': True,
            'NSRequiresAquaSystemAppearance': False,

            # Document types (for aaw:// URLs)
            'CFBundleURLTypes': [{
                'CFBundleURLName': 'Alabama Auction Watcher Protocol',
                'CFBundleURLSchemes': ['aaw'],
                'CFBundleTypeRole': 'Viewer'
            }],

            # Application description
            'CFBundleGetInfoString': f'{self.app_name} {self.version} - Professional Real Estate Auction Intelligence',
            'NSHumanReadableCopyright': '© 2024 Alabama Auction Watcher Team',

            # Security and permissions
            'NSAppleScriptEnabled': False,
            'LSUIElement': False,  # Show in Dock
            'LSBackgroundOnly': False,

            # File associations (optional)
            'CFBundleDocumentTypes': [{
                'CFBundleTypeName': 'Alabama Auction Watcher Data',
                'CFBundleTypeExtensions': ['aaw'],
                'CFBundleTypeRole': 'Editor',
                'LSItemContentTypes': ['com.alabamaauctionwatcher.data']
            }],

            # System requirements
            'LSRequiresNativeExecution': True,
            'LSArchitecturePriority': ['x86_64', 'arm64']
        }

        plist_path = self.contents_dir / "Info.plist"
        with open(plist_path, 'wb') as f:
            plistlib.dump(info_plist, f)

        print(f"[OK] Created Info.plist: {plist_path}")

    def create_launcher_script(self):
        """Create the main launcher script"""
        print("[INFO] Creating launcher script...")

        launcher_script = f'''#!/bin/bash
# Alabama Auction Watcher - macOS Launcher
# Professional launcher script for macOS .app bundle

set -e

# Get the directory containing this script
APP_DIR="$( cd "$( dirname "${{BASH_SOURCE[0]}}" )" &> /dev/null && pwd )"
BUNDLE_DIR="$APP_DIR/.."
RESOURCES_DIR="$BUNDLE_DIR/Resources"

# Set up environment
export PYTHONPATH="$RESOURCES_DIR:$PYTHONPATH"
export AAW_BUNDLE_MODE=1
export AAW_RESOURCES_DIR="$RESOURCES_DIR"

# Log file
LOG_FILE="$HOME/Library/Logs/{self.app_name.replace(" ", "")}.log"
mkdir -p "$(dirname "$LOG_FILE")"

# Function to log messages
log_message() {{
    echo "$(date '+%Y-%m-%d %H:%M:%S') - $1" >> "$LOG_FILE"
}}

# Function to show error dialog
show_error() {{
    osascript -e "display dialog \\"$1\\" with title \\"{self.app_name}\\" buttons {{\\"OK\\"}} default button \\"OK\\" with icon stop"
}}

# Function to check dependencies
check_python() {{
    if ! command -v python3 &> /dev/null; then
        show_error "Python 3 is required but not installed. Please install Python 3.8 or later from python.org"
        log_message "ERROR: Python 3 not found"
        exit 1
    fi

    # Check Python version
    PYTHON_VERSION=$(python3 -c "import sys; print(sys.version_info[:2])")
    log_message "INFO: Found Python version: $PYTHON_VERSION"
}}

# Function to install dependencies
install_dependencies() {{
    local REQUIREMENTS_FILE="$RESOURCES_DIR/requirements.txt"
    if [[ -f "$REQUIREMENTS_FILE" ]]; then
        log_message "INFO: Installing Python dependencies..."
        python3 -m pip install --user -r "$REQUIREMENTS_FILE" >> "$LOG_FILE" 2>&1
        if [[ $? -eq 0 ]]; then
            log_message "INFO: Dependencies installed successfully"
        else
            log_message "WARNING: Some dependencies may not have installed correctly"
        fi
    fi
}}

# Function to start backend service
start_backend() {{
    local BACKEND_SCRIPT="$RESOURCES_DIR/start_backend_api.py"
    if [[ -f "$BACKEND_SCRIPT" ]]; then
        log_message "INFO: Starting backend service..."
        cd "$RESOURCES_DIR"
        python3 "$BACKEND_SCRIPT" --daemon >> "$LOG_FILE" 2>&1 &
        BACKEND_PID=$!
        log_message "INFO: Backend service started with PID: $BACKEND_PID"

        # Wait a moment for service to initialize
        sleep 2

        # Check if service is still running
        if kill -0 $BACKEND_PID 2>/dev/null; then
            log_message "INFO: Backend service confirmed running"
        else
            log_message "WARNING: Backend service may have failed to start"
        fi
    fi
}}

# Function to start frontend
start_frontend() {{
    local STREAMLIT_APP="$RESOURCES_DIR/streamlit_app/app.py"
    if [[ -f "$STREAMLIT_APP" ]]; then
        log_message "INFO: Starting frontend application..."
        cd "$RESOURCES_DIR"

        # Set Streamlit configuration
        export STREAMLIT_SERVER_HEADLESS=true
        export STREAMLIT_SERVER_PORT=8501
        export STREAMLIT_SERVER_ADDRESS=127.0.0.1
        export STREAMLIT_BROWSER_GATHER_USAGE_STATS=false

        python3 -m streamlit run "$STREAMLIT_APP" >> "$LOG_FILE" 2>&1 &
        FRONTEND_PID=$!
        log_message "INFO: Frontend started with PID: $FRONTEND_PID"

        # Wait for frontend to initialize
        sleep 3

        # Open browser
        open "http://127.0.0.1:8501"
        log_message "INFO: Opened application in default browser"
    else
        show_error "Application files not found. Please reinstall {self.app_name}."
        log_message "ERROR: Streamlit app not found at: $STREAMLIT_APP"
        exit 1
    fi
}}

# Main execution
main() {{
    log_message "INFO: Starting {self.app_name} v{self.version}"
    log_message "INFO: Bundle directory: $BUNDLE_DIR"
    log_message "INFO: Resources directory: $RESOURCES_DIR"

    # Check system requirements
    check_python

    # Install/update dependencies
    install_dependencies

    # Start services
    start_backend
    start_frontend

    log_message "INFO: {self.app_name} startup completed"
}}

# Execute main function
main "$@"
'''

        launcher_path = self.macos_dir / "launch_alabama_auction_watcher"
        with open(launcher_path, 'w', encoding='utf-8') as f:
            f.write(launcher_script)

        # Make executable
        os.chmod(launcher_path, 0o755)
        print(f"[OK] Created launcher: {launcher_path}")

    def copy_application_files(self):
        """Copy application files to Resources directory"""
        print("[INFO] Copying application files to bundle...")

        # File mappings: (source, destination)
        file_mappings = [
            # Core application
            ("streamlit_app", "streamlit_app"),
            ("frontend", "frontend"),
            ("backend_api", "backend_api"),
            ("config", "config"),
            ("scripts", "scripts"),

            # Main files
            ("requirements.txt", "requirements.txt"),
            ("start_backend_api.py", "start_backend_api.py"),

            # Database (if exists)
            ("alabama_auction_watcher.db", "alabama_auction_watcher.db")
        ]

        for source_rel, dest_rel in file_mappings:
            source_path = self.source_dir / source_rel
            dest_path = self.resources_dir / dest_rel

            if source_path.exists():
                if source_path.is_file():
                    # Copy single file
                    dest_path.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(source_path, dest_path)
                    print(f"[INFO] Copied file: {source_rel}")
                elif source_path.is_dir():
                    # Copy entire directory
                    if dest_path.exists():
                        shutil.rmtree(dest_path)
                    shutil.copytree(source_path, dest_path)
                    print(f"[INFO] Copied directory: {source_rel}")
            else:
                print(f"[WARNING] Source not found: {source_rel}")

    def copy_icon_files(self):
        """Copy icon files to Resources directory"""
        print("[INFO] Copying icon files...")

        # Copy main app icon
        main_icon_source = self.source_dir / "branding" / "generated" / "macos" / "alabama-auction-watcher.icns"
        main_icon_dest = self.resources_dir / "alabama_auction_watcher.icns"

        if main_icon_source.exists():
            shutil.copy2(main_icon_source, main_icon_dest)
            print(f"[OK] Copied main icon: {main_icon_dest.name}")
        else:
            print("[WARNING] Main icon not found - app may not display correctly")

        # Copy additional icons
        icon_source_dir = self.source_dir / "branding" / "generated" / "macos"
        if icon_source_dir.exists():
            for icon_file in icon_source_dir.glob("*.icns"):
                if icon_file.name != "alabama-auction-watcher.icns":  # Already copied
                    dest_path = self.resources_dir / icon_file.name
                    shutil.copy2(icon_file, dest_path)
                    print(f"[INFO] Copied icon: {icon_file.name}")

    def create_version_plist(self):
        """Create version.plist for detailed version information"""
        version_info = {
            'ProjectName': self.app_name,
            'ProjectVersion': self.version,
            'SourceVersion': self.build_number,
            'BuildVersion': self.build_number,
            'BuildDate': __import__('datetime').datetime.now().isoformat(),
        }

        version_plist_path = self.contents_dir / "version.plist"
        with open(version_plist_path, 'wb') as f:
            plistlib.dump(version_info, f)

        print(f"[INFO] Created version.plist: {version_plist_path}")

    def create_pkginfo(self):
        """Create PkgInfo file"""
        pkginfo_path = self.contents_dir / "PkgInfo"
        with open(pkginfo_path, 'w') as f:
            f.write("APPLAAAW")  # Package type + Signature

        print(f"[INFO] Created PkgInfo: {pkginfo_path}")

    def create_pkg_installer(self):
        """Create macOS PKG installer"""
        print("[INFO] Creating macOS PKG installer...")

        pkg_name = f"{self.app_name.replace(' ', '')}-{self.version}.pkg"
        pkg_path = self.build_dir / pkg_name

        # Create installer using pkgbuild (requires macOS)
        if sys.platform == 'darwin':
            try:
                cmd = [
                    'pkgbuild',
                    '--root', str(self.build_dir),
                    '--identifier', self.bundle_identifier,
                    '--version', self.version,
                    '--install-location', '/Applications',
                    str(pkg_path)
                ]

                result = subprocess.run(cmd, capture_output=True, text=True)
                if result.returncode == 0:
                    print(f"[OK] Created PKG installer: {pkg_path}")
                    return True
                else:
                    print(f"[ERROR] PKG creation failed: {result.stderr}")
                    return False

            except Exception as e:
                print(f"[ERROR] PKG creation error: {e}")
                return False
        else:
            print("[INFO] PKG creation skipped (not running on macOS)")
            print(f"[INFO] .app bundle ready for manual PKG creation: {self.app_bundle_dir}")
            return True

    def create_installation_script(self):
        """Create installation script for manual installation"""
        install_script = f'''#!/bin/bash
# Alabama Auction Watcher - macOS Installation Script

set -e

APP_NAME="{self.app_name}"
BUNDLE_NAME="{self.app_name}.app"
SOURCE_DIR="$(dirname "$0")"
APPLICATIONS_DIR="/Applications"
USER_APPLICATIONS_DIR="$HOME/Applications"

echo "Installing $APP_NAME for macOS..."

# Check if running as admin
if [[ $EUID -eq 0 ]]; then
    INSTALL_DIR="$APPLICATIONS_DIR"
    echo "Installing system-wide to $INSTALL_DIR"
else
    INSTALL_DIR="$USER_APPLICATIONS_DIR"
    echo "Installing for current user to $INSTALL_DIR"
    mkdir -p "$INSTALL_DIR"
fi

# Remove existing installation
if [[ -d "$INSTALL_DIR/$BUNDLE_NAME" ]]; then
    echo "Removing existing installation..."
    rm -rf "$INSTALL_DIR/$BUNDLE_NAME"
fi

# Copy app bundle
echo "Copying application bundle..."
cp -R "$SOURCE_DIR/$BUNDLE_NAME" "$INSTALL_DIR/"

# Set proper permissions
echo "Setting permissions..."
chmod +x "$INSTALL_DIR/$BUNDLE_NAME/Contents/MacOS/launch_alabama_auction_watcher"

# Register app with Launch Services
echo "Registering with Launch Services..."
/System/Library/Frameworks/CoreServices.framework/Frameworks/LaunchServices.framework/Support/lsregister -f "$INSTALL_DIR/$BUNDLE_NAME"

echo ""
echo "Installation completed successfully!"
echo "You can now launch $APP_NAME from:"
echo "- Applications folder"
echo "- Launchpad"
echo "- Spotlight search"
echo ""
echo "First launch may take a moment to install Python dependencies."
'''

        install_script_path = self.build_dir / "install.sh"
        with open(install_script_path, 'w', encoding='utf-8') as f:
            f.write(install_script)

        os.chmod(install_script_path, 0o755)
        print(f"[INFO] Created installation script: {install_script_path}")

    def create_bundle_info(self):
        """Create bundle information file"""
        bundle_info = {
            "app_name": self.app_name,
            "bundle_identifier": self.bundle_identifier,
            "version": self.version,
            "build_number": self.build_number,
            "created_date": __import__('datetime').datetime.now().isoformat(),
            "bundle_structure": {
                "app_bundle": str(self.app_bundle_dir.relative_to(self.build_dir)),
                "executable": "Contents/MacOS/launch_alabama_auction_watcher",
                "resources": "Contents/Resources",
                "info_plist": "Contents/Info.plist"
            },
            "features": [
                "Native macOS .app bundle",
                "Launch Services integration",
                "URL scheme handler (aaw://)",
                "Automatic dependency management",
                "Professional installer"
            ]
        }

        info_file = self.build_dir / "bundle_info.json"
        with open(info_file, 'w', encoding='utf-8') as f:
            json.dump(bundle_info, f, indent=2)

        print(f"[INFO] Created bundle info: {info_file}")

    def build_app_bundle(self) -> bool:
        """Complete app bundle build process"""
        print("[TARGET] macOS .app Bundle Creator - Alabama Auction Watcher")
        print("=" * 60)

        try:
            # Create build directory
            self.build_dir.mkdir(exist_ok=True)
            print(f"[INFO] Build directory: {self.build_dir}")

            # Create bundle structure
            self.create_bundle_structure()

            # Create configuration files
            self.create_info_plist()
            self.create_version_plist()
            self.create_pkginfo()

            # Create launcher
            self.create_launcher_script()

            # Copy application files
            self.copy_application_files()
            self.copy_icon_files()

            # Create installation helpers
            self.create_installation_script()
            self.create_bundle_info()

            # Create PKG installer
            self.create_pkg_installer()

            print("\n[SUCCESS] macOS .app bundle created successfully!")
            print(f"[INFO] App bundle: {self.app_bundle_dir}")
            print(f"[INFO] Installation script: {self.build_dir / 'install.sh'}")

            return True

        except Exception as e:
            print(f"[ERROR] Bundle creation failed: {e}")
            return False

def main():
    """Main execution function"""
    creator = MacOSAppBundleCreator()

    if creator.build_app_bundle():
        print("\n[OK] macOS app bundle build completed!")
        sys.exit(0)
    else:
        print("\n[ERROR] macOS app bundle build failed!")
        sys.exit(1)

if __name__ == '__main__':
    main()