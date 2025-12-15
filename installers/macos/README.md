# Alabama Auction Watcher - macOS Installer

## Enterprise .app Bundle and PKG Installer for macOS

This directory contains the macOS application bundle creator and installer system for Alabama Auction Watcher, providing native macOS integration and professional deployment capabilities.

## Quick Start

### Build macOS .app Bundle
```bash
# Navigate to macOS installer directory
cd /path/to/auction/installers/macos

# Create .app bundle and PKG installer
python3 create_macos_app.py
```

### Install Application
```bash
# Install from built bundle
cd build
sudo ./install.sh
```

## Installation Methods

### Method 1: Automated Bundle Creation (Recommended)
- **File**: `create_macos_app.py`
- **Requirements**: Python 3.8+, macOS 10.14+
- **Output**: Native `.app` bundle + PKG installer

### Method 2: Manual Installation
- **Process**: Build .app bundle, then copy to /Applications
- **Benefits**: Full control over installation location
- **Use Case**: Developer testing and customization

### Method 3: Enterprise PKG Deployment
- **File**: Generated `.pkg` file
- **Requirements**: macOS Package Installer
- **Benefits**: Silent deployment, enterprise management

## macOS Integration Features

### Native .app Bundle Structure
```
Alabama Auction Watcher.app/
├── Contents/
│   ├── Info.plist                    # Application metadata
│   ├── PkgInfo                       # Package type information
│   ├── version.plist                 # Version details
│   ├── MacOS/
│   │   └── launch_alabama_auction_watcher  # Main executable
│   ├── Resources/                    # Application resources
│   │   ├── alabama_auction_watcher.icns   # App icon
│   │   ├── streamlit_app/           # Frontend application
│   │   ├── backend_api/             # Backend services
│   │   ├── config/                  # Configuration
│   │   ├── scripts/                 # Utility scripts
│   │   └── requirements.txt         # Python dependencies
│   └── Frameworks/                  # Future use (external libraries)
```

### System Integration
- **Dock Integration**: Professional app icon in Dock
- **Launchpad**: Native Launchpad integration
- **Spotlight**: Searchable via Spotlight
- **Launch Services**: Proper system registration
- **URL Scheme**: Handle `aaw://` protocol links
- **File Associations**: Open `.aaw` data files
- **Auto-dependency**: Automatic Python package installation

## System Requirements

### Minimum Requirements
- **macOS Version**: 10.14 (Mojave) or later
- **Architecture**: Intel x64 or Apple Silicon (M1/M2)
- **RAM**: 4GB minimum, 8GB recommended
- **Storage**: 500MB for app, 2GB for data
- **Python**: 3.8 or later (auto-detected)

### Recommended Environment
- **macOS Version**: 12.0 (Monterey) or later
- **RAM**: 16GB for large datasets
- **Network**: Stable internet for real-time data
- **Browser**: Safari, Chrome, Firefox, or Edge

## Installation Process

### Automated Installation
1. **Download/Build**: Run `python3 create_macos_app.py`
2. **Execute Installer**: Run `./build/install.sh`
3. **System Registration**: Automatic Launch Services registration
4. **Verification**: Launch from Applications folder or Spotlight

### Manual Installation
1. **Build Bundle**: Create .app bundle using creator script
2. **Copy Bundle**: Move `.app` to `/Applications` or `~/Applications`
3. **Set Permissions**: Ensure executable permissions on launcher
4. **Register**: Run `lsregister -f /Applications/Alabama\ Auction\ Watcher.app`

### Enterprise Deployment
```bash
# Silent PKG installation
sudo installer -pkg "AlabamaAuctionWatcher-1.0.0.pkg" -target /

# Verify installation
ls -la /Applications/Alabama\ Auction\ Watcher.app

# Test launch
open "/Applications/Alabama Auction Watcher.app"
```

## Application Behavior

### First Launch
1. **Dependency Check**: Verifies Python 3.8+ installation
2. **Package Installation**: Auto-installs required Python packages
3. **Service Startup**: Launches backend API service
4. **Frontend Launch**: Starts Streamlit web interface
5. **Browser Opening**: Opens application in default browser

### Subsequent Launches
1. **Quick Start**: Cached dependencies for faster startup
2. **Service Management**: Intelligent service lifecycle
3. **State Preservation**: Maintains previous session state

### Background Operation
- **Backend Service**: Runs as user daemon process
- **Port Management**: Automatic port allocation (8501, 8000)
- **Resource Cleanup**: Proper cleanup on application quit

## Configuration and Customization

### Bundle Customization
```python
# Edit create_macos_app.py
class MacOSAppBundleCreator:
    def __init__(self):
        self.app_name = "Alabama Auction Watcher"  # Customize name
        self.bundle_identifier = "com.yourcompany.app"  # Custom ID
        self.version = "1.0.0"  # Version number
```

### Info.plist Customization
- **URL Schemes**: Add custom protocol handlers
- **File Types**: Associate additional file extensions
- **Permissions**: Request specific system permissions
- **Categories**: App Store category classification

