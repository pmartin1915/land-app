# Alabama Auction Watcher - Icon Deployment Guide

## Enterprise Icon Set - Generated Structure

This directory contains the enterprise icon deployment structure for Alabama Auction Watcher.

### Platform Directories

#### Windows (`./windows/`)
- `.ico` files for Windows desktop integration
- Multiple resolution PNG files for various Windows contexts

#### macOS (`./macos/`)
- `.icns` files for macOS app bundle integration
- High-resolution PNG files for macOS contexts

#### Linux (`./linux/`)
- PNG files for Linux desktop environments
- Multiple sizes for different desktop themes and contexts

#### Web (`./web/`)
- Web-optimized PNG files for documentation and web deployment

### Icon Set

1. **alabama-auction-watcher** - Main application icon
2. **aaw-backend** - Backend API service icon
3. **aaw-analytics** - Analytics dashboard icon
4. **aaw-health** - System health monitor icon
5. **aaw-settings** - Settings configuration icon

### Next Steps for Full Icon Generation

To generate full-resolution icons from the SVG sources, you'll need:

1. **Install Inkscape**: https://inkscape.org/release/
2. **Install ImageMagick**: https://imagemagick.org/script/download.php
3. **Run**: `python generate_icons.py`

### Manual Icon Creation (Alternative)

If automated tools aren't available, you can manually create icons:

1. Open each SVG file in a graphics editor (Inkscape, Adobe Illustrator, etc.)
2. Export to PNG at required sizes
3. Use online converters for ICO/ICNS formats:
   - ICO: https://convertio.co/png-ico/
   - ICNS: https://cloudconvert.com/png-to-icns

### Integration Instructions

#### Windows Desktop Integration
Copy `.ico` files to your application directory and reference in:
- Desktop shortcuts (.lnk files)
- Windows Installer (MSI) resources
- Application manifests

#### macOS Bundle Integration
```bash
cp generated/macos/*.icns MyApp.app/Contents/Resources/
```

#### Linux Desktop Integration
```bash
# Install to system icon cache
for size in 16 32 48 64 128 256; do
    cp generated/linux/*_${size}x${size}.png ~/.local/share/icons/hicolor/${size}x${size}/apps/
done
update-icon-caches ~/.local/share/icons/hicolor
```

Generated: 2025-09-24 09:47:12
