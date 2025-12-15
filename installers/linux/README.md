# Alabama Auction Watcher - Linux Packages

## Professional .deb and .rpm Packages for Linux Distributions

This directory contains the Linux package creation system for Alabama Auction Watcher, providing native package manager integration across major Linux distributions.

## Quick Start

### Build Linux Packages
```bash
# Navigate to Linux installer directory
cd /path/to/auction/installers/linux

# Create .deb and .rpm packages
python3 create_linux_packages.py
```

### Install Packages

#### Debian/Ubuntu (.deb)
```bash
# Install package
sudo dpkg -i build/alabama-auction-watcher_1.0.0-1_all.deb

# Fix dependencies if needed
sudo apt-get install -f

# Alternative: Use apt for dependency resolution
sudo apt install ./build/alabama-auction-watcher_1.0.0-1_all.deb
```

#### RedHat/CentOS/Fedora (.rpm)
```bash
# Build RPM (on RPM-based system)
rpmbuild -ba build/rpm/SPECS/alabama-auction-watcher.spec

# Install RPM
sudo rpm -ivh build/rpm/RPMS/noarch/alabama-auction-watcher-1.0.0-1.noarch.rpm

# Or use package manager
sudo yum install build/rpm/RPMS/noarch/alabama-auction-watcher-1.0.0-1.noarch.rpm
sudo dnf install build/rpm/RPMS/noarch/alabama-auction-watcher-1.0.0-1.noarch.rpm
```

## Package Features

### Distribution Support
- **Debian/Ubuntu**: Native .deb packages with proper dependencies
- **RedHat/CentOS/Fedora**: RPM packages with spec files
- **Universal**: Architecture-independent Python application

### System Integration
- **Desktop Entry**: Application menu integration
- **Icon Themes**: Multi-resolution icons for all desktop environments
- **MIME Types**: File association and URL scheme handling
- **XDG Compliance**: Follows freedesktop.org standards

### Package Management
- **Dependencies**: Automatic Python 3.8+ and pip requirements
- **Post-install**: Desktop database and icon cache updates
- **Removal**: Clean uninstallation with optional data preservation
- **Upgrades**: In-place upgrade support

## Installation Structure

### File System Layout (FHS Compliant)
```
/opt/alabama-auction-watcher/          # Main application
├── streamlit_app/                     # Frontend application
├── backend_api/                       # Backend services
├── config/                            # Configuration files
├── scripts/                           # Utility scripts
├── requirements.txt                   # Python dependencies
└── start_backend_api.py               # Backend launcher

/usr/local/bin/
└── alabama-auction-watcher            # Main launcher script

/usr/share/applications/
└── alabama-auction-watcher.desktop    # Desktop integration

/usr/share/icons/hicolor/              # Application icons
├── 16x16/apps/alabama-auction-watcher.png
├── 32x32/apps/alabama-auction-watcher.png
├── 48x48/apps/alabama-auction-watcher.png
├── 64x64/apps/alabama-auction-watcher.png
├── 128x128/apps/alabama-auction-watcher.png
├── 256x256/apps/alabama-auction-watcher.png
└── 512x512/apps/alabama-auction-watcher.png

/usr/share/doc/alabama-auction-watcher/
├── README                             # Installation guide
└── changelog                          # Package changelog
```

### User Data Locations
```
~/.local/share/alabama-auction-watcher/
└── logs/                              # Application logs

~/.config/alabama-auction-watcher/     # User configuration (future)
```

## System Requirements

### Minimum Requirements
- **Distribution**: Any modern Linux distribution
- **Kernel**: 3.10+ (CentOS 7) or 4.4+ (Ubuntu 16.04)
- **Architecture**: x86_64 or aarch64
- **Python**: 3.8 or later
- **RAM**: 2GB minimum, 4GB recommended
- **Storage**: 500MB for application, 2GB for data

### Dependencies
#### Required
- `python3` (>= 3.8)
- `python3-pip`
- `python3-venv`

#### Recommended
- `python3-tk` (for certain GUI components)
- `xdg-utils` (for proper desktop integration)

#### Suggested
- Web browser: `chromium-browser`, `firefox`, or `google-chrome-stable`

## Installation Methods

### Method 1: Package Manager (Recommended)
```bash
# Debian/Ubuntu
sudo apt install ./alabama-auction-watcher_1.0.0-1_all.deb

# RedHat/CentOS (with EPEL)
sudo yum install alabama-auction-watcher-1.0.0-1.noarch.rpm

# Fedora
sudo dnf install alabama-auction-watcher-1.0.0-1.noarch.rpm
```

### Method 2: Direct Package Installation
```bash
# Debian/Ubuntu
sudo dpkg -i alabama-auction-watcher_1.0.0-1_all.deb
sudo apt-get install -f  # Fix dependencies

# RedHat/CentOS/Fedora
sudo rpm -ivh alabama-auction-watcher-1.0.0-1.noarch.rpm
```

### Method 3: Repository Installation (Future)
```bash
# Add repository (future feature)
sudo apt-add-repository ppa:alabama-auction-watcher/stable
sudo apt update
sudo apt install alabama-auction-watcher
```

## Usage

### Launching the Application
```bash
# Command line
alabama-auction-watcher

# Desktop launcher
# Search for "Alabama Auction Watcher" in application menu

# Direct execution
/opt/alabama-auction-watcher/start_backend_api.py
```

### Application Behavior
1. **Dependency Check**: Verifies Python 3.8+ and pip
2. **Package Installation**: Auto-installs Python dependencies
3. **Service Startup**: Launches backend API service
4. **Frontend Launch**: Starts Streamlit web interface
5. **Browser Opening**: Opens application in default browser