### Icon Customization
- **Source**: Update `.icns` files in branding/generated/macos/
- **Resolution**: Support multiple resolutions (16px - 1024px)
- **Variants**: Different icons for different contexts

## Security and Code Signing

### Development Signing
```bash
# Sign with development certificate
codesign --force --sign "Developer ID Application: Your Name" \
    "Alabama Auction Watcher.app"
```

### Distribution Signing
```bash
# Sign for distribution
codesign --force --sign "Developer ID Application: Your Name" \
    --entitlements entitlements.plist \
    "Alabama Auction Watcher.app"

# Create signed PKG
productbuild --component "Alabama Auction Watcher.app" /Applications \
    --sign "Developer ID Installer: Your Name" \
    "AlabamaAuctionWatcher-Signed.pkg"
```

### Notarization (App Store Distribution)
```bash
# Submit for notarization
xcrun altool --notarize-app \
    --primary-bundle-id "com.alabamaauctionwatcher.app" \
    --username "your-apple-id@example.com" \
    --password "@keychain:altool" \
    --file "AlabamaAuctionWatcher.pkg"
```

## Troubleshooting

### Common Issues

#### "App is damaged and can't be opened"
- **Cause**: Code signing or quarantine issue
- **Solution**:
  ```bash
  sudo xattr -rd com.apple.quarantine "/Applications/Alabama Auction Watcher.app"
  ```

#### "Python not found" Error
- **Cause**: Python 3 not installed or not in PATH
- **Solution**: Install Python from https://python.org or Homebrew
  ```bash
  brew install python@3.11
  ```

#### App Doesn't Appear in Launchpad
- **Cause**: Launch Services not updated
- **Solution**: Re-register with Launch Services
  ```bash
  /System/Library/Frameworks/CoreServices.framework/Frameworks/LaunchServices.framework/Support/lsregister -f "/Applications/Alabama Auction Watcher.app"
  ```

#### Backend Service Fails to Start
- **Check**: View logs in Console.app or:
  ```bash
  tail -f ~/Library/Logs/AlabamaAuctionWatcher.log
  ```

### Advanced Troubleshooting

#### Debug Mode
```bash
# Launch with debug logging
open -a "Alabama Auction Watcher" --args --debug
```

#### Manual Service Management
```bash
# Check running processes
ps aux | grep "streamlit\|python.*auction"

# Kill services if hung
pkill -f "streamlit run"
pkill -f "start_backend_api.py"
```

#### Permissions Issues
```bash
# Reset app permissions
sudo chmod -R 755 "/Applications/Alabama Auction Watcher.app"
sudo chown -R $(whoami):staff "/Applications/Alabama Auction Watcher.app"
```

## Uninstallation

### Simple Removal
```bash
# Remove application
sudo rm -rf "/Applications/Alabama Auction Watcher.app"

# Clean Launch Services cache
/System/Library/Frameworks/CoreServices.framework/Frameworks/LaunchServices.framework/Support/lsregister -kill -r -domain local -domain system -domain user
```

### Complete Cleanup
```bash
# Remove all traces
sudo rm -rf "/Applications/Alabama Auction Watcher.app"
rm -rf ~/Library/Logs/AlabamaAuctionWatcher.log
rm -rf ~/Library/Application\ Support/AlabamaAuctionWatcher
rm -rf ~/Library/Preferences/com.alabamaauctionwatcher.app.plist
```

## Development and Testing

### Local Development
```bash
# Test bundle locally
python3 create_macos_app.py
cd build
open "Alabama Auction Watcher.app"
```

### Bundle Validation
```bash
# Validate bundle structure
find "Alabama Auction Watcher.app" -type f -exec file {} \;

# Check Info.plist
plutil -lint "Alabama Auction Watcher.app/Contents/Info.plist"

# Verify code signing
codesign -v "Alabama Auction Watcher.app"
```

### Performance Testing
```bash
# Monitor resource usage
sudo fs_usage -w -f pathname "Alabama Auction Watcher"
top -pid $(pgrep -f "Alabama Auction Watcher")
```

## Enterprise Deployment

### Mass Deployment
- **PKG Distribution**: Deploy via enterprise management tools
- **Custom Configuration**: Pre-configure settings via config files
- **License Management**: Integrate with enterprise license systems

### Configuration Management
```bash
# Deploy custom settings
sudo defaults write /Applications/Alabama\ Auction\ Watcher.app/Contents/Resources/config.plist \
    DefaultServer "https://your-server.com"
```

### Monitoring and Maintenance
- **Log Aggregation**: Collect logs via enterprise tools
- **Update Management**: Automated update deployment
- **Usage Analytics**: Monitor application usage patterns

---

**Platform**: macOS 10.14+
**Architecture**: Universal (Intel + Apple Silicon)
**Version**: 1.0.0
**Bundle ID**: com.alabamaauctionwatcher.app