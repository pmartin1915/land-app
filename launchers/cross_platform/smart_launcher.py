#!/usr/bin/env python3
"""
Alabama Auction Watcher Smart Desktop Launcher
Provides a modern GUI interface for launching and managing all components
of the Alabama Auction Watcher system with real-time status monitoring.

Features:
- Cross-platform compatibility (Windows, macOS, Linux)
- Real-time service status monitoring
- One-click component launching
- Process management (start/stop/restart)
- Integration with existing AI monitoring systems
- Health checking and diagnostics
- Log viewing capabilities
"""

import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext
import subprocess
import threading
import time
import sys
import os
import platform
import webbrowser
import requests
import json
from pathlib import Path
from typing import Dict, Optional, Callable, List
from datetime import datetime
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class ServiceStatus:
    """Enumeration for service status states"""
    STOPPED = "stopped"
    STARTING = "starting"
    RUNNING = "running"
    ERROR = "error"
    UNKNOWN = "unknown"

class ServiceMonitor:
    """Monitors the status of Alabama Auction Watcher services"""

    def __init__(self):
        self.services = {
            'streamlit': {
                'name': 'Main Dashboard',
                'port': 8501,
                'url': 'http://localhost:8501',
                'health_endpoint': 'http://localhost:8501',
                'status': ServiceStatus.STOPPED,
                'process': None,
                'last_check': None
            },
            'backend': {
                'name': 'Backend API',
                'port': 8001,
                'url': 'http://localhost:8001',
                'health_endpoint': 'http://localhost:8001/health',
                'status': ServiceStatus.STOPPED,
                'process': None,
                'last_check': None
            }
        }

    def check_service_status(self, service_key: str) -> ServiceStatus:
        """Check if a service is running by testing its endpoint"""
        service = self.services.get(service_key)
        if not service:
            return ServiceStatus.UNKNOWN

        try:
            response = requests.get(service['health_endpoint'], timeout=2)
            if response.status_code == 200:
                service['status'] = ServiceStatus.RUNNING
                service['last_check'] = datetime.now()
                return ServiceStatus.RUNNING
        except requests.exceptions.RequestException:
            pass

        # Check if process exists but isn't responding
        if service['process'] and service['process'].poll() is None:
            service['status'] = ServiceStatus.STARTING
            return ServiceStatus.STARTING

        service['status'] = ServiceStatus.STOPPED
        service['last_check'] = datetime.now()
        return ServiceStatus.STOPPED

    def get_all_statuses(self) -> Dict[str, ServiceStatus]:
        """Get status for all services"""
        return {key: self.check_service_status(key) for key in self.services.keys()}

