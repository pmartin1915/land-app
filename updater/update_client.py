#!/usr/bin/env python3
"""
Alabama Auction Watcher - Update Client
User-friendly update interface and notification system
"""

import sys
import json
import subprocess
from pathlib import Path
from typing import Dict, Optional
import tkinter as tk
from tkinter import ttk, messagebox
import threading
import time

try:
    import plyer  # For cross-platform notifications
except ImportError:
    plyer = None

from update_manager import UpdateManager

class UpdateNotificationSystem:
    """Cross-platform update notification system"""

    def __init__(self):
        self.app_name = "Alabama Auction Watcher"

    def show_desktop_notification(self, title: str, message: str, urgency: str = "normal"):
        """Show desktop notification"""
        try:
            if plyer:
                plyer.notification.notify(
                    title=title,
                    message=message,
                    app_name=self.app_name,
                    timeout=10
                )
                return True

            # Fallback for different platforms
            if sys.platform.startswith('win'):
                return self._show_windows_notification(title, message)
            elif sys.platform == 'darwin':
                return self._show_macos_notification(title, message)
            else:
                return self._show_linux_notification(title, message, urgency)

        except Exception as e:
            print(f"Failed to show notification: {e}")
            return False

    def _show_windows_notification(self, title: str, message: str) -> bool:
        """Windows notification using PowerShell"""
        try:
            ps_script = f'''
            Add-Type -AssemblyName System.Windows.Forms
            $notification = New-Object System.Windows.Forms.NotifyIcon
            $notification.Icon = [System.Drawing.SystemIcons]::Information
            $notification.BalloonTipTitle = "{title}"
            $notification.BalloonTipText = "{message}"
            $notification.Visible = $true
            $notification.ShowBalloonTip(10000)
            Start-Sleep -Seconds 10
            $notification.Dispose()
            '''

            subprocess.run(['powershell', '-Command', ps_script],
                         capture_output=True, creationflags=subprocess.CREATE_NO_WINDOW)
            return True
        except:
            return False

    def _show_macos_notification(self, title: str, message: str) -> bool:
        """macOS notification using osascript"""
        try:
            script = f'display notification "{message}" with title "{title}"'
            subprocess.run(['osascript', '-e', script], capture_output=True)
            return True
        except:
            return False

    def _show_linux_notification(self, title: str, message: str, urgency: str) -> bool:
        """Linux notification using notify-send"""
        try:
            cmd = ['notify-send', '-u', urgency, '-t', '10000', title, message]
            subprocess.run(cmd, capture_output=True)
            return True
        except:
            return False

