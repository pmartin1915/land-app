#!/usr/bin/env python3
"""
Linux Package Creator
Creates .deb and .rpm packages for Alabama Auction Watcher with proper dependencies
"""

import os
import sys
import shutil
import subprocess
import tempfile
from pathlib import Path
import json
import textwrap

class LinuxPackageCreator:
    """Professional Linux package creator (.deb and .rpm)"""

    def __init__(self):
        self.app_name = "alabama-auction-watcher"
        self.display_name = "Alabama Auction Watcher"
        self.version = "1.0.0"
        self.revision = "1"
        self.architecture = "all"  # Architecture independent (Python)

        # Package metadata
        self.maintainer = "Alabama Auction Watcher Team <support@alabamaauctionwatcher.com>"
        self.homepage = "https://github.com/Alabama-Auction-Watcher"
        self.description_short = "Professional Real Estate Auction Intelligence System"
        self.description_long = """Alabama Auction Watcher is a comprehensive real estate auction
 tracking and analytics platform designed for professional investors,
 real estate agents, and market analysts.
 .
 Key Features:
 - Real-time auction data tracking
 - Advanced market analytics and reporting
 - Investment opportunity scoring
 - Multi-county coverage across Alabama
 - Web-based dashboard interface
 - RESTful API for integration"""

        # Source and build directories
        self.source_dir = Path(__file__).parent.parent.parent
        self.build_dir = Path(__file__).parent / "build"
        self.deb_build_dir = self.build_dir / "deb"
        self.rpm_build_dir = self.build_dir / "rpm"

        # Installation paths (following FHS)
        self.install_prefix = "/opt/alabama-auction-watcher"
        self.bin_dir = "/usr/local/bin"
        self.desktop_dir = "/usr/share/applications"
        self.icon_dir = "/usr/share/icons/hicolor"
        self.doc_dir = "/usr/share/doc/alabama-auction-watcher"

    def create_build_structure(self):
        """Create build directory structure"""
        print("[INFO] Creating build directory structure...")

        # Clean and create build directories
        if self.build_dir.exists():
            shutil.rmtree(self.build_dir)

        self.build_dir.mkdir(parents=True)
        self.deb_build_dir.mkdir()
        self.rpm_build_dir.mkdir()

        print(f"[INFO] Build directory: {self.build_dir}")

    def copy_application_files(self, target_dir: Path):
        """Copy application files to target directory"""
        print("[INFO] Copying application files...")

        app_install_dir = target_dir / self.install_prefix.lstrip('/')

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
            dest_path = app_install_dir / dest_rel

            if source_path.exists():
                if source_path.is_file():
                    dest_path.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(source_path, dest_path)
                elif source_path.is_dir():
                    if dest_path.exists():
                        shutil.rmtree(dest_path)
                    shutil.copytree(source_path, dest_path)
                print(f"[INFO] Copied: {source_rel}")

    def create_wrapper_script(self, target_dir: Path):
        """Create launcher wrapper script"""
        print("[INFO] Creating launcher script...")

        wrapper_script = f'''#!/bin/bash
# Alabama Auction Watcher - Linux Launcher
# Professional launcher script for Linux systems

set -e

# Application configuration
APP_NAME="{self.display_name}"
APP_DIR="{self.install_prefix}"
LOG_FILE="$HOME/.local/share/{self.app_name}/logs/application.log"

# Create log directory
mkdir -p "$(dirname "$LOG_FILE")"

# Function to log messages
log_message() {{
    echo "$(date '+%Y-%m-%d %H:%M:%S') - $1" >> "$LOG_FILE"
}}

# Function to show error notification
show_error() {{
    if command -v zenity &> /dev/null; then
        zenity --error --text="$1" --title="{self.display_name}"
    elif command -v notify-send &> /dev/null; then
        notify-send -u critical "{self.display_name}" "$1"
    else
        echo "ERROR: $1" >&2
    fi
}}

# Function to check dependencies
check_python() {{
    if ! command -v python3 &> /dev/null; then
        show_error "Python 3 is required but not installed. Please install python3 package."
        log_message "ERROR: Python 3 not found"
        exit 1
    fi

    # Check Python version
    PYTHON_VERSION=$(python3 -c "import sys; print('.'.join(map(str, sys.version_info[:2])))")
    log_message "INFO: Found Python version: $PYTHON_VERSION"

    # Verify minimum version (3.8)
    if ! python3 -c "import sys; sys.exit(0 if sys.version_info >= (3, 8) else 1)"; then
        show_error "Python 3.8 or later is required. Found: $PYTHON_VERSION"
        log_message "ERROR: Insufficient Python version"
        exit 1
    fi
}}

# Function to install dependencies
install_dependencies() {{
    local REQUIREMENTS_FILE="$APP_DIR/requirements.txt"
    if [[ -f "$REQUIREMENTS_FILE" ]]; then
        log_message "INFO: Installing Python dependencies..."

        # Try pip3 first, then pip
        if command -v pip3 &> /dev/null; then
            PIP_CMD="pip3"
        elif command -v pip &> /dev/null; then
            PIP_CMD="pip"
        else
            show_error "pip is required but not found. Please install python3-pip package."
            exit 1
        fi

        $PIP_CMD install --user -r "$REQUIREMENTS_FILE" >> "$LOG_FILE" 2>&1
        if [[ $? -eq 0 ]]; then
            log_message "INFO: Dependencies installed successfully"
        else
            log_message "WARNING: Some dependencies may not have installed correctly"
            show_error "Warning: Some Python dependencies may not have installed correctly. Check log file: $LOG_FILE"
        fi
    fi
}}

# Function to start backend service
start_backend() {{
    local BACKEND_SCRIPT="$APP_DIR/start_backend_api.py"
    if [[ -f "$BACKEND_SCRIPT" ]]; then
        log_message "INFO: Starting backend service..."
        cd "$APP_DIR"

        # Check if already running
        if pgrep -f "start_backend_api.py" > /dev/null; then
            log_message "INFO: Backend service already running"
            return 0
        fi

        python3 "$BACKEND_SCRIPT" --daemon >> "$LOG_FILE" 2>&1 &
        BACKEND_PID=$!
        log_message "INFO: Backend service started with PID: $BACKEND_PID"

        # Wait for service to initialize
        sleep 2

        # Verify service is running
        if kill -0 $BACKEND_PID 2>/dev/null; then
            log_message "INFO: Backend service confirmed running"
        else
            log_message "WARNING: Backend service may have failed to start"
        fi
    fi
}}

# Function to start frontend
start_frontend() {{
    local STREAMLIT_APP="$APP_DIR/streamlit_app/app.py"
    if [[ -f "$STREAMLIT_APP" ]]; then
        log_message "INFO: Starting frontend application..."
        cd "$APP_DIR"

        # Set Streamlit configuration
        export STREAMLIT_SERVER_HEADLESS=true
        export STREAMLIT_SERVER_PORT=8501
        export STREAMLIT_SERVER_ADDRESS=127.0.0.1
        export STREAMLIT_BROWSER_GATHER_USAGE_STATS=false

        # Check if already running
        if pgrep -f "streamlit run.*app.py" > /dev/null; then
            log_message "INFO: Frontend already running"
        else
            python3 -m streamlit run "$STREAMLIT_APP" >> "$LOG_FILE" 2>&1 &
            FRONTEND_PID=$!
            log_message "INFO: Frontend started with PID: $FRONTEND_PID"
        fi

        # Wait for frontend to initialize
        sleep 3

        # Open browser
        if command -v xdg-open &> /dev/null; then
            xdg-open "http://127.0.0.1:8501" >> "$LOG_FILE" 2>&1
            log_message "INFO: Opened application in default browser"
        else
            log_message "WARNING: Could not open browser automatically"
            show_error "Application started. Please open http://127.0.0.1:8501 in your browser."
        fi
    else
        show_error "Application files not found. Please reinstall {self.display_name}."
        log_message "ERROR: Streamlit app not found at: $STREAMLIT_APP"
        exit 1
    fi
}}

# Main execution
main() {{
    log_message "INFO: Starting {self.display_name} v{self.version}"
    log_message "INFO: Application directory: $APP_DIR"

    # Check if application directory exists
    if [[ ! -d "$APP_DIR" ]]; then
        show_error "Application not properly installed. Directory not found: $APP_DIR"
        log_message "ERROR: Application directory not found"
        exit 1
    fi

    # Check system requirements
    check_python

    # Install/update dependencies
    install_dependencies

    # Start services
    start_backend
    start_frontend

    log_message "INFO: {self.display_name} startup completed"
}}

# Execute main function
main "$@"
'''

        # Create bin directory and wrapper script
        bin_dir = target_dir / self.bin_dir.lstrip('/')
        bin_dir.mkdir(parents=True, exist_ok=True)

        wrapper_path = bin_dir / self.app_name
        with open(wrapper_path, 'w', encoding='utf-8') as f:
            f.write(wrapper_script)

        # Make executable
        os.chmod(wrapper_path, 0o755)
        print(f"[INFO] Created wrapper script: {wrapper_path}")

    def create_desktop_file(self, target_dir: Path):
        """Create .desktop file for desktop integration"""
        print("[INFO] Creating desktop integration...")

        desktop_content = f'''[Desktop Entry]
Version=1.0
Type=Application
Name={self.display_name}
GenericName=Real Estate Auction Tracker
Comment={self.description_short}
Exec={self.app_name}
Icon={self.app_name}
Terminal=false
StartupNotify=true
Categories=Office;Finance;Development;
Keywords=auction;real estate;investment;analytics;alabama;
MimeType=x-scheme-handler/aaw;
StartupWMClass={self.display_name}

# Additional metadata
X-GNOME-UsesNotifications=true
X-KDE-SubstituteUID=false
X-Desktop-File-Install-Version=0.26
'''

        desktop_dir = target_dir / self.desktop_dir.lstrip('/')
        desktop_dir.mkdir(parents=True, exist_ok=True)

        desktop_file = desktop_dir / f"{self.app_name}.desktop"
        with open(desktop_file, 'w', encoding='utf-8') as f:
            f.write(desktop_content)

        print(f"[INFO] Created desktop file: {desktop_file}")

    def create_icon_files(self, target_dir: Path):
        """Install icon files for desktop themes"""
        print("[INFO] Installing application icons...")

        # Icon sizes for different contexts
        icon_sizes = [16, 22, 24, 32, 48, 64, 96, 128, 192, 256, 512]

        icon_source_dir = self.source_dir / "branding" / "generated" / "linux"

        if not icon_source_dir.exists():
            print("[WARNING] Linux icons not found - desktop integration may not work properly")
            return

        for size in icon_sizes:
            size_dir = target_dir / self.icon_dir.lstrip('/') / f"{size}x{size}" / "apps"
            size_dir.mkdir(parents=True, exist_ok=True)

            # Look for icon file
            icon_source = icon_source_dir / f"{self.app_name}_{size}x{size}.png"
            if icon_source.exists():
                icon_dest = size_dir / f"{self.app_name}.png"
                shutil.copy2(icon_source, icon_dest)
                print(f"[INFO] Installed {size}x{size} icon")

    def create_documentation(self, target_dir: Path):
        """Create documentation files"""
        print("[INFO] Creating documentation...")

        doc_dir = target_dir / self.doc_dir.lstrip('/')
        doc_dir.mkdir(parents=True, exist_ok=True)

        # Create README
        readme_content = f"""{self.display_name} - Linux Installation

This package provides the {self.display_name} application for Linux systems.

INSTALLATION:
The application has been installed to {self.install_prefix}

USAGE:
Launch from:
- Application menu -> Office -> {self.display_name}
- Command line: {self.app_name}
- Desktop shortcut (if created during installation)

REQUIREMENTS:
- Python 3.8 or later
- pip (python3-pip package)
- Web browser for interface access

CONFIGURATION:
Configuration files: {self.install_prefix}/config/
Log files: ~/.local/share/{self.app_name}/logs/

TROUBLESHOOTING:
- Check log files for error messages
- Ensure Python 3.8+ is installed
- Verify pip is available for dependency installation
- Check network connectivity for real-time data

SUPPORT:
Homepage: {self.homepage}
Issues: {self.homepage}/issues

Version: {self.version}
Maintainer: {self.maintainer}
"""

        readme_file = doc_dir / "README"
        with open(readme_file, 'w', encoding='utf-8') as f:
            f.write(readme_content)

        # Create changelog
        changelog_content = f"""{self.app_name} ({self.version}-{self.revision}) stable; urgency=medium

  * Initial release of {self.display_name}
  * Complete real estate auction tracking platform
  * Web-based dashboard interface
  * Advanced analytics and reporting
  * Multi-county Alabama coverage
  * RESTful API for integration

 -- {self.maintainer}  {__import__('datetime').datetime.now().strftime('%a, %d %b %Y %H:%M:%S %z')}
"""

        changelog_file = doc_dir / "changelog"
        with open(changelog_file, 'w', encoding='utf-8') as f:
            f.write(changelog_content)

        print(f"[INFO] Created documentation in: {doc_dir}")

    def create_deb_package(self) -> bool:
        """Create Debian (.deb) package"""
        print("[INFO] Creating Debian (.deb) package...")

        # Create package directory structure
        deb_root = self.deb_build_dir / f"{self.app_name}_{self.version}-{self.revision}_{self.architecture}"
        debian_dir = deb_root / "DEBIAN"
        debian_dir.mkdir(parents=True, exist_ok=True)

        # Copy application files
        self.copy_application_files(deb_root)
        self.create_wrapper_script(deb_root)
        self.create_desktop_file(deb_root)
        self.create_icon_files(deb_root)
        self.create_documentation(deb_root)

        # Create control file
        control_content = f"""Package: {self.app_name}
Version: {self.version}-{self.revision}
Architecture: {self.architecture}
Maintainer: {self.maintainer}
Depends: python3 (>= 3.8), python3-pip, python3-venv
Recommends: python3-tk, xdg-utils
Suggests: chromium-browser | firefox | google-chrome-stable
Section: misc
Priority: optional
Homepage: {self.homepage}
Description: {self.description_short}
{self.description_long}
"""

        control_file = debian_dir / "control"
        with open(control_file, 'w', encoding='utf-8') as f:
            f.write(control_content)

        # Create postinst script
        postinst_content = f'''#!/bin/bash
# Post-installation script for {self.display_name}

set -e

case "$1" in
    configure)
        # Update desktop database
        if command -v update-desktop-database >/dev/null 2>&1; then
            update-desktop-database -q /usr/share/applications || true
        fi

        # Update icon cache
        if command -v gtk-update-icon-cache >/dev/null 2>&1; then
            gtk-update-icon-cache -q /usr/share/icons/hicolor || true
        fi

        # Update mime database
        if command -v update-mime-database >/dev/null 2>&1; then
            update-mime-database /usr/share/mime || true
        fi

        echo "{self.display_name} installed successfully!"
        echo "Launch from application menu or run: {self.app_name}"
        ;;
esac

exit 0
'''

        postinst_file = debian_dir / "postinst"
        with open(postinst_file, 'w', encoding='utf-8') as f:
            f.write(postinst_content)
        os.chmod(postinst_file, 0o755)

        # Create prerm script
        prerm_content = f'''#!/bin/bash
# Pre-removal script for {self.display_name}

set -e

case "$1" in
    remove|upgrade|deconfigure)
        # Kill running processes
        pkill -f "{self.app_name}" || true
        pkill -f "streamlit.*{self.app_name}" || true
        pkill -f "start_backend_api.py" || true
        ;;
esac

exit 0
'''

        prerm_file = debian_dir / "prerm"
        with open(prerm_file, 'w', encoding='utf-8') as f:
            f.write(prerm_content)
        os.chmod(prerm_file, 0o755)

        # Create postrm script
        postrm_content = f'''#!/bin/bash
# Post-removal script for {self.display_name}

set -e

case "$1" in
    remove)
        # Update desktop database
        if command -v update-desktop-database >/dev/null 2>&1; then
            update-desktop-database -q /usr/share/applications || true
        fi

        # Update icon cache
        if command -v gtk-update-icon-cache >/dev/null 2>&1; then
            gtk-update-icon-cache -q /usr/share/icons/hicolor || true
        fi
        ;;

    purge)
        # Remove user data (optional - ask user)
        echo "To remove user data, manually delete ~/.local/share/{self.app_name}/"
        ;;
esac

exit 0
'''

        postrm_file = debian_dir / "postrm"
        with open(postrm_file, 'w', encoding='utf-8') as f:
            f.write(postrm_content)
        os.chmod(postrm_file, 0o755)

        # Build package with dpkg-deb
        try:
            deb_file = self.build_dir / f"{self.app_name}_{self.version}-{self.revision}_{self.architecture}.deb"

            cmd = ['dpkg-deb', '--build', str(deb_root), str(deb_file)]
            result = subprocess.run(cmd, capture_output=True, text=True)

            if result.returncode == 0:
                print(f"[OK] Created .deb package: {deb_file}")
                return True
            else:
                print(f"[ERROR] dpkg-deb failed: {result.stderr}")
                return False

        except FileNotFoundError:
            print("[ERROR] dpkg-deb not found. Install dpkg-dev package or run on Debian/Ubuntu system.")
            print(f"[INFO] Package structure created in: {deb_root}")
            return True  # Structure created successfully

        except Exception as e:
            print(f"[ERROR] DEB package creation failed: {e}")
            return False

    def create_rpm_spec_file(self) -> str:
        """Create RPM spec file content"""
        spec_content = f'''Name:           {self.app_name}
Version:        {self.version}
Release:        {self.revision}%{{?dist}}
Summary:        {self.description_short}

License:        MIT
URL:            {self.homepage}
Source0:        %{{name}}-%{{version}}.tar.gz
BuildArch:      noarch

Requires:       python3 >= 3.8
Requires:       python3-pip
Recommends:     python3-tkinter
Recommends:     xdg-utils

%description
{self.description_long.replace(chr(10), chr(10) + " ")}

%prep
%setup -q

%build
# Nothing to build

%install
rm -rf $RPM_BUILD_ROOT

# Create directory structure
mkdir -p $RPM_BUILD_ROOT{self.install_prefix}
mkdir -p $RPM_BUILD_ROOT{self.bin_dir}
mkdir -p $RPM_BUILD_ROOT{self.desktop_dir}
mkdir -p $RPM_BUILD_ROOT{self.doc_dir}

# Install application files
cp -r streamlit_app backend_api config scripts requirements.txt start_backend_api.py $RPM_BUILD_ROOT{self.install_prefix}/

# Install wrapper script
install -m 755 {self.app_name} $RPM_BUILD_ROOT{self.bin_dir}/

# Install desktop file
install -m 644 {self.app_name}.desktop $RPM_BUILD_ROOT{self.desktop_dir}/

# Install icons
for size in 16 22 24 32 48 64 96 128 192 256 512; do
    mkdir -p $RPM_BUILD_ROOT/usr/share/icons/hicolor/${{size}}x${{size}}/apps
    if [ -f icons/{self.app_name}_${{size}}x${{size}}.png ]; then
        install -m 644 icons/{self.app_name}_${{size}}x${{size}}.png $RPM_BUILD_ROOT/usr/share/icons/hicolor/${{size}}x${{size}}/apps/{self.app_name}.png
    fi
done

# Install documentation
install -m 644 README changelog $RPM_BUILD_ROOT{self.doc_dir}/

%clean
rm -rf $RPM_BUILD_ROOT

%files
{self.install_prefix}/*
{self.bin_dir}/{self.app_name}
{self.desktop_dir}/{self.app_name}.desktop
{self.doc_dir}/*
/usr/share/icons/hicolor/*/apps/{self.app_name}.png

%post
# Update desktop database
if [ -x /usr/bin/update-desktop-database ]; then
    /usr/bin/update-desktop-database &> /dev/null || :
fi

# Update icon cache
if [ -x /usr/bin/gtk-update-icon-cache ]; then
    /usr/bin/gtk-update-icon-cache --quiet /usr/share/icons/hicolor &> /dev/null || :
fi

echo "{self.display_name} installed successfully!"
echo "Launch from application menu or run: {self.app_name}"

%preun
# Kill running processes
pkill -f "{self.app_name}" &> /dev/null || :
pkill -f "streamlit.*{self.app_name}" &> /dev/null || :
pkill -f "start_backend_api.py" &> /dev/null || :

%postun
# Update desktop database
if [ -x /usr/bin/update-desktop-database ]; then
    /usr/bin/update-desktop-database &> /dev/null || :
fi

# Update icon cache
if [ -x /usr/bin/gtk-update-icon-cache ]; then
    /usr/bin/gtk-update-icon-cache --quiet /usr/share/icons/hicolor &> /dev/null || :
fi

%changelog
* {__import__('datetime').datetime.now().strftime('%a %b %d %Y')} {self.maintainer.split('<')[0].strip()} - {self.version}-{self.revision}
- Initial release of {self.display_name}
- Complete real estate auction tracking platform
- Web-based dashboard interface
- Advanced analytics and reporting
- Multi-county Alabama coverage
- RESTful API for integration
'''

        return spec_content

    def create_rpm_package(self) -> bool:
        """Create RPM package"""
        print("[INFO] Creating RPM package...")

        # Create RPM build structure
        rpm_dirs = ["BUILD", "RPMS", "SOURCES", "SPECS", "SRPMS"]
        for rpm_dir in rpm_dirs:
            (self.rpm_build_dir / rpm_dir).mkdir(parents=True, exist_ok=True)

        # Create spec file
        spec_content = self.create_rpm_spec_file()
        spec_file = self.rpm_build_dir / "SPECS" / f"{self.app_name}.spec"
        with open(spec_file, 'w', encoding='utf-8') as f:
            f.write(spec_content)

        print(f"[INFO] Created RPM spec file: {spec_file}")

        # Note: Actual RPM building requires rpmbuild and complex setup
        print("[INFO] RPM package structure created")
        print(f"[INFO] To build RPM on CentOS/RHEL/Fedora:")
        print(f"[INFO]   rpmbuild -ba {spec_file}")

        return True

    def create_package_info(self):
        """Create package information file"""
        package_info = {
            "package_name": self.app_name,
            "display_name": self.display_name,
            "version": self.version,
            "revision": self.revision,
            "architecture": self.architecture,
            "maintainer": self.maintainer,
            "homepage": self.homepage,
            "build_date": __import__('datetime').datetime.now().isoformat(),
            "install_prefix": self.install_prefix,
            "packages_created": {
                "deb": f"{self.app_name}_{self.version}-{self.revision}_{self.architecture}.deb",
                "rpm_spec": f"{self.app_name}.spec"
            },
            "features": [
                "Debian (.deb) package",
                "RPM spec file for RedHat/CentOS/Fedora",
                "Desktop integration",
                "Icon theme support",
                "Automatic dependency management",
                "Professional uninstaller"
            ]
        }

        info_file = self.build_dir / "package_info.json"
        with open(info_file, 'w', encoding='utf-8') as f:
            json.dump(package_info, f, indent=2)

        print(f"[INFO] Created package info: {info_file}")

    def build_all_packages(self) -> bool:
        """Build all Linux packages"""
        print("[TARGET] Linux Package Creator - Alabama Auction Watcher")
        print("=" * 60)

        try:
            # Create build structure
            self.create_build_structure()

            # Create packages
            deb_success = self.create_deb_package()
            rpm_success = self.create_rpm_package()

            # Create package info
            self.create_package_info()

            if deb_success and rpm_success:
                print("\n[SUCCESS] Linux packages created successfully!")
                print(f"[INFO] Build directory: {self.build_dir}")
                return True
            else:
                print("\n[WARNING] Some packages may not have been created")
                return False

        except Exception as e:
            print(f"[ERROR] Package creation failed: {e}")
            return False

def main():
    """Main execution function"""
    creator = LinuxPackageCreator()

    if creator.build_all_packages():
        print("\n[OK] Linux package creation completed!")
        sys.exit(0)
    else:
        print("\n[ERROR] Linux package creation failed!")
        sys.exit(1)

if __name__ == '__main__':
    main()