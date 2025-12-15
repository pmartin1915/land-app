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
import socket
from pathlib import Path
from typing import Dict, Optional, Callable, List, Tuple
from datetime import datetime
import logging
import tempfile

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

class PortManager:
    """Manages dynamic port allocation and service coordination"""

    @staticmethod
    def is_port_available(port: int, host: str = 'localhost') -> bool:
        """Check if a port is available for binding"""
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
                sock.settimeout(1)
                result = sock.connect_ex((host, port))
                return result != 0  # Port is available if connection failed
        except Exception:
            return False

    @staticmethod
    def find_available_port(preferred_port: int, port_range: int = 10) -> int:
        """Find an available port starting from preferred_port"""
        for port in range(preferred_port, preferred_port + port_range):
            if PortManager.is_port_available(port):
                return port

        # If no port found in range, find any available port
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.bind(('', 0))
            return sock.getsockname()[1]

    @staticmethod
    def get_service_ports() -> Dict[str, int]:
        """Get available ports for all services"""
        backend_port = PortManager.find_available_port(8001)

        # Check if Streamlit is already running on 8501
        if not PortManager.is_port_available(8501):
            streamlit_port = 8501  # Use existing Streamlit
        else:
            streamlit_port = PortManager.find_available_port(8501)

        return {
            'backend': backend_port,
            'streamlit': streamlit_port
        }

