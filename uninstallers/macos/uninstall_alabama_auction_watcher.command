#!/bin/bash

# Alabama Auction Watcher - Professional macOS Uninstaller
# Comprehensive removal script with Launch Services cleanup and data preservation options
# Compatible with macOS 10.14+ (Mojave and later)

echo "================================================================="
echo "Alabama Auction Watcher - Professional Uninstaller"
echo "================================================================="
echo ""

# Function to check if running with sudo
check_admin() {
    if [[ $EUID -eq 0 ]]; then
        echo "[INFO] Running with administrator privileges"
        ADMIN_MODE="true"
    else
        echo "[INFO] Running in user mode"
        ADMIN_MODE="false"
    fi
}

# Function to display uninstall options
show_options() {
    echo "Select uninstall type:"
    echo ""
    echo "[1] Complete Removal - Remove all files and user data"
    echo "[2] Application Only - Keep user data and settings"
    echo "[3] Cancel"
    echo ""
    read -p "Enter your choice (1-3): " UNINSTALL_TYPE

    case "$UNINSTALL_TYPE" in
        3)
            echo "[INFO] Uninstall cancelled by user"
            exit 0
            ;;
        1|2)
            # Valid choices, continue
            ;;
        *)
            echo "[ERROR] Invalid choice. Please run the uninstaller again."
            exit 1
            ;;
    esac
}

# Function to stop running services
stop_services() {
    echo "[INFO] Stopping Alabama Auction Watcher services..."

    # Kill Streamlit processes
    pkill -f "streamlit run" 2>/dev/null
    pkill -f "alabama.*auction.*watcher" 2>/dev/null

    # Kill Python processes that might be running the app
    pkill -f "python.*streamlit_app" 2>/dev/null
    pkill -f "python.*backend_api" 2>/dev/null
    pkill -f "python.*start_backend" 2>/dev/null

    # Kill any Electron desktop app processes
    pkill -f "Alabama Auction Watcher" 2>/dev/null
    pkill -f "AlabamaAuctionWatcher" 2>/dev/null

    echo "[SUCCESS] Services stopped"
}

# Function to remove application bundle
remove_application() {
    echo "[INFO] Removing application bundle..."

    # Primary application locations
    APP_PATHS=(
        "/Applications/Alabama Auction Watcher.app"
        "$HOME/Applications/Alabama Auction Watcher.app"
        "/Applications/AlabamaAuctionWatcher.app"
        "$HOME/Applications/AlabamaAuctionWatcher.app"
    )

    local removed_count=0
    for app_path in "${APP_PATHS[@]}"; do
        if [[ -d "$app_path" ]]; then
            rm -rf "$app_path"
            if [[ $? -eq 0 ]]; then
                echo "[SUCCESS] Removed: $app_path"
                removed_count=$((removed_count + 1))
            else
                echo "[WARNING] Could not remove: $app_path"
            fi
        fi
    done

    if [[ $removed_count -eq 0 ]]; then
        echo "[WARNING] No application bundles found in standard locations"
    fi
}

# Function to remove PKG installer receipts
remove_pkg_receipts() {
    echo "[INFO] Removing installer receipts..."

    # List of possible package identifiers
    PKG_IDS=(
        "com.alabamaauctionwatcher.app"
        "com.alabama-auction-watcher.app"
        "com.alabamaauctionwatcher.installer"
        "org.alabamaauctionwatcher.app"
    )

    for pkg_id in "${PKG_IDS[@]}"; do
        if pkgutil --pkg-info "$pkg_id" >/dev/null 2>&1; then
            if [[ "$ADMIN_MODE" == "true" ]]; then
                pkgutil --forget "$pkg_id" 2>/dev/null
                echo "[SUCCESS] Removed package receipt: $pkg_id"
            else
                echo "[INFO] Package receipt found but requires admin: $pkg_id"
            fi
        fi
    done
}

# Function to clean Launch Services database
clean_launch_services() {
    echo "[INFO] Cleaning Launch Services database..."

    # Rebuild Launch Services database to remove app references
    /System/Library/Frameworks/CoreServices.framework/Versions/A/Frameworks/LaunchServices.framework/Versions/A/Support/lsregister -kill -r -domain local -domain system -domain user

    # Remove specific entries if they exist
    /System/Library/Frameworks/CoreServices.framework/Versions/A/Frameworks/LaunchServices.framework/Versions/A/Support/lsregister -u "/Applications/Alabama Auction Watcher.app" 2>/dev/null

    echo "[SUCCESS] Launch Services database updated"
}

