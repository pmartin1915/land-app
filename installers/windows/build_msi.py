#!/usr/bin/env python3
"""
Windows MSI Installer Build System
Builds enterprise-grade Windows installer for Alabama Auction Watcher
"""

import os
import sys
import subprocess
import shutil
from pathlib import Path
import tempfile

class WindowsInstallerBuilder:
    """Professional Windows MSI installer builder"""

    def __init__(self, source_dir: Path, output_dir: Path):
        self.source_dir = source_dir
        self.output_dir = output_dir
        self.installer_dir = source_dir / 'installers' / 'windows'
        self.wix_version = "3.11"  # WiX Toolset version

        # Build configuration
        self.product_name = "Alabama Auction Watcher"
        self.product_version = "1.0.0.0"
        self.manufacturer = "Alabama Auction Watcher Team"

        # Setup output structure
        self.setup_output_structure()

    def setup_output_structure(self):
        """Create organized output directory structure"""
        self.output_dir.mkdir(parents=True, exist_ok=True)
        (self.output_dir / 'logs').mkdir(exist_ok=True)
        (self.output_dir / 'temp').mkdir(exist_ok=True)
        print(f"[INFO] Created build structure in: {self.output_dir}")

    def check_wix_toolset(self) -> bool:
        """Check for WiX Toolset installation"""
        wix_paths = [
            Path("C:/Program Files (x86)/WiX Toolset v3.11/bin"),
            Path("C:/Program Files/WiX Toolset v3.11/bin"),
            Path("C:/WiX/bin")
        ]

        for wix_path in wix_paths:
            if (wix_path / "candle.exe").exists() and (wix_path / "light.exe").exists():
                print(f"[OK] WiX Toolset found: {wix_path}")
                return True

        print("[ERROR] WiX Toolset not found")
        print("Please install WiX Toolset from: https://wixtoolset.org/releases/")
        return False

    def check_dependencies(self) -> bool:
        """Check for required build dependencies"""
        dependencies = {
            'candle.exe': 'WiX Compiler',
            'light.exe': 'WiX Linker'
        }

        all_available = True
        for tool, description in dependencies.items():
            if shutil.which(tool):
                print(f"[OK] {description}: Available")
            else:
                print(f"[ERROR] {description}: Missing")
                all_available = False

        return all_available

    def prepare_source_files(self):
        """Prepare and validate source files for packaging"""
        print("[INFO] Preparing source files for packaging...")

        required_files = [
            self.source_dir / "Alabama Auction Watcher.bat",
            self.source_dir / "streamlit_app" / "app.py",
            self.source_dir / "requirements.txt",
            self.source_dir / "start_backend_api.py"
        ]

        missing_files = []
        for file_path in required_files:
            if not file_path.exists():
                missing_files.append(file_path)
            else:
                print(f"[OK] Found: {file_path.name}")

        if missing_files:
            print("[ERROR] Missing required source files:")
            for missing in missing_files:
                print(f"  - {missing}")
            return False

        # Check icon files
        icon_dir = self.source_dir / "branding" / "generated" / "windows"
        if not icon_dir.exists():
            print("[ERROR] Icon files not found. Run icon generation first.")
            return False

        print("[OK] All source files validated")
        return True

    def create_supporting_files(self):
        """Create license and branding files for installer"""

        # Create license file
        license_content = """SOFTWARE LICENSE AGREEMENT

Alabama Auction Watcher

This software is provided "as is" without warranty of any kind, express or implied,
including but not limited to the warranties of merchantability, fitness for a
particular purpose and noninfringement.

Copyright (c) 2024 Alabama Auction Watcher Team

Permission is hereby granted to use this software for legitimate real estate
auction tracking and analysis purposes.

TERMS AND CONDITIONS:

1. PERMITTED USE: This software may be used for tracking public real estate
   auction information and performing market analysis.

2. RESTRICTIONS: Users may not use this software for:
   - Illegal activities
   - Unauthorized access to systems
   - Spamming or abuse of auction systems

3. DATA USAGE: Users are responsible for complying with all applicable data
   protection and privacy laws.

4. LIABILITY: The software is provided without warranty. The authors are not
   liable for any damages arising from use of this software.

5. UPDATES: This license applies to all versions and updates of the software.

By installing this software, you agree to these terms and conditions.
"""

        license_path = self.installer_dir / "License.rtf"
        with open(license_path, 'w', encoding='utf-8') as f:
            # Convert to RTF format
            rtf_content = r"""{\\rtf1\\ansi\\deff0 {\\fonttbl {\\f0 Times New Roman;}}
\\f0\\fs20 """ + license_content.replace('\n', '\\par\n') + "}"
            f.write(rtf_content)

        print(f"[INFO] Created license file: {license_path}")

    def build_installer(self) -> bool:
        """Build the Windows MSI installer"""
        print("[INFO] Building Windows MSI installer...")

        # Define paths
        wxs_file = self.installer_dir / "AlabamaAuctionWatcher.wxs"
        wixobj_file = self.output_dir / "temp" / "AlabamaAuctionWatcher.wixobj"
        msi_file = self.output_dir / f"{self.product_name.replace(' ', '')}-{self.product_version}.msi"

        try:
            # Step 1: Compile with candle.exe
            print("[BUILD] Compiling WiX source files...")
            candle_cmd = [
                'candle.exe',
                '-nologo',
                '-out', str(wixobj_file),
                str(wxs_file)
            ]

            result = subprocess.run(candle_cmd, capture_output=True, text=True, timeout=120)
            if result.returncode != 0:
                print(f"[ERROR] Candle compilation failed:")
                print(result.stderr)
                return False

            print("[OK] WiX compilation completed")

            # Step 2: Link with light.exe
            print("[BUILD] Linking installer components...")
            light_cmd = [
                'light.exe',
                '-nologo',
                '-ext', 'WixUIExtension',
                '-out', str(msi_file),
                str(wixobj_file)
            ]

            result = subprocess.run(light_cmd, capture_output=True, text=True, timeout=120)
            if result.returncode != 0:
                print(f"[ERROR] Light linking failed:")
                print(result.stderr)
                return False

            print(f"[SUCCESS] MSI installer created: {msi_file}")
            return True

        except subprocess.TimeoutExpired:
            print("[ERROR] Build process timed out")
            return False
        except Exception as e:
            print(f"[ERROR] Build failed: {e}")
            return False

    def create_installer_metadata(self):
        """Create installer metadata and verification files"""
        metadata = {
            "product_name": self.product_name,
            "version": self.product_version,
            "manufacturer": self.manufacturer,
            "build_date": __import__('datetime').datetime.now().isoformat(),
            "installer_type": "Windows MSI",
            "features": [
                "Desktop integration",
                "Start Menu shortcuts",
                "Registry integration",
                "URL protocol handler",
                "Automatic service startup",
                "Professional uninstaller"
            ]
        }

        metadata_file = self.output_dir / "installer_metadata.json"
        with open(metadata_file, 'w', encoding='utf-8') as f:
            __import__('json').dump(metadata, f, indent=2)

        print(f"[INFO] Created installer metadata: {metadata_file}")

    def build_all(self) -> bool:
        """Complete build process"""
        print("[TARGET] Windows MSI Installer Build System")
        print("=" * 60)

        # Check dependencies
        if not self.check_dependencies():
            print("[ERROR] Missing build dependencies")
            return False

        # Prepare source files
        if not self.prepare_source_files():
            print("[ERROR] Source file preparation failed")
            return False

        # Create supporting files
        self.create_supporting_files()

        # Build installer
        if not self.build_installer():
            print("[ERROR] Installer build failed")
            return False

        # Create metadata
        self.create_installer_metadata()

        print("\n[SUCCESS] Windows MSI installer build completed!")
        print(f"[INFO] Installer available in: {self.output_dir}")
        return True

def main():
    """Main execution function"""
    script_dir = Path(__file__).parent.parent.parent  # Go up to auction root
    output_dir = Path(__file__).parent / 'build'

    print(f"[INFO] Source directory: {script_dir}")
    print(f"[INFO] Output directory: {output_dir}")

    builder = WindowsInstallerBuilder(script_dir, output_dir)

    if builder.build_all():
        print("\n[OK] Build completed successfully!")
        sys.exit(0)
    else:
        print("\n[ERROR] Build failed!")
        sys.exit(1)

if __name__ == '__main__':
    main()