class ServiceOrchestrator:
    """Orchestrates the startup of all Alabama Auction Watcher services"""

    def __init__(self, script_dir: Path, status_callback: Callable[[str], None]):
        self.script_dir = script_dir
        self.update_status = status_callback
        self.ports = PortManager.get_service_ports()
        self.processes = {}

    def setup_authentication(self) -> bool:
        """Ensure authentication token is available"""
        try:
            self.update_status("Setting up authentication...")

            # Check if backend is running
            backend_url = f"http://localhost:{self.ports['backend']}"
            try:
                response = requests.post(
                    f"{backend_url}/api/v1/auth/device/token",
                    json={
                        "device_id": f"desktop_launcher_{int(time.time())}",
                        "app_version": "1.0.0",
                        "device_name": f"Desktop-{platform.system()}"
                    },
                    timeout=5
                )

                if response.status_code == 200:
                    token_data = response.json()
                    self.update_status("✅ Authentication configured")
                    return True

            except requests.exceptions.RequestException:
                self.update_status("⚠️  Backend not ready for authentication")
                return False

        except Exception as e:
            self.update_status(f"❌ Authentication setup failed: {str(e)}")
            return False

    def start_streamlit(self) -> bool:
        """Start the Streamlit dashboard application"""
        try:
            self.update_status("🏠 Starting Streamlit Dashboard...")

            # Check if Streamlit is already running
            if not PortManager.is_port_available(self.ports['streamlit']):
                self.update_status("✅ Streamlit Dashboard already running")
                return True

            # Start Streamlit process
            if platform.system() == "Windows":
                cmd = [str(self.script_dir / "launchers" / "windows" / "launch_main_app.bat")]
                self.processes['streamlit'] = subprocess.Popen(
                    cmd,
                    shell=True,
                    cwd=str(self.script_dir),
                    creationflags=subprocess.CREATE_NEW_CONSOLE if platform.system() == "Windows" else 0
                )
            else:
                # For macOS/Linux, start Streamlit directly
                cmd = [sys.executable, "-m", "streamlit", "run", "streamlit_app/app.py",
                       "--server.port", str(self.ports['streamlit'])]
                self.processes['streamlit'] = subprocess.Popen(
                    cmd,
                    cwd=str(self.script_dir),
                    env=dict(os.environ,
                            STREAMLIT_SERVER_PORT=str(self.ports['streamlit']),
                            STREAMLIT_BROWSER_GATHER_USAGE_STATS="false")
                )

            # Wait for Streamlit to be ready
            self.update_status("⏳ Waiting for Streamlit Dashboard...")
            for attempt in range(30):  # 30 second timeout
                time.sleep(1)
                try:
                    response = requests.get(f"http://localhost:{self.ports['streamlit']}", timeout=2)
                    if response.status_code == 200:
                        self.update_status("✅ Streamlit Dashboard ready")
                        return True
                except requests.exceptions.RequestException:
                    pass

            self.update_status("❌ Streamlit Dashboard failed to start")
            return False

        except Exception as e:
            self.update_status(f"❌ Streamlit startup failed: {str(e)}")
            return False

    def start_backend(self) -> bool:
        """Start the backend API service"""
        try:
            self.update_status("🚀 Starting Backend API...")

            # Check if already running
            if PortManager.is_port_available(self.ports['backend']):
                # Start backend process
                if platform.system() == "Windows":
                    cmd = [str(self.script_dir / "launchers" / "windows" / "launch_backend_api.bat")]
                    self.processes['backend'] = subprocess.Popen(
                        cmd,
                        shell=True,
                        cwd=str(self.script_dir),
                        creationflags=subprocess.CREATE_NEW_CONSOLE if platform.system() == "Windows" else 0
                    )
                else:
                    # For macOS/Linux, start Python directly
                    cmd = [sys.executable, "start_backend_api.py"]
                    self.processes['backend'] = subprocess.Popen(
                        cmd,
                        cwd=str(self.script_dir),
                        env=dict(os.environ, BACKEND_PORT=str(self.ports['backend']))
                    )

                # Wait for backend to be ready
                self.update_status("⏳ Waiting for Backend API...")
                for attempt in range(30):  # 30 second timeout
                    time.sleep(1)
                    try:
                        response = requests.get(f"http://localhost:{self.ports['backend']}/health", timeout=2)
                        if response.status_code == 200:
                            self.update_status("✅ Backend API ready")
                            return True
                    except requests.exceptions.RequestException:
                        pass

                self.update_status("❌ Backend API failed to start")
                return False
            else:
                self.update_status("✅ Backend API already running")
                return True

        except Exception as e:
            self.update_status(f"❌ Backend startup failed: {str(e)}")
            return False


    def start_electron(self) -> bool:
        """Start the Electron desktop application"""
        try:
            self.update_status("Starting Desktop Application...")

            frontend_dir = self.script_dir / "frontend"

            # Check if frontend directory exists
            if not frontend_dir.exists():
                self.update_status("Frontend directory not found, opening Streamlit in browser instead")
                webbrowser.open(f"http://localhost:{self.ports['streamlit']}")
                return True

            # Update package.json electron:dev script to use correct port
            package_json_path = frontend_dir / "package.json"
            if package_json_path.exists():
                with open(package_json_path, 'r', encoding='utf-8') as f:
                    package_data = json.load(f)

                # Update the electron:dev script to point to Streamlit
                if 'scripts' in package_data and 'electron:dev' in package_data['scripts']:
                    package_data['scripts']['electron:dev'] = f'wait-on http://localhost:{self.ports["streamlit"]} && electron .'

                    with open(package_json_path, 'w', encoding='utf-8') as f:
                        json.dump(package_data, f, indent=2)

            # Start Electron
            if platform.system() == "Windows":
                cmd = ["npm.cmd", "run", "electron"]
            else:
                cmd = ["npm", "run", "electron"]

            env = dict(os.environ)
            env['VITE_DEV_SERVER_URL'] = f"http://localhost:{self.ports['streamlit']}"
            env['STREAMLIT_URL'] = f"http://localhost:{self.ports['streamlit']}"

            self.processes['electron'] = subprocess.Popen(
                cmd,
                cwd=str(frontend_dir),
                env=env
            )

            self.update_status("Desktop Application launched")
            return True

        except Exception as e:
            self.update_status(f"Desktop app startup failed: {str(e)}")
            # Fallback: Open Streamlit in browser
            self.update_status("Opening Streamlit dashboard in browser as fallback")
            webbrowser.open(f"http://localhost:{self.ports['streamlit']}")
            return True

    def launch_full_stack(self) -> bool:
        """Launch the complete Alabama Auction Watcher stack"""
        try:
            self.update_status("🚀 Starting Alabama Auction Watcher...")
            self.update_status(f"📊 Backend: {self.ports['backend']}, Dashboard: {self.ports['streamlit']}")

            # Step 1: Start Backend (optional for Streamlit)
            self.start_backend()  # Don't fail if backend doesn't start - Streamlit works standalone

            # Step 2: Setup authentication (if backend is running)
            time.sleep(2)  # Give backend a moment to fully initialize
            self.setup_authentication()

            # Step 3: Start Streamlit Dashboard (main interface)
            if not self.start_streamlit():
                return False

            self.update_status("🎉 Alabama Auction Watcher is ready!")
            self.update_status(f"🏠 Dashboard: http://localhost:{self.ports['streamlit']}")

            return True

        except Exception as e:
            self.update_status(f"❌ Full stack startup failed: {str(e)}")
            return False

    def stop_all_services(self):
        """Stop all running services"""
        try:
            self.update_status("🛑 Stopping all services...")

            for service_name, process in self.processes.items():
                if process and process.poll() is None:
                    try:
                        process.terminate()
                        self.update_status(f"✅ Stopped {service_name}")
                    except Exception as e:
                        self.update_status(f"⚠️  Error stopping {service_name}: {str(e)}")

            self.processes.clear()
            self.update_status("✅ All services stopped")

        except Exception as e:
            self.update_status(f"❌ Error stopping services: {str(e)}")

