#!/usr/bin/env python3
"""
Alabama Auction Watcher - Code Signing Manager
Enterprise-grade digital signing and certificate management system
"""

import os
import sys
import subprocess
import tempfile
from pathlib import Path
from typing import Dict, List, Optional, Tuple
import json
import hashlib
import base64
from datetime import datetime, timedelta
import shutil

class CodeSigningManager:
    """Professional code signing and certificate management"""

    def __init__(self, config_file: Optional[Path] = None):
        self.config_file = config_file or Path(__file__).parent / "signing_config.json"
        self.config = self.load_configuration()

        # Certificate paths and settings
        self.cert_dir = Path(__file__).parent / "certificates"
        self.cert_dir.mkdir(exist_ok=True)

        # Platform-specific signing tools
        self.signing_tools = self.detect_signing_tools()

        # Supported file types for signing
        self.signable_extensions = {
            'windows': ['.exe', '.msi', '.dll', '.cab', '.ocx'],
            'macos': ['.app', '.pkg', '.dmg', '.kext'],
            'linux': ['.deb', '.rpm', '.appimage']
        }

    def load_configuration(self) -> Dict:
        """Load signing configuration"""
        default_config = {
            "certificates": {
                "windows": {
                    "code_signing_cert": "",
                    "timestamp_server": "http://timestamp.digicert.com",
                    "cert_password": "",
                    "store_location": "CurrentUser",
                    "cert_thumbprint": ""
                },
                "macos": {
                    "developer_id_application": "",
                    "developer_id_installer": "",
                    "apple_id_email": "",
                    "app_specific_password": "",
                    "team_id": "",
                    "keychain": "login"
                },
                "linux": {
                    "gpg_key_id": "",
                    "gpg_passphrase": "",
                    "signing_key_path": "",
                    "public_key_path": ""
                }
            },
            "security_settings": {
                "verify_before_signing": True,
                "require_secure_timestamp": True,
                "hash_algorithm": "SHA256",
                "minimum_key_size": 2048,
                "certificate_validation": True
            },
            "enterprise_settings": {
                "require_approval": False,
                "approval_email": "",
                "audit_logging": True,
                "backup_certificates": True
            }
        }

        if self.config_file.exists():
            try:
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    user_config = json.load(f)
                    # Merge with defaults
                    self._deep_merge(default_config, user_config)
            except Exception as e:
                self.log_message(f"ERROR: Failed to load config: {e}")

        return default_config

    def _deep_merge(self, base_dict: Dict, update_dict: Dict):
        """Deep merge configuration dictionaries"""
        for key, value in update_dict.items():
            if key in base_dict and isinstance(base_dict[key], dict) and isinstance(value, dict):
                self._deep_merge(base_dict[key], value)
            else:
                base_dict[key] = value

    def save_configuration(self):
        """Save current configuration"""
        try:
            self.config_file.parent.mkdir(parents=True, exist_ok=True)
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(self.config, f, indent=2)
        except Exception as e:
            self.log_message(f"ERROR: Failed to save config: {e}")

    def log_message(self, message: str):
        """Log signing operations"""
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        log_entry = f"[{timestamp}] {message}"

        print(log_entry)

        # Log to file if audit logging is enabled
        if self.config.get("enterprise_settings", {}).get("audit_logging", False):
            log_file = Path(__file__).parent / "logs" / "signing_audit.log"
            log_file.parent.mkdir(exist_ok=True)

            try:
                with open(log_file, 'a', encoding='utf-8') as f:
                    f.write(log_entry + '\n')
            except Exception:
                pass  # Don't fail if logging fails

    def detect_signing_tools(self) -> Dict[str, Dict[str, Optional[str]]]:
        """Detect available code signing tools"""
        tools = {
            'windows': {
                'signtool': None,
                'mage': None,
                'makecert': None
            },
            'macos': {
                'codesign': None,
                'productbuild': None,
                'xcrun': None,
                'altool': None
            },
            'linux': {
                'gpg': None,
                'dpkg-sig': None,
                'rpm': None
            }
        }

        # Windows signing tools
        if sys.platform.startswith('win'):
            # Look for Windows SDK tools
            sdk_paths = [
                "C:\\Program Files (x86)\\Windows Kits\\10\\bin\\*\\x64",
                "C:\\Program Files\\Microsoft SDKs\\Windows\\*\\bin",
            ]

            for tool in tools['windows']:
                tool_path = shutil.which(f"{tool}.exe")
                if tool_path:
                    tools['windows'][tool] = tool_path

        # macOS signing tools
        elif sys.platform == 'darwin':
            for tool in tools['macos']:
                tool_path = shutil.which(tool)
                if tool_path:
                    tools['macos'][tool] = tool_path

        # Linux signing tools
        else:
            for tool in tools['linux']:
                tool_path = shutil.which(tool)
                if tool_path:
                    tools['linux'][tool] = tool_path

        return tools

    def validate_certificate(self, platform: str) -> Tuple[bool, str]:
        """Validate certificate configuration for platform"""
        cert_config = self.config.get("certificates", {}).get(platform, {})

        if platform == 'windows':
            cert_path = cert_config.get('code_signing_cert')
            if not cert_path:
                return False, "Windows code signing certificate not configured"

            if not Path(cert_path).exists():
                return False, f"Certificate file not found: {cert_path}"

            # Validate certificate using certutil
            if self.signing_tools['windows']['signtool']:
                try:
                    result = subprocess.run([
                        'certutil', '-verify', '-urlfetch', cert_path
                    ], capture_output=True, text=True)

                    if result.returncode != 0:
                        return False, f"Certificate validation failed: {result.stderr}"

                except Exception as e:
                    return False, f"Certificate validation error: {e}"

        elif platform == 'macos':
            dev_id = cert_config.get('developer_id_application')
            if not dev_id:
                return False, "macOS Developer ID not configured"

            # Check if certificate exists in keychain
            try:
                result = subprocess.run([
                    'security', 'find-identity', '-v', '-p', 'codesigning'
                ], capture_output=True, text=True)

                if dev_id not in result.stdout:
                    return False, f"Developer ID certificate not found in keychain: {dev_id}"

            except Exception as e:
                return False, f"Keychain validation error: {e}"

        elif platform == 'linux':
            gpg_key = cert_config.get('gpg_key_id')
            if not gpg_key:
                return False, "GPG signing key not configured"

            # Verify GPG key exists
            try:
                result = subprocess.run([
                    'gpg', '--list-secret-keys', gpg_key
                ], capture_output=True, text=True)

                if result.returncode != 0:
                    return False, f"GPG key not found: {gpg_key}"

            except Exception as e:
                return False, f"GPG validation error: {e}"

        return True, "Certificate validation successful"

    def sign_windows_file(self, file_path: Path) -> Tuple[bool, str]:
        """Sign Windows executable or installer"""
        if not self.signing_tools['windows']['signtool']:
            return False, "signtool.exe not found - install Windows SDK"

        cert_config = self.config["certificates"]["windows"]

        # Validate certificate first
        valid, message = self.validate_certificate('windows')
        if not valid:
            return False, f"Certificate validation failed: {message}"

        try:
            # Build signtool command
            cmd = [
                self.signing_tools['windows']['signtool'],
                'sign',
                '/fd', self.config["security_settings"]["hash_algorithm"],
                '/tr', cert_config["timestamp_server"],
                '/td', self.config["security_settings"]["hash_algorithm"]
            ]

            # Add certificate information
            if cert_config.get("cert_thumbprint"):
                cmd.extend(['/sha1', cert_config["cert_thumbprint"]])
            elif cert_config.get("code_signing_cert"):
                cmd.extend(['/f', cert_config["code_signing_cert"]])
                if cert_config.get("cert_password"):
                    cmd.extend(['/p', cert_config["cert_password"]])

            # Add file to sign
            cmd.append(str(file_path))

            # Execute signing
            self.log_message(f"Signing Windows file: {file_path}")
            result = subprocess.run(cmd, capture_output=True, text=True)

            if result.returncode == 0:
                self.log_message(f"Successfully signed: {file_path}")
                return True, "File signed successfully"
            else:
                error_msg = f"Signing failed: {result.stderr}"
                self.log_message(f"ERROR: {error_msg}")
                return False, error_msg

        except Exception as e:
            error_msg = f"Signing error: {e}"
            self.log_message(f"ERROR: {error_msg}")
            return False, error_msg

    def sign_macos_app(self, app_path: Path) -> Tuple[bool, str]:
        """Sign macOS application bundle"""
        if not self.signing_tools['macos']['codesign']:
            return False, "codesign not found - install Xcode Command Line Tools"

        cert_config = self.config["certificates"]["macos"]

        # Validate certificate first
        valid, message = self.validate_certificate('macos')
        if not valid:
            return False, f"Certificate validation failed: {message}"

        try:
            developer_id = cert_config["developer_id_application"]

            # Sign the application
            cmd = [
                'codesign',
                '--force',
                '--verify',
                '--verbose',
                '--sign', developer_id,
                '--options', 'runtime',
                '--timestamp'
            ]

            # Add entitlements if they exist
            entitlements_path = app_path.parent / "entitlements.plist"
            if entitlements_path.exists():
                cmd.extend(['--entitlements', str(entitlements_path)])

            cmd.append(str(app_path))

            self.log_message(f"Signing macOS app: {app_path}")
            result = subprocess.run(cmd, capture_output=True, text=True)

            if result.returncode == 0:
                self.log_message(f"Successfully signed: {app_path}")

                # Verify signature
                verify_result = self.verify_macos_signature(app_path)
                if verify_result[0]:
                    return True, "App signed and verified successfully"
                else:
                    return False, f"Signing succeeded but verification failed: {verify_result[1]}"
            else:
                error_msg = f"Signing failed: {result.stderr}"
                self.log_message(f"ERROR: {error_msg}")
                return False, error_msg

        except Exception as e:
            error_msg = f"Signing error: {e}"
            self.log_message(f"ERROR: {error_msg}")
            return False, error_msg

    def sign_macos_installer(self, pkg_path: Path) -> Tuple[bool, str]:
        """Sign macOS installer package"""
        if not self.signing_tools['macos']['productbuild']:
            return False, "productbuild not found"

        cert_config = self.config["certificates"]["macos"]
        installer_cert = cert_config.get("developer_id_installer")

        if not installer_cert:
            return False, "Developer ID Installer certificate not configured"

        try:
            # Create signed installer
            temp_pkg = pkg_path.with_suffix('.unsigned.pkg')
            shutil.move(pkg_path, temp_pkg)

            cmd = [
                'productbuild',
                '--sign', installer_cert,
                '--package', str(temp_pkg),
                str(pkg_path)
            ]

            self.log_message(f"Signing macOS installer: {pkg_path}")
            result = subprocess.run(cmd, capture_output=True, text=True)

            # Clean up temporary file
            temp_pkg.unlink()

            if result.returncode == 0:
                self.log_message(f"Successfully signed installer: {pkg_path}")
                return True, "Installer signed successfully"
            else:
                error_msg = f"Installer signing failed: {result.stderr}"
                self.log_message(f"ERROR: {error_msg}")
                return False, error_msg

        except Exception as e:
            error_msg = f"Installer signing error: {e}"
            self.log_message(f"ERROR: {error_msg}")
            return False, error_msg

    def notarize_macos_app(self, app_path: Path) -> Tuple[bool, str]:
        """Submit macOS app for notarization"""
        if not self.signing_tools['macos']['xcrun']:
            return False, "xcrun not found"

        cert_config = self.config["certificates"]["macos"]
        apple_id = cert_config.get("apple_id_email")
        app_password = cert_config.get("app_specific_password")

        if not apple_id or not app_password:
            return False, "Apple ID credentials not configured for notarization"

        try:
            # Create zip archive for notarization
            zip_path = app_path.with_suffix('.zip')

            self.log_message(f"Creating archive for notarization: {zip_path}")
            subprocess.run(['zip', '-r', str(zip_path), str(app_path)], check=True)

            # Submit for notarization
            cmd = [
                'xcrun', 'altool',
                '--notarize-app',
                '--primary-bundle-id', f'com.alabamaauctionwatcher.{app_path.stem}',
                '--username', apple_id,
                '--password', app_password,
                '--file', str(zip_path)
            ]

            self.log_message(f"Submitting for notarization: {app_path}")
            result = subprocess.run(cmd, capture_output=True, text=True)

            # Clean up zip file
            zip_path.unlink()

            if result.returncode == 0:
                # Extract request UUID from output
                output = result.stdout
                if "RequestUUID" in output:
                    uuid_line = [line for line in output.split('\n') if 'RequestUUID' in line][0]
                    request_uuid = uuid_line.split('=')[1].strip()

                    self.log_message(f"Notarization submitted. Request UUID: {request_uuid}")
                    return True, f"Notarization submitted successfully. UUID: {request_uuid}"
                else:
                    return True, "Notarization submitted successfully"
            else:
                error_msg = f"Notarization submission failed: {result.stderr}"
                self.log_message(f"ERROR: {error_msg}")
                return False, error_msg

        except Exception as e:
            error_msg = f"Notarization error: {e}"
            self.log_message(f"ERROR: {error_msg}")
            return False, error_msg

    def sign_linux_package(self, package_path: Path) -> Tuple[bool, str]:
        """Sign Linux package (.deb or .rpm)"""
        cert_config = self.config["certificates"]["linux"]
        gpg_key = cert_config.get("gpg_key_id")

        if not gpg_key:
            return False, "GPG key not configured for Linux package signing"

        try:
            if package_path.suffix == '.deb':
                return self._sign_deb_package(package_path)
            elif package_path.suffix == '.rpm':
                return self._sign_rpm_package(package_path)
            else:
                return False, f"Unsupported package format: {package_path.suffix}"

        except Exception as e:
            error_msg = f"Package signing error: {e}"
            self.log_message(f"ERROR: {error_msg}")
            return False, error_msg

    def _sign_deb_package(self, deb_path: Path) -> Tuple[bool, str]:
        """Sign Debian package"""
        if not self.signing_tools['linux']['dpkg-sig']:
            return False, "dpkg-sig not found - install dpkg-sig package"

        cert_config = self.config["certificates"]["linux"]
        gpg_key = cert_config["gpg_key_id"]

        try:
            cmd = [
                'dpkg-sig',
                '--sign', 'builder',
                '-k', gpg_key,
                str(deb_path)
            ]

            self.log_message(f"Signing Debian package: {deb_path}")
            result = subprocess.run(cmd, capture_output=True, text=True)

            if result.returncode == 0:
                self.log_message(f"Successfully signed: {deb_path}")
                return True, "Debian package signed successfully"
            else:
                error_msg = f"Debian signing failed: {result.stderr}"
                self.log_message(f"ERROR: {error_msg}")
                return False, error_msg

        except Exception as e:
            return False, f"Debian signing error: {e}"

    def _sign_rpm_package(self, rpm_path: Path) -> Tuple[bool, str]:
        """Sign RPM package"""
        if not self.signing_tools['linux']['rpm']:
            return False, "rpm not found"

        cert_config = self.config["certificates"]["linux"]
        gpg_key = cert_config["gpg_key_id"]

        try:
            cmd = [
                'rpm',
                '--resign',
                '--define', f'_gpg_name {gpg_key}',
                str(rpm_path)
            ]

            self.log_message(f"Signing RPM package: {rpm_path}")
            result = subprocess.run(cmd, capture_output=True, text=True)

            if result.returncode == 0:
                self.log_message(f"Successfully signed: {rpm_path}")
                return True, "RPM package signed successfully"
            else:
                error_msg = f"RPM signing failed: {result.stderr}"
                self.log_message(f"ERROR: {error_msg}")
                return False, error_msg

        except Exception as e:
            return False, f"RPM signing error: {e}"

    def verify_windows_signature(self, file_path: Path) -> Tuple[bool, str]:
        """Verify Windows code signature"""
        if not self.signing_tools['windows']['signtool']:
            return False, "signtool.exe not found"

        try:
            cmd = [
                self.signing_tools['windows']['signtool'],
                'verify',
                '/pa', '/v',
                str(file_path)
            ]

            result = subprocess.run(cmd, capture_output=True, text=True)

            if result.returncode == 0:
                return True, "Windows signature verified successfully"
            else:
                return False, f"Signature verification failed: {result.stderr}"

        except Exception as e:
            return False, f"Verification error: {e}"

    def verify_macos_signature(self, app_path: Path) -> Tuple[bool, str]:
        """Verify macOS code signature"""
        if not self.signing_tools['macos']['codesign']:
            return False, "codesign not found"

        try:
            cmd = [
                'codesign',
                '--verify',
                '--deep',
                '--verbose=2',
                str(app_path)
            ]

            result = subprocess.run(cmd, capture_output=True, text=True)

            if result.returncode == 0:
                return True, "macOS signature verified successfully"
            else:
                return False, f"Signature verification failed: {result.stderr}"

        except Exception as e:
            return False, f"Verification error: {e}"

    def verify_linux_signature(self, package_path: Path) -> Tuple[bool, str]:
        """Verify Linux package signature"""
        try:
            if package_path.suffix == '.deb':
                if not self.signing_tools['linux']['dpkg-sig']:
                    return False, "dpkg-sig not found"

                cmd = ['dpkg-sig', '--verify', str(package_path)]
                result = subprocess.run(cmd, capture_output=True, text=True)

                if result.returncode == 0:
                    return True, "Debian package signature verified"
                else:
                    return False, f"Verification failed: {result.stderr}"

            elif package_path.suffix == '.rpm':
                cmd = ['rpm', '--checksig', str(package_path)]
                result = subprocess.run(cmd, capture_output=True, text=True)

                if 'OK' in result.stdout:
                    return True, "RPM package signature verified"
                else:
                    return False, f"Verification failed: {result.stdout}"

            else:
                return False, f"Unsupported package format: {package_path.suffix}"

        except Exception as e:
            return False, f"Verification error: {e}"

    def sign_file(self, file_path: Path, platform: Optional[str] = None) -> Tuple[bool, str]:
        """Sign file for specified platform"""
        if not file_path.exists():
            return False, f"File not found: {file_path}"

        # Auto-detect platform if not specified
        if platform is None:
            if sys.platform.startswith('win'):
                platform = 'windows'
            elif sys.platform == 'darwin':
                platform = 'macos'
            else:
                platform = 'linux'

        # Check if file type is signable for this platform
        file_ext = file_path.suffix.lower()
        if file_ext not in self.signable_extensions.get(platform, []):
            return False, f"File type {file_ext} not signable for {platform}"

        # Perform platform-specific signing
        if platform == 'windows':
            return self.sign_windows_file(file_path)
        elif platform == 'macos':
            if file_ext == '.app':
                return self.sign_macos_app(file_path)
            elif file_ext == '.pkg':
                return self.sign_macos_installer(file_path)
            else:
                return False, f"Unsupported macOS file type: {file_ext}"
        elif platform == 'linux':
            return self.sign_linux_package(file_path)
        else:
            return False, f"Unsupported platform: {platform}"

    def create_certificate_report(self) -> Dict:
        """Create certificate status report"""
        report = {
            "timestamp": datetime.now().isoformat(),
            "platforms": {},
            "signing_tools": self.signing_tools,
            "configuration_status": "loaded"
        }

        # Check each platform
        for platform in ['windows', 'macos', 'linux']:
            valid, message = self.validate_certificate(platform)
            report["platforms"][platform] = {
                "certificate_valid": valid,
                "status_message": message,
                "tools_available": any(self.signing_tools.get(platform, {}).values())
            }

        return report