class UpdateDialog:
    """GUI dialog for update management"""

    def __init__(self, parent=None):
        self.root = tk.Toplevel(parent) if parent else tk.Tk()
        self.root.title("Alabama Auction Watcher - Update Manager")
        self.root.geometry("500x400")
        self.root.resizable(False, False)

        # Center window
        self.center_window()

        # Update manager
        self.update_manager = UpdateManager()
        self.available_update = None

        # Create UI
        self.create_widgets()

        # Check for updates on startup
        self.check_for_updates()

    def center_window(self):
        """Center the window on screen"""
        self.root.update_idletasks()
        x = (self.root.winfo_screenwidth() // 2) - (self.root.winfo_width() // 2)
        y = (self.root.winfo_screenheight() // 2) - (self.root.winfo_height() // 2)
        self.root.geometry(f"+{x}+{y}")

    def create_widgets(self):
        """Create GUI widgets"""
        # Main frame
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)

        # Title
        title_label = ttk.Label(main_frame, text="Update Manager",
                               font=("Arial", 16, "bold"))
        title_label.pack(pady=(0, 20))

        # Current version info
        version_frame = ttk.LabelFrame(main_frame, text="Current Version", padding="10")
        version_frame.pack(fill=tk.X, pady=(0, 10))

        ttk.Label(version_frame, text=f"Installed Version: {self.update_manager.current_version}").pack(anchor=tk.W)
        self.last_check_label = ttk.Label(version_frame, text="Last Check: Never")
        self.last_check_label.pack(anchor=tk.W)

        # Update status
        self.status_frame = ttk.LabelFrame(main_frame, text="Update Status", padding="10")
        self.status_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 10))

        self.status_text = tk.Text(self.status_frame, height=8, wrap=tk.WORD, state=tk.DISABLED)
        scrollbar = ttk.Scrollbar(self.status_frame, command=self.status_text.yview)
        self.status_text.configure(yscrollcommand=scrollbar.set)

        self.status_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        # Progress bar
        self.progress = ttk.Progressbar(main_frame, mode='indeterminate')
        self.progress.pack(fill=tk.X, pady=(0, 10))

        # Button frame
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(fill=tk.X)

        self.check_button = ttk.Button(button_frame, text="Check for Updates", command=self.check_for_updates)
        self.check_button.pack(side=tk.LEFT, padx=(0, 5))

        self.download_button = ttk.Button(button_frame, text="Download Update", command=self.download_update, state=tk.DISABLED)
        self.download_button.pack(side=tk.LEFT, padx=5)

        self.install_button = ttk.Button(button_frame, text="Install Update", command=self.install_update, state=tk.DISABLED)
        self.install_button.pack(side=tk.LEFT, padx=5)

        self.settings_button = ttk.Button(button_frame, text="Settings", command=self.show_settings)
        self.settings_button.pack(side=tk.RIGHT, padx=(5, 0))

        # Update last check time
        self.update_last_check_time()

    def append_status(self, text: str):
        """Append text to status display"""
        self.status_text.configure(state=tk.NORMAL)
        self.status_text.insert(tk.END, text + "\n")
        self.status_text.see(tk.END)
        self.status_text.configure(state=tk.DISABLED)
        self.root.update_idletasks()

    def update_last_check_time(self):
        """Update last check time display"""
        if self.update_manager.last_check:
            check_time = self.update_manager.last_check.strftime("%Y-%m-%d %H:%M:%S")
            self.last_check_label.config(text=f"Last Check: {check_time}")
        else:
            self.last_check_label.config(text="Last Check: Never")

    def check_for_updates(self):
        """Check for updates in background thread"""
        def check_thread():
            try:
                self.progress.start()
                self.check_button.config(state=tk.DISABLED)
                self.append_status("Checking for updates...")

                self.available_update = self.update_manager.check_for_updates()

                if self.available_update:
                    version = self.available_update['version']
                    self.append_status(f"Update available: {version}")
                    self.append_status(f"Release date: {self.available_update.get('release_date', 'Unknown')}")

                    if self.available_update.get('critical'):
                        self.append_status("⚠️ This is a critical security update!")

                    if self.available_update.get('changelog'):
                        self.append_status(f"\nChangelog:\n{self.available_update['changelog']}")

                    self.download_button.config(state=tk.NORMAL)

                    # Show notification
                    notifier = UpdateNotificationSystem()
                    notifier.show_desktop_notification(
                        "Update Available",
                        f"Alabama Auction Watcher {version} is available",
                        "critical" if self.available_update.get('critical') else "normal"
                    )

                else:
                    self.append_status("Your application is up to date!")
                    self.download_button.config(state=tk.DISABLED)
                    self.install_button.config(state=tk.DISABLED)

                self.update_last_check_time()

            except Exception as e:
                self.append_status(f"Error checking for updates: {e}")

            finally:
                self.progress.stop()
                self.check_button.config(state=tk.NORMAL)

        threading.Thread(target=check_thread, daemon=True).start()

    def download_update(self):
        """Download available update"""
        if not self.available_update:
            return

        def download_thread():
            try:
                self.progress.start()
                self.download_button.config(state=tk.DISABLED)
                self.append_status(f"Downloading update {self.available_update['version']}...")

                package_path = self.update_manager.download_update(self.available_update)

                if package_path:
                    self.append_status(f"Download completed: {package_path.name}")
                    self.install_button.config(state=tk.NORMAL)
                    self.downloaded_package = package_path
                else:
                    self.append_status("Download failed!")

            except Exception as e:
                self.append_status(f"Download error: {e}")

            finally:
                self.progress.stop()
                self.download_button.config(state=tk.NORMAL)

        threading.Thread(target=download_thread, daemon=True).start()

    def install_update(self):
        """Install downloaded update"""
        if not hasattr(self, 'downloaded_package'):
            return

        # Confirm installation
        if not messagebox.askyesno("Confirm Update",
                                  "This will install the update and restart the application.\n\nProceed?"):
            return

        def install_thread():
            try:
                self.progress.start()
                self.install_button.config(state=tk.DISABLED)
                self.append_status("Creating backup...")

                # Create backup
                backup_path = self.update_manager.create_backup()
                if backup_path:
                    self.append_status(f"Backup created: {backup_path.name}")
                else:
                    self.append_status("Warning: Backup creation failed!")

                self.append_status("Installing update...")

                # Apply update
                success = self.update_manager.apply_update(self.downloaded_package, backup_path)

                if success:
                    self.append_status("Update installed successfully!")
                    self.append_status("Please restart the application.")

                    messagebox.showinfo("Update Complete",
                                       "Update installed successfully!\nPlease restart the application.")
                else:
                    self.append_status("Update installation failed!")
                    messagebox.showerror("Update Failed", "Update installation failed. Check logs for details.")

            except Exception as e:
                self.append_status(f"Installation error: {e}")

            finally:
                self.progress.stop()

        threading.Thread(target=install_thread, daemon=True).start()

    def show_settings(self):
        """Show update settings dialog"""
        SettingsDialog(self.root, self.update_manager)