### Configuration
- **Application**: `/opt/alabama-auction-watcher/config/`
- **User Settings**: `~/.config/alabama-auction-watcher/` (future)
- **Logs**: `~/.local/share/alabama-auction-watcher/logs/`

## Troubleshooting

### Common Issues

#### Package Installation Fails
```bash
# Check dependencies
apt-cache policy python3 python3-pip

# Fix broken packages
sudo apt-get install -f

# Force installation (if needed)
sudo dpkg -i --force-depends package.deb
```

#### Python Dependencies Fail to Install
```bash
# Update pip
python3 -m pip install --upgrade pip

# Install dependencies manually
python3 -m pip install --user streamlit pandas numpy

# Check Python version
python3 --version  # Should be 3.8+
```

#### Application Doesn't Start
```bash
# Check logs
tail -f ~/.local/share/alabama-auction-watcher/logs/application.log

# Test Python environment
python3 -c "import streamlit; print('Streamlit OK')"

# Check running processes
ps aux | grep -E "(streamlit|alabama-auction)"
```

#### Desktop Integration Issues
```bash
# Update desktop database
sudo update-desktop-database

# Update icon cache
sudo gtk-update-icon-cache /usr/share/icons/hicolor

# Refresh application menu
killall nautilus && nautilus &  # GNOME
kbuildsycoca5  # KDE
```

### Advanced Troubleshooting

#### Debug Mode
```bash
# Enable debug logging
export AAW_DEBUG=1
alabama-auction-watcher
```

#### Manual Service Management
```bash
# Check service status
systemctl --user status alabama-auction-watcher  # If systemd service exists

# Manual backend start
cd /opt/alabama-auction-watcher
python3 start_backend_api.py --debug

# Manual frontend start
cd /opt/alabama-auction-watcher
python3 -m streamlit run streamlit_app/app.py --server.port=8501
```

#### Network Issues
```bash
# Check port availability
netstat -tulpn | grep :8501
netstat -tulpn | grep :8000

# Test connectivity
curl http://127.0.0.1:8501
curl http://127.0.0.1:8000/health
```

## Package Management

### Upgrading
```bash
# Download new package
wget https://releases.example.com/alabama-auction-watcher_1.1.0-1_all.deb

# Upgrade (preserves configuration and data)
sudo apt install ./alabama-auction-watcher_1.1.0-1_all.deb
```

### Removing
```bash
# Remove package (keeps configuration)
sudo apt remove alabama-auction-watcher

# Purge package (removes everything)
sudo apt purge alabama-auction-watcher

# Manual cleanup (if needed)
sudo rm -rf /opt/alabama-auction-watcher
rm -rf ~/.local/share/alabama-auction-watcher
```

### Verification
```bash
# Check package status
dpkg -l | grep alabama-auction-watcher
rpm -qa | grep alabama-auction-watcher

# Verify files
dpkg -L alabama-auction-watcher
rpm -ql alabama-auction-watcher

# Check integrity
dpkg -V alabama-auction-watcher
rpm -V alabama-auction-watcher
```

## Development and Customization

### Building Custom Packages
```python
# Edit create_linux_packages.py
class LinuxPackageCreator:
    def __init__(self):
        self.app_name = "alabama-auction-watcher"  # Package name
        self.display_name = "Alabama Auction Watcher"  # Display name
        self.version = "1.0.0"  # Version number
        self.maintainer = "Your Name <email@example.com>"  # Maintainer
```

### Custom Dependencies
```python
# In create_deb_package method, edit control file
control_content = f"""Package: {self.app_name}
Depends: python3 (>= 3.8), python3-pip, your-custom-package
Recommends: additional-package
"""
```

### Desktop Integration Customization
```python
# Edit create_desktop_file method
desktop_content = f"""[Desktop Entry]
Categories=Office;Finance;Development;YourCategory;
Keywords=auction;real estate;your-keywords;
"""
```

## Distribution-Specific Notes

### Debian/Ubuntu
- Uses `dpkg-deb` for package creation
- Follows Debian Policy Manual
- Supports automatic dependency resolution with `apt`

### RedHat/CentOS/Fedora
- Uses RPM spec files for package definition
- Requires `rpmbuild` for actual package creation
- Supports both YUM and DNF package managers

### Arch Linux (Future)
- PKGBUILD file creation planned
- AUR (Arch User Repository) submission considered

### openSUSE (Future)
- RPM-based but may need openSUSE-specific adjustments
- zypper package manager support

## Enterprise Deployment

### Mass Installation
```bash
# Ansible playbook example
- name: Install Alabama Auction Watcher
  apt:
    deb: "/path/to/alabama-auction-watcher_1.0.0-1_all.deb"
  become: yes
```

### Configuration Management
```bash
# Puppet manifest example
package { 'alabama-auction-watcher':
  ensure   => installed,
  provider => dpkg,
  source   => '/path/to/package.deb',
}
```

### Monitoring
```bash
# Check application health
curl -f http://localhost:8501/healthz || echo "Application down"

# Monitor resource usage
systemctl --user status alabama-auction-watcher
journalctl --user -u alabama-auction-watcher -f
```

---

**Supported Distributions**:
- Debian 10+, Ubuntu 18.04+
- CentOS 7+, RHEL 7+, Fedora 30+
- openSUSE Leap 15+

**Package Format**: .deb (Debian), .rpm (RedHat)
**Architecture**: all (architecture independent)
**Standards**: FHS, XDG, Debian Policy, RPM Guidelines