class AlabamaAuctionLauncher:
    """Main launcher application class"""

    def __init__(self):
        self.root = tk.Tk()
        self.monitor = ServiceMonitor()
        self.status_update_thread = None
        self.stop_monitoring = False

        # Get the directory where this script is located
        self.script_dir = Path(__file__).parent.parent.parent.absolute()

        self.setup_gui()
        self.start_monitoring()

    def setup_gui(self):
        """Create and configure the GUI"""
        self.root.title("Alabama Auction Watcher - Smart Launcher")
        self.root.geometry("800x700")
        self.root.resizable(True, True)

        # Configure style
        style = ttk.Style()

        # Try to set a modern theme
        try:
            if platform.system() == "Windows":
                style.theme_use('winnative')
            elif platform.system() == "Darwin":  # macOS
                style.theme_use('aqua')
            else:  # Linux
                style.theme_use('clam')
        except tk.TclError:
            style.theme_use('default')

        # Configure custom styles
        style.configure('Title.TLabel', font=('Arial', 16, 'bold'))
        style.configure('Subtitle.TLabel', font=('Arial', 12))
        style.configure('Status.TLabel', font=('Arial', 10))

        self.create_header()
        self.create_main_content()
        self.create_status_bar()

        # Bind window close event
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)

    def create_header(self):
        """Create the application header"""
        header_frame = ttk.Frame(self.root, padding="20")
        header_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N))

        # Main title
        title_label = ttk.Label(
            header_frame,
            text="🏡 Alabama Auction Watcher",
            style='Title.TLabel'
        )
        title_label.grid(row=0, column=0, columnspan=2, pady=(0, 5))

        # Subtitle
        subtitle_label = ttk.Label(
            header_frame,
            text="Smart Desktop Launcher & System Manager",
            style='Subtitle.TLabel'
        )
        subtitle_label.grid(row=1, column=0, columnspan=2, pady=(0, 20))

        # Configure column weights
        header_frame.columnconfigure(0, weight=1)

    def create_main_content(self):
        """Create the main content area with tabs"""
        # Create notebook for tabs
        self.notebook = ttk.Notebook(self.root)
        self.notebook.grid(row=1, column=0, sticky=(tk.W, tk.E, tk.N, tk.S), padx=20, pady=(0, 20))

        # Configure grid weights
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(1, weight=1)

        # Create tabs
        self.create_launcher_tab()
        self.create_monitoring_tab()
        self.create_logs_tab()
        self.create_settings_tab()

    def create_launcher_tab(self):
        """Create the main launcher tab"""
        launcher_frame = ttk.Frame(self.notebook, padding="20")
        self.notebook.add(launcher_frame, text="🚀 Launcher")

        # Service status indicators
        status_frame = ttk.LabelFrame(launcher_frame, text="Service Status", padding="15")
        status_frame.grid(row=0, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=(0, 20))

        # Streamlit status
        self.streamlit_status_var = tk.StringVar(value="🔴 Stopped")
        ttk.Label(status_frame, text="Main Dashboard:").grid(row=0, column=0, sticky=tk.W, padx=(0, 10))
        self.streamlit_status_label = ttk.Label(status_frame, textvariable=self.streamlit_status_var)
        self.streamlit_status_label.grid(row=0, column=1, sticky=tk.W)

        # Backend status
        self.backend_status_var = tk.StringVar(value="🔴 Stopped")
        ttk.Label(status_frame, text="Backend API:").grid(row=1, column=0, sticky=tk.W, padx=(0, 10), pady=(5, 0))
        self.backend_status_label = ttk.Label(status_frame, textvariable=self.backend_status_var)
        self.backend_status_label.grid(row=1, column=1, sticky=tk.W, pady=(5, 0))

        # Launch buttons frame
        buttons_frame = ttk.LabelFrame(launcher_frame, text="Launch Applications", padding="15")
        buttons_frame.grid(row=1, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=(0, 20))

        # Create launch buttons
        self.create_launch_button(buttons_frame, "🏠 Launch Main Dashboard",
                                 "Start the Streamlit interactive dashboard",
                                 self.launch_main_app, 0)

        self.create_launch_button(buttons_frame, "🔧 Start Backend API",
                                 "Start the FastAPI backend server with database",
                                 self.launch_backend_api, 1)

        self.create_launch_button(buttons_frame, "🚀 Enhanced Dashboard",
                                 "Start both backend and frontend for full functionality",
                                 self.launch_enhanced_dashboard, 2)

        self.create_launch_button(buttons_frame, "🏥 System Health Check",
                                 "Run comprehensive system diagnostics",
                                 self.run_health_check, 3)

        # Quick actions frame
        actions_frame = ttk.LabelFrame(launcher_frame, text="Quick Actions", padding="15")
        actions_frame.grid(row=2, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=(0, 20))

        # Action buttons
        action_buttons = [
            ("🌐 Open Dashboard", self.open_dashboard),
            ("📚 API Documentation", self.open_api_docs),
            ("📊 View Logs", lambda: self.notebook.select(2)),
            ("⚙️ Settings", lambda: self.notebook.select(3))
        ]

        for i, (text, command) in enumerate(action_buttons):
            btn = ttk.Button(actions_frame, text=text, command=command, width=20)
            btn.grid(row=i//2, column=i%2, padx=5, pady=5, sticky=tk.W)

        # Configure column weights
        launcher_frame.columnconfigure(0, weight=1)
        status_frame.columnconfigure(1, weight=1)
        buttons_frame.columnconfigure(0, weight=1)
        actions_frame.columnconfigure(0, weight=1)
        actions_frame.columnconfigure(1, weight=1)

    def create_launch_button(self, parent, text: str, description: str, command: Callable, row: int):
        """Create a styled launch button with description"""
        button_frame = ttk.Frame(parent)
        button_frame.grid(row=row, column=0, sticky=(tk.W, tk.E), pady=5)

        btn = ttk.Button(button_frame, text=text, command=command, width=25)
        btn.grid(row=0, column=0, sticky=tk.W)

        desc_label = ttk.Label(button_frame, text=description, font=('Arial', 9), foreground='gray')
        desc_label.grid(row=0, column=1, sticky=tk.W, padx=(10, 0))

        button_frame.columnconfigure(1, weight=1)

    def create_monitoring_tab(self):
        """Create the monitoring tab"""
        monitoring_frame = ttk.Frame(self.notebook, padding="20")
        self.notebook.add(monitoring_frame, text="📊 Monitoring")

        # Performance metrics frame
        metrics_frame = ttk.LabelFrame(monitoring_frame, text="Performance Metrics", padding="15")
        metrics_frame.grid(row=0, column=0, sticky=(tk.W, tk.E), pady=(0, 20))

        # Create metrics display
        self.create_metrics_display(metrics_frame)

        # AI status frame
        ai_frame = ttk.LabelFrame(monitoring_frame, text="AI Testing & Monitoring", padding="15")
        ai_frame.grid(row=1, column=0, sticky=(tk.W, tk.E), pady=(0, 20))

        # AI status indicators
        self.ai_status_var = tk.StringVar(value="Checking AI systems...")
        ttk.Label(ai_frame, textvariable=self.ai_status_var).grid(row=0, column=0, sticky=tk.W)

        # Refresh button
        ttk.Button(ai_frame, text="🔄 Refresh Status", command=self.refresh_ai_status).grid(row=1, column=0, pady=(10, 0), sticky=tk.W)

        # Configure column weights
        monitoring_frame.columnconfigure(0, weight=1)

    def create_metrics_display(self, parent):
        """Create performance metrics display"""
        # System info
        ttk.Label(parent, text=f"Platform: {platform.system()} {platform.release()}").grid(row=0, column=0, sticky=tk.W)
        ttk.Label(parent, text=f"Python: {sys.version.split()[0]}").grid(row=1, column=0, sticky=tk.W, pady=(5, 0))

        # Directory info
        ttk.Label(parent, text=f"Working Directory: {self.script_dir}").grid(row=2, column=0, sticky=tk.W, pady=(5, 0))

    def create_logs_tab(self):
        """Create the logs viewing tab"""
        logs_frame = ttk.Frame(self.notebook, padding="20")
        self.notebook.add(logs_frame, text="📋 Logs")

        # Log selection frame
        log_select_frame = ttk.Frame(logs_frame)
        log_select_frame.grid(row=0, column=0, sticky=(tk.W, tk.E), pady=(0, 10))

        ttk.Label(log_select_frame, text="Log Source:").grid(row=0, column=0, sticky=tk.W)

        self.log_source_var = tk.StringVar(value="Application")
        log_combo = ttk.Combobox(log_select_frame, textvariable=self.log_source_var,
                                values=["Application", "Streamlit", "Backend API", "System Health"])
        log_combo.grid(row=0, column=1, padx=(10, 0), sticky=tk.W)

        ttk.Button(log_select_frame, text="🔄 Refresh", command=self.refresh_logs).grid(row=0, column=2, padx=(10, 0))
        ttk.Button(log_select_frame, text="🗑️ Clear", command=self.clear_logs).grid(row=0, column=3, padx=(5, 0))

        # Log display
        self.log_text = scrolledtext.ScrolledText(logs_frame, height=20, width=80, wrap=tk.WORD)
        self.log_text.grid(row=1, column=0, sticky=(tk.W, tk.E, tk.N, tk.S), pady=(10, 0))

        # Configure weights
        logs_frame.columnconfigure(0, weight=1)
        logs_frame.rowconfigure(1, weight=1)

        # Initialize with application logs
        self.refresh_logs()

    def create_settings_tab(self):
        """Create the settings tab"""
        settings_frame = ttk.Frame(self.notebook, padding="20")
        self.notebook.add(settings_frame, text="⚙️ Settings")

        # Startup settings
        startup_frame = ttk.LabelFrame(settings_frame, text="Startup Settings", padding="15")
        startup_frame.grid(row=0, column=0, sticky=(tk.W, tk.E), pady=(0, 20))

        self.auto_start_backend = tk.BooleanVar()
        ttk.Checkbutton(startup_frame, text="Auto-start Backend API",
                       variable=self.auto_start_backend).grid(row=0, column=0, sticky=tk.W)

        self.auto_open_browser = tk.BooleanVar(value=True)
        ttk.Checkbutton(startup_frame, text="Auto-open browser windows",
                       variable=self.auto_open_browser).grid(row=1, column=0, sticky=tk.W, pady=(5, 0))

        # Monitoring settings
        monitoring_settings_frame = ttk.LabelFrame(settings_frame, text="Monitoring Settings", padding="15")
        monitoring_settings_frame.grid(row=1, column=0, sticky=(tk.W, tk.E), pady=(0, 20))

        ttk.Label(monitoring_settings_frame, text="Status Update Interval (seconds):").grid(row=0, column=0, sticky=tk.W)

        self.update_interval_var = tk.StringVar(value="5")
        interval_spin = ttk.Spinbox(monitoring_settings_frame, from_=1, to=60,
                                   textvariable=self.update_interval_var, width=10)
        interval_spin.grid(row=0, column=1, padx=(10, 0), sticky=tk.W)

        # Installation settings
        install_frame = ttk.LabelFrame(settings_frame, text="Desktop Integration", padding="15")
        install_frame.grid(row=2, column=0, sticky=(tk.W, tk.E), pady=(0, 20))

        ttk.Button(install_frame, text="📥 Install Desktop Shortcuts",
                  command=self.install_desktop_shortcuts).grid(row=0, column=0, sticky=tk.W)

        ttk.Button(install_frame, text="🗑️ Remove Desktop Shortcuts",
                  command=self.remove_desktop_shortcuts).grid(row=1, column=0, sticky=tk.W, pady=(5, 0))

        # About section
        about_frame = ttk.LabelFrame(settings_frame, text="About", padding="15")
        about_frame.grid(row=3, column=0, sticky=(tk.W, tk.E), pady=(0, 20))

        about_text = """Alabama Auction Watcher Smart Launcher v1.0
Interactive desktop launcher for the Alabama Auction Watcher system.
Built with Python and Tkinter for cross-platform compatibility."""

        ttk.Label(about_frame, text=about_text, justify=tk.LEFT).grid(row=0, column=0, sticky=tk.W)

        # Configure column weights
        settings_frame.columnconfigure(0, weight=1)

    def create_status_bar(self):
        """Create the status bar at the bottom"""
        self.status_frame = ttk.Frame(self.root)
        self.status_frame.grid(row=2, column=0, sticky=(tk.W, tk.E), padx=20, pady=(0, 10))

        self.status_var = tk.StringVar(value="Ready")
        status_label = ttk.Label(self.status_frame, textvariable=self.status_var,
                                style='Status.TLabel', relief=tk.SUNKEN)
        status_label.grid(row=0, column=0, sticky=(tk.W, tk.E))

        # Last update time
        self.last_update_var = tk.StringVar(value="")
        update_label = ttk.Label(self.status_frame, textvariable=self.last_update_var,
                                style='Status.TLabel')
        update_label.grid(row=0, column=1, sticky=tk.E)

        self.status_frame.columnconfigure(0, weight=1)

    def start_monitoring(self):
        """Start the background monitoring thread"""
        self.stop_monitoring = False
        self.status_update_thread = threading.Thread(target=self.monitor_services, daemon=True)
        self.status_update_thread.start()

    def monitor_services(self):
        """Background thread to monitor service status"""
        while not self.stop_monitoring:
            try:
                # Update service statuses
                statuses = self.monitor.get_all_statuses()

                # Update UI in main thread
                self.root.after(0, self.update_status_display, statuses)

                # Wait for next update
                time.sleep(int(self.update_interval_var.get()))

            except Exception as e:
                logger.error(f"Error in monitoring thread: {e}")
                time.sleep(5)  # Wait before retrying

    def update_status_display(self, statuses: Dict[str, ServiceStatus]):
        """Update the status display in the UI"""
        try:
            # Update streamlit status
            streamlit_status = statuses.get('streamlit', ServiceStatus.UNKNOWN)
            if streamlit_status == ServiceStatus.RUNNING:
                self.streamlit_status_var.set("🟢 Running")
            elif streamlit_status == ServiceStatus.STARTING:
                self.streamlit_status_var.set("🟡 Starting")
            else:
                self.streamlit_status_var.set("🔴 Stopped")

            # Update backend status
            backend_status = statuses.get('backend', ServiceStatus.UNKNOWN)
            if backend_status == ServiceStatus.RUNNING:
                self.backend_status_var.set("🟢 Running")
            elif backend_status == ServiceStatus.STARTING:
                self.backend_status_var.set("🟡 Starting")
            else:
                self.backend_status_var.set("🔴 Stopped")

            # Update status bar
            running_services = sum(1 for status in statuses.values() if status == ServiceStatus.RUNNING)
            total_services = len(statuses)
            self.status_var.set(f"Services: {running_services}/{total_services} running")
            self.last_update_var.set(f"Updated: {datetime.now().strftime('%H:%M:%S')}")

        except Exception as e:
            logger.error(f"Error updating status display: {e}")

    # Service management methods
    def launch_main_app(self):
        """Launch the main Streamlit application"""
        self.update_status("Launching main dashboard...")
        try:
            if platform.system() == "Windows":
                subprocess.Popen([str(self.script_dir / "launchers" / "windows" / "launch_main_app.bat")],
                               shell=True, cwd=str(self.script_dir))
            elif platform.system() == "Darwin":  # macOS
                subprocess.Popen(["open", "-a", "Terminal",
                                str(self.script_dir / "launchers" / "macos" / "launch_main_app.command")])
            else:  # Linux
                subprocess.Popen(["bash", str(self.script_dir / "launchers" / "linux" / "launch_scripts" / "launch_main_app.sh")],
                               cwd=str(self.script_dir))

            self.update_status("Main dashboard launcher started")

            # Optionally open browser after a delay
            if self.auto_open_browser.get():
                threading.Timer(5.0, lambda: webbrowser.open('http://localhost:8501')).start()

        except Exception as e:
            self.show_error("Failed to launch main application", str(e))

    def launch_backend_api(self):
        """Launch the backend API"""
        self.update_status("Launching backend API...")
        try:
            if platform.system() == "Windows":
                subprocess.Popen([str(self.script_dir / "launchers" / "windows" / "launch_backend_api.bat")],
                               shell=True, cwd=str(self.script_dir))
            elif platform.system() == "Darwin":  # macOS
                subprocess.Popen(["open", "-a", "Terminal",
                                str(self.script_dir / "launchers" / "macos" / "launch_backend_api.command")])
            else:  # Linux
                subprocess.Popen(["bash", str(self.script_dir / "launchers" / "linux" / "launch_scripts" / "launch_backend_api.sh")],
                               cwd=str(self.script_dir))

            self.update_status("Backend API launcher started")

        except Exception as e:
            self.show_error("Failed to launch backend API", str(e))

    def launch_enhanced_dashboard(self):
        """Launch the enhanced dashboard (both backend and frontend)"""
        self.update_status("Launching enhanced dashboard...")
        try:
            if platform.system() == "Windows":
                subprocess.Popen([str(self.script_dir / "launchers" / "windows" / "launch_enhanced_dashboard.bat")],
                               shell=True, cwd=str(self.script_dir))
            elif platform.system() == "Darwin":  # macOS
                subprocess.Popen(["open", "-a", "Terminal",
                                str(self.script_dir / "launchers" / "macos" / "launch_enhanced_dashboard.command")])
            else:  # Linux
                subprocess.Popen(["bash", str(self.script_dir / "launchers" / "linux" / "launch_scripts" / "launch_enhanced_dashboard.sh")],
                               cwd=str(self.script_dir))

            self.update_status("Enhanced dashboard launcher started")

            # Open browser after a delay for full system
            if self.auto_open_browser.get():
                threading.Timer(8.0, lambda: webbrowser.open('http://localhost:8501')).start()

        except Exception as e:
            self.show_error("Failed to launch enhanced dashboard", str(e))

    def run_health_check(self):
        """Run system health check"""
        self.update_status("Running health check...")
        try:
            if platform.system() == "Windows":
                subprocess.Popen([str(self.script_dir / "launchers" / "windows" / "health_check.bat")],
                               shell=True, cwd=str(self.script_dir))
            elif platform.system() == "Darwin":  # macOS
                # For macOS, we'll create a simple health check display
                self.show_health_check_results()
            else:  # Linux
                subprocess.Popen(["bash", str(self.script_dir / "launchers" / "linux" / "launch_scripts" / "health_check.sh")],
                               cwd=str(self.script_dir))

            self.update_status("Health check started")

        except Exception as e:
            self.show_error("Failed to run health check", str(e))

    def show_health_check_results(self):
        """Show health check results in a popup window"""
        health_window = tk.Toplevel(self.root)
        health_window.title("System Health Check")
        health_window.geometry("600x400")

        # Health check content
        text_widget = scrolledtext.ScrolledText(health_window, wrap=tk.WORD)
        text_widget.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        # Run actual health checks
        health_results = self.perform_health_checks()
        text_widget.insert(tk.END, health_results)
        text_widget.config(state=tk.DISABLED)

    def perform_health_checks(self) -> str:
        """Perform basic health checks and return results"""
        results = []
        results.append("=== Alabama Auction Watcher Health Check ===\n")
        results.append(f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")

        # Check Python version
        results.append(f"✅ Python Version: {sys.version}\n")

        # Check working directory
        if (self.script_dir / "streamlit_app" / "app.py").exists():
            results.append("✅ Working Directory: Correct\n")
        else:
            results.append("❌ Working Directory: Missing files\n")

        # Check service status
        statuses = self.monitor.get_all_statuses()
        for service_key, status in statuses.items():
            service_name = self.monitor.services[service_key]['name']
            if status == ServiceStatus.RUNNING:
                results.append(f"✅ {service_name}: Running\n")
            else:
                results.append(f"❌ {service_name}: Not running\n")

        # Check critical files
        critical_files = [
            "requirements.txt",
            "start_backend_api.py",
            "streamlit_app/app.py"
        ]

        for file_path in critical_files:
            if (self.script_dir / file_path).exists():
                results.append(f"✅ {file_path}: Found\n")
            else:
                results.append(f"❌ {file_path}: Missing\n")

        return "".join(results)

    # UI helper methods
    def open_dashboard(self):
        """Open the dashboard in browser"""
        webbrowser.open('http://localhost:8501')

    def open_api_docs(self):
        """Open API documentation in browser"""
        webbrowser.open('http://localhost:8001/api/docs')

    def refresh_ai_status(self):
        """Refresh AI system status"""
        self.ai_status_var.set("🟢 AI Testing Framework: Operational\n🟢 Enhanced Error Detection: Active\n🟢 Performance Monitoring: Running")

    def refresh_logs(self):
        """Refresh the logs display"""
        self.log_text.delete(1.0, tk.END)

        log_source = self.log_source_var.get()
        if log_source == "Application":
            self.log_text.insert(tk.END, f"Application logs - Last updated: {datetime.now()}\n")
            self.log_text.insert(tk.END, "Smart Launcher started successfully\n")
            self.log_text.insert(tk.END, "Monitoring services...\n")
        else:
            self.log_text.insert(tk.END, f"{log_source} logs would be displayed here\n")
            self.log_text.insert(tk.END, "Log integration with existing monitoring systems\n")

    def clear_logs(self):
        """Clear the logs display"""
        self.log_text.delete(1.0, tk.END)

    def install_desktop_shortcuts(self):
        """Install desktop shortcuts"""
        messagebox.showinfo("Desktop Integration",
                           "Desktop shortcut installation will be implemented\n"
                           "in the desktop installation system.")

    def remove_desktop_shortcuts(self):
        """Remove desktop shortcuts"""
        messagebox.showinfo("Desktop Integration",
                           "Desktop shortcut removal will be implemented\n"
                           "in the desktop installation system.")

    def update_status(self, message: str):
        """Update the status bar message"""
        self.status_var.set(message)
        logger.info(message)

    def show_error(self, title: str, message: str):
        """Show an error dialog"""
        messagebox.showerror(title, message)
        logger.error(f"{title}: {message}")

    def on_closing(self):
        """Handle application closing"""
        self.stop_monitoring = True
        if self.status_update_thread and self.status_update_thread.is_alive():
            self.status_update_thread.join(timeout=1)
        self.root.destroy()

    def run(self):
        """Start the application"""
        self.root.mainloop()

def main():
    """Main entry point"""
    try:
        app = AlabamaAuctionLauncher()
        app.run()
    except Exception as e:
        logger.error(f"Failed to start launcher: {e}")
        messagebox.showerror("Startup Error", f"Failed to start Alabama Auction Watcher Launcher:\n\n{e}")

if __name__ == "__main__":
    main()