class SettingsDialog:
    """Update settings configuration dialog"""

    def __init__(self, parent, update_manager: UpdateManager):
        self.update_manager = update_manager
        self.window = tk.Toplevel(parent)
        self.window.title("Update Settings")
        self.window.geometry("400x500")
        self.window.resizable(False, False)

        # Center window
        self.center_window()

        # Create settings UI
        self.create_settings_widgets()

        # Load current settings
        self.load_settings()

    def center_window(self):
        """Center the window on screen"""
        self.window.update_idletasks()
        x = (self.window.winfo_screenwidth() // 2) - (self.window.winfo_width() // 2)
        y = (self.window.winfo_screenheight() // 2) - (self.window.winfo_height() // 2)
        self.window.geometry(f"+{x}+{y}")

    def create_settings_widgets(self):
        """Create settings UI widgets"""
        main_frame = ttk.Frame(self.window, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)

        # General settings
        general_frame = ttk.LabelFrame(main_frame, text="General Settings", padding="10")
        general_frame.pack(fill=tk.X, pady=(0, 10))

        self.auto_update_var = tk.BooleanVar()
        ttk.Checkbutton(general_frame, text="Enable automatic updates",
                       variable=self.auto_update_var).pack(anchor=tk.W)

        self.beta_channel_var = tk.BooleanVar()
        ttk.Checkbutton(general_frame, text="Receive beta updates",
                       variable=self.beta_channel_var).pack(anchor=tk.W)

        ttk.Label(general_frame, text="Check interval (hours):").pack(anchor=tk.W, pady=(10, 0))
        self.check_interval_var = tk.StringVar()
        ttk.Entry(general_frame, textvariable=self.check_interval_var, width=10).pack(anchor=tk.W)

        # Notification settings
        notif_frame = ttk.LabelFrame(main_frame, text="Notifications", padding="10")
        notif_frame.pack(fill=tk.X, pady=(0, 10))

        self.desktop_notifications_var = tk.BooleanVar()
        ttk.Checkbutton(notif_frame, text="Show desktop notifications",
                       variable=self.desktop_notifications_var).pack(anchor=tk.W)

        self.email_notifications_var = tk.BooleanVar()
        ttk.Checkbutton(notif_frame, text="Email notifications",
                       variable=self.email_notifications_var).pack(anchor=tk.W)

        ttk.Label(notif_frame, text="Admin email:").pack(anchor=tk.W, pady=(10, 0))
        self.admin_email_var = tk.StringVar()
        ttk.Entry(notif_frame, textvariable=self.admin_email_var, width=30).pack(anchor=tk.W, fill=tk.X)

        # Enterprise settings
        enterprise_frame = ttk.LabelFrame(main_frame, text="Enterprise Settings", padding="10")
        enterprise_frame.pack(fill=tk.X, pady=(0, 10))

        self.enterprise_mode_var = tk.BooleanVar()
        ttk.Checkbutton(enterprise_frame, text="Enterprise mode",
                       variable=self.enterprise_mode_var).pack(anchor=tk.W)

        ttk.Label(enterprise_frame, text="Update window start hour (0-23):").pack(anchor=tk.W, pady=(10, 0))
        self.start_hour_var = tk.StringVar()
        ttk.Entry(enterprise_frame, textvariable=self.start_hour_var, width=10).pack(anchor=tk.W)

        ttk.Label(enterprise_frame, text="Update window end hour (0-23):").pack(anchor=tk.W, pady=(5, 0))
        self.end_hour_var = tk.StringVar()
        ttk.Entry(enterprise_frame, textvariable=self.end_hour_var, width=10).pack(anchor=tk.W)

        # Buttons
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(fill=tk.X, pady=(20, 0))

        ttk.Button(button_frame, text="Save", command=self.save_settings).pack(side=tk.RIGHT, padx=(5, 0))
        ttk.Button(button_frame, text="Cancel", command=self.window.destroy).pack(side=tk.RIGHT)
        ttk.Button(button_frame, text="Reset to Defaults", command=self.reset_to_defaults).pack(side=tk.LEFT)

    def load_settings(self):
        """Load current settings into UI"""
        config = self.update_manager.config

        self.auto_update_var.set(config.get("auto_update", False))
        self.beta_channel_var.set(config.get("beta_channel", False))
        self.check_interval_var.set(str(config.get("check_interval_hours", 24)))

        notif = config.get("notification_preferences", {})
        self.desktop_notifications_var.set(notif.get("show_desktop_notifications", True))
        self.email_notifications_var.set(notif.get("email_notifications", False))
        self.admin_email_var.set(notif.get("admin_email", ""))

        self.enterprise_mode_var.set(config.get("enterprise_mode", False))

        window = config.get("allowed_update_window", {})
        self.start_hour_var.set(str(window.get("start_hour", 2)))
        self.end_hour_var.set(str(window.get("end_hour", 6)))

    def save_settings(self):
        """Save settings to configuration"""
        try:
            # Update configuration
            self.update_manager.config["auto_update"] = self.auto_update_var.get()
            self.update_manager.config["beta_channel"] = self.beta_channel_var.get()
            self.update_manager.config["check_interval_hours"] = int(self.check_interval_var.get())
            self.update_manager.config["enterprise_mode"] = self.enterprise_mode_var.get()

            # Notification preferences
            self.update_manager.config["notification_preferences"] = {
                "show_desktop_notifications": self.desktop_notifications_var.get(),
                "email_notifications": self.email_notifications_var.get(),
                "admin_email": self.admin_email_var.get()
            }

            # Update window
            self.update_manager.config["allowed_update_window"] = {
                "start_hour": int(self.start_hour_var.get()),
                "end_hour": int(self.end_hour_var.get())
            }

            # Save to file
            self.update_manager.save_configuration()

            messagebox.showinfo("Settings Saved", "Update settings have been saved successfully!")
            self.window.destroy()

        except ValueError as e:
            messagebox.showerror("Invalid Input", "Please check your numeric inputs and try again.")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to save settings: {e}")

    def reset_to_defaults(self):
        """Reset settings to defaults"""
        if messagebox.askyesno("Reset Settings", "Reset all settings to defaults?"):
            # Reset to default values
            self.auto_update_var.set(False)
            self.beta_channel_var.set(False)
            self.check_interval_var.set("24")
            self.desktop_notifications_var.set(True)
            self.email_notifications_var.set(False)
            self.admin_email_var.set("")
            self.enterprise_mode_var.set(False)
            self.start_hour_var.set("2")
            self.end_hour_var.set("6")

def main():
    """Main update client execution"""
    import argparse

    parser = argparse.ArgumentParser(description='Alabama Auction Watcher Update Client')
    parser.add_argument('--gui', action='store_true', help='Show GUI interface')
    parser.add_argument('--notify', action='store_true', help='Check and notify about updates')
    parser.add_argument('--daemon', action='store_true', help='Run notification daemon')

    args = parser.parse_args()

    if args.gui or len(sys.argv) == 1:
        # Show GUI
        root = tk.Tk()
        root.withdraw()  # Hide main window
        dialog = UpdateDialog()
        dialog.root.protocol("WM_DELETE_WINDOW", root.destroy)
        root.mainloop()

    elif args.notify:
        # Check and notify
        manager = UpdateManager()
        update_info = manager.check_for_updates()

        if update_info:
            notifier = UpdateNotificationSystem()
            notifier.show_desktop_notification(
                "Update Available",
                f"Alabama Auction Watcher {update_info['version']} is available",
                "critical" if update_info.get('critical') else "normal"
            )
            print(f"Update available: {update_info['version']}")
        else:
            print("No updates available")

    elif args.daemon:
        # Run as notification daemon
        manager = UpdateManager()
        notifier = UpdateNotificationSystem()

        while True:
            try:
                if manager.should_check_for_updates():
                    update_info = manager.check_for_updates()

                    if update_info:
                        notifier.show_desktop_notification(
                            "Update Available",
                            f"Alabama Auction Watcher {update_info['version']} is available",
                            "critical" if update_info.get('critical') else "normal"
                        )

                # Sleep for 1 hour before next check
                time.sleep(3600)

            except KeyboardInterrupt:
                break
            except Exception as e:
                print(f"Daemon error: {e}")
                time.sleep(300)  # 5 minutes before retry

if __name__ == '__main__':
    main()