#!/usr/bin/env python3
"""
Alabama Auction Watcher - Installer Asset Creator
Creates professional branding assets for the installer UI
"""

import os
from pathlib import Path
import json

try:
    from PIL import Image, ImageDraw, ImageFont
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False

class InstallerAssetCreator:
    """Create professional installer branding assets"""

    def __init__(self):
        self.app_name = "Alabama Auction Watcher"
        self.brand_colors = {
            'primary': '#6C8EF5',
            'secondary': '#2C3E50',
            'accent': '#2980B9',
            'white': '#FFFFFF',
            'light_gray': '#F8F9FA',
            'dark_gray': '#495057'
        }

        # Asset specifications
        self.assets_dir = Path(__file__).parent / "assets"
        self.assets_dir.mkdir(exist_ok=True)

    def create_banner_image(self):
        """Create installer banner image (600x80)"""
        if not PIL_AVAILABLE:
            print("PIL not available - skipping image creation")
            return

        try:
            # Create banner
            width, height = 600, 80
            banner = Image.new('RGB', (width, height), color='#FFFFFF')
            draw = ImageDraw.Draw(banner)

            # Background gradient effect
            for i in range(height):
                color_value = int(255 - (i / height) * 20)  # Subtle gradient
                color = (color_value, color_value, 255)  # Blue tint
                draw.line([(0, i), (width, i)], fill=color)

            # Main brand color bar at top
            draw.rectangle([0, 0, width, 8], fill=self.brand_colors['primary'])

            # App name
            try:
                font = ImageFont.truetype("arial.ttf", 24)
            except:
                font = ImageFont.load_default()

            text = self.app_name
            text_bbox = draw.textbbox((0, 0), text, font=font)
            text_width = text_bbox[2] - text_bbox[0]
            text_height = text_bbox[3] - text_bbox[1]

            x = (width - text_width) // 2
            y = (height - text_height) // 2 - 5

            # Text shadow
            draw.text((x + 2, y + 2), text, fill=self.brand_colors['dark_gray'], font=font)
            # Main text
            draw.text((x, y), text, fill=self.brand_colors['secondary'], font=font)

            # Subtitle
            try:
                subtitle_font = ImageFont.truetype("arial.ttf", 12)
            except:
                subtitle_font = ImageFont.load_default()

            subtitle = "Professional Real Estate Intelligence"
            subtitle_bbox = draw.textbbox((0, 0), subtitle, font=subtitle_font)
            subtitle_width = subtitle_bbox[2] - subtitle_bbox[0]

            subtitle_x = (width - subtitle_width) // 2
            subtitle_y = y + text_height + 2

            draw.text((subtitle_x, subtitle_y), subtitle, fill=self.brand_colors['accent'], font=subtitle_font)

            # Save banner
            banner_path = self.assets_dir / "installer_banner.png"
            banner.save(banner_path, "PNG")
            print(f"Created banner: {banner_path}")

        except Exception as e:
            print(f"Error creating banner: {e}")

    def create_side_image(self):
        """Create installer side panel image (150x400)"""
        if not PIL_AVAILABLE:
            return

        try:
            # Create side panel
            width, height = 150, 400
            side_img = Image.new('RGB', (width, height), color=self.brand_colors['primary'])
            draw = ImageDraw.Draw(side_img)

            # Gradient background
            for i in range(width):
                color_intensity = int(108 + (i / width) * 30)  # Gradient from primary color
                color = (color_intensity, 142, 245)
                draw.line([(i, 0), (i, height)], fill=color)

            # Decorative elements
            # Alabama state outline (simplified)
            alabama_points = [
                (75, 100), (85, 95), (95, 100), (105, 110), (110, 130),
                (105, 150), (95, 160), (85, 165), (75, 160), (65, 150),
                (60, 130), (65, 110), (75, 100)
            ]
            draw.polygon(alabama_points, outline='#FFFFFF', width=2)

            # Property/investment icons (simplified)
            # House icon
            house_points = [(70, 200), (80, 190), (90, 200), (90, 220), (70, 220)]
            draw.polygon(house_points, outline='#FFFFFF', width=2)

            # Dollar sign
            draw.text((70, 250), "$", fill='#FFFFFF', font=ImageFont.load_default())

            # Chart/graph representation
            chart_x = [30, 50, 70, 90, 110]
            chart_y = [320, 310, 300, 295, 290]
            for i in range(len(chart_x) - 1):
                draw.line([(chart_x[i], chart_y[i]), (chart_x[i + 1], chart_y[i + 1])],
                         fill='#FFFFFF', width=2)

            # Save side image
            side_path = self.assets_dir / "installer_side.png"
            side_img.save(side_path, "PNG")
            print(f"Created side image: {side_path}")

        except Exception as e:
            print(f"Error creating side image: {e}")

    def create_installer_config(self):
        """Create installer configuration template"""
        config = {
            "branding": {
                "app_name": self.app_name,
                "app_version": "1.0.0",
                "publisher": "Alabama Auction Watcher Team",
                "website": "https://github.com/Alabama-Auction-Watcher",
                "support_url": "https://github.com/Alabama-Auction-Watcher/issues",
                "colors": self.brand_colors
            },
            "installation": {
                "default_install_dir": {
                    "windows": "C:\\Program Files\\Alabama Auction Watcher",
                    "macos": "/Applications",
                    "linux": "/opt/alabama-auction-watcher"
                },
                "required_space_mb": 500,
                "estimated_time_minutes": 5
            },
            "components": {
                "core": {
                    "name": "Core Application",
                    "description": "Main application files and web interface",
                    "size_mb": 250,
                    "required": True
                },
                "desktop_integration": {
                    "name": "Desktop Integration",
                    "description": "Desktop shortcuts and file associations",
                    "size_mb": 10,
                    "required": False,
                    "default_selected": True
                },
                "sample_data": {
                    "name": "Sample Data",
                    "description": "Sample auction data for testing and learning",
                    "size_mb": 75,
                    "required": False,
                    "default_selected": False
                },
                "development_tools": {
                    "name": "Development Tools",
                    "description": "API documentation and development utilities",
                    "size_mb": 50,
                    "required": False,
                    "default_selected": False
                }
            },
            "shortcuts": {
                "desktop": {
                    "name": "Alabama Auction Watcher",
                    "description": "Launch the main application",
                    "default_enabled": True
                },
                "start_menu": {
                    "folder": "Alabama Auction Watcher",
                    "items": [
                        {
                            "name": "Alabama Auction Watcher",
                            "description": "Main application"
                        },
                        {
                            "name": "User Guide",
                            "description": "Application documentation"
                        },
                        {
                            "name": "Uninstall",
                            "description": "Remove Alabama Auction Watcher"
                        }
                    ]
                }
            },
            "system_requirements": {
                "windows": {
                    "min_version": "Windows 10",
                    "ram_mb": 4096,
                    "disk_space_mb": 2048
                },
                "macos": {
                    "min_version": "macOS 10.14",
                    "ram_mb": 4096,
                    "disk_space_mb": 2048
                },
                "linux": {
                    "min_kernel": "3.10",
                    "ram_mb": 2048,
                    "disk_space_mb": 2048
                }
            }
        }

        config_path = self.assets_dir / "installer_config.json"
        with open(config_path, 'w', encoding='utf-8') as f:
            json.dump(config, f, indent=2)

        print(f"Created installer config: {config_path}")

    def create_style_guide(self):
        """Create installer UI style guide"""
        style_guide = f"""# Alabama Auction Watcher - Installer Style Guide

## Brand Colors

### Primary Palette
- **Primary Blue**: {self.brand_colors['primary']} (Main brand color)
- **Secondary Dark**: {self.brand_colors['secondary']} (Text and headers)
- **Accent Blue**: {self.brand_colors['accent']} (Links and highlights)

### Neutral Palette
- **White**: {self.brand_colors['white']} (Backgrounds and text)
- **Light Gray**: {self.brand_colors['light_gray']} (Subtle backgrounds)
- **Dark Gray**: {self.brand_colors['dark_gray']} (Secondary text)

## Typography

### Font Hierarchy
1. **Title**: Arial 16pt Bold (Page titles)
2. **Header**: Arial 12pt Bold (Section headers)
3. **Body**: Arial 10pt Regular (Body text)
4. **Caption**: Arial 9pt Regular (Captions and hints)

### Text Colors
- **Primary Text**: {self.brand_colors['secondary']}
- **Secondary Text**: {self.brand_colors['dark_gray']}
- **Accent Text**: {self.brand_colors['accent']}

## UI Components

### Buttons
- **Primary Button**: {self.brand_colors['primary']} background, white text
- **Secondary Button**: White background, {self.brand_colors['primary']} border
- **Cancel Button**: {self.brand_colors['dark_gray']} background

### Progress Indicators
- **Progress Bar**: {self.brand_colors['primary']} fill
- **Success State**: #16A34A (Green)
- **Warning State**: #F59E0B (Orange)
- **Error State**: #EF4444 (Red)

## Layout Guidelines

### Spacing
- **Page Margins**: 20px
- **Section Spacing**: 20px vertical
- **Element Spacing**: 10px vertical
- **Button Spacing**: 5px horizontal

### Image Specifications
- **Banner**: 600x80px (installer_banner.png)
- **Side Panel**: 150x400px (installer_side.png)
- **Icons**: 32x32px minimum

## Professional Standards

### User Experience
- Clear navigation with Back/Next buttons
- Progress indication throughout installation
- Helpful error messages and recovery options
- Consistent visual hierarchy

### Accessibility
- High contrast ratios for text
- Keyboard navigation support
- Screen reader compatibility
- Clear visual feedback

### Cross-Platform Consistency
- Native look and feel per platform
- Consistent branding across all platforms
- Platform-appropriate UI conventions
"""

        style_path = self.assets_dir / "style_guide.md"
        with open(style_path, 'w', encoding='utf-8') as f:
            f.write(style_guide)

        print(f"Created style guide: {style_path}")

    def create_all_assets(self):
        """Create all installer assets"""
        print(f"Creating installer assets for {self.app_name}...")
        print(f"Output directory: {self.assets_dir}")

        # Create visual assets
        if PIL_AVAILABLE:
            self.create_banner_image()
            self.create_side_image()
        else:
            print("PIL not available - visual assets skipped")
            print("Install Pillow with: pip install Pillow")

        # Create configuration and documentation
        self.create_installer_config()
        self.create_style_guide()

        print("\nAsset creation completed!")
        print(f"Assets created in: {self.assets_dir}")

def main():
    """Main asset creation execution"""
    creator = InstallerAssetCreator()
    creator.create_all_assets()

if __name__ == '__main__':
    main()