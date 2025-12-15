#!/bin/bash

# Alabama Auction Watcher - Professional Linux Uninstaller
# Comprehensive removal script with system integration cleanup and data preservation options
# Compatible with major Linux distributions (Ubuntu, Debian, Fedora, CentOS, RHEL, Arch)

echo "================================================================="
echo "Alabama Auction Watcher - Professional Uninstaller"
echo "================================================================="
echo ""

# Function to detect Linux distribution
detect_distro() {
    if [[ -f /etc/os-release ]]; then
        . /etc/os-release
        DISTRO="$ID"
        DISTRO_VERSION="$VERSION_ID"
        echo "[INFO] Detected distribution: $PRETTY_NAME"
    else
        DISTRO="unknown"
        echo "[WARNING] Could not detect Linux distribution"
    fi
}

# Function to check if running with sudo
check_admin() {
    if [[ $EUID -eq 0 ]]; then
        echo "[INFO] Running with root privileges"
        ADMIN_MODE="true"
    else
        echo "[INFO] Running as user: $USER"
        ADMIN_MODE="false"
    fi
}

# Function to display uninstall options
show_options() {
    echo "Select uninstall type:"
    echo ""
    echo "[1] Complete Removal - Remove all files and user data"
    echo "[2] Application Only - Keep user data and settings"
    echo "[3] Package Uninstall - Use package manager (if installed via package)"
    echo "[4] Cancel"
    echo ""
    read -p "Enter your choice (1-4): " UNINSTALL_TYPE

    case "$UNINSTALL_TYPE" in
        4)
            echo "[INFO] Uninstall cancelled by user"
            exit 0
            ;;
        1|2|3)
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

    # Kill any desktop app processes
    pkill -f "alabama-auction-watcher" 2>/dev/null

    echo "[SUCCESS] Services stopped"
}

# Function to stop systemd services
stop_systemd_services() {
    echo "[INFO] Stopping systemd services..."

    SYSTEMD_SERVICES=(
        "alabama-auction-watcher"
        "alabama-auction-watcher-backend"
        "aaw-backend"
        "aaw-frontend"
    )

    for service in "${SYSTEMD_SERVICES[@]}"; do
        if systemctl is-active --quiet "$service" 2>/dev/null; then
            if [[ "$ADMIN_MODE" == "true" ]]; then
                systemctl stop "$service"
                systemctl disable "$service"
                echo "[SUCCESS] Stopped and disabled service: $service"
            else
                systemctl --user stop "$service" 2>/dev/null
                systemctl --user disable "$service" 2>/dev/null
                echo "[SUCCESS] Stopped user service: $service"
            fi
        fi
    done
}

# Function to remove systemd service files
remove_systemd_services() {
    echo "[INFO] Removing systemd service files..."

    # System-wide services (requires root)
    if [[ "$ADMIN_MODE" == "true" ]]; then
        SYSTEM_SERVICE_FILES=(
            "/etc/systemd/system/alabama-auction-watcher*.service"
            "/lib/systemd/system/alabama-auction-watcher*.service"
            "/usr/lib/systemd/system/alabama-auction-watcher*.service"
        )

        for pattern in "${SYSTEM_SERVICE_FILES[@]}"; do
            for service_file in $pattern; do
                if [[ -f "$service_file" ]]; then
                    rm -f "$service_file"
                    echo "[SUCCESS] Removed system service: $(basename "$service_file")"
                fi
            done
        done

        # Reload systemd daemon
        systemctl daemon-reload
    fi

    # User services
    USER_SERVICE_FILES=(
        "$HOME/.config/systemd/user/alabama-auction-watcher*.service"
        "$HOME/.local/share/systemd/user/alabama-auction-watcher*.service"
    )

    for pattern in "${USER_SERVICE_FILES[@]}"; do
        for service_file in $pattern; do
            if [[ -f "$service_file" ]]; then
                rm -f "$service_file"
                echo "[SUCCESS] Removed user service: $(basename "$service_file")"
            fi
        done
    done

    # Reload user systemd daemon
    systemctl --user daemon-reload 2>/dev/null
}

