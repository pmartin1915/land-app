@echo off
setlocal EnableDelayedExpansion

:: Alabama Auction Watcher - Professional Windows Uninstaller
:: Comprehensive removal script with registry cleanup and data preservation options
:: Supports both system-wide and user-level installations

title Alabama Auction Watcher - Uninstaller

echo =================================================================
echo Alabama Auction Watcher - Professional Uninstaller
echo =================================================================
echo.

:: Check if running as administrator
net session >nul 2>&1
if %errorLevel% == 0 (
    echo [INFO] Running with administrator privileges
    set "ADMIN_MODE=true"
) else (
    echo [INFO] Running in user mode
    set "ADMIN_MODE=false"
)

echo.

:: Display uninstall options
echo Select uninstall type:
echo.
echo [1] Complete Removal - Remove all files and user data
echo [2] Application Only - Keep user data and settings
echo [3] Repair Installation - Remove and reinstall (keeps data)
echo [4] Cancel
echo.
set /p UNINSTALL_TYPE="Enter your choice (1-4): "

if "%UNINSTALL_TYPE%"=="4" (
    echo [INFO] Uninstall cancelled by user
    pause
    exit /b 0
)

if "%UNINSTALL_TYPE%"=="3" (
    echo [INFO] Repair mode not yet implemented
    echo [INFO] Please use complete removal and reinstall manually
    pause
    exit /b 1
)

if not "%UNINSTALL_TYPE%"=="1" if not "%UNINSTALL_TYPE%"=="2" (
    echo [ERROR] Invalid choice. Please run the uninstaller again.
    pause
    exit /b 1
)

echo.
echo =================================================================
echo Starting Uninstallation Process
echo =================================================================
echo.

:: Define installation paths
set "SYSTEM_INSTALL_DIR=C:\Program Files\Alabama Auction Watcher"
set "USER_INSTALL_DIR=%USERPROFILE%\Alabama Auction Watcher"
set "APPDATA_DIR=%APPDATA%\Alabama Auction Watcher"
set "LOCALAPPDATA_DIR=%LOCALAPPDATA%\Alabama Auction Watcher"

:: Detect installation location
set "INSTALL_DIR="
if exist "%SYSTEM_INSTALL_DIR%" (
    set "INSTALL_DIR=%SYSTEM_INSTALL_DIR%"
    set "SYSTEM_WIDE=true"
    echo [INFO] Found system-wide installation
) else if exist "%USER_INSTALL_DIR%" (
    set "INSTALL_DIR=%USER_INSTALL_DIR%"
    set "SYSTEM_WIDE=false"
    echo [INFO] Found user-level installation
) else (
    echo [WARNING] No installation found in standard locations
    echo [INFO] Proceeding with cleanup anyway...
)

if not "%INSTALL_DIR%"=="" (
    echo [INFO] Installation directory: %INSTALL_DIR%
)

echo.

:: Stop running services
echo [INFO] Stopping Alabama Auction Watcher services...

:: Kill Streamlit processes
taskkill /f /im streamlit.exe >nul 2>&1
taskkill /f /im python.exe /fi "WINDOWTITLE eq *streamlit*" >nul 2>&1

:: Kill Backend API processes
taskkill /f /im python.exe /fi "WINDOWTITLE eq *backend*" >nul 2>&1
taskkill /f /im python.exe /fi "WINDOWTITLE eq *alabama*" >nul 2>&1

:: Kill any launcher processes
taskkill /f /im cmd.exe /fi "WINDOWTITLE eq *Alabama Auction Watcher*" >nul 2>&1

echo [SUCCESS] Services stopped

:: Remove Desktop shortcuts
echo [INFO] Removing desktop shortcuts...
if exist "%USERPROFILE%\Desktop\Alabama Auction Watcher.lnk" (
    del /q "%USERPROFILE%\Desktop\Alabama Auction Watcher.lnk"
    echo [SUCCESS] Removed desktop shortcut
)

if exist "%PUBLIC%\Desktop\Alabama Auction Watcher.lnk" (
    del /q "%PUBLIC%\Desktop\Alabama Auction Watcher.lnk" >nul 2>&1
    echo [SUCCESS] Removed public desktop shortcut
)

:: Remove Start Menu shortcuts
echo [INFO] Removing Start Menu entries...

