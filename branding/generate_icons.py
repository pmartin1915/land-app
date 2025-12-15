#!/usr/bin/env python3
"""
Alabama Auction Watcher - Icon Generation System
Converts SVG icons to all required formats and sizes for enterprise deployment

Features:
- Multi-resolution icon generation
- Platform-specific format conversion (.ico, .icns, .png)
- High-DPI support
- Batch processing
- Quality validation
"""

import os
import sys
import subprocess
from pathlib import Path
from typing import List, Dict, Tuple
import json
import shutil

# Icon size specifications for different platforms
ICON_SPECS = {
    'windows': {
        'formats': ['.ico'],
        'sizes': [16, 32, 48, 64, 128, 256],
        'description': 'Windows ICO files with embedded multi-resolution'
    },
    'macos': {
        'formats': ['.icns', '.png'],
        'sizes': [16, 32, 64, 128, 256, 512, 1024],
        'description': 'macOS ICNS bundles and PNG variants'
    },
    'linux': {
        'formats': ['.png'],
        'sizes': [16, 22, 24, 32, 48, 64, 96, 128, 192, 256, 512],
        'description': 'Linux PNG icons for various themes and contexts'
    },
    'web': {
        'formats': ['.png', '.svg'],
        'sizes': [16, 32, 64, 128, 192, 512],
        'description': 'Web-optimized icons for documentation and websites'
    }
}

# Icon definitions
ICONS = {
    'main_app': {
        'svg_file': 'main_app_icon.svg',
        'name': 'alabama-auction-watcher',
        'description': 'Main application icon',
        'priority': 1
    },
    'backend_api': {
        'svg_file': 'backend_api_icon.svg',
        'name': 'aaw-backend',
        'description': 'Backend API service icon',
        'priority': 2
    },
    'analytics': {
        'svg_file': 'analytics_dashboard_icon.svg',
        'name': 'aaw-analytics',
        'description': 'Analytics dashboard icon',
        'priority': 3
    },
    'health': {
        'svg_file': 'system_health_icon.svg',
        'name': 'aaw-health',
        'description': 'System health monitor icon',
        'priority': 4
    },
    'settings': {
        'svg_file': 'settings_icon.svg',
        'name': 'aaw-settings',
        'description': 'Settings and configuration icon',
        'priority': 5
    }
}

