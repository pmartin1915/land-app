#!/usr/bin/env python3
"""
Alabama Auction Watcher System Tray Integration
Provides background system tray functionality for the Alabama Auction Watcher
with quick access to all launcher functions and real-time status monitoring.

Features:
- Cross-platform system tray icon
- Context menu with quick actions
- Real-time service status indicators
- Background monitoring
- Desktop notifications
- Auto-startup capabilities
"""

import sys
import platform
import threading
import time
import webbrowser
from pathlib import Path
import logging

# System tray implementation varies by platform
try:
    if platform.system() == "Windows":
        import pystray
        from pystray import MenuItem as item
        from PIL import Image, ImageDraw
        TRAY_AVAILABLE = True
    elif platform.system() == "Darwin":  # macOS
        import pystray
        from pystray import MenuItem as item
        from PIL import Image, ImageDraw
        TRAY_AVAILABLE = True
    else:  # Linux
        try:
            import pystray
            from pystray import MenuItem as item
            from PIL import Image, ImageDraw
            TRAY_AVAILABLE = True
        except ImportError:
            # Fallback for Linux systems without pystray
            TRAY_AVAILABLE = False
except ImportError:
    TRAY_AVAILABLE = False

# Import our service components from the main launcher
from smart_launcher import ServiceMonitor, ServiceStatus, ServiceOrchestrator, PortManager

logger = logging.getLogger(__name__)