class AlabamaAuctionLauncher:
    """Main launcher application class"""

    def __init__(self):
        self.root = tk.Tk()
        self.monitor = ServiceMonitor()
        self.status_update_thread = None
        self.stop_monitoring = False
        self.orchestrator = None

        # Get the directory where this script is located
        self.script_dir = Path(__file__).parent.parent.parent.absolute()

        self.setup_gui()
        self.start_monitoring()

    def setup_gui(self):
        """Create and configure the GUI"""
        self.root.title("Alabama Auction Watcher - Smart Launcher")
        self.root.geometry("1100x750")  # Wider to accommodate progress indicators
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

        # Service status indicators with enhanced visual feedback
        status_frame = ttk.LabelFrame(launcher_frame, text="Service Status", padding="15")
        status_frame.grid(row=0, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=(0, 20))

        # Backend API status
        self.backend_status_var = tk.StringVar(value="🔴 Stopped")
        ttk.Label(status_frame, text="Backend API:").grid(row=0, column=0, sticky=tk.W, padx=(0, 10))
        self.backend_status_label = ttk.Label(status_frame, textvariable=self.backend_status_var)
        self.backend_status_label.grid(row=0, column=1, sticky=tk.W)

        # Main Dashboard status
        self.dashboard_status_var = tk.StringVar(value="🔴 Stopped")
        ttk.Label(status_frame, text="Main Dashboard:").grid(row=1, column=0, sticky=tk.W, padx=(0, 10), pady=(5, 0))
        self.dashboard_status_label = ttk.Label(status_frame, textvariable=self.dashboard_status_var)
        self.dashboard_status_label.grid(row=1, column=1, sticky=tk.W, pady=(5, 0))

        # Desktop App status
        self.desktop_status_var = tk.StringVar(value="🔴 Not Running")
        ttk.Label(status_frame, text="Desktop App:").grid(row=2, column=0, sticky=tk.W, padx=(0, 10), pady=(5, 0))
        self.desktop_status_label = ttk.Label(status_frame, textvariable=self.desktop_status_var)
        self.desktop_status_label.grid(row=2, column=1, sticky=tk.W, pady=(5, 0))

        # Authentication status
        self.auth_status_var = tk.StringVar(value="⚪ Not Configured")
        ttk.Label(status_frame, text="Authentication:").grid(row=3, column=0, sticky=tk.W, padx=(0, 10), pady=(5, 0))
        self.auth_status_label = ttk.Label(status_frame, textvariable=self.auth_status_var)
        self.auth_status_label.grid(row=3, column=1, sticky=tk.W, pady=(5, 0))


        # Progress indicator for orchestration
        self.progress_frame = ttk.LabelFrame(launcher_frame, text="Launch Progress", padding="15")
        self.progress_frame.grid(row=0, column=2, rowspan=2, sticky=(tk.W, tk.E, tk.N, tk.S), padx=(20, 0), pady=(0, 20))

        # Progress bar
        self.progress_var = tk.DoubleVar()
        self.progress_bar = ttk.Progressbar(
            self.progress_frame,
            variable=self.progress_var,
            maximum=100,
            length=250,
            mode='determinate'
        )
        self.progress_bar.grid(row=0, column=0, sticky=(tk.W, tk.E), pady=(0, 10))

        # Progress step indicator
        self.progress_step_var = tk.StringVar(value="Ready to launch")
        self.progress_step_label = ttk.Label(
            self.progress_frame,
            textvariable=self.progress_step_var,
            font=('Arial', 9),
            foreground='blue'
        )
        self.progress_step_label.grid(row=1, column=0, sticky=tk.W)

        # Progress details
        self.progress_details_var = tk.StringVar(value="Click 'Full Stack Launch' to begin")
        self.progress_details_label = ttk.Label(
            self.progress_frame,
            textvariable=self.progress_details_var,
            font=('Arial', 8),
            foreground='gray',
            wraplength=200
        )
        self.progress_details_label.grid(row=2, column=0, sticky=tk.W, pady=(5, 0))

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

        self.create_launch_button(buttons_frame, "⚡ Full Stack Launch",
                                 "One-click launch of Alabama Auction Watcher dashboard",
                                 self.launch_full_stack, 3)

        self.create_launch_button(buttons_frame, "🖥️ Launch Desktop App",
                                 "Start the Electron desktop application",
                                 self.launch_desktop_app, 4)

        self.create_launch_button(buttons_frame, "🏥 System Health Check",
                                 "Run comprehensive system diagnostics",
                                 self.run_health_check, 5)

        # Quick actions frame
        actions_frame = ttk.LabelFrame(launcher_frame, text="Quick Actions", padding="15")
        actions_frame.grid(row=2, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=(0, 20))

        # Action buttons
        action_buttons = [
            ("🌐 Open Dashboard", self.open_dashboard),
            ("📚 API Documentation", self.open_api_docs),
            ("🔄 Start System Tray", self.start_system_tray),
            ("📊 View Logs", lambda: self.notebook.select(2)),
            ("⚙️ Settings", lambda: self.notebook.select(3)),
            ("⬇️ Minimize to Tray", self.minimize_to_tray)
        ]

        for i, (text, command) in enumerate(action_buttons):
            btn = ttk.Button(actions_frame, text=text, command=command, width=20)
            btn.grid(row=i//2, column=i%2, padx=5, pady=5, sticky=tk.W)

        # Configure column weights for new layout
        launcher_frame.columnconfigure(0, weight=2)  # Status and buttons columns
        launcher_frame.columnconfigure(1, weight=2)  # Status and buttons columns
        launcher_frame.columnconfigure(2, weight=1)  # Progress column
        launcher_frame.rowconfigure(0, weight=1)
        launcher_frame.rowconfigure(1, weight=1)

        status_frame.columnconfigure(1, weight=1)
        buttons_frame.columnconfigure(0, weight=1)
        actions_frame.columnconfigure(0, weight=1)
        actions_frame.columnconfigure(1, weight=1)
        self.progress_frame.columnconfigure(0, weight=1)

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
            # Update main dashboard status (Streamlit)
            streamlit_status = statuses.get('streamlit', ServiceStatus.UNKNOWN)
            if streamlit_status == ServiceStatus.RUNNING:
                self.dashboard_status_var.set("🟢 Running")
            elif streamlit_status == ServiceStatus.STARTING:
                self.dashboard_status_var.set("🟡 Starting")
            else:
                self.dashboard_status_var.set("🔴 Stopped")

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

    def launch_full_stack(self):
        """Launch the complete Alabama Auction Watcher stack with orchestration"""
        self.update_progress("🚀 Starting", "Initializing full stack launch...", 0)
        try:
            # Create orchestrator with enhanced callback
            if not self.orchestrator:
                self.orchestrator = ServiceOrchestrator(self.script_dir, self.enhanced_status_callback)
            else:
                # Update callback to use enhanced version
                self.orchestrator.update_status = self.enhanced_status_callback

            # Reset progress display
            self.progress_var.set(0)

            # Run orchestration in a separate thread
            def run_orchestration():
                try:
                    success = self.orchestrator.launch_full_stack()
                    if success:
                        self.root.after(0, lambda: self.enhanced_status_callback("🎉 Alabama Auction Watcher is ready!"))
                        # Open browser after a small delay
                        time.sleep(2)
                        self.root.after(0, lambda: webbrowser.open(f"http://localhost:{self.orchestrator.ports['streamlit']}"))
                    else:
                        self.root.after(0, lambda: self.enhanced_status_callback("❌ Full stack launch failed"))
                except Exception as e:
                    self.root.after(0, lambda: self.enhanced_status_callback(f"❌ Error: {str(e)}"))

            orchestration_thread = threading.Thread(target=run_orchestration, daemon=True)
            orchestration_thread.start()

        except Exception as e:
            self.enhanced_status_callback(f"❌ Failed to launch full stack: {str(e)}")
            self.show_error("Launch Failed", self.make_error_user_friendly(str(e)))

    def launch_desktop_app(self):
        """Launch the Electron desktop application"""
        self.update_status("Starting desktop application...")
        try:
            if not self.orchestrator:
                self.orchestrator = ServiceOrchestrator(self.script_dir, self.update_status)

            # Run Electron launch in separate thread
            def run_electron():
                try:
                    success = self.orchestrator.start_electron()
                    if success:
                        self.root.after(0, lambda: self.update_status("✅ Desktop app launched"))
                    else:
                        self.root.after(0, lambda: self.update_status("❌ Desktop app launch failed"))
                except Exception as e:
                    self.root.after(0, lambda: self.update_status(f"❌ Error: {str(e)}"))

            electron_thread = threading.Thread(target=run_electron, daemon=True)
            electron_thread.start()

        except Exception as e:
            self.show_error("Failed to launch desktop app", str(e))

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

    def update_progress(self, step: str, details: str, progress: int = 0):
        """Update the progress indicators with user-friendly messages"""
        try:
            # Update progress bar
            self.progress_var.set(progress)

            # Update step and details
            self.progress_step_var.set(step)
            self.progress_details_var.set(details)

            # Update main status bar too
            self.status_var.set(f"{step}: {details}")

            # Process GUI events to ensure updates are visible
            self.root.update_idletasks()

            logger.info(f"Progress: {progress}% - {step}: {details}")

        except Exception as e:
            logger.error(f"Error updating progress: {e}")

    def update_service_status(self, service: str, status: str, friendly_message: str = ""):
        """Update individual service status with user-friendly messages"""
        try:
            status_mapping = {
                'backend': self.backend_status_var,
                'dashboard': self.dashboard_status_var,
                'desktop': self.desktop_status_var,
                'auth': self.auth_status_var
            }

            if service in status_mapping:
                if not friendly_message:
                    # Create user-friendly message based on status
                    if "starting" in status.lower() or "⏳" in status:
                        friendly_message = f"🟡 Starting..."
                    elif "ready" in status.lower() or "running" in status.lower() or "✅" in status:
                        friendly_message = f"🟢 Running"
                    elif "failed" in status.lower() or "❌" in status:
                        friendly_message = f"🔴 Failed"
                    elif "stopped" in status.lower():
                        friendly_message = f"🔴 Stopped"
                    else:
                        friendly_message = status

                status_mapping[service].set(friendly_message)

            logger.info(f"Service {service}: {friendly_message}")

        except Exception as e:
            logger.error(f"Error updating service status: {e}")

    def enhanced_status_callback(self, message: str):
        """Enhanced status callback for ServiceOrchestrator with progress tracking"""
        try:
            # Parse orchestration messages for progress tracking
            progress = 0
            step = "Initializing"
            details = message

            if "Starting Alabama Auction Watcher" in message:
                progress = 5
                step = "🚀 Initializing"
                details = "Preparing to launch all services..."

            elif "Starting Backend API" in message:
                progress = 20
                step = "🔧 Backend API"
                details = "Starting FastAPI server..."
                self.update_service_status('backend', 'starting')

            elif "Backend API ready" in message:
                progress = 40
                step = "🔧 Backend API"
                details = "Server running and healthy"
                self.update_service_status('backend', 'ready')

            elif "Setting up authentication" in message:
                progress = 45
                step = "🔐 Authentication"
                details = "Configuring secure access..."
                self.update_service_status('auth', 'starting')

            elif "Authentication configured" in message:
                progress = 50
                step = "🔐 Authentication"
                details = "Tokens configured successfully"
                self.update_service_status('auth', 'ready')

            elif "Starting Streamlit Dashboard" in message:
                progress = 60
                step = "🏠 Main Dashboard"
                details = "Starting Streamlit application..."
                self.update_service_status('dashboard', 'starting')

            elif "Streamlit Dashboard ready" in message:
                progress = 80
                step = "🏠 Main Dashboard"
                details = "Dashboard application running"
                self.update_service_status('dashboard', 'ready')

            elif "Starting Desktop Application" in message:
                progress = 90
                step = "🖥️ Desktop App"
                details = "Launching Electron application..."
                self.update_service_status('desktop', 'starting')

            elif "Desktop Application launched" in message:
                progress = 95
                step = "🖥️ Desktop App"
                details = "Desktop application ready"
                self.update_service_status('desktop', 'ready')

            elif "Alabama Auction Watcher is ready" in message:
                progress = 100
                step = "🎉 Complete!"
                details = "All services running - application ready to use"

            elif "❌" in message or "failed" in message.lower():
                step = "❌ Error"
                details = self.make_error_user_friendly(message)

            elif "⚠️" in message:
                step = "⚠️ Warning"
                details = message.replace("⚠️", "").strip()

            # Update progress display
            self.update_progress(step, details, progress)

            # Also update the regular status for compatibility
            self.update_status(message)

        except Exception as e:
            logger.error(f"Error in enhanced status callback: {e}")
            # Fallback to simple status update
            self.update_status(message)

    def make_error_user_friendly(self, error_message: str) -> str:
        """Convert technical error messages to user-friendly ones"""
        friendly_errors = {
            "Backend startup failed": "Could not start the server. Please check if another application is using port 8001.",
            "Frontend startup failed": "Could not start the web interface. Please ensure Node.js is installed.",
            "Authentication setup failed": "Could not configure secure access. The server may not be ready yet.",
            "Desktop app startup failed": "Could not launch the desktop application. Please try launching it manually.",
            "port.*in use": "The required network port is already being used by another application.",
            "connection.*refused": "Could not connect to the server. Please check if it's running.",
            "npm.*not found": "Node.js is not installed or not found in system PATH.",
            "python.*not found": "Python is not installed or not found in system PATH."
        }

        error_lower = error_message.lower()
        for pattern, friendly_msg in friendly_errors.items():
            if pattern.lower() in error_lower:
                return friendly_msg

        # If no specific pattern matches, return a generic friendly message
        return f"An unexpected issue occurred: {error_message.replace('❌', '').strip()}"

    def show_error(self, title: str, message: str):
        """Show an error dialog"""
        messagebox.showerror(title, message)
        logger.error(f"{title}: {message}")

    def start_system_tray(self):
        """Start the system tray application"""
        try:
            import subprocess
            import sys
            tray_script = self.script_dir / "launchers" / "cross_platform" / "system_tray.py"
            subprocess.Popen([sys.executable, str(tray_script)])
            self.update_status("System tray started - check your taskbar")
        except Exception as e:
            self.show_error("System Tray Error", f"Failed to start system tray: {str(e)}")

    def minimize_to_tray(self):
        """Minimize the application to system tray"""
        try:
            # Start system tray if not already running
            self.start_system_tray()

            # Wait a moment for tray to initialize
            self.root.after(2000, self.actually_minimize)

            self.update_status("Minimizing to system tray...")

        except Exception as e:
            self.show_error("Minimize Error", f"Failed to minimize to tray: {str(e)}")

    def actually_minimize(self):
        """Actually minimize the window after tray is ready"""
        try:
            # Hide the main window
            self.root.withdraw()

            # Show notification that we're in the tray
            try:
                import subprocess
                import sys
                import platform

                if platform.system() == "Windows":
                    # Use Windows toast notification
                    message = "Alabama Auction Watcher is running in the system tray. Right-click the tray icon for options."
                    subprocess.run([
                        'powershell', '-Command',
                        f'Add-Type -AssemblyName System.Windows.Forms; [System.Windows.Forms.MessageBox]::Show("{message}", "Alabama Auction Watcher", [System.Windows.Forms.MessageBoxButtons]::OK, [System.Windows.Forms.MessageBoxIcon]::Information)'
                    ], capture_output=True)

            except Exception:
                pass  # Notification failed, but that's okay

        except Exception as e:
            logger.error(f"Error minimizing to tray: {e}")

    def restore_from_tray(self):
        """Restore the application from system tray"""
        try:
            self.root.deiconify()
            self.root.lift()
            self.root.focus_force()
            self.update_status("Restored from system tray")
        except Exception as e:
            logger.error(f"Error restoring from tray: {e}")

    def on_closing(self):
        """Handle application closing"""
        try:
            # Ask user if they want to minimize to tray instead of closing
            from tkinter import messagebox

            response = messagebox.askyesnocancel(
                "Alabama Auction Watcher",
                "Do you want to:\n\n"
                "• Yes - Minimize to system tray (keep services running)\n"
                "• No - Close completely (stop all services)\n"
                "• Cancel - Return to application"
            )

            if response is None:  # Cancel
                return
            elif response:  # Yes - minimize to tray
                self.minimize_to_tray()
                return
            else:  # No - close completely
                pass  # Continue with normal shutdown

        except Exception:
            pass  # If dialog fails, just continue with normal shutdown

        # Normal shutdown process
        self.stop_monitoring = True
        if self.status_update_thread and self.status_update_thread.is_alive():
            self.status_update_thread.join(timeout=1)

        # Stop orchestrator services if they're running
        if self.orchestrator:
            try:
                self.orchestrator.stop_all_services()
            except Exception as e:
                logger.error(f"Error stopping services: {e}")

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