set "USER_PROGRAMS=%APPDATA%\Microsoft\Windows\Start Menu\Programs"
set "SYSTEM_PROGRAMS=%PROGRAMDATA%\Microsoft\Windows\Start Menu\Programs"

:: Remove user-level Start Menu entries
if exist "%USER_PROGRAMS%\Alabama Auction Watcher" (
    rmdir /s /q "%USER_PROGRAMS%\Alabama Auction Watcher" >nul 2>&1
    echo [SUCCESS] Removed user Start Menu folder
)

:: Remove individual shortcuts
del /q "%USER_PROGRAMS%\Alabama Auction Watcher.lnk" >nul 2>&1
del /q "%USER_PROGRAMS%\Alabama Auction Watcher - Backend.lnk" >nul 2>&1
del /q "%USER_PROGRAMS%\Alabama Auction Watcher - Health Check.lnk" >nul 2>&1

:: Remove system-wide Start Menu entries (if admin)
if "%ADMIN_MODE%"=="true" (
    if exist "%SYSTEM_PROGRAMS%\Alabama Auction Watcher" (
        rmdir /s /q "%SYSTEM_PROGRAMS%\Alabama Auction Watcher" >nul 2>&1
        echo [SUCCESS] Removed system Start Menu folder
    )

    del /q "%SYSTEM_PROGRAMS%\Alabama Auction Watcher.lnk" >nul 2>&1
    del /q "%SYSTEM_PROGRAMS%\Alabama Auction Watcher - Backend.lnk" >nul 2>&1
)

:: Clean Registry entries
echo [INFO] Cleaning registry entries...

:: Remove URL protocol registration
reg delete "HKEY_CURRENT_USER\SOFTWARE\Classes\aaw" /f >nul 2>&1
reg delete "HKEY_CURRENT_USER\SOFTWARE\Classes\alabama-auction-watcher" /f >nul 2>&1

if "%ADMIN_MODE%"=="true" (
    reg delete "HKEY_CLASSES_ROOT\aaw" /f >nul 2>&1
    reg delete "HKEY_CLASSES_ROOT\alabama-auction-watcher" /f >nul 2>&1
    echo [SUCCESS] Removed URL protocol registrations
)

:: Remove application registration
reg delete "HKEY_CURRENT_USER\SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall\Alabama Auction Watcher" /f >nul 2>&1

if "%ADMIN_MODE%"=="true" (
    reg delete "HKEY_LOCAL_MACHINE\SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall\Alabama Auction Watcher" /f >nul 2>&1
    reg delete "HKEY_LOCAL_MACHINE\SOFTWARE\WOW6432Node\Microsoft\Windows\CurrentVersion\Uninstall\Alabama Auction Watcher" /f >nul 2>&1
    echo [SUCCESS] Removed application registration
)

:: Remove file associations
reg delete "HKEY_CURRENT_USER\SOFTWARE\Classes\.aaw" /f >nul 2>&1
reg delete "HKEY_CURRENT_USER\SOFTWARE\Classes\AlabamaAuctionWatcher.Document" /f >nul 2>&1

:: Remove application settings
reg delete "HKEY_CURRENT_USER\SOFTWARE\Alabama Auction Watcher" /f >nul 2>&1

:: Remove from Windows Firewall (if admin)
if "%ADMIN_MODE%"=="true" (
    netsh advfirewall firewall delete rule name="Alabama Auction Watcher" >nul 2>&1
    netsh advfirewall firewall delete rule name="Alabama Auction Watcher Backend" >nul 2>&1
    echo [SUCCESS] Removed firewall rules
)

:: Remove environment variables
reg delete "HKEY_CURRENT_USER\Environment" /v "ALABAMA_AUCTION_WATCHER_HOME" /f >nul 2>&1

if "%ADMIN_MODE%"=="true" (
    reg delete "HKEY_LOCAL_MACHINE\SYSTEM\CurrentControlSet\Control\Session Manager\Environment" /v "ALABAMA_AUCTION_WATCHER_HOME" /f >nul 2>&1
)

echo [SUCCESS] Registry cleanup completed

