# Alabama Auction Watcher - Application Icons

This directory contains placeholder icon files for the desktop launcher integration. These should be replaced with proper high-quality icons for a professional desktop experience.

## Required Icons

### Main Application Icons
- `main_app.ico` - Main dashboard application (16x16, 32x32, 48x48, 256x256)
- `backend_api.ico` - Backend API server (16x16, 32x32, 48x48, 256x256)
- `enhanced_dashboard.ico` - Enhanced dashboard with AI monitoring (16x16, 32x32, 48x48, 256x256)
- `health_check.ico` - System health check utility (16x16, 32x32, 48x48, 256x256)

### Platform-Specific Requirements

#### Windows (.ico files)
- Must contain multiple sizes: 16x16, 32x32, 48x48, 256x256 pixels
- Should be in .ico format for best compatibility
- Transparency supported

#### macOS (.icns files)
- Should be converted to .icns format for proper macOS integration
- Multiple resolutions required: 16x16, 32x32, 128x128, 256x256, 512x512, 1024x1024
- Use Icon Composer or online converters

#### Linux (.png/.svg files)
- Can use PNG or SVG format
- Standard sizes: 16x16, 22x22, 32x32, 48x48, 64x64, 128x128, 256x256
- SVG preferred for scalability

## Icon Design Guidelines

### Visual Style
- **Theme**: Modern, professional, real estate/property related
- **Colors**: Use Alabama Auction Watcher brand colors
  - Primary: Blue (#1f77b4) for main app
  - Secondary: Green (#2ca02c) for backend/API
  - Warning: Orange (#ff7f0e) for health checks
  - Enhanced: Purple/gradient for AI features
- **Style**: Flat design with subtle shadows/gradients

### Icon Concepts

#### Main App Icon
- House/property symbol with auction elements
- Possibly combined with Alabama state outline
- Color: Primary blue theme

#### Backend API Icon
- Server/database symbol
- Gear/cog elements for configuration
- Color: Green theme for "go/ready" status

#### Enhanced Dashboard Icon
- Brain/AI symbol combined with charts
- Monitoring/analytics elements
- Color: Purple/gradient for advanced features

#### Health Check Icon
- Medical cross or checkmark symbol
- System monitoring elements
- Color: Orange/red for attention/alerts

## Creating the Icons

### Option 1: Design Software
Use professional design software like:
- Adobe Illustrator (for vector graphics)
- Photoshop (for raster graphics)
- GIMP (free alternative)
- Inkscape (free vector graphics)

### Option 2: Online Icon Generators
- Favicon.io
- IconArchive
- Canva (icon creation)
- Figma (free design tool)

### Option 3: Icon Libraries
Purchase or download from:
- Flaticon (with attribution)
- Icons8
- Font Awesome (for simple symbols)
- Material Design Icons

## Converting Between Formats

### To Windows .ico
```bash
# Using ImageMagick
convert icon.png -define icon:auto-resize="256,48,32,16" icon.ico

# Using online converter
# Visit: https://convertio.co/png-ico/
```

### To macOS .icns
```bash
# Using iconutil (macOS)
iconutil -c icns icon.iconset

# Or use online converter
# Visit: https://cloudconvert.com/png-to-icns
```

### To Linux formats
```bash
# PNG files can be used directly
# For SVG, ensure proper sizing attributes
```

## Installation

Once you have created the proper icons:

1. Replace the placeholder files in this directory
2. Update the desktop files and launchers to reference the correct icon paths
3. For system-wide installation, copy icons to:
   - Windows: Usually handled by installer
   - macOS: Bundle with .app package
   - Linux: `/usr/share/icons/hicolor/[size]/apps/` or `~/.local/share/icons/`

## Testing Icons

After creating icons, test them by:

1. **Windows**: Double-click the .bat files and check taskbar icons
2. **macOS**: Test .command files and check dock icons
3. **Linux**: Install .desktop files and check application menu

## Current Status

🔄 **PLACEHOLDER FILES** - The current icon files are simple placeholders. Professional icons should be created for production use.

Priority order for icon creation:
1. Main app icon (most visible)
2. Enhanced dashboard icon (key feature)
3. Backend API icon (for developers)
4. Health check icon (utility)