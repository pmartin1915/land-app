# Alabama Auction Watcher - Security and Code Signing

## Enterprise-Grade Digital Security System

This directory contains the comprehensive security and code signing infrastructure for Alabama Auction Watcher, ensuring trust, integrity, and compliance across all deployment platforms.

## Overview

### Security Components
- **Code Signing Manager**: Cross-platform digital signature management
- **Certificate Management**: Enterprise certificate lifecycle management
- **Security Validation**: Integrity verification and validation
- **Compliance Reporting**: Audit trails and compliance documentation
- **Trust Establishment**: Enterprise security policy compliance

### Supported Platforms
- **Windows**: Authenticode signing with SHA-256 timestamps
- **macOS**: Developer ID signing with notarization support
- **Linux**: GPG package signing for distribution trust

## Quick Start

### Initial Setup
```bash
# Navigate to security directory
cd /path/to/auction/security

# Configure certificates (edit signing_config.json)
# Install required tools for your platform
# Initialize certificate validation
python code_signing_manager.py --report
```

### Sign Application Files
```bash
# Sign Windows executable
python code_signing_manager.py --sign ../installers/windows/setup.exe --platform windows

# Sign macOS application
python code_signing_manager.py --sign ../installers/macos/AlabamaAuctionWatcher.app --platform macos

# Sign Linux package
python code_signing_manager.py --sign ../installers/linux/alabama-auction-watcher.deb --platform linux
```

### Verify Signatures
```bash
# Verify signed file
python code_signing_manager.py --verify signed_file.exe

# Generate certificate status report
python code_signing_manager.py --report > certificate_report.json
```

## Platform-Specific Implementation

### Windows Code Signing

#### Requirements
- **Windows SDK**: Contains signtool.exe for Authenticode signing
- **Code Signing Certificate**: From trusted CA (DigiCert, Sectigo, etc.)
- **Timestamp Server**: For long-term signature validity

#### Certificate Types
- **Standard Code Signing**: Basic application signing
- **EV Code Signing**: Extended validation for enhanced trust
- **Kernel Mode**: For driver signing (if needed)

#### Implementation
```bash
# Install Windows SDK
# Download from: https://developer.microsoft.com/en-us/windows/downloads/windows-sdk/

# Configure certificate in signing_config.json
{
  "windows": {
    "code_signing_cert": "C:/path/to/certificate.p12",
    "cert_password": "your_password",
    "timestamp_server": "http://timestamp.digicert.com"
  }
}

# Sign executable
signtool sign /f certificate.p12 /p password /tr http://timestamp.digicert.com /td SHA256 /fd SHA256 application.exe
```

#### Best Practices
- Use SHA-256 hash algorithm (SHA-1 deprecated)
- Always include timestamp for long-term validity
- Store certificates securely (hardware tokens recommended)
- Validate signatures before distribution

### macOS Code Signing

#### Requirements
- **Xcode Command Line Tools**: Contains codesign utility
- **Developer ID Certificate**: From Apple Developer Program
- **Apple ID**: For notarization service access

#### Certificate Types
- **Developer ID Application**: For app bundle signing
- **Developer ID Installer**: For PKG installer signing
- **Mac App Store**: For App Store distribution

#### Implementation
```bash
# Install Xcode Command Line Tools
xcode-select --install

# Configure certificates
{
  "macos": {
    "developer_id_application": "Developer ID Application: Your Name (TEAM_ID)",
    "developer_id_installer": "Developer ID Installer: Your Name (TEAM_ID)",
    "apple_id_email": "your-apple-id@example.com",
    "app_specific_password": "app-specific-password"
  }
}

# Sign application bundle
codesign --force --sign "Developer ID Application: Your Name" --options runtime --timestamp MyApp.app

# Sign installer
productbuild --sign "Developer ID Installer: Your Name" --component MyApp.app /Applications MyApp.pkg

# Notarize for Gatekeeper
xcrun altool --notarize-app --primary-bundle-id com.company.app --username your-apple-id --password app-password --file MyApp.zip
```

#### Gatekeeper Requirements
- **Hardened Runtime**: Required for macOS 10.14+
- **Notarization**: Required for Gatekeeper acceptance
- **Entitlements**: Define app capabilities and permissions

### Linux Package Signing

#### Requirements
- **GPG**: GNU Privacy Guard for package signing
- **Package Tools**: dpkg-sig (Debian), rpm (RedHat)
- **GPG Key Pair**: For package authentication

#### Supported Formats
- **Debian (.deb)**: dpkg-sig signing
- **RPM (.rpm)**: rpm --resign signing
- **AppImage**: Embedded signature support

#### Implementation
```bash
# Generate GPG key
gpg --gen-key

# Configure signing
{
  "linux": {
    "gpg_key_id": "your-key-id",
    "gpg_passphrase": "your-passphrase",
    "public_key_path": "/path/to/public.key"
  }
}

# Sign Debian package
dpkg-sig --sign builder -k your-key-id package.deb

# Sign RPM package
rpm --resign --define '_gpg_name your-key-id' package.rpm

# Export public key for distribution
gpg --export --armor your-key-id > public.key
```

#### Repository Integration
- **APT Repository**: Release file signing for Debian/Ubuntu
- **YUM/DNF Repository**: Repodata signing for RedHat/Fedora
- **Key Distribution**: Public key distribution for package managers

## Certificate Management

### Certificate Lifecycle

#### Acquisition
1. **Purchase Certificate**: From trusted Certificate Authority
2. **Generate CSR**: Certificate Signing Request with proper attributes
3. **Validation Process**: Domain/Organization/Extended validation
4. **Certificate Installation**: Import into appropriate store/keychain