class IconGenerator:
    """Professional icon generation system"""

    def __init__(self, source_dir: Path, output_dir: Path):
        self.source_dir = source_dir
        self.output_dir = output_dir
        self.stats = {
            'generated': 0,
            'failed': 0,
            'platforms': set(),
            'formats': set()
        }

        # Create output directory structure
        self.setup_output_structure()

        # Check for required tools
        self.check_dependencies()

    def setup_output_structure(self):
        """Create organized output directory structure"""
        directories = [
            'windows',
            'macos',
            'linux',
            'web',
            'source',
            'documentation'
        ]

        for directory in directories:
            (self.output_dir / directory).mkdir(parents=True, exist_ok=True)

        print(f"[INFO] Created output structure in: {self.output_dir}")

    def check_dependencies(self):
        """Check for required conversion tools"""
        tools = {
            'inkscape': 'SVG to PNG conversion',
            'imagemagick': 'Image format conversion and ICO creation',
            'iconutil': 'macOS ICNS creation (macOS only)'
        }

        available_tools = []
        missing_tools = []

        for tool, description in tools.items():
            if shutil.which(tool) or self.check_tool_alternate(tool):
                available_tools.append(tool)
                print(f"[OK] {tool}: Available")
            else:
                missing_tools.append(tool)
                print(f"[ERROR] {tool}: Missing - {description}")

        if missing_tools:
            print(f"\n[WARNING] Missing tools: {', '.join(missing_tools)}")
            print("Installation recommendations:")
            if 'inkscape' in missing_tools:
                print("  - Inkscape: https://inkscape.org/release/")
            if 'imagemagick' in missing_tools:
                print("  - ImageMagick: https://imagemagick.org/script/download.php")
            if 'iconutil' in missing_tools and sys.platform == 'darwin':
                print("  - iconutil: Built into macOS (Xcode Command Line Tools)")

    def check_tool_alternate(self, tool: str) -> bool:
        """Check for alternate tool installations"""
        alternates = {
            'inkscape': ['inkscape.exe', 'inkscape.app'],
            'imagemagick': ['magick', 'convert'],
            'iconutil': []  # macOS only
        }

        if tool in alternates:
            for alt in alternates[tool]:
                if shutil.which(alt):
                    return True
        return False

    def svg_to_png(self, svg_path: Path, png_path: Path, size: int) -> bool:
        """Convert SVG to PNG using Inkscape"""
        try:
            # Try different Inkscape command variants
            inkscape_commands = [
                ['magick', str(svg_path), '-resize', f'{size}x{size}', str(png_path)],  # ImageMagick primary
                ['magick', 'convert', str(svg_path), '-resize', f'{size}x{size}', str(png_path)],  # ImageMagick convert
                ['inkscape', '--export-type=png', f'--export-width={size}', f'--export-height={size}', f'--export-filename={png_path}', str(svg_path)],
                ['inkscape', '-w', str(size), '-h', str(size), '-e', str(png_path), str(svg_path)]  # Older Inkscape
            ]

            for cmd in inkscape_commands:
                try:
                    result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
                    if result.returncode == 0 and png_path.exists():
                        return True
                except (subprocess.TimeoutExpired, FileNotFoundError):
                    continue

            print(f"[ERROR] Failed to convert {svg_path.name} to {size}x{size} PNG")
            return False

        except Exception as e:
            print(f"[ERROR] Error converting SVG to PNG: {e}")
            return False

    def create_ico_file(self, png_files: List[Path], ico_path: Path) -> bool:
        """Create Windows ICO file from PNG files"""
        try:
            # Use ImageMagick to create ICO
            cmd = ['magick'] + [str(f) for f in png_files] + [str(ico_path)]
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)

            if result.returncode == 0 and ico_path.exists():
                return True
            else:
                print(f"[ERROR] ICO creation failed: {result.stderr}")
                return False

        except Exception as e:
            print(f"[ERROR] Error creating ICO file: {e}")
            return False

    def create_icns_file(self, png_files: Dict[int, Path], icns_path: Path) -> bool:
        """Create macOS ICNS file from PNG files"""
        if sys.platform != 'darwin':
            print("[WARNING] ICNS creation requires macOS")
            return False

        try:
            # Create iconset directory
            iconset_dir = icns_path.parent / f"{icns_path.stem}.iconset"
            iconset_dir.mkdir(exist_ok=True)

            # Map sizes to iconset naming convention
            iconset_mapping = {
                16: 'icon_16x16.png',
                32: 'icon_16x16@2x.png',
                64: 'icon_32x32@2x.png',
                128: 'icon_128x128.png',
                256: 'icon_128x128@2x.png',
                512: 'icon_256x256@2x.png',
                1024: 'icon_512x512@2x.png'
            }

            # Copy PNG files with correct names
            for size, png_path in png_files.items():
                if size in iconset_mapping:
                    target = iconset_dir / iconset_mapping[size]
                    shutil.copy2(png_path, target)

            # Create ICNS using iconutil
            cmd = ['iconutil', '-c', 'icns', str(iconset_dir), '-o', str(icns_path)]
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)

            # Cleanup iconset directory
            shutil.rmtree(iconset_dir, ignore_errors=True)

            if result.returncode == 0 and icns_path.exists():
                return True
            else:
                print(f"[ERROR] ICNS creation failed: {result.stderr}")
                return False

        except Exception as e:
            print(f"[ERROR] Error creating ICNS file: {e}")
            return False

    def generate_icon_set(self, icon_key: str, icon_config: Dict) -> bool:
        """Generate complete icon set for all platforms"""
        print(f"\n[DESIGN] Generating icon set: {icon_config['name']}")

        svg_path = self.source_dir / icon_config['svg_file']
        if not svg_path.exists():
            print(f"[ERROR] SVG source not found: {svg_path}")
            return False

        success_count = 0
        total_count = 0

        # Generate for each platform
        for platform, specs in ICON_SPECS.items():
            print(f"  [PLATFORM] Platform: {platform}")

            platform_dir = self.output_dir / platform
            png_files = {}
            temp_pngs = []

            # Generate PNG files for this platform
            for size in specs['sizes']:
                png_filename = f"{icon_config['name']}_{size}x{size}.png"
                png_path = platform_dir / png_filename

                if self.svg_to_png(svg_path, png_path, size):
                    png_files[size] = png_path
                    temp_pngs.append(png_path)
                    print(f"    [OK] {size}x{size} PNG")
                    success_count += 1
                else:
                    print(f"    [ERROR] {size}x{size} PNG failed")

                total_count += 1

            # Create platform-specific formats
            if '.ico' in specs['formats'] and png_files:
                ico_path = platform_dir / f"{icon_config['name']}.ico"
                if self.create_ico_file(list(png_files.values())[:6], ico_path):  # Limit to 6 sizes for ICO
                    print(f"    [OK] ICO file created")
                    success_count += 1
                else:
                    print(f"    [ERROR] ICO creation failed")
                total_count += 1

            if '.icns' in specs['formats'] and png_files and sys.platform == 'darwin':
                icns_path = platform_dir / f"{icon_config['name']}.icns"
                if self.create_icns_file(png_files, icns_path):
                    print(f"    [OK] ICNS file created")
                    success_count += 1
                else:
                    print(f"    [ERROR] ICNS creation failed")
                total_count += 1

        # Copy source SVG to source directory
        source_copy = self.output_dir / 'source' / icon_config['svg_file']
        shutil.copy2(svg_path, source_copy)

        # Update statistics
        self.stats['generated'] += success_count
        self.stats['failed'] += (total_count - success_count)

        success_rate = (success_count / total_count * 100) if total_count > 0 else 0
        print(f"  [STATS] Success rate: {success_rate:.1f}% ({success_count}/{total_count})")

        return success_rate > 80  # Consider successful if >80% generated

    def generate_documentation(self):
        """Generate icon usage documentation"""
        doc_content = f"""# Alabama Auction Watcher - Icon Documentation

## Generated Icon Sets

This document provides information about the generated icon sets for enterprise deployment.

### Icon Inventory

"""

        for icon_key, icon_config in ICONS.items():
            doc_content += f"#### {icon_config['name']}\n"
            doc_content += f"- **Description**: {icon_config['description']}\n"
            doc_content += f"- **Source**: {icon_config['svg_file']}\n"
            doc_content += f"- **Priority**: {icon_config['priority']}\n\n"

        doc_content += f"""### Platform Support

"""

        for platform, specs in ICON_SPECS.items():
            doc_content += f"#### {platform.title()}\n"
            doc_content += f"- **Formats**: {', '.join(specs['formats'])}\n"
            doc_content += f"- **Sizes**: {', '.join(map(str, specs['sizes']))}\n"
            doc_content += f"- **Description**: {specs['description']}\n\n"

        doc_content += f"""### Usage Instructions

#### Windows
Copy `.ico` files to application directory and reference in:
- Desktop shortcuts (.lnk files)
- Windows Installer (MSI) resources
- Application manifests

#### macOS
Copy `.icns` files to application bundle:
```bash
cp icons/macos/*.icns MyApp.app/Contents/Resources/
```

#### Linux
Install PNG icons to system icon themes:
```bash
cp icons/linux/*_16x16.png ~/.local/share/icons/hicolor/16x16/apps/
cp icons/linux/*_32x32.png ~/.local/share/icons/hicolor/32x32/apps/
# ... repeat for all sizes
update-icon-caches ~/.local/share/icons/hicolor
```

### Generation Statistics

- **Total Generated**: {self.stats['generated']}
- **Failed**: {self.stats['failed']}
- **Platforms**: {len(self.stats['platforms'])}
- **Formats**: {len(self.stats['formats'])}

Generated on: {__import__('datetime').datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
"""

        doc_path = self.output_dir / 'documentation' / 'ICON_USAGE.md'
        with open(doc_path, 'w', encoding='utf-8') as f:
            f.write(doc_content)

        print(f"[DOCS] Documentation generated: {doc_path}")

    def generate_all(self) -> bool:
        """Generate all icon sets"""
        print("[START] Starting enterprise icon generation...")
        print(f"[INFO] Source directory: {self.source_dir}")
        print(f"[INFO] Output directory: {self.output_dir}")

        success_count = 0

        # Sort icons by priority
        sorted_icons = sorted(ICONS.items(), key=lambda x: x[1]['priority'])

        for icon_key, icon_config in sorted_icons:
            if self.generate_icon_set(icon_key, icon_config):
                success_count += 1

        # Generate documentation
        self.generate_documentation()

        # Print summary
        print(f"\n[STATS] Generation Summary:")
        print(f"[OK] Successful icon sets: {success_count}/{len(ICONS)}")
        print(f"[STATS] Total icons generated: {self.stats['generated']}")
        print(f"[ERROR] Failed generations: {self.stats['failed']}")

        if success_count == len(ICONS):
            print("[SUCCESS] All icon sets generated successfully!")
            return True
        else:
            print("[WARNING] Some icon sets failed. Check the output above.")
            return False

def main():
    """Main execution function"""
    script_dir = Path(__file__).parent
    source_dir = script_dir / 'icons'
    output_dir = script_dir / 'generated'

    print("[TARGET] Alabama Auction Watcher - Enterprise Icon Generator")
    print("=" * 60)

    if not source_dir.exists():
        print(f"[ERROR] Source directory not found: {source_dir}")
        sys.exit(1)

    generator = IconGenerator(source_dir, output_dir)

    if generator.generate_all():
        print("\n[OK] Icon generation completed successfully!")
        print(f"[INFO] Generated icons available in: {output_dir}")
        sys.exit(0)
    else:
        print("\n[ERROR] Icon generation completed with errors!")
        sys.exit(1)

if __name__ == '__main__':
    main()