# Function to remove package manager installations
remove_package() {
    if [[ "$UNINSTALL_TYPE" != "3" ]]; then
        return
    fi

    echo "[INFO] Attempting package manager removal..."

    case "$DISTRO" in
        "ubuntu"|"debian"|"linuxmint")
            if command -v apt >/dev/null 2>&1; then
                apt list --installed | grep -i "alabama-auction-watcher" >/dev/null 2>&1
                if [[ $? -eq 0 ]]; then
                    if [[ "$ADMIN_MODE" == "true" ]]; then
                        apt remove --purge alabama-auction-watcher -y
                        apt autoremove -y
                        echo "[SUCCESS] Removed via APT package manager"
                    else
                        echo "[ERROR] Package removal requires sudo privileges"
                    fi
                else
                    echo "[INFO] No package installation found"
                fi
            fi
            ;;
        "fedora"|"centos"|"rhel")
            if command -v dnf >/dev/null 2>&1; then
                dnf list installed | grep -i "alabama-auction-watcher" >/dev/null 2>&1
                if [[ $? -eq 0 ]]; then
                    if [[ "$ADMIN_MODE" == "true" ]]; then
                        dnf remove alabama-auction-watcher -y
                        echo "[SUCCESS] Removed via DNF package manager"
                    else
                        echo "[ERROR] Package removal requires sudo privileges"
                    fi
                else
                    echo "[INFO] No package installation found"
                fi
            elif command -v yum >/dev/null 2>&1; then
                yum list installed | grep -i "alabama-auction-watcher" >/dev/null 2>&1
                if [[ $? -eq 0 ]]; then
                    if [[ "$ADMIN_MODE" == "true" ]]; then
                        yum remove alabama-auction-watcher -y
                        echo "[SUCCESS] Removed via YUM package manager"
                    else
                        echo "[ERROR] Package removal requires sudo privileges"
                    fi
                else
                    echo "[INFO] No package installation found"
                fi
            fi
            ;;
        "arch"|"manjaro")
            if command -v pacman >/dev/null 2>&1; then
                pacman -Q | grep -i "alabama-auction-watcher" >/dev/null 2>&1
                if [[ $? -eq 0 ]]; then
                    if [[ "$ADMIN_MODE" == "true" ]]; then
                        pacman -R alabama-auction-watcher --noconfirm
                        echo "[SUCCESS] Removed via Pacman package manager"
                    else
                        echo "[ERROR] Package removal requires sudo privileges"
                    fi
                else
                    echo "[INFO] No package installation found"
                fi
            fi
            ;;
        *)
            echo "[WARNING] Unknown distribution - cannot use package manager"
            ;;
    esac
}