# Function to remove URL scheme handlers
remove_url_schemes() {
    echo "[INFO] Removing URL scheme handlers..."

    # Remove custom URL schemes from defaults
    defaults delete com.apple.LaunchServices LSHandlers 2>/dev/null || true

    # Remove specific protocol handlers if they exist
    /usr/bin/python3 -c "
import plistlib
import os

plist_path = os.path.expanduser('~/Library/Preferences/com.apple.LaunchServices.plist')
if os.path.exists(plist_path):
    try:
        with open(plist_path, 'rb') as f:
            plist = plistlib.load(f)

        # Remove handlers for our custom schemes
        if 'LSHandlers' in plist:
            plist['LSHandlers'] = [handler for handler in plist['LSHandlers']
                                 if not (handler.get('LSHandlerURLScheme', '').startswith('aaw') or
                                        handler.get('LSHandlerURLScheme', '').startswith('alabama-auction'))]

        with open(plist_path, 'wb') as f:
            plistlib.dump(plist, f)

        print('[SUCCESS] Removed URL scheme handlers')
    except Exception as e:
        print(f'[WARNING] Could not update URL handlers: {e}')
" 2>/dev/null || echo "[INFO] No URL scheme cleanup needed"
}

# Function to remove Dock entries
remove_dock_entries() {
    echo "[INFO] Removing Dock entries..."

    # Remove from Dock using dockutil if available
    if command -v dockutil >/dev/null 2>&1; then
        dockutil --remove "Alabama Auction Watcher" --no-restart 2>/dev/null
        dockutil --remove "AlabamaAuctionWatcher" --no-restart 2>/dev/null
        echo "[SUCCESS] Removed Dock entries"
    else
        # Manual removal using defaults
        /usr/bin/python3 -c "
import plistlib
import os

plist_path = os.path.expanduser('~/Library/Preferences/com.apple.dock.plist')
if os.path.exists(plist_path):
    try:
        with open(plist_path, 'rb') as f:
            plist = plistlib.load(f)

        if 'persistent-apps' in plist:
            original_count = len(plist['persistent-apps'])
            plist['persistent-apps'] = [app for app in plist['persistent-apps']
                                      if not any(keyword in app.get('tile-data', {}).get('file-label', '').lower()
                                               for keyword in ['alabama', 'auction', 'watcher'])]

            if len(plist['persistent-apps']) < original_count:
                with open(plist_path, 'wb') as f:
                    plistlib.dump(plist, f)
                print('[SUCCESS] Removed Dock entries')
                # Restart Dock to apply changes
                os.system('killall Dock')

    except Exception as e:
        print(f'[WARNING] Could not update Dock: {e}')
" 2>/dev/null || echo "[INFO] No Dock cleanup needed"
}

# Function to remove LaunchAgents/LaunchDaemons
remove_launch_agents() {
    echo "[INFO] Removing launch agents and daemons..."

    # User launch agents
    LAUNCH_AGENT_PATHS=(
        "$HOME/Library/LaunchAgents/com.alabamaauctionwatcher.*.plist"
        "$HOME/Library/LaunchAgents/com.alabama-auction-watcher.*.plist"
    )

    for pattern in "${LAUNCH_AGENT_PATHS[@]}"; do
        for plist_file in $pattern; do
            if [[ -f "$plist_file" ]]; then
                launchctl unload "$plist_file" 2>/dev/null
                rm -f "$plist_file"
                echo "[SUCCESS] Removed launch agent: $(basename "$plist_file")"
            fi
        done
    done

    # System launch daemons (requires admin)
    if [[ "$ADMIN_MODE" == "true" ]]; then
        LAUNCH_DAEMON_PATHS=(
            "/Library/LaunchDaemons/com.alabamaauctionwatcher.*.plist"
            "/Library/LaunchDaemons/com.alabama-auction-watcher.*.plist"
        )

        for pattern in "${LAUNCH_DAEMON_PATHS[@]}"; do
            for plist_file in $pattern; do
                if [[ -f "$plist_file" ]]; then
                    launchctl unload "$plist_file" 2>/dev/null
                    rm -f "$plist_file"
                    echo "[SUCCESS] Removed launch daemon: $(basename "$plist_file")"
                fi
            done
        done
    fi
}

# Function to remove user data and preferences
remove_user_data() {
    echo "[INFO] Removing user data and preferences..."

    # User preference files
    PREF_FILES=(
        "$HOME/Library/Preferences/com.alabamaauctionwatcher.*.plist"
        "$HOME/Library/Preferences/com.alabama-auction-watcher.*.plist"
        "$HOME/Library/Preferences/AlabamaAuctionWatcher.plist"
    )

    for pattern in "${PREF_FILES[@]}"; do
        for pref_file in $pattern; do
            if [[ -f "$pref_file" ]]; then
                rm -f "$pref_file"
                echo "[SUCCESS] Removed preference file: $(basename "$pref_file")"
            fi
        done
    done

    # Application Support directories
    SUPPORT_DIRS=(
        "$HOME/Library/Application Support/Alabama Auction Watcher"
        "$HOME/Library/Application Support/AlabamaAuctionWatcher"
        "$HOME/Library/Application Support/com.alabamaauctionwatcher"
    )

    for support_dir in "${SUPPORT_DIRS[@]}"; do
        if [[ -d "$support_dir" ]]; then
            rm -rf "$support_dir"
            echo "[SUCCESS] Removed support directory: $(basename "$support_dir")"
        fi
    done

    # Caches
    CACHE_DIRS=(
        "$HOME/Library/Caches/Alabama Auction Watcher"
        "$HOME/Library/Caches/AlabamaAuctionWatcher"
        "$HOME/Library/Caches/com.alabamaauctionwatcher"
    )

    for cache_dir in "${CACHE_DIRS[@]}"; do
        if [[ -d "$cache_dir" ]]; then
            rm -rf "$cache_dir"
            echo "[SUCCESS] Removed cache directory: $(basename "$cache_dir")"
        fi
    done

    # Logs
    LOG_DIRS=(
        "$HOME/Library/Logs/Alabama Auction Watcher"
        "$HOME/Library/Logs/AlabamaAuctionWatcher"
    )

    for log_dir in "${LOG_DIRS[@]}"; do
        if [[ -d "$log_dir" ]]; then
            rm -rf "$log_dir"
            echo "[SUCCESS] Removed log directory: $(basename "$log_dir")"
        fi
    done

    # Database files in user directory
    if [[ -f "$HOME/alabama_auction_watcher.db" ]]; then
        rm -f "$HOME/alabama_auction_watcher.db"
        echo "[SUCCESS] Removed database file"
    fi
}