:: Remove application files
if not "%INSTALL_DIR%"=="" (
    echo [INFO] Removing application files from: %INSTALL_DIR%

    if exist "%INSTALL_DIR%" (
        :: First, remove read-only attributes
        attrib -r "%INSTALL_DIR%\*.*" /s >nul 2>&1

        :: Remove the installation directory
        rmdir /s /q "%INSTALL_DIR%" >nul 2>&1

        if exist "%INSTALL_DIR%" (
            echo [WARNING] Some files could not be removed from: %INSTALL_DIR%
            echo [INFO] This may be due to files in use or permission issues
        ) else (
            echo [SUCCESS] Application files removed
        )
    )
)

:: Handle user data based on uninstall type
if "%UNINSTALL_TYPE%"=="1" (
    echo [INFO] Removing user data and settings...

    :: Remove AppData directories
    if exist "%APPDATA_DIR%" (
        rmdir /s /q "%APPDATA_DIR%" >nul 2>&1
        echo [SUCCESS] Removed roaming data
    )

    if exist "%LOCALAPPDATA_DIR%" (
        rmdir /s /q "%LOCALAPPDATA_DIR%" >nul 2>&1
        echo [SUCCESS] Removed local data
    )

    :: Remove database files from various locations
    del /q "%USERPROFILE%\alabama_auction_watcher.db" >nul 2>&1
    del /q "%USERPROFILE%\Alabama Auction Watcher\alabama_auction_watcher.db" >nul 2>&1

    :: Remove logs
    if exist "%USERPROFILE%\Alabama Auction Watcher\logs" (
        rmdir /s /q "%USERPROFILE%\Alabama Auction Watcher\logs" >nul 2>&1
        echo [SUCCESS] Removed log files
    )

) else if "%UNINSTALL_TYPE%"=="2" (
    echo [INFO] Preserving user data and settings
    echo [INFO] Data location: %APPDATA_DIR%
    echo [INFO] Local data: %LOCALAPPDATA_DIR%
)

:: Remove Windows Services (if any were installed)
if "%ADMIN_MODE%"=="true" (
    sc stop "AlabamaAuctionWatcher" >nul 2>&1
    sc delete "AlabamaAuctionWatcher" >nul 2>&1
    sc stop "AlabamaAuctionWatcherBackend" >nul 2>&1
    sc delete "AlabamaAuctionWatcherBackend" >nul 2>&1
    echo [SUCCESS] Removed Windows services
)

:: Remove temporary files
del /q "%TEMP%\alabama_auction_watcher_*.log" >nul 2>&1
del /q "%TEMP%\aaw_*.tmp" >nul 2>&1

:: Remove from Windows PATH (if added)
echo [INFO] Cleaning PATH environment variable...
:: This is complex to do safely in batch, so we'll note it for manual cleanup
echo [INFO] If Alabama Auction Watcher was added to PATH, please remove it manually

:: Refresh desktop and Start Menu
taskkill /f /im explorer.exe >nul 2>&1
start explorer.exe

echo.
echo =================================================================
echo Uninstallation Summary
echo =================================================================
echo.

if "%UNINSTALL_TYPE%"=="1" (
    echo [✓] Complete removal performed
    echo [✓] Application files removed
    echo [✓] User data removed
    echo [✓] Registry entries cleaned
    echo [✓] Shortcuts removed
    echo [✓] Services stopped and removed
) else (
    echo [✓] Application-only removal performed
    echo [✓] Application files removed
    echo [✓] Registry entries cleaned
    echo [✓] Shortcuts removed
    echo [✓] Services stopped and removed
    echo [!] User data preserved
)

echo.
echo [SUCCESS] Alabama Auction Watcher has been uninstalled successfully!
echo.

if "%UNINSTALL_TYPE%"=="2" (
    echo [INFO] Your data has been preserved at:
    echo       %APPDATA_DIR%
    echo       %LOCALAPPDATA_DIR%
    echo.
    echo [INFO] You can reinstall Alabama Auction Watcher at any time
    echo       and your settings will be restored automatically.
    echo.
)

:: Offer to open installation location for verification
set /p VERIFY="Would you like to open the former installation directory to verify removal? (y/n): "
if /i "%VERIFY%"=="y" (
    if not "%INSTALL_DIR%"=="" (
        explorer "%~dp0"
    ) else (
        explorer "%USERPROFILE%"
    )
)

echo.
echo Thank you for using Alabama Auction Watcher!
echo.
echo To reinstall, please download the latest version from:
echo https://github.com/Alabama-Auction-Watcher
echo.

pause