#### Maintenance
- **Expiry Monitoring**: Automated alerts before expiration
- **Renewal Process**: Seamless certificate renewal workflow
- **Backup Strategy**: Secure certificate backup and recovery
- **Revocation Handling**: Certificate revocation list management

#### Security Best Practices
- **Hardware Security Modules (HSM)**: For high-security environments
- **Certificate Pinning**: Prevent man-in-the-middle attacks
- **Regular Audits**: Certificate usage and security reviews
- **Access Control**: Strict certificate access management

### Enterprise Certificate Management

#### Centralized Management
```json
{
  "enterprise_settings": {
    "certificate_server": "https://ca.company.com",
    "auto_enrollment": true,
    "centralized_revocation": true,
    "policy_enforcement": true
  }
}
```

#### Compliance Requirements
- **SOC 2 Type II**: Security controls and auditing
- **ISO 27001**: Information security management
- **NIST Framework**: Cybersecurity framework compliance
- **Industry Standards**: Sector-specific requirements

## Security Validation

### Pre-Signing Validation
```python
# Validate file integrity
def validate_file_integrity(file_path):
    # Check file hash against known good values
    # Verify file is not corrupted or tampered
    # Validate file format and structure

# Validate certificate status
def validate_certificate(cert_path):
    # Check certificate expiry
    # Verify certificate chain
    # Validate certificate usage
    # Check revocation status
```

### Post-Signing Verification
```python
# Verify signature integrity
def verify_signature(signed_file):
    # Validate cryptographic signature
    # Check timestamp validity
    # Verify certificate chain
    # Confirm signature algorithms
```

### Continuous Monitoring
- **Signature Validation**: Regular verification of deployed signatures
- **Certificate Monitoring**: Continuous certificate health checks
- **Threat Detection**: Monitoring for signature-based attacks
- **Compliance Scanning**: Automated compliance verification

## Enterprise Integration

### Active Directory Integration
```json
{
  "enterprise": {
    "ad_certificate_services": true,
    "auto_enrollment": true,
    "group_policy_management": true,
    "centralized_revocation": true
  }
}
```

### Cloud Security Integration
- **Azure Key Vault**: Certificate storage and management
- **AWS Certificate Manager**: Cloud-based certificate lifecycle
- **Google Cloud KMS**: Key management service integration
- **HashiCorp Vault**: Multi-cloud secrets management

### DevOps Integration
```yaml
# CI/CD Pipeline Integration
stages:
  - build
  - test
  - sign
  - verify
  - deploy

sign_artifacts:
  stage: sign
  script:
    - python security/code_signing_manager.py --sign build/installer.exe
    - python security/code_signing_manager.py --verify build/installer.exe
  artifacts:
    paths:
      - build/*.exe
    expire_in: 1 week
```

## Troubleshooting

### Common Issues

#### Windows Signing Issues
```bash
# Certificate not found
- Check certificate installation in Windows Certificate Store
- Verify certificate path in configuration
- Ensure certificate has private key

# Timestamp server failures
- Try alternative timestamp servers
- Check network connectivity
- Verify firewall settings

# Signature verification failures
- Check certificate expiry
- Verify certificate chain
- Validate timestamp integrity
```

#### macOS Signing Issues
```bash
# Developer ID not found
security find-identity -v -p codesigning

# Keychain access issues
security unlock-keychain login.keychain

# Notarization failures
xcrun altool --notarization-history 0 -u your-apple-id

# Gatekeeper issues
spctl --assess --verbose=4 MyApp.app
```

#### Linux Signing Issues
```bash
# GPG key not found
gpg --list-secret-keys

# Package signing failures
dpkg-sig --verify package.deb
rpm --checksig package.rpm

# Repository integration
apt-key add public.key
rpm --import public.key
```

### Debugging Tools
- **Windows**: signtool verify, certlm.msc
- **macOS**: codesign --verify, spctl --assess
- **Linux**: gpg --verify, rpm --checksig

## Security Best Practices

### Code Integrity
1. **Source Code Protection**: Secure development environments
2. **Build Pipeline Security**: Secure CI/CD with signing integration
3. **Artifact Validation**: Pre-signing integrity verification
4. **Supply Chain Security**: Third-party component validation

### Certificate Security
1. **Secure Storage**: Hardware security modules (HSM)
2. **Access Control**: Role-based certificate access
3. **Rotation Policy**: Regular certificate renewal
4. **Incident Response**: Certificate compromise procedures

### Operational Security
1. **Audit Logging**: Comprehensive signing operation logs
2. **Monitoring**: Real-time security monitoring
3. **Alerting**: Automated security incident alerts
4. **Compliance**: Regular security compliance reviews

## Compliance and Auditing

### Audit Trail
```json
{
  "timestamp": "2024-01-15T10:30:00Z",
  "operation": "sign_file",
  "file_path": "/path/to/installer.exe",
  "certificate_thumbprint": "ABC123...",
  "user": "build-service",
  "platform": "windows",
  "success": true,
  "hash_before": "SHA256:DEF456...",
  "hash_after": "SHA256:GHI789..."
}
```

### Compliance Reports
- **Certificate Inventory**: Current certificate status
- **Signing Activity**: Historical signing operations
- **Security Incidents**: Security-related events
- **Policy Compliance**: Adherence to signing policies

### Regulatory Requirements
- **GDPR**: Data protection in certificate handling
- **SOX**: Financial reporting system integrity
- **HIPAA**: Healthcare application security (if applicable)
- **FedRAMP**: Federal cloud security requirements

---

**Security Level**: Enterprise Grade
**Compliance**: SOC 2, ISO 27001, NIST Compatible
**Supported Platforms**: Windows, macOS, Linux
**Certificate Types**: Code Signing, EV Code Signing, Developer ID
**Update Frequency**: Continuous monitoring with quarterly reviews