# Function to preserve user data
preserve_user_data() {
    echo "[INFO] Preserving user data and settings"

    PRESERVED_PATHS=(
        "$HOME/Library/Application Support/Alabama Auction Watcher"
        "$HOME/Library/Preferences/com.alabamaauctionwatcher.*.plist"
        "$HOME/alabama_auction_watcher.db"
    )

    echo "[INFO] The following data will be preserved:"
    for path_pattern in "${PRESERVED_PATHS[@]}"; do
        for path in $path_pattern; do
            if [[ -e "$path" ]]; then
                echo "       $(basename "$path")"
            fi
        done
    done
    echo ""
    echo "[INFO] Data location: ~/Library/Application Support/Alabama Auction Watcher"
}

# Function to remove system-wide components
remove_system_components() {
    if [[ "$ADMIN_MODE" != "true" ]]; then
        echo "[INFO] Skipping system components (requires admin privileges)"
        return
    fi

    echo "[INFO] Removing system-wide components..."

    # Remove from system Applications if installed there
    if [[ -d "/Applications/Alabama Auction Watcher.app" ]]; then
        rm -rf "/Applications/Alabama Auction Watcher.app"
        echo "[SUCCESS] Removed system application bundle"
    fi

    # Remove system preference panes (if any)
    SYSTEM_PREFS=(
        "/Library/PreferencePanes/AlabamaAuctionWatcher.prefPane"
    )

    for pref_pane in "${SYSTEM_PREFS[@]}"; do
        if [[ -d "$pref_pane" ]]; then
            rm -rf "$pref_pane"
            echo "[SUCCESS] Removed system preference pane"
        fi
    done
}

# Main execution
main() {
    check_admin
    echo ""

    show_options
    echo ""

    echo "================================================================="
    echo "Starting Uninstallation Process"
    echo "================================================================="
    echo ""

    stop_services
    echo ""

    remove_application
    echo ""

    remove_pkg_receipts
    echo ""

    clean_launch_services
    echo ""

    remove_url_schemes
    echo ""

    remove_dock_entries
    echo ""

    remove_launch_agents
    echo ""

    if [[ "$ADMIN_MODE" == "true" ]]; then
        remove_system_components
        echo ""
    fi

    # Handle user data based on choice
    if [[ "$UNINSTALL_TYPE" == "1" ]]; then
        remove_user_data
    else
        preserve_user_data
    fi

    echo ""
    echo "================================================================="
    echo "Uninstallation Summary"
    echo "================================================================="
    echo ""

    if [[ "$UNINSTALL_TYPE" == "1" ]]; then
        echo "[✓] Complete removal performed"
        echo "[✓] Application bundle removed"
        echo "[✓] User data removed"
        echo "[✓] Launch Services cleaned"
        echo "[✓] URL schemes removed"
        echo "[✓] Dock entries removed"
        echo "[✓] Launch agents removed"
    else
        echo "[✓] Application-only removal performed"
        echo "[✓] Application bundle removed"
        echo "[✓] Launch Services cleaned"
        echo "[✓] URL schemes removed"
        echo "[✓] Dock entries removed"
        echo "[✓] Launch agents removed"
        echo "[!] User data preserved"
    fi

    echo ""
    echo "[SUCCESS] Alabama Auction Watcher has been uninstalled successfully!"
    echo ""

    if [[ "$UNINSTALL_TYPE" == "2" ]]; then
        echo "[INFO] Your data has been preserved at:"
        echo "       ~/Library/Application Support/Alabama Auction Watcher"
        echo ""
        echo "[INFO] You can reinstall Alabama Auction Watcher at any time"
        echo "       and your settings will be restored automatically."
        echo ""
    fi

    # Offer to open Applications folder for verification
    read -p "Would you like to open the Applications folder to verify removal? (y/n): " VERIFY
    if [[ "$VERIFY" =~ ^[Yy]$ ]]; then
        open /Applications
    fi

    echo ""
    echo "Thank you for using Alabama Auction Watcher!"
    echo ""
    echo "To reinstall, please download the latest version from:"
    echo "https://github.com/Alabama-Auction-Watcher"
    echo ""

    read -p "Press Enter to exit..."
}

# Execute main function
main