def main():
    """Main code signing execution"""
    import argparse

    parser = argparse.ArgumentParser(description='Alabama Auction Watcher Code Signing Manager')
    parser.add_argument('--sign', type=Path, help='File to sign')
    parser.add_argument('--verify', type=Path, help='File to verify')
    parser.add_argument('--platform', choices=['windows', 'macos', 'linux'], help='Target platform')
    parser.add_argument('--report', action='store_true', help='Generate certificate report')
    parser.add_argument('--config', type=Path, help='Configuration file path')

    args = parser.parse_args()

    signer = CodeSigningManager(args.config)

    if args.report:
        report = signer.create_certificate_report()
        print(json.dumps(report, indent=2))

    elif args.sign:
        success, message = signer.sign_file(args.sign, args.platform)
        if success:
            print(f"SUCCESS: {message}")
            sys.exit(0)
        else:
            print(f"ERROR: {message}")
            sys.exit(1)

    elif args.verify:
        platform = args.platform or ('windows' if sys.platform.startswith('win') else
                                   'macos' if sys.platform == 'darwin' else 'linux')

        if platform == 'windows':
            success, message = signer.verify_windows_signature(args.verify)
        elif platform == 'macos':
            success, message = signer.verify_macos_signature(args.verify)
        else:
            success, message = signer.verify_linux_signature(args.verify)

        if success:
            print(f"VERIFIED: {message}")
            sys.exit(0)
        else:
            print(f"VERIFICATION FAILED: {message}")
            sys.exit(1)

    else:
        parser.print_help()

if __name__ == '__main__':
    main()