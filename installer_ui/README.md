# Alabama Auction Watcher - Professional Installer UI

## Enterprise-Grade Installation Experience

This directory contains the professional installer UI system for Alabama Auction Watcher, providing a polished, branded installation experience across all platforms.

## Features

### Professional Wizard Interface
- **Multi-step Installation**: Guided installation process with clear navigation
- **Custom Branding**: Professional branding with logo, colors, and imagery
- **License Agreement**: Integrated license acceptance workflow
- **Component Selection**: Granular control over installed components
- **Progress Tracking**: Real-time installation progress with detailed logging

### Cross-Platform Support
- **Windows**: Native Windows installer experience with modern styling
- **macOS**: Mac-native interface following Apple Human Interface Guidelines
- **Linux**: GTK/Qt integration for seamless Linux desktop experience

### Installation Options
- **Installation Types**: Typical, Complete, and Custom installation modes
- **Destination Selection**: User-configurable installation directory
- **Component Selection**: Modular component installation
- **Desktop Integration**: Optional shortcuts and system integration
- **User vs System**: Per-user or system-wide installation options

## Usage

### Basic Installation Wizard
```python
from installer_wizard import InstallerWizard

# Create and run installer
installer = InstallerWizard()
installer.run()
```

### Custom Installer Configuration
```python
# Custom installer with specific branding
installer = InstallerWizard()
installer.app_name = "Your Custom App Name"
installer.app_version = "2.0.0"
installer.publisher = "Your Company"
installer.website = "https://yourcompany.com"
installer.run()
```

### Command Line Usage
```bash
# Run installer GUI
python installer_wizard.py

# Silent installation (future feature)
python installer_wizard.py --silent --install-dir "C:\CustomPath"

# Configuration-driven installation
python installer_wizard.py --config installer_config.json
```

## Installer Workflow

### Page Flow
1. **Welcome Page**: Application introduction and system requirements
2. **License Agreement**: License acceptance requirement
3. **Installation Type**: Typical, Complete, or Custom selection
4. **Destination Folder**: Installation directory selection
5. **Component Selection**: Feature and component selection
6. **Ready to Install**: Installation summary and confirmation
7. **Installation Progress**: Real-time progress with logging
8. **Completion**: Success confirmation and launch options

### Installation Steps
1. **Preparation**: Verify system requirements and permissions
2. **Directory Creation**: Create installation directory structure
3. **File Copying**: Copy application files with progress tracking
4. **Dependency Installation**: Install Python packages and dependencies
5. **Desktop Integration**: Create shortcuts and file associations
6. **System Registration**: Register application with operating system
7. **Finalization**: Complete installation and cleanup

## Customization

### Branding Assets
Create custom branding assets in the `assets/` directory:

```
installer_ui/assets/
├── installer_banner.png     # Top banner (600x80px)
├── installer_side.png       # Side panel image (150x400px)
├── app_icon.ico            # Application icon
└── background.png          # Background image (optional)
```

### Color Scheme
The installer uses a professional color palette:

- **Primary**: #6C8EF5 (Indigo Blue)
- **Secondary**: #2C3E50 (Dark Blue-Gray)
- **Accent**: #2980B9 (Blue)
- **Success**: #16A34A (Green)
- **Warning**: #F59E0B (Orange)
- **Error**: #EF4444 (Red)

### Custom Styling
```python
# Custom TTK styles
style = ttk.Style()

style.configure('Custom.Title.TLabel',
               font=('Your Font', 18, 'bold'),
               foreground='#YourColor')

style.configure('Custom.Button.TButton',
               font=('Your Font', 10),
               background='#YourColor')
```

### Component Configuration
```python
# Custom components
components = {
    'core': {
        'name': 'Core Application',
        'size': '150 MB',
        'required': True,
        'description': 'Main application files'
    },
    'optional': {
        'name': 'Optional Features',
        'size': '50 MB',
        'required': False,
        'description': 'Additional features and tools'
    }
}
```

## Platform-Specific Features

### Windows
- **Modern Visual Styles**: Windows 10/11 native styling
- **Administrator Elevation**: Automatic UAC prompts when needed
- **Registry Integration**: Proper Windows registry entries
- **MSI Integration**: Can integrate with Windows Installer packages
- **File Associations**: Register file types and protocols
- **Start Menu**: Professional Start Menu integration

