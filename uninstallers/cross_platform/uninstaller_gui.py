#!/usr/bin/env python3
"""
Alabama Auction Watcher - Professional Cross-Platform Uninstaller GUI
Modern tkinter-based uninstaller with Alabama Auction Watcher branding
Provides user-friendly interface for complete application removal
"""

import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext
import subprocess
import threading
import sys
import os
import platform
from pathlib import Path
from typing import Optional, List, Callable
from datetime import datetime
import json
import tempfile
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class UninstallerGUI:
    """Professional cross-platform uninstaller with GUI"""

    def __init__(self):
        self.root = tk.Tk()
        self.platform_system = platform.system().lower()
        self.uninstaller_thread = None
        self.uninstall_running = False

        # Get the directory where this script is located
        self.script_dir = Path(__file__).parent.parent.parent.absolute()

        # Brand colors (matching Alabama Auction Watcher)
        self.colors = {
            'primary': '#6C8EF5',
            'secondary': '#2C3E50',
            'accent': '#2980B9',
            'success': '#16A34A',
            'warning': '#F59E0B',
            'error': '#EF4444',
            'white': '#FFFFFF',
            'light_gray': '#F8F9FA',
            'dark_gray': '#495057'
        }

        self.setup_gui()

    def setup_gui(self):
        """Create and configure the main GUI"""
        self.root.title("Alabama Auction Watcher - Uninstaller")
        self.root.geometry("800x700")
        self.root.resizable(True, True)

        # Configure style
        style = ttk.Style()

        # Try to set a modern theme
        try:
            if self.platform_system == "windows":
                style.theme_use('winnative')
            elif self.platform_system == "darwin":
                style.theme_use('aqua')
            else:
                style.theme_use('clam')
        except tk.TclError:
            style.theme_use('default')

        # Configure custom styles
        style.configure('Title.TLabel', font=('Arial', 18, 'bold'), foreground=self.colors['secondary'])
        style.configure('Subtitle.TLabel', font=('Arial', 12), foreground=self.colors['dark_gray'])
        style.configure('Header.TLabel', font=('Arial', 14, 'bold'), foreground=self.colors['primary'])
        style.configure('Status.TLabel', font=('Arial', 10))

        # Configure button styles
        style.configure('Primary.TButton', font=('Arial', 10, 'bold'))
        style.configure('Danger.TButton', font=('Arial', 10, 'bold'))

        self.create_header()
        self.create_main_content()
        self.create_footer()

        # Center the window
        self.center_window()

        # Bind window close event
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)

    def center_window(self):
        """Center the window on the screen"""
        self.root.update_idletasks()
        width = self.root.winfo_width()
        height = self.root.winfo_height()
        x = (self.root.winfo_screenwidth() // 2) - (width // 2)
        y = (self.root.winfo_screenheight() // 2) - (height // 2)
        self.root.geometry(f"{width}x{height}+{x}+{y}")

    def create_header(self):
        """Create the application header"""
        header_frame = ttk.Frame(self.root, padding="30")
        header_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N))

        # Main title with icon
        title_frame = ttk.Frame(header_frame)
        title_frame.grid(row=0, column=0, columnspan=2, pady=(0, 10))

        # Title
        title_label = ttk.Label(
            title_frame,
            text="🏡 Alabama Auction Watcher",
            style='Title.TLabel'
        )
        title_label.grid(row=0, column=0)

        # Subtitle
        subtitle_label = ttk.Label(
            header_frame,
            text="Professional Uninstaller",
            style='Subtitle.TLabel'
        )
        subtitle_label.grid(row=1, column=0, columnspan=2, pady=(0, 10))

        # Platform info
        platform_info = f"Platform: {platform.system()} {platform.release()}"
        platform_label = ttk.Label(
            header_frame,
            text=platform_info,
            font=('Arial', 9),
            foreground=self.colors['dark_gray']
        )
        platform_label.grid(row=2, column=0, columnspan=2, pady=(0, 20))

        # Configure column weights
        header_frame.columnconfigure(0, weight=1)

    def create_main_content(self):
        """Create the main content area"""
        # Create notebook for tabs
        self.notebook = ttk.Notebook(self.root)
        self.notebook.grid(row=1, column=0, sticky=(tk.W, tk.E, tk.N, tk.S), padx=30, pady=(0, 20))

        # Configure grid weights
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(1, weight=1)

        # Create tabs
        self.create_uninstall_tab()
        self.create_status_tab()
        self.create_about_tab()

    def create_uninstall_tab(self):
        """Create the main uninstall tab"""
        uninstall_frame = ttk.Frame(self.notebook, padding="20")
        self.notebook.add(uninstall_frame, text="🗑️ Uninstall")

        # Uninstall type selection
        type_frame = ttk.LabelFrame(uninstall_frame, text="Uninstall Options", padding="15")
        type_frame.grid(row=0, column=0, sticky=(tk.W, tk.E), pady=(0, 20))

        self.uninstall_type = tk.StringVar(value="complete")

        # Complete removal option
        complete_radio = ttk.Radiobutton(
            type_frame,
            text="Complete Removal",
            variable=self.uninstall_type,
            value="complete"
        )
        complete_radio.grid(row=0, column=0, sticky=tk.W, pady=5)

        complete_desc = ttk.Label(
            type_frame,
            text="Remove all files, settings, and user data",
            font=('Arial', 9),
            foreground=self.colors['dark_gray']
        )
        complete_desc.grid(row=0, column=1, sticky=tk.W, padx=(10, 0), pady=5)

        # Application only option
        app_only_radio = ttk.Radiobutton(
            type_frame,
            text="Application Only",
            variable=self.uninstall_type,
            value="app_only"
        )
        app_only_radio.grid(row=1, column=0, sticky=tk.W, pady=5)

        app_only_desc = ttk.Label(
            type_frame,
            text="Keep user data and settings for future installations",
            font=('Arial', 9),
            foreground=self.colors['dark_gray']
        )
        app_only_desc.grid(row=1, column=1, sticky=tk.W, padx=(10, 0), pady=5)

        # What will be removed section
        removal_frame = ttk.LabelFrame(uninstall_frame, text="What Will Be Removed", padding="15")
        removal_frame.grid(row=1, column=0, sticky=(tk.W, tk.E), pady=(0, 20))

        # Create removal checklist
        self.create_removal_checklist(removal_frame)

        # Progress section
        progress_frame = ttk.LabelFrame(uninstall_frame, text="Uninstall Progress", padding="15")
        progress_frame.grid(row=2, column=0, sticky=(tk.W, tk.E), pady=(0, 20))

        # Progress bar
        self.progress_var = tk.DoubleVar()
        self.progress_bar = ttk.Progressbar(
            progress_frame,
            variable=self.progress_var,
            maximum=100,
            length=500,
            mode='determinate'
        )
        self.progress_bar.grid(row=0, column=0, sticky=(tk.W, tk.E), pady=(0, 10))

        # Progress status
        self.progress_status_var = tk.StringVar(value="Ready to uninstall")
        self.progress_status_label = ttk.Label(
            progress_frame,
            textvariable=self.progress_status_var,
            style='Status.TLabel'
        )
        self.progress_status_label.grid(row=1, column=0, sticky=tk.W)

        # Action buttons frame
        button_frame = ttk.Frame(uninstall_frame)
        button_frame.grid(row=3, column=0, sticky=(tk.W, tk.E), pady=(20, 0))

        # Uninstall button
        self.uninstall_button = ttk.Button(
            button_frame,
            text="🗑️ Start Uninstall",
            command=self.start_uninstall,
            style='Primary.TButton',
            width=20
        )
        self.uninstall_button.grid(row=0, column=0, padx=(0, 10))

        # Cancel button
        self.cancel_button = ttk.Button(
            button_frame,
            text="❌ Cancel",
            command=self.cancel_uninstall,
            width=15
        )
        self.cancel_button.grid(row=0, column=1, padx=(0, 10))

        # Close button (initially hidden)
        self.close_button = ttk.Button(
            button_frame,
            text="✅ Close",
            command=self.root.quit,
            style='Primary.TButton',
            width=15
        )
        # Don't grid initially - will show after completion

        # Configure column weights
        uninstall_frame.columnconfigure(0, weight=1)
        type_frame.columnconfigure(1, weight=1)
        removal_frame.columnconfigure(0, weight=1)
        progress_frame.columnconfigure(0, weight=1)
        button_frame.columnconfigure(2, weight=1)  # Push buttons to left

    def create_removal_checklist(self, parent):
        """Create the removal checklist"""
        platform_items = self.get_platform_removal_items()

        for i, item in enumerate(platform_items):
            # Checkmark icon
            check_label = ttk.Label(parent, text="✓", foreground=self.colors['success'])
            check_label.grid(row=i, column=0, sticky=tk.W, padx=(0, 10))

            # Item description
            item_label = ttk.Label(parent, text=item, font=('Arial', 10))
            item_label.grid(row=i, column=1, sticky=tk.W, pady=2)

        parent.columnconfigure(1, weight=1)

    def get_platform_removal_items(self) -> List[str]:
        """Get platform-specific removal items"""
        common_items = [
            "Application files and directories",
            "Configuration files and settings",
            "Log files and temporary data",
            "Database files (if complete removal selected)"
        ]

        if self.platform_system == "windows":
            return common_items + [
                "Desktop and Start Menu shortcuts",
                "Windows registry entries",
                "URL protocol handlers",
                "File associations",
                "Windows services (if any)"
            ]
        elif self.platform_system == "darwin":
            return common_items + [
                "Application bundle from Applications folder",
                "Launch Services database entries",
                "URL scheme handlers",
                "Dock entries",
                "LaunchAgents and LaunchDaemons"
            ]
        else:  # Linux
            return common_items + [
                "Desktop entry files",
                "Application icons (all sizes)",
                "MIME type associations",
                "Systemd service files",
                "Package manager entries (if applicable)"
            ]

    def create_status_tab(self):
        """Create the status/log viewing tab"""
        status_frame = ttk.Frame(self.notebook, padding="20")
        self.notebook.add(status_frame, text="📋 Status")

        # Log display
        log_frame = ttk.LabelFrame(status_frame, text="Uninstall Log", padding="10")
        log_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S), pady=(0, 20))

        self.log_text = scrolledtext.ScrolledText(
            log_frame,
            height=20,
            width=70,
            wrap=tk.WORD,
            font=('Consolas', 9)
        )
        self.log_text.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))

        # Action buttons
        log_button_frame = ttk.Frame(log_frame)
        log_button_frame.grid(row=1, column=0, sticky=(tk.W, tk.E), pady=(10, 0))

        ttk.Button(
            log_button_frame,
            text="🔄 Refresh",
            command=self.refresh_log
        ).grid(row=0, column=0, padx=(0, 10))

        ttk.Button(
            log_button_frame,
            text="📄 Save Log",
            command=self.save_log
        ).grid(row=0, column=1, padx=(0, 10))

        ttk.Button(
            log_button_frame,
            text="🗑️ Clear Log",
            command=self.clear_log
        ).grid(row=0, column=2)

        # Configure weights
        status_frame.columnconfigure(0, weight=1)
        status_frame.rowconfigure(0, weight=1)
        log_frame.columnconfigure(0, weight=1)
        log_frame.rowconfigure(0, weight=1)

        # Initialize log
        self.log_message("Alabama Auction Watcher Uninstaller initialized")
        self.log_message(f"Platform: {platform.system()} {platform.release()}")
        self.log_message(f"Uninstaller location: {self.script_dir}")

    def create_about_tab(self):
        """Create the about tab"""
        about_frame = ttk.Frame(self.notebook, padding="30")
        self.notebook.add(about_frame, text="ℹ️ About")

        # Application info
        info_text = f"""Alabama Auction Watcher - Professional Uninstaller

Version: 1.0.0
Platform: {platform.system()} {platform.release()}
Python: {sys.version.split()[0]}

This uninstaller will safely remove Alabama Auction Watcher from your system.
You can choose to keep your data and settings for future installations.

Features:
• Complete or selective removal options
• Cross-platform compatibility (Windows, macOS, Linux)
• Professional user interface with progress tracking
• Comprehensive system integration cleanup
• Enterprise-grade logging and reporting
• Data preservation options

Support:
For support and updates, visit:
https://github.com/Alabama-Auction-Watcher

© 2024 Alabama Auction Watcher Team
Licensed under MIT License"""

        info_label = ttk.Label(
            about_frame,
            text=info_text,
            justify=tk.LEFT,
            font=('Arial', 10)
        )
        info_label.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N))

        about_frame.columnconfigure(0, weight=1)

    def create_footer(self):
        """Create the footer with status"""
        self.footer_frame = ttk.Frame(self.root)
        self.footer_frame.grid(row=2, column=0, sticky=(tk.W, tk.E), padx=30, pady=(0, 20))

        # Status label
        self.status_var = tk.StringVar(value="Ready")
        status_label = ttk.Label(
            self.footer_frame,
            textvariable=self.status_var,
            style='Status.TLabel',
            relief=tk.SUNKEN,
            padding="5"
        )
        status_label.grid(row=0, column=0, sticky=(tk.W, tk.E))

        # Time label
        self.time_var = tk.StringVar(value=datetime.now().strftime('%H:%M:%S'))
        time_label = ttk.Label(
            self.footer_frame,
            textvariable=self.time_var,
            style='Status.TLabel',
            padding="5"
        )
        time_label.grid(row=0, column=1, sticky=tk.E)

        self.footer_frame.columnconfigure(0, weight=1)

        # Update time every second
        self.update_time()

    def update_time(self):
        """Update the time display"""
        self.time_var.set(datetime.now().strftime('%H:%M:%S'))
        self.root.after(1000, self.update_time)

    def log_message(self, message: str, level: str = "INFO"):
        """Add a message to the log"""
        timestamp = datetime.now().strftime('%H:%M:%S')
        log_entry = f"[{timestamp}] [{level}] {message}"

        self.log_text.insert(tk.END, log_entry + '\n')
        self.log_text.see(tk.END)

        # Also log to console
        logger.log(getattr(logging, level, logging.INFO), message)

    def update_status(self, message: str):
        """Update the status bar"""
        self.status_var.set(message)
        self.progress_status_var.set(message)
        self.log_message(message)

    def update_progress(self, progress: int):
        """Update the progress bar"""
        self.progress_var.set(progress)
        self.root.update_idletasks()

    def start_uninstall(self):
        """Start the uninstall process"""
        # Confirm with user
        uninstall_type_text = "complete removal" if self.uninstall_type.get() == "complete" else "application-only removal"

        response = messagebox.askyesno(
            "Confirm Uninstall",
            f"Are you sure you want to proceed with {uninstall_type_text} of Alabama Auction Watcher?\n\n"
            f"This action cannot be undone.",
            icon='warning'
        )

        if not response:
            self.update_status("Uninstall cancelled by user")
            return

        # Disable buttons
        self.uninstall_button.config(state='disabled')
        self.uninstall_running = True

        # Start uninstall in separate thread
        self.uninstaller_thread = threading.Thread(
            target=self.run_uninstall,
            daemon=True
        )
        self.uninstaller_thread.start()

    def run_uninstall(self):
        """Run the actual uninstall process"""
        try:
            self.update_status("Starting uninstall process...")
            self.update_progress(0)

            # Get platform-specific uninstaller
            uninstaller_script = self.get_uninstaller_script()

            if not uninstaller_script or not uninstaller_script.exists():
                raise Exception(f"Platform-specific uninstaller not found: {uninstaller_script}")

            self.update_status(f"Found uninstaller: {uninstaller_script.name}")
            self.update_progress(10)

            # Prepare command based on platform
            if self.platform_system == "windows":
                cmd = self.prepare_windows_command(uninstaller_script)
            elif self.platform_system == "darwin":
                cmd = self.prepare_macos_command(uninstaller_script)
            else:  # Linux
                cmd = self.prepare_linux_command(uninstaller_script)

            self.update_status("Executing platform-specific uninstaller...")
            self.update_progress(20)

            # Execute the command
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                cwd=str(self.script_dir)
            )

            # Monitor progress
            self.monitor_uninstall_process(process)

            # Wait for completion
            return_code = process.wait()

            if return_code == 0:
                self.update_status("Uninstall completed successfully!")
                self.update_progress(100)
                self.log_message("Uninstall completed successfully!", "SUCCESS")

                # Show completion
                self.root.after(0, self.show_completion_success)
            else:
                raise Exception(f"Uninstaller returned error code: {return_code}")

        except Exception as e:
            error_msg = f"Uninstall failed: {str(e)}"
            self.log_message(error_msg, "ERROR")
            self.update_status("Uninstall failed!")
            self.root.after(0, lambda: self.show_completion_error(str(e)))

        finally:
            self.uninstall_running = False
            self.root.after(0, self.enable_buttons)

    def get_uninstaller_script(self) -> Optional[Path]:
        """Get the platform-specific uninstaller script"""
        if self.platform_system == "windows":
            return self.script_dir / "uninstallers" / "windows" / "uninstall_alabama_auction_watcher.bat"
        elif self.platform_system == "darwin":
            return self.script_dir / "uninstallers" / "macos" / "uninstall_alabama_auction_watcher.command"
        else:  # Linux
            return self.script_dir / "uninstallers" / "linux" / "uninstall_alabama_auction_watcher.sh"

    def prepare_windows_command(self, script_path: Path) -> List[str]:
        """Prepare Windows command"""
        uninstall_choice = "1" if self.uninstall_type.get() == "complete" else "2"
        return ["cmd", "/c", f'echo {uninstall_choice} | "{script_path}"']

    def prepare_macos_command(self, script_path: Path) -> List[str]:
        """Prepare macOS command"""
        uninstall_choice = "1" if self.uninstall_type.get() == "complete" else "2"
        return ["bash", "-c", f'echo {uninstall_choice} | bash "{script_path}"']

    def prepare_linux_command(self, script_path: Path) -> List[str]:
        """Prepare Linux command"""
        uninstall_choice = "1" if self.uninstall_type.get() == "complete" else "2"
        return ["bash", "-c", f'echo {uninstall_choice} | bash "{script_path}"']

    def monitor_uninstall_process(self, process):
        """Monitor the uninstall process and update progress"""
        progress = 30
        progress_steps = [
            "Stopping services...",
            "Removing shortcuts...",
            "Cleaning registry/system...",
            "Removing application files...",
            "Cleaning user data...",
            "Finalizing cleanup..."
        ]

        step_increment = 60 / len(progress_steps)  # 60% progress for actual steps

        for i, step in enumerate(progress_steps):
            if not self.uninstall_running:
                break

            self.update_status(step)
            progress += step_increment
            self.update_progress(int(progress))

            # Simulate step duration
            import time
            time.sleep(1)

    def show_completion_success(self):
        """Show successful completion dialog"""
        preservation_msg = ""
        if self.uninstall_type.get() == "app_only":
            preservation_msg = "\n\nYour data and settings have been preserved and will be available if you reinstall Alabama Auction Watcher."

        messagebox.showinfo(
            "Uninstall Complete",
            f"Alabama Auction Watcher has been successfully uninstalled from your system.{preservation_msg}\n\n"
            f"Thank you for using Alabama Auction Watcher!"
        )

        # Show close button
        self.close_button.grid(row=0, column=2)

    def show_completion_error(self, error: str):
        """Show error completion dialog"""
        messagebox.showerror(
            "Uninstall Failed",
            f"The uninstall process encountered an error:\n\n{error}\n\n"
            f"Please check the log for more details or try running the platform-specific uninstaller manually."
        )

    def enable_buttons(self):
        """Re-enable buttons after uninstall"""
        self.uninstall_button.config(state='normal')

    def cancel_uninstall(self):
        """Cancel the uninstall process"""
        if self.uninstall_running:
            response = messagebox.askyesno(
                "Cancel Uninstall",
                "An uninstall is currently in progress. Are you sure you want to cancel?\n\n"
                "This may leave your system in an inconsistent state.",
                icon='warning'
            )
            if response:
                self.uninstall_running = False
                self.update_status("Uninstall cancelled")
        else:
            self.root.quit()

    def refresh_log(self):
        """Refresh the log display"""
        # Log is updated in real-time, so just scroll to end
        self.log_text.see(tk.END)

    def save_log(self):
        """Save the log to a file"""
        from tkinter import filedialog

        filename = filedialog.asksaveasfilename(
            title="Save Uninstall Log",
            defaultextension=".txt",
            filetypes=[("Text files", "*.txt"), ("All files", "*.*")],
            initialname=f"alabama_auction_watcher_uninstall_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
        )

        if filename:
            try:
                with open(filename, 'w', encoding='utf-8') as f:
                    f.write(self.log_text.get(1.0, tk.END))
                messagebox.showinfo("Save Successful", f"Log saved to:\n{filename}")
            except Exception as e:
                messagebox.showerror("Save Failed", f"Failed to save log:\n{str(e)}")

    def clear_log(self):
        """Clear the log display"""
        self.log_text.delete(1.0, tk.END)
        self.log_message("Log cleared")

    def on_closing(self):
        """Handle window closing"""
        if self.uninstall_running:
            response = messagebox.askyesno(
                "Uninstall In Progress",
                "An uninstall is currently running. Are you sure you want to close the uninstaller?\n\n"
                "This may leave your system in an inconsistent state.",
                icon='warning'
            )
            if not response:
                return

        self.root.destroy()

    def run(self):
        """Start the GUI application"""
        self.root.mainloop()

def main():
    """Main entry point"""
    try:
        app = UninstallerGUI()
        app.run()
    except Exception as e:
        logger.error(f"Failed to start uninstaller GUI: {e}")
        # Fallback to console message
        print(f"Failed to start uninstaller GUI: {e}")
        input("Press Enter to exit...")

if __name__ == "__main__":
    main()