class SystemTrayManager:
    """Manages the system tray icon and functionality"""

    def __init__(self):
        self.monitor = ServiceMonitor()
        self.icon = None
        self.is_running = False
        self.orchestrator = None
        self.script_dir = Path(__file__).parent.parent.parent.absolute()

        if not TRAY_AVAILABLE:
            logger.warning("System tray functionality not available on this platform")
            return

    def create_icon_image(self, status: str = "idle") -> Image.Image:
        """Create the tray icon image based on system status"""
        # Create a 64x64 image
        width = 64
        height = 64
        image = Image.new('RGBA', (width, height), (0, 0, 0, 0))
        draw = ImageDraw.Draw(image)

        # Define colors based on status
        if status == "running":
            primary_color = (34, 177, 76)  # Green
            secondary_color = (46, 204, 113)
        elif status == "partial":
            primary_color = (243, 156, 18)  # Orange
            secondary_color = (255, 193, 7)
        elif status == "error":
            primary_color = (231, 76, 60)  # Red
            secondary_color = (255, 99, 99)
        else:  # idle
            primary_color = (52, 73, 94)  # Gray
            secondary_color = (149, 165, 166)

        # Draw a house icon (representing the auction watcher)
        # Base of house
        draw.rectangle([width//4, height//2, 3*width//4, 3*height//4],
                      fill=primary_color, outline=secondary_color, width=2)

        # Roof
        roof_points = [
            (width//2, height//4),  # Top
            (width//6, height//2),  # Left
            (5*width//6, height//2)  # Right
        ]
        draw.polygon(roof_points, fill=secondary_color, outline=primary_color, width=2)

        # Door
        draw.rectangle([width//2 - width//12, height//2 + height//8,
                       width//2 + width//12, 3*height//4],
                      fill=(139, 69, 19))  # Brown door

        # Window
        draw.rectangle([width//4 + width//16, height//2 + width//16,
                       width//2 - width//16, height//2 + height//8],
                      fill=(135, 206, 235))  # Sky blue window

        return image

    def get_system_status(self) -> str:
        """Get overall system status"""
        try:
            statuses = self.monitor.get_all_statuses()
            running_count = sum(1 for status in statuses.values() if status == ServiceStatus.RUNNING)
            total_count = len(statuses)

            if running_count == total_count and total_count > 0:
                return "running"
            elif running_count > 0:
                return "partial"
            elif any(status == ServiceStatus.ERROR for status in statuses.values()):
                return "error"
            else:
                return "idle"
        except Exception as e:
            logger.error(f"Error getting system status: {e}")
            return "error"

    def create_menu(self):
        """Create the context menu for the tray icon"""
        return [
            item(
                "Alabama Auction Watcher",
                lambda: None,  # Header item, non-clickable
                enabled=False
            ),
            item(
                "Status",
                self.create_status_submenu()
            ),
            item("─" * 20, lambda: None, enabled=False),  # Separator
            item(
                "⚡ Full Stack Launch",
                self.launch_full_stack
            ),
            item(
                "🖥️ Desktop Application",
                self.launch_desktop_app
            ),
            item("─" * 15, lambda: None, enabled=False),  # Sub-separator
            item(
                "🏠 Launch Main Dashboard",
                self.launch_main_dashboard
            ),
            item(
                "🔧 Start Backend API",
                self.launch_backend_api
            ),
            item(
                "🚀 Enhanced Dashboard",
                self.launch_enhanced_dashboard
            ),
            item("─" * 20, lambda: None, enabled=False),  # Separator
            item(
                "Quick Actions",
                [
                    item("🌐 Open Dashboard", self.open_dashboard),
                    item("📚 API Documentation", self.open_api_docs),
                    item("🏥 Health Check", self.run_health_check),
                ]
            ),
            item(
                "Tools",
                [
                    item("📊 Show Launcher GUI", self.show_launcher_gui),
                    item("📋 View Logs", self.view_logs),
                    item("⚙️ Settings", self.show_settings),
                ]
            ),
            item("─" * 20, lambda: None, enabled=False),  # Separator
            item("❌ Exit", self.quit_application)
        ]

    def create_status_submenu(self):
        """Create status submenu with current service states"""
        try:
            statuses = self.monitor.get_all_statuses()
            menu_items = []

            for service_key, status in statuses.items():
                service_name = self.monitor.services[service_key]['name']
                if status == ServiceStatus.RUNNING:
                    status_text = f"🟢 {service_name}: Running"
                elif status == ServiceStatus.STARTING:
                    status_text = f"🟡 {service_name}: Starting"
                else:
                    status_text = f"🔴 {service_name}: Stopped"

                menu_items.append(item(status_text, lambda: None, enabled=False))

            # Add refresh option
            menu_items.append(item("─" * 15, lambda: None, enabled=False))
            menu_items.append(item("🔄 Refresh", self.refresh_status))

            return menu_items

        except Exception as e:
            logger.error(f"Error creating status submenu: {e}")
            return [item("Error loading status", lambda: None, enabled=False)]

    # Action methods
    def launch_full_stack(self, icon=None, item=None):
        """Launch the complete Alabama Auction Watcher stack with orchestration"""
        try:
            # Create orchestrator with status callback
            if not self.orchestrator:
                self.orchestrator = ServiceOrchestrator(
                    self.script_dir,
                    lambda msg: self.show_notification("Alabama Auction Watcher", msg.replace("🚀", "").replace("✅", "").strip())
                )

            # Show starting notification
            self.show_notification("Alabama Auction Watcher", "Starting full stack launch...")

            # Run orchestration in background thread
            def run_orchestration():
                try:
                    success = self.orchestrator.launch_full_stack()
                    if success:
                        self.show_notification("Alabama Auction Watcher", f"🎉 Ready! Open: http://localhost:{self.orchestrator.ports['frontend']}")
                        # Auto-open browser
                        import webbrowser
                        webbrowser.open(f"http://localhost:{self.orchestrator.ports['frontend']}")
                    else:
                        self.show_notification("Alabama Auction Watcher", "❌ Launch failed - check system resources")
                except Exception as e:
                    self.show_notification("Error", f"Launch error: {str(e)}")

            import threading
            orchestration_thread = threading.Thread(target=run_orchestration, daemon=True)
            orchestration_thread.start()

        except Exception as e:
            logger.error(f"Error launching full stack: {e}")
            self.show_notification("Error", f"Failed to start full stack: {e}")

    def launch_desktop_app(self, icon=None, item=None):
        """Launch the Electron desktop application"""
        try:
            # Check if frontend is running first
            frontend_port = 5173  # Default port
            if self.orchestrator and self.orchestrator.ports.get('frontend'):
                frontend_port = self.orchestrator.ports['frontend']

            import requests
            try:
                requests.get(f"http://localhost:{frontend_port}", timeout=2)
                # Frontend is running, launch Electron
                frontend_dir = self.script_dir / "frontend"

                if platform.system() == "Windows":
                    import subprocess
                    subprocess.Popen(["npm.cmd", "run", "electron"], cwd=str(frontend_dir))
                else:
                    import subprocess
                    subprocess.Popen(["npm", "run", "electron"], cwd=str(frontend_dir))

                self.show_notification("Alabama Auction Watcher", "Desktop application launching...")

            except requests.exceptions.RequestException:
                # Frontend not running, suggest full stack launch
                self.show_notification("Alabama Auction Watcher", "Please use 'Full Stack Launch' first to start all services")

        except Exception as e:
            logger.error(f"Error launching desktop app: {e}")
            self.show_notification("Error", f"Failed to launch desktop app: {e}")

    def launch_main_dashboard(self, icon=None, item=None):
        """Launch the main Streamlit dashboard"""
        try:
            if platform.system() == "Windows":
                import subprocess
                subprocess.Popen([str(self.script_dir / "launchers" / "windows" / "launch_main_app.bat")],
                               shell=True, cwd=str(self.script_dir))
            elif platform.system() == "Darwin":  # macOS
                import subprocess
                subprocess.Popen(["open", "-a", "Terminal",
                                str(self.script_dir / "launchers" / "macos" / "launch_main_app.command")])
            else:  # Linux
                import subprocess
                subprocess.Popen(["bash", str(self.script_dir / "launchers" / "linux" / "launch_scripts" / "launch_main_app.sh")],
                               cwd=str(self.script_dir))

            self.show_notification("Alabama Auction Watcher", "Main dashboard launcher started")

        except Exception as e:
            logger.error(f"Error launching main dashboard: {e}")
            self.show_notification("Error", f"Failed to launch main dashboard: {e}")

    def launch_backend_api(self, icon=None, item=None):
        """Launch the backend API"""
        try:
            if platform.system() == "Windows":
                import subprocess
                subprocess.Popen([str(self.script_dir / "launchers" / "windows" / "launch_backend_api.bat")],
                               shell=True, cwd=str(self.script_dir))
            elif platform.system() == "Darwin":  # macOS
                import subprocess
                subprocess.Popen(["open", "-a", "Terminal",
                                str(self.script_dir / "launchers" / "macos" / "launch_backend_api.command")])
            else:  # Linux
                import subprocess
                subprocess.Popen(["bash", str(self.script_dir / "launchers" / "linux" / "launch_scripts" / "launch_backend_api.sh")],
                               cwd=str(self.script_dir))

            self.show_notification("Alabama Auction Watcher", "Backend API launcher started")

        except Exception as e:
            logger.error(f"Error launching backend API: {e}")
            self.show_notification("Error", f"Failed to launch backend API: {e}")

    def launch_enhanced_dashboard(self, icon=None, item=None):
        """Launch the enhanced dashboard"""
        try:
            if platform.system() == "Windows":
                import subprocess
                subprocess.Popen([str(self.script_dir / "launchers" / "windows" / "launch_enhanced_dashboard.bat")],
                               shell=True, cwd=str(self.script_dir))
            elif platform.system() == "Darwin":  # macOS
                import subprocess
                subprocess.Popen(["open", "-a", "Terminal",
                                str(self.script_dir / "launchers" / "macos" / "launch_enhanced_dashboard.command")])
            else:  # Linux
                import subprocess
                subprocess.Popen(["bash", str(self.script_dir / "launchers" / "linux" / "launch_scripts" / "launch_enhanced_dashboard.sh")],
                               cwd=str(self.script_dir))

            self.show_notification("Alabama Auction Watcher", "Enhanced dashboard launcher started")

        except Exception as e:
            logger.error(f"Error launching enhanced dashboard: {e}")
            self.show_notification("Error", f"Failed to launch enhanced dashboard: {e}")

    def open_dashboard(self, icon=None, item=None):
        """Open the dashboard in browser"""
        webbrowser.open('http://localhost:8501')

    def open_api_docs(self, icon=None, item=None):
        """Open API documentation in browser"""
        webbrowser.open('http://localhost:8001/api/docs')

    def run_health_check(self, icon=None, item=None):
        """Run system health check"""
        try:
            if platform.system() == "Windows":
                import subprocess
                subprocess.Popen([str(self.script_dir / "launchers" / "windows" / "health_check.bat")],
                               shell=True, cwd=str(self.script_dir))
            else:
                # For non-Windows, show a simple status
                self.show_health_status()

        except Exception as e:
            logger.error(f"Error running health check: {e}")
            self.show_notification("Error", f"Failed to run health check: {e}")

    def show_health_status(self):
        """Show a simple health status notification"""
        try:
            statuses = self.monitor.get_all_statuses()
            running_count = sum(1 for status in statuses.values() if status == ServiceStatus.RUNNING)
            total_count = len(statuses)

            message = f"Services: {running_count}/{total_count} running"
            self.show_notification("System Health", message)

        except Exception as e:
            self.show_notification("Health Check", f"Error: {e}")

    def show_launcher_gui(self, icon=None, item=None):
        """Show the main launcher GUI"""
        try:
            import subprocess
            import sys
            subprocess.Popen([sys.executable, str(self.script_dir / "launchers" / "cross_platform" / "smart_launcher.py")])
        except Exception as e:
            logger.error(f"Error showing launcher GUI: {e}")

    def view_logs(self, icon=None, item=None):
        """View application logs"""
        self.show_notification("Logs", "Log viewing functionality available in main launcher GUI")

    def show_settings(self, icon=None, item=None):
        """Show settings"""
        self.show_notification("Settings", "Settings available in main launcher GUI")

    def refresh_status(self, icon=None, item=None):
        """Refresh service status"""
        try:
            # Force a status update
            self.monitor.get_all_statuses()
            self.update_icon()
            self.show_notification("Status", "Service status refreshed")
        except Exception as e:
            logger.error(f"Error refreshing status: {e}")

    def show_notification(self, title: str, message: str):
        """Show a desktop notification"""
        if TRAY_AVAILABLE and self.icon:
            try:
                self.icon.notify(message, title)
            except Exception as e:
                logger.error(f"Error showing notification: {e}")

    def update_icon(self):
        """Update the tray icon based on current status"""
        if TRAY_AVAILABLE and self.icon:
            try:
                current_status = self.get_system_status()
                new_image = self.create_icon_image(current_status)
                self.icon.icon = new_image
            except Exception as e:
                logger.error(f"Error updating icon: {e}")

    def quit_application(self, icon=None, item=None):
        """Quit the system tray application"""
        self.is_running = False
        if self.icon:
            self.icon.stop()

    def monitoring_loop(self):
        """Background monitoring loop"""
        while self.is_running:
            try:
                self.update_icon()
                time.sleep(10)  # Update every 10 seconds
            except Exception as e:
                logger.error(f"Error in monitoring loop: {e}")
                time.sleep(30)  # Wait longer on error

    def start(self):
        """Start the system tray application"""
        if not TRAY_AVAILABLE:
            print("System tray functionality not available on this platform")
            print("Please install pystray and pillow: pip install pystray pillow")
            return False

        try:
            # Create initial icon
            initial_image = self.create_icon_image("idle")

            # Create the tray icon
            self.icon = pystray.Icon(
                "alabama_auction_watcher",
                initial_image,
                "Alabama Auction Watcher",
                menu=pystray.Menu(*self.create_menu())
            )

            self.is_running = True

            # Start monitoring in background
            monitoring_thread = threading.Thread(target=self.monitoring_loop, daemon=True)
            monitoring_thread.start()

            # Show startup notification
            def show_startup_notification():
                time.sleep(2)  # Wait for tray icon to be ready
                self.show_notification("Alabama Auction Watcher", "System tray started - Right-click for options")

            notification_thread = threading.Thread(target=show_startup_notification, daemon=True)
            notification_thread.start()

            # Run the tray icon (this blocks)
            self.icon.run()

            return True

        except Exception as e:
            logger.error(f"Error starting system tray: {e}")
            return False

def main():
    """Main entry point for system tray"""
    # Set up logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    # Create and start system tray
    tray_manager = SystemTrayManager()

    if tray_manager.start():
        logger.info("System tray started successfully")
    else:
        logger.error("Failed to start system tray")
        sys.exit(1)

if __name__ == "__main__":
    main()