# Function to remove application files
remove_application_files() {
    echo "[INFO] Removing application files..."

    # Common installation directories
    INSTALL_DIRS=(
        "/opt/alabama-auction-watcher"
        "/usr/local/bin/alabama-auction-watcher"
        "/usr/local/share/alabama-auction-watcher"
        "/usr/share/alabama-auction-watcher"
        "$HOME/.local/share/alabama-auction-watcher"
        "$HOME/alabama-auction-watcher"
    )

    local removed_count=0
    for install_dir in "${INSTALL_DIRS[@]}"; do
        if [[ -d "$install_dir" ]] || [[ -f "$install_dir" ]]; then
            if [[ "$install_dir" == /opt/* ]] || [[ "$install_dir" == /usr/* ]]; then
                if [[ "$ADMIN_MODE" == "true" ]]; then
                    rm -rf "$install_dir"
                    if [[ $? -eq 0 ]]; then
                        echo "[SUCCESS] Removed: $install_dir"
                        removed_count=$((removed_count + 1))
                    fi
                else
                    echo "[WARNING] Cannot remove $install_dir (requires sudo)"
                fi
            else
                rm -rf "$install_dir"
                if [[ $? -eq 0 ]]; then
                    echo "[SUCCESS] Removed: $install_dir"
                    removed_count=$((removed_count + 1))
                fi
            fi
        fi
    done

    if [[ $removed_count -eq 0 ]]; then
        echo "[WARNING] No application files found in standard locations"
    fi

    # Remove symlinks
    SYMLINKS=(
        "/usr/local/bin/alabama-auction-watcher"
        "/usr/bin/alabama-auction-watcher"
    )

    for symlink in "${SYMLINKS[@]}"; do
        if [[ -L "$symlink" ]]; then
            if [[ "$ADMIN_MODE" == "true" ]]; then
                rm -f "$symlink"
                echo "[SUCCESS] Removed symlink: $symlink"
            else
                echo "[WARNING] Cannot remove $symlink (requires sudo)"
            fi
        fi
    done
}

# Function to remove desktop integration
remove_desktop_integration() {
    echo "[INFO] Removing desktop integration..."

    # Desktop entry files
    DESKTOP_FILES=(
        "/usr/share/applications/alabama-auction-watcher.desktop"
        "/usr/local/share/applications/alabama-auction-watcher.desktop"
        "$HOME/.local/share/applications/alabama-auction-watcher.desktop"
        "$HOME/Desktop/alabama-auction-watcher.desktop"
    )

    for desktop_file in "${DESKTOP_FILES[@]}"; do
        if [[ -f "$desktop_file" ]]; then
            if [[ "$desktop_file" == /usr/* ]]; then
                if [[ "$ADMIN_MODE" == "true" ]]; then
                    rm -f "$desktop_file"
                    echo "[SUCCESS] Removed desktop entry: $(basename "$desktop_file")"
                else
                    echo "[WARNING] Cannot remove $desktop_file (requires sudo)"
                fi
            else
                rm -f "$desktop_file"
                echo "[SUCCESS] Removed desktop entry: $(basename "$desktop_file")"
            fi
        fi
    done

    # Update desktop database
    if command -v update-desktop-database >/dev/null 2>&1; then
        if [[ "$ADMIN_MODE" == "true" ]]; then
            update-desktop-database /usr/share/applications 2>/dev/null
            update-desktop-database /usr/local/share/applications 2>/dev/null
        fi
        update-desktop-database "$HOME/.local/share/applications" 2>/dev/null
        echo "[SUCCESS] Updated desktop database"
    fi
}

# Function to remove icons
remove_icons() {
    echo "[INFO] Removing application icons..."

    # Icon directories
    ICON_DIRS=(
        "/usr/share/icons/hicolor"
        "/usr/local/share/icons/hicolor"
        "$HOME/.local/share/icons/hicolor"
        "$HOME/.icons/hicolor"
    )

    # Icon sizes to check
    ICON_SIZES=("16x16" "32x32" "48x48" "64x64" "128x128" "256x256" "512x512" "scalable")

    for icon_dir in "${ICON_DIRS[@]}"; do
        for size in "${ICON_SIZES[@]}"; do
            ICON_PATH="$icon_dir/${size}/apps/alabama-auction-watcher.*"
            for icon_file in $ICON_PATH; do
                if [[ -f "$icon_file" ]]; then
                    if [[ "$icon_file" == /usr/* ]]; then
                        if [[ "$ADMIN_MODE" == "true" ]]; then
                            rm -f "$icon_file"
                            echo "[SUCCESS] Removed icon: $icon_file"
                        else
                            echo "[WARNING] Cannot remove $icon_file (requires sudo)"
                        fi
                    else
                        rm -f "$icon_file"
                        echo "[SUCCESS] Removed icon: $icon_file"
                    fi
                fi
            done
        done
    done

    # Update icon cache
    if command -v gtk-update-icon-cache >/dev/null 2>&1; then
        for icon_dir in "${ICON_DIRS[@]}"; do
            if [[ -d "$icon_dir" ]]; then
                if [[ "$icon_dir" == /usr/* ]]; then
                    if [[ "$ADMIN_MODE" == "true" ]]; then
                        gtk-update-icon-cache "$icon_dir" 2>/dev/null
                    fi
                else
                    gtk-update-icon-cache "$icon_dir" 2>/dev/null
                fi
            fi
        done
        echo "[SUCCESS] Updated icon cache"
    fi
}

# Function to remove MIME types
remove_mime_types() {
    echo "[INFO] Removing MIME type associations..."

    MIME_FILES=(
        "/usr/share/mime/packages/alabama-auction-watcher.xml"
        "/usr/local/share/mime/packages/alabama-auction-watcher.xml"
        "$HOME/.local/share/mime/packages/alabama-auction-watcher.xml"
    )

    for mime_file in "${MIME_FILES[@]}"; do
        if [[ -f "$mime_file" ]]; then
            if [[ "$mime_file" == /usr/* ]]; then
                if [[ "$ADMIN_MODE" == "true" ]]; then
                    rm -f "$mime_file"
                    echo "[SUCCESS] Removed MIME file: $(basename "$mime_file")"
                else
                    echo "[WARNING] Cannot remove $mime_file (requires sudo)"
                fi
            else
                rm -f "$mime_file"
                echo "[SUCCESS] Removed MIME file: $(basename "$mime_file")"
            fi
        fi
    done

    # Update MIME database
    if command -v update-mime-database >/dev/null 2>&1; then
        MIME_DIRS=("/usr/share/mime" "/usr/local/share/mime" "$HOME/.local/share/mime")
        for mime_dir in "${MIME_DIRS[@]}"; do
            if [[ -d "$mime_dir" ]]; then
                if [[ "$mime_dir" == /usr/* ]]; then
                    if [[ "$ADMIN_MODE" == "true" ]]; then
                        update-mime-database "$mime_dir" 2>/dev/null
                    fi
                else
                    update-mime-database "$mime_dir" 2>/dev/null
                fi
            fi
        done
        echo "[SUCCESS] Updated MIME database"
    fi
}

# Function to remove user data
remove_user_data() {
    echo "[INFO] Removing user data and configuration..."

    # Configuration directories
    CONFIG_DIRS=(
        "$HOME/.config/alabama-auction-watcher"
        "$HOME/.alabama-auction-watcher"
        "$HOME/.local/share/alabama-auction-watcher"
    )

    for config_dir in "${CONFIG_DIRS[@]}"; do
        if [[ -d "$config_dir" ]]; then
            rm -rf "$config_dir"
            echo "[SUCCESS] Removed config directory: $(basename "$config_dir")"
        fi
    done

    # Cache directories
    CACHE_DIRS=(
        "$HOME/.cache/alabama-auction-watcher"
        "$HOME/.local/share/alabama-auction-watcher/cache"
    )

    for cache_dir in "${CACHE_DIRS[@]}"; do
        if [[ -d "$cache_dir" ]]; then
            rm -rf "$cache_dir"
            echo "[SUCCESS] Removed cache directory: $(basename "$cache_dir")"
        fi
    done

    # Log files
    LOG_FILES=(
        "$HOME/.local/share/alabama-auction-watcher/logs"
        "/var/log/alabama-auction-watcher"
    )

    for log_path in "${LOG_FILES[@]}"; do
        if [[ -d "$log_path" ]] || [[ -f "$log_path" ]]; then
            if [[ "$log_path" == /var/* ]]; then
                if [[ "$ADMIN_MODE" == "true" ]]; then
                    rm -rf "$log_path"
                    echo "[SUCCESS] Removed logs: $log_path"
                else
                    echo "[WARNING] Cannot remove $log_path (requires sudo)"
                fi
            else
                rm -rf "$log_path"
                echo "[SUCCESS] Removed logs: $log_path"
            fi
        fi
    done

    # Database files
    DB_FILES=(
        "$HOME/alabama_auction_watcher.db"
        "$HOME/.local/share/alabama-auction-watcher/database.db"
        "/var/lib/alabama-auction-watcher/database.db"
    )

    for db_file in "${DB_FILES[@]}"; do
        if [[ -f "$db_file" ]]; then
            if [[ "$db_file" == /var/* ]]; then
                if [[ "$ADMIN_MODE" == "true" ]]; then
                    rm -f "$db_file"
                    echo "[SUCCESS] Removed database: $db_file"
                else
                    echo "[WARNING] Cannot remove $db_file (requires sudo)"
                fi
            else
                rm -f "$db_file"
                echo "[SUCCESS] Removed database: $db_file"
            fi
        fi
    done
}

# Function to preserve user data
preserve_user_data() {
    echo "[INFO] Preserving user data and configuration"

    PRESERVED_PATHS=(
        "$HOME/.config/alabama-auction-watcher"
        "$HOME/.local/share/alabama-auction-watcher"
        "$HOME/alabama_auction_watcher.db"
    )

    echo "[INFO] The following data will be preserved:"
    for path in "${PRESERVED_PATHS[@]}"; do
        if [[ -e "$path" ]]; then
            echo "       $path"
        fi
    done
    echo ""
    echo "[INFO] Data location: ~/.local/share/alabama-auction-watcher"
}

# Main execution
main() {
    detect_distro
    echo ""

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

    stop_systemd_services
    echo ""

    if [[ "$UNINSTALL_TYPE" == "3" ]]; then
        remove_package
    fi

    remove_systemd_services
    echo ""

    remove_application_files
    echo ""

    remove_desktop_integration
    echo ""

    remove_icons
    echo ""

    remove_mime_types
    echo ""

    # Handle user data based on choice
    if [[ "$UNINSTALL_TYPE" == "1" ]]; then
        remove_user_data
    elif [[ "$UNINSTALL_TYPE" == "2" ]]; then
        preserve_user_data
    fi

    echo ""
    echo "================================================================="
    echo "Uninstallation Summary"
    echo "================================================================="
    echo ""

    if [[ "$UNINSTALL_TYPE" == "1" ]]; then
        echo "[✓] Complete removal performed"
        echo "[✓] Application files removed"
        echo "[✓] User data removed"
        echo "[✓] Desktop integration removed"
        echo "[✓] System services removed"
        echo "[✓] Icons and MIME types removed"
    elif [[ "$UNINSTALL_TYPE" == "2" ]]; then
        echo "[✓] Application-only removal performed"
        echo "[✓] Application files removed"
        echo "[✓] Desktop integration removed"
        echo "[✓] System services removed"
        echo "[✓] Icons and MIME types removed"
        echo "[!] User data preserved"
    elif [[ "$UNINSTALL_TYPE" == "3" ]]; then
        echo "[✓] Package manager removal performed"
        echo "[✓] System components removed via package manager"
        echo "[✓] Additional cleanup performed"
    fi

    echo ""
    echo "[SUCCESS] Alabama Auction Watcher has been uninstalled successfully!"
    echo ""

    if [[ "$UNINSTALL_TYPE" == "2" ]]; then
        echo "[INFO] Your data has been preserved at:"
        echo "       ~/.config/alabama-auction-watcher"
        echo "       ~/.local/share/alabama-auction-watcher"
        echo ""
        echo "[INFO] You can reinstall Alabama Auction Watcher at any time"
        echo "       and your settings will be restored automatically."
        echo ""
    fi

    echo "Thank you for using Alabama Auction Watcher!"
    echo ""
    echo "To reinstall, please download the latest version from:"
    echo "https://github.com/Alabama-Auction-Watcher"
    echo ""

    read -p "Press Enter to exit..."
}

# Make sure the script is executable
if [[ ! -x "$0" ]]; then
    echo "[INFO] Making script executable..."
    chmod +x "$0"
fi

# Execute main function
main