### macOS
- **Native Look**: macOS Aqua interface compliance
- **App Bundle**: Integration with .app bundle installation
- **Launchpad**: Automatic Launchpad registration
- **Gatekeeper**: Code signing preparation and validation
- **Accessibility**: VoiceOver and accessibility support

### Linux
- **Desktop Environment**: GNOME, KDE, XFCE support
- **Package Integration**: Seamless integration with system package managers
- **XDG Compliance**: Follows freedesktop.org standards
- **Icon Themes**: Multi-resolution icon installation
- **Desktop Files**: Proper .desktop file creation

## Security Features

### Integrity Verification
- **Checksum Validation**: SHA-256 file integrity verification
- **Digital Signatures**: Code signing validation (when available)
- **Secure Download**: HTTPS-only download verification
- **Path Validation**: Secure installation path validation

### Permission Management
- **Least Privilege**: Request minimal required permissions
- **User Choice**: Allow user vs. system installation choice
- **Temporary Files**: Secure temporary file handling
- **Cleanup**: Comprehensive cleanup on failure or cancellation

## Enterprise Features

### Silent Installation
```bash
# Unattended installation
python installer_wizard.py \
    --silent \
    --install-dir "/opt/alabama-auction-watcher" \
    --no-desktop-shortcut \
    --no-start-menu \
    --accept-license
```

### Configuration Management
```json
{
  "installation": {
    "type": "complete",
    "destination": "/opt/alabama-auction-watcher",
    "components": ["core", "web", "analytics"],
    "shortcuts": {
      "desktop": false,
      "start_menu": true
    }
  },
  "enterprise": {
    "silent_mode": true,
    "accept_license": true,
    "install_for_all_users": true
  }
}
```

### Deployment Integration
- **Group Policy**: Windows Group Policy deployment
- **Ansible**: Linux automation integration
- **Jamf**: macOS enterprise deployment
- **SCCM**: Microsoft System Center integration

## Error Handling

### Robust Error Management
- **Graceful Failures**: User-friendly error messages
- **Automatic Retry**: Retry failed operations
- **Rollback**: Automatic cleanup on installation failure
- **Logging**: Comprehensive installation logging

### Common Issues
```python
# Handle insufficient permissions
if not check_admin_rights():
    show_elevation_prompt()

# Handle disk space issues
if not check_disk_space(required_space):
    show_space_warning()

# Handle dependency issues
if not check_dependencies():
    offer_dependency_installation()
```

## Testing and Validation

### Installer Testing
```bash
# Test installer on clean system
python test_installer.py --clean-environment

# Test upgrade scenarios
python test_installer.py --upgrade-test

# Test uninstallation
python test_installer.py --uninstall-test
```

### Validation Checklist
- [ ] All pages display correctly
- [ ] Navigation works properly
- [ ] License agreement functions
- [ ] File copying completes successfully
- [ ] Shortcuts are created properly
- [ ] Application launches after installation
- [ ] Uninstallation removes all components

## Performance Optimization

### Resource Management
- **Memory Efficient**: Minimal memory footprint during installation
- **Background Processing**: Non-blocking UI updates
- **Progress Reporting**: Accurate progress calculation
- **Cancellation Support**: Clean cancellation at any stage

### Installation Speed
- **Parallel Operations**: Concurrent file operations where safe
- **Compression**: Efficient file compression and decompression
- **Caching**: Smart caching of downloaded components
- **Resume Support**: Resume interrupted installations

## Internationalization

### Multi-Language Support
```python
# Language configuration
LANGUAGES = {
    'en': 'English',
    'es': 'Español',
    'fr': 'Français',
    'de': 'Deutsch'
}

# Localized strings
STRINGS = {
    'en': {
        'welcome_title': 'Welcome to Alabama Auction Watcher Setup',
        'license_title': 'License Agreement'
    }
}
```

### Localization Features
- **RTL Support**: Right-to-left language support
- **Font Selection**: Automatic font selection for languages
- **Cultural Adaptation**: Date/time format localization
- **Accessibility**: Screen reader compatibility

---

**Version**: 1.0.0
**Platform Compatibility**: Windows 10+, macOS 10.14+, Linux (modern distributions)
**Dependencies**: Python 3.8+, tkinter, Pillow (optional)
**License**: MIT License