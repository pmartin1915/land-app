# Alabama Auction Watcher - Windows Installer

## Enterprise Desktop Integration for Windows

This directory contains the Windows desktop integration system for Alabama Auction Watcher, providing professional installation and desktop integration capabilities.

## Installation Methods

### Method 1: Self-Contained Python Installer (Recommended)
- **File**: `create_windows_installer.py`
- **Requirements**: Python 3.8+
- **Features**: Complete desktop integration without external dependencies

### Method 2: Professional MSI Installer
- **File**: `build_msi.py` + `AlabamaAuctionWatcher.wxs`
- **Requirements**: WiX Toolset 3.11+
- **Features**: Enterprise-grade MSI package with advanced features

## Quick Installation

### For End Users
```cmd
# Navigate to the installer directory
cd C:\auction\installers\windows

# Run the Python installer (Administrator recommended)
python create_windows_installer.py
```

### For System Administrators
```cmd
# Build MSI package (requires WiX Toolset)
python build_msi.py

# Install MSI silently across enterprise
msiexec /i "build\AlabamaAuctionWatcher-1.0.0.0.msi" /quiet
```

## Installation Features

### Desktop Integration
- **Desktop Shortcut**: Quick access from desktop
- **Start Menu Integration**: Professional Start Menu folder with multiple shortcuts
- **URL Protocol**: Handle `aaw://` links for direct application launching
- **Registry Integration**: Proper Windows registry entries for system integration

### Shortcuts Created
1. **Alabama Auction Watcher** - Main application launcher
2. **Backend Service Manager** - Backend service control
3. **Uninstall Alabama Auction Watcher** - Clean removal tool

### Registry Entries
- Application registration in `HKCU\Software\AlabamaAuctionWatcher`
- URL protocol handler for `aaw://` links
- Proper uninstall information for Add/Remove Programs

## File Structure After Installation

```
C:\Program Files\Alabama Auction Watcher\
├── Application\
│   ├── Alabama Auction Watcher.bat
│   ├── streamlit_app\
│   ├── frontend\
│   ├── requirements.txt
│   └── scripts\
├── Backend\
│   ├── start_backend_api.py
│   └── backend_api\
├── Config\
│   └── [configuration files]
├── Icons\
│   ├── alabama-auction-watcher.ico
│   ├── aaw-backend.ico
│   ├── aaw-analytics.ico
│   ├── aaw-health.ico
│   └── aaw-settings.ico
├── Logs\
├── uninstall.py
└── installation_info.json
```

## Prerequisites

### System Requirements
- **Operating System**: Windows 10/11 (Windows 7/8.1 supported)
- **Architecture**: x64 (x86 compatible)
- **RAM**: 4GB minimum, 8GB recommended
- **Storage**: 500MB for installation, 2GB for data
- **Network**: Internet connection for real-time data

### Software Dependencies
- **Python 3.8+**: Required for application execution
- **Web Browser**: Chrome, Firefox, Edge, or Safari for web interface
- **Administrator Rights**: Recommended for system-wide installation

## Installation Process

### Step 1: Pre-Installation
1. Ensure Python 3.8+ is installed
2. Download/clone Alabama Auction Watcher repository
3. Navigate to `installers/windows/` directory

### Step 2: Installation
1. Right-click Command Prompt → "Run as administrator"
2. Execute: `python create_windows_installer.py`
3. Follow prompts for installation location
4. Wait for installation completion

### Step 3: Post-Installation Verification
1. Check desktop shortcut creation
2. Verify Start Menu entries
3. Test `aaw://` protocol by opening: `aaw://test`
4. Launch application from desktop shortcut

## Uninstallation

### Method 1: Start Menu
1. Open Start Menu → Alabama Auction Watcher
2. Click "Uninstall Alabama Auction Watcher"
3. Confirm removal

### Method 2: Direct Script
1. Navigate to installation directory
2. Execute: `python uninstall.py`
3. Confirm removal

### Method 3: Manual Cleanup (if needed)
1. Delete installation directory: `C:\Program Files\Alabama Auction Watcher`
2. Remove shortcuts from Desktop and Start Menu
3. Clean registry entries (optional)

## Troubleshooting

### Common Issues

#### "Permission Denied" During Installation
- **Solution**: Run Command Prompt as Administrator
- **Alternative**: Choose user-level installation when prompted

#### "Python not found"
- **Solution**: Install Python from https://python.org
- **Check**: Ensure Python is added to PATH environment variable

#### Desktop Shortcut Not Working
- **Check**: Verify installation path in shortcut properties
- **Fix**: Recreate shortcut manually pointing to `Alabama Auction Watcher.bat`

#### URL Protocol Not Working
- **Check**: Registry entries in `HKCU\Software\Classes\aaw`
- **Fix**: Re-run installer to recreate registry entries

### Advanced Troubleshooting

#### Installation Log Location
- **File**: `%TEMP%\alabama_auction_watcher_install.log`
- **Contents**: Detailed installation progress and errors

#### Registry Verification
```cmd
# Check application registration
reg query "HKCU\Software\AlabamaAuctionWatcher"

# Check URL protocol
reg query "HKCU\Software\Classes\aaw"
```

#### Service Verification
```cmd
# Check if backend service is running
tasklist | findstr python
netstat -an | findstr :8000
```

## Security Considerations

### Installation Security
- Installer creates user-level registry entries only
- No system service installation by default
- All files installed with user permissions

### Runtime Security
- Application runs with user privileges
- Local data storage in user directory
- No elevation of privileges required for operation

### Network Security
- Local-only web interface (127.0.0.1)
- Backend API bound to localhost
- No external network services exposed

## Enterprise Deployment

### Group Policy Installation
```cmd
# Silent installation for enterprise deployment
python create_windows_installer.py --silent --install-dir "C:\ProgramData\AlabamaAuctionWatcher"
```

### Configuration Management
- Use `installation_info.json` for deployment verification
- Monitor installation status through registry queries
- Automated updates through configuration management systems

### Multi-User Considerations
- Per-user installation recommended
- Shared configuration in `%PROGRAMDATA%`
- Individual user data in `%APPDATA%`

## Support and Maintenance

### Version Updates
1. Download new version
2. Run installer (will upgrade existing installation)
3. Previous settings and data preserved

### Backup Recommendations
- **Configuration**: `Config/` directory
- **Data**: `*.db` database files
- **Logs**: `Logs/` directory

### Performance Monitoring
- Monitor CPU usage of Python processes
- Check memory consumption during peak usage
- Review log files for errors or warnings

---

**Generated**: Alabama Auction Watcher Enterprise Installation System
**Version**: 1.0.0.0
**Platform**: Windows 10/11
**Last Updated**: 2024