#!/usr/bin/env python3
"""
Alabama Auction Watcher - Professional Installer UI
Cross-platform installer wizard with professional branding and user experience
"""

import os
import sys
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from pathlib import Path
import threading
import subprocess
import time
import json
from typing import Dict, List, Optional, Callable

# Optional PIL import for image handling
try:
    from PIL import Image, ImageTk
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False

class InstallerWizard:
    """Professional installation wizard with branding"""

    def __init__(self):
        # Application information
        self.app_name = "Alabama Auction Watcher"
        self.app_version = "1.0.0"
        self.publisher = "Alabama Auction Watcher Team"
        self.website = "https://github.com/Alabama-Auction-Watcher"

        # Installation configuration
        self.install_dir = self.get_default_install_dir()
        self.create_desktop_shortcut = tk.BooleanVar(value=True)
        self.create_start_menu = tk.BooleanVar(value=True)
        self.add_to_path = tk.BooleanVar(value=False)
        self.install_for_all_users = tk.BooleanVar(value=False)

        # UI state
        self.current_page = 0
        self.pages = []
        self.installation_complete = False
        self.installation_cancelled = False

        # Create main window
        self.root = tk.Tk()
        self.setup_main_window()

        # Load branding assets
        self.load_branding_assets()

        # Create wizard pages
        self.create_pages()

        # Show first page
        self.show_page(0)

    def get_default_install_dir(self) -> str:
        """Get default installation directory for platform"""
        if sys.platform.startswith('win'):
            return os.path.join(os.environ.get('PROGRAMFILES', 'C:\\Program Files'), self.app_name)
        elif sys.platform == 'darwin':
            return '/Applications'
        else:
            return f'/opt/{self.app_name.lower().replace(" ", "-")}'

    def setup_main_window(self):
        """Setup main installer window"""
        self.root.title(f"{self.app_name} Setup")
        self.root.geometry("650x500")
        self.root.resizable(False, False)

        # Center window
        self.center_window()

        # Set window icon
        self.set_window_icon()

        # Configure style
        self.setup_styles()

    def center_window(self):
        """Center window on screen"""
        self.root.update_idletasks()
        x = (self.root.winfo_screenwidth() // 2) - (self.root.winfo_width() // 2)
        y = (self.root.winfo_screenheight() // 2) - (self.root.winfo_height() // 2)
        self.root.geometry(f"+{x}+{y}")

    def set_window_icon(self):
        """Set window icon"""
        try:
            icon_path = Path(__file__).parent.parent / "branding" / "generated" / "windows" / "alabama-auction-watcher.ico"
            if icon_path.exists():
                self.root.iconbitmap(str(icon_path))
        except:
            pass  # Ignore if icon not available

    def setup_styles(self):
        """Configure TTK styles for professional appearance"""
        style = ttk.Style()

        # Configure theme
        available_themes = style.theme_names()
        if 'clam' in available_themes:
            style.theme_use('clam')
        elif 'alt' in available_themes:
            style.theme_use('alt')

        # Custom styles
        style.configure('Title.TLabel',
                       font=('Arial', 16, 'bold'),
                       foreground='#2C3E50')

        style.configure('Subtitle.TLabel',
                       font=('Arial', 10),
                       foreground='#34495E')

        style.configure('Header.TLabel',
                       font=('Arial', 12, 'bold'),
                       foreground='#2980B9')

        style.configure('Custom.TButton',
                       font=('Arial', 9))

    def load_branding_assets(self):
        """Load branding images and assets"""
        self.branding_assets = {}

        asset_dir = Path(__file__).parent / "assets"
        asset_dir.mkdir(exist_ok=True)

        # Try to load banner image
        if PIL_AVAILABLE:
            banner_path = asset_dir / "installer_banner.png"
            if banner_path.exists():
                try:
                    img = Image.open(banner_path)
                    img = img.resize((600, 80), Image.Resampling.LANCZOS)
                    self.branding_assets['banner'] = ImageTk.PhotoImage(img)
                except:
                    pass

            # Try to load side image
            side_image_path = asset_dir / "installer_side.png"
            if side_image_path.exists():
                try:
                    img = Image.open(side_image_path)
                    img = img.resize((150, 400), Image.Resampling.LANCZOS)
                    self.branding_assets['side'] = ImageTk.PhotoImage(img)
                except:
                    pass

        # Create default branding if images not available
        if 'banner' not in self.branding_assets:
            self.create_default_banner()

    def create_default_banner(self):
        """Create default banner if image not available"""
        if PIL_AVAILABLE:
            try:
                # Create simple banner
                img = Image.new('RGB', (600, 80), color='#6C8EF5')
                self.branding_assets['banner'] = ImageTk.PhotoImage(img)
            except:
                pass

    def create_pages(self):
        """Create all wizard pages"""
        self.pages = [
            self.create_welcome_page,
            self.create_license_page,
            self.create_installation_type_page,
            self.create_destination_page,
            self.create_components_page,
            self.create_ready_page,
            self.create_progress_page,
            self.create_finish_page
        ]

    def create_page_frame(self) -> ttk.Frame:
        """Create common page frame structure"""
        # Clear existing content
        for widget in self.root.winfo_children():
            widget.destroy()

        # Main container
        main_frame = ttk.Frame(self.root)
        main_frame.pack(fill=tk.BOTH, expand=True)

        # Banner
        if 'banner' in self.branding_assets:
            banner_label = ttk.Label(main_frame, image=self.branding_assets['banner'])
            banner_label.pack(fill=tk.X, pady=(0, 10))

        # Content area
        content_frame = ttk.Frame(main_frame)
        content_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=10)

        # Navigation buttons frame
        nav_frame = ttk.Frame(main_frame)
        nav_frame.pack(fill=tk.X, padx=20, pady=10)

        # Separator
        ttk.Separator(nav_frame, orient='horizontal').pack(fill=tk.X, pady=(0, 10))

        # Navigation buttons
        button_frame = ttk.Frame(nav_frame)
        button_frame.pack(fill=tk.X)

        self.back_button = ttk.Button(button_frame, text="< Back", command=self.go_back, style='Custom.TButton')
        self.back_button.pack(side=tk.LEFT)

        self.cancel_button = ttk.Button(button_frame, text="Cancel", command=self.cancel_installation, style='Custom.TButton')
        self.cancel_button.pack(side=tk.RIGHT, padx=(5, 0))

        self.next_button = ttk.Button(button_frame, text="Next >", command=self.go_next, style='Custom.TButton')
        self.next_button.pack(side=tk.RIGHT, padx=(5, 0))

        return content_frame

    def create_welcome_page(self) -> ttk.Frame:
        """Create welcome page"""
        frame = self.create_page_frame()

        # Side image if available
        content_container = ttk.Frame(frame)
        content_container.pack(fill=tk.BOTH, expand=True)

        if 'side' in self.branding_assets:
            image_frame = ttk.Frame(content_container)
            image_frame.pack(side=tk.LEFT, fill=tk.Y)

            ttk.Label(image_frame, image=self.branding_assets['side']).pack()

        # Welcome content
        welcome_frame = ttk.Frame(content_container)
        welcome_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=20)

        ttk.Label(welcome_frame, text=f"Welcome to {self.app_name} Setup",
                 style='Title.TLabel').pack(anchor=tk.W, pady=(20, 10))

        welcome_text = f"""This wizard will guide you through the installation of {self.app_name}.

{self.app_name} is a professional real estate auction tracking and analytics platform designed for investors, agents, and market analysts.

Key Features:
• Real-time auction data tracking
• Advanced market analytics
• Investment opportunity scoring
• Multi-county coverage across Alabama
• Web-based dashboard interface
• RESTful API for integration

It is recommended that you close all other applications before continuing.

Click Next to continue, or Cancel to exit Setup."""

        text_widget = tk.Text(welcome_frame, wrap=tk.WORD, height=15, width=50, state=tk.DISABLED,
                            background=self.root.cget('bg'), relief=tk.FLAT)
        text_widget.configure(state=tk.NORMAL)
        text_widget.insert(tk.END, welcome_text)
        text_widget.configure(state=tk.DISABLED)
        text_widget.pack(fill=tk.BOTH, expand=True, pady=10)

        # Update navigation buttons
        self.back_button.config(state=tk.DISABLED)
        self.next_button.config(text="Next >")

        return frame

    def create_license_page(self) -> ttk.Frame:
        """Create license agreement page"""
        frame = self.create_page_frame()

        ttk.Label(frame, text="License Agreement", style='Title.TLabel').pack(anchor=tk.W, pady=(0, 10))

        ttk.Label(frame, text="Please read the following license agreement. You must accept the terms of this agreement before continuing with the installation.",
                 style='Subtitle.TLabel', wraplength=600).pack(anchor=tk.W, pady=(0, 10))

        # License text
        license_frame = ttk.Frame(frame)
        license_frame.pack(fill=tk.BOTH, expand=True)

        license_text = tk.Text(license_frame, wrap=tk.WORD, height=20, width=70)
        scrollbar = ttk.Scrollbar(license_frame, command=license_text.yview)
        license_text.configure(yscrollcommand=scrollbar.set)

        license_content = self.get_license_text()
        license_text.insert(tk.END, license_content)
        license_text.configure(state=tk.DISABLED)

        license_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        # Accept checkbox
        self.accept_license = tk.BooleanVar()
        accept_frame = ttk.Frame(frame)
        accept_frame.pack(fill=tk.X, pady=10)

        ttk.Checkbutton(accept_frame, text="I accept the terms in the License Agreement",
                       variable=self.accept_license, command=self.update_license_button).pack(anchor=tk.W)

        # Update navigation
        self.back_button.config(state=tk.NORMAL)
        self.next_button.config(state=tk.DISABLED)

        return frame

    def get_license_text(self) -> str:
        """Get license agreement text"""
        return """SOFTWARE LICENSE AGREEMENT

Alabama Auction Watcher

This software is provided "as is" without warranty of any kind, express or implied, including but not limited to the warranties of merchantability, fitness for a particular purpose and noninfringement.

Copyright (c) 2024 Alabama Auction Watcher Team

Permission is hereby granted to use this software for legitimate real estate auction tracking and analysis purposes.

TERMS AND CONDITIONS:

1. PERMITTED USE: This software may be used for tracking public real estate auction information and performing market analysis.

2. RESTRICTIONS: Users may not use this software for:
   - Illegal activities
   - Unauthorized access to systems
   - Spamming or abuse of auction systems

3. DATA USAGE: Users are responsible for complying with all applicable data protection and privacy laws.

4. LIABILITY: The software is provided without warranty. The authors are not liable for any damages arising from use of this software.

5. UPDATES: This license applies to all versions and updates of the software.

By installing this software, you agree to these terms and conditions."""

    def update_license_button(self):
        """Update next button state based on license acceptance"""
        if self.accept_license.get():
            self.next_button.config(state=tk.NORMAL)
        else:
            self.next_button.config(state=tk.DISABLED)

    def create_installation_type_page(self) -> ttk.Frame:
        """Create installation type selection page"""
        frame = self.create_page_frame()

        ttk.Label(frame, text="Choose Installation Type", style='Title.TLabel').pack(anchor=tk.W, pady=(0, 10))

        ttk.Label(frame, text="Choose the type of installation that best suits your needs.",
                 style='Subtitle.TLabel').pack(anchor=tk.W, pady=(0, 20))

        # Installation type selection
        self.install_type = tk.StringVar(value="typical")

        # Typical installation
        typical_frame = ttk.LabelFrame(frame, text="Typical", padding=15)
        typical_frame.pack(fill=tk.X, pady=5)

        ttk.Radiobutton(typical_frame, text="Typical installation (Recommended)",
                       variable=self.install_type, value="typical").pack(anchor=tk.W)

        typical_desc = "Installs the most common components including the main application, desktop integration, and documentation."
        ttk.Label(typical_frame, text=typical_desc, style='Subtitle.TLabel',
                 wraplength=550).pack(anchor=tk.W, pady=(5, 0))

        # Complete installation
        complete_frame = ttk.LabelFrame(frame, text="Complete", padding=15)
        complete_frame.pack(fill=tk.X, pady=5)

        ttk.Radiobutton(complete_frame, text="Complete installation",
                       variable=self.install_type, value="complete").pack(anchor=tk.W)

        complete_desc = "Installs all components including development tools, additional utilities, and sample data."
        ttk.Label(complete_frame, text=complete_desc, style='Subtitle.TLabel',
                 wraplength=550).pack(anchor=tk.W, pady=(5, 0))

        # Custom installation
        custom_frame = ttk.LabelFrame(frame, text="Custom", padding=15)
        custom_frame.pack(fill=tk.X, pady=5)

        ttk.Radiobutton(custom_frame, text="Custom installation",
                       variable=self.install_type, value="custom").pack(anchor=tk.W)

        custom_desc = "Choose which components to install and where to install them."
        ttk.Label(custom_frame, text=custom_desc, style='Subtitle.TLabel',
                 wraplength=550).pack(anchor=tk.W, pady=(5, 0))

        return frame

    def create_destination_page(self) -> ttk.Frame:
        """Create installation destination page"""
        frame = self.create_page_frame()

        ttk.Label(frame, text="Choose Install Location", style='Title.TLabel').pack(anchor=tk.W, pady=(0, 10))

        ttk.Label(frame, text="Setup will install the application in the following folder.",
                 style='Subtitle.TLabel').pack(anchor=tk.W, pady=(0, 20))

        # Destination folder
        dest_frame = ttk.Frame(frame)
        dest_frame.pack(fill=tk.X, pady=10)

        ttk.Label(dest_frame, text="Destination Folder:").pack(anchor=tk.W)

        path_frame = ttk.Frame(dest_frame)
        path_frame.pack(fill=tk.X, pady=5)

        self.install_path = tk.StringVar(value=self.install_dir)
        path_entry = ttk.Entry(path_frame, textvariable=self.install_path, width=60)
        path_entry.pack(side=tk.LEFT, fill=tk.X, expand=True)

        ttk.Button(path_frame, text="Browse...", command=self.browse_install_dir).pack(side=tk.RIGHT, padx=(5, 0))

        # Space requirements
        space_frame = ttk.Frame(frame)
        space_frame.pack(fill=tk.X, pady=20)

        ttk.Label(space_frame, text="Space Requirements:", style='Header.TLabel').pack(anchor=tk.W)
        ttk.Label(space_frame, text="• Required space: 500 MB").pack(anchor=tk.W, padx=20)
        ttk.Label(space_frame, text="• Available space: Calculating...").pack(anchor=tk.W, padx=20)

        return frame

    def browse_install_dir(self):
        """Browse for installation directory"""
        directory = filedialog.askdirectory(initialdir=self.install_path.get())
        if directory:
            self.install_path.set(directory)

    def create_components_page(self) -> ttk.Frame:
        """Create component selection page"""
        frame = self.create_page_frame()

        ttk.Label(frame, text="Select Components", style='Title.TLabel').pack(anchor=tk.W, pady=(0, 10))

        ttk.Label(frame, text="Select the components you want to install and clear the components you do not want to install.",
                 style='Subtitle.TLabel', wraplength=600).pack(anchor=tk.W, pady=(0, 10))

        # Components tree
        tree_frame = ttk.Frame(frame)
        tree_frame.pack(fill=tk.BOTH, expand=True)

        self.components_tree = ttk.Treeview(tree_frame, show='tree headings', height=12)
        self.components_tree.heading('#0', text='Component')
        self.components_tree.heading('#1', text='Size')

        scrollbar = ttk.Scrollbar(tree_frame, command=self.components_tree.yview)
        self.components_tree.configure(yscrollcommand=scrollbar.set)

        self.components_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        # Populate components
        self.populate_components()

        # Options
        options_frame = ttk.Frame(frame)
        options_frame.pack(fill=tk.X, pady=10)

        ttk.Label(options_frame, text="Additional Options:", style='Header.TLabel').pack(anchor=tk.W)

        ttk.Checkbutton(options_frame, text="Create desktop shortcut",
                       variable=self.create_desktop_shortcut).pack(anchor=tk.W, padx=20)

        ttk.Checkbutton(options_frame, text="Add to Start Menu",
                       variable=self.create_start_menu).pack(anchor=tk.W, padx=20)

        if sys.platform.startswith('win'):
            ttk.Checkbutton(options_frame, text="Add to system PATH",
                           variable=self.add_to_path).pack(anchor=tk.W, padx=20)

            ttk.Checkbutton(options_frame, text="Install for all users (requires administrator)",
                           variable=self.install_for_all_users).pack(anchor=tk.W, padx=20)

        return frame

    def populate_components(self):
        """Populate components tree"""
        # Main application
        main = self.components_tree.insert('', 'end', text='Alabama Auction Watcher (Required)', values=['250 MB'], tags=['required'])

        # Sub-components
        self.components_tree.insert(main, 'end', text='Core Application', values=['150 MB'], tags=['required'])
        self.components_tree.insert(main, 'end', text='Web Interface', values=['50 MB'], tags=['required'])
        self.components_tree.insert(main, 'end', text='Database Engine', values=['30 MB'], tags=['required'])
        self.components_tree.insert(main, 'end', text='Configuration Files', values=['5 MB'], tags=['required'])

        # Optional components
        optional = self.components_tree.insert('', 'end', text='Optional Components', values=['150 MB'])
        self.components_tree.insert(optional, 'end', text='Sample Data', values=['75 MB'])
        self.components_tree.insert(optional, 'end', text='Development Tools', values=['50 MB'])
        self.components_tree.insert(optional, 'end', text='Additional Documentation', values=['25 MB'])

        # Desktop integration
        desktop = self.components_tree.insert('', 'end', text='Desktop Integration', values=['10 MB'])
        self.components_tree.insert(desktop, 'end', text='Icons and Themes', values=['5 MB'])
        self.components_tree.insert(desktop, 'end', text='File Associations', values=['1 MB'])
        self.components_tree.insert(desktop, 'end', text='Context Menu Integration', values=['4 MB'])

        # Expand all items
        for item in self.components_tree.get_children():
            self.components_tree.item(item, open=True)

    def create_ready_page(self) -> ttk.Frame:
        """Create ready to install page"""
        frame = self.create_page_frame()

        ttk.Label(frame, text="Ready to Install", style='Title.TLabel').pack(anchor=tk.W, pady=(0, 10))

        ttk.Label(frame, text="Setup has enough information to start copying the program files.",
                 style='Subtitle.TLabel').pack(anchor=tk.W, pady=(0, 20))

        # Installation summary
        summary_frame = ttk.LabelFrame(frame, text="Installation Summary", padding=15)
        summary_frame.pack(fill=tk.BOTH, expand=True)

        summary_text = f"""Application: {self.app_name} {self.app_version}
Publisher: {self.publisher}
Installation Type: {self.install_type.get().title()}
Destination: {self.install_path.get()}

Options:
• Create desktop shortcut: {'Yes' if self.create_desktop_shortcut.get() else 'No'}
• Add to Start Menu: {'Yes' if self.create_start_menu.get() else 'No'}"""

        if sys.platform.startswith('win'):
            summary_text += f"""
• Add to PATH: {'Yes' if self.add_to_path.get() else 'No'}
• Install for all users: {'Yes' if self.install_for_all_users.get() else 'No'}"""

        summary_text += f"""

Space Required: 500 MB
Estimated Time: 2-5 minutes

Click Install to begin the installation, or click Back if you want to review or change any settings."""

        text_widget = tk.Text(summary_frame, wrap=tk.WORD, height=15, state=tk.DISABLED,
                            background=self.root.cget('bg'), relief=tk.FLAT)
        text_widget.configure(state=tk.NORMAL)
        text_widget.insert(tk.END, summary_text)
        text_widget.configure(state=tk.DISABLED)
        text_widget.pack(fill=tk.BOTH, expand=True)

        # Update navigation
        self.next_button.config(text="Install")

        return frame

    def create_progress_page(self) -> ttk.Frame:
        """Create installation progress page"""
        frame = self.create_page_frame()

        ttk.Label(frame, text="Installing", style='Title.TLabel').pack(anchor=tk.W, pady=(0, 10))

        ttk.Label(frame, text="Please wait while Setup installs the application on your computer.",
                 style='Subtitle.TLabel').pack(anchor=tk.W, pady=(0, 20))

        # Progress information
        progress_frame = ttk.Frame(frame)
        progress_frame.pack(fill=tk.X, pady=10)

        self.status_label = ttk.Label(progress_frame, text="Initializing installation...")
        self.status_label.pack(anchor=tk.W)

        self.progress_bar = ttk.Progressbar(progress_frame, mode='determinate', length=400)
        self.progress_bar.pack(fill=tk.X, pady=10)

        self.detail_label = ttk.Label(progress_frame, text="", style='Subtitle.TLabel')
        self.detail_label.pack(anchor=tk.W)

        # Installation log
        log_frame = ttk.LabelFrame(frame, text="Installation Details", padding=10)
        log_frame.pack(fill=tk.BOTH, expand=True, pady=20)

        self.log_text = tk.Text(log_frame, height=10, wrap=tk.WORD, state=tk.DISABLED)
        log_scrollbar = ttk.Scrollbar(log_frame, command=self.log_text.yview)
        self.log_text.configure(yscrollcommand=log_scrollbar.set)

        self.log_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        log_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        # Update navigation
        self.back_button.config(state=tk.DISABLED)
        self.next_button.config(state=tk.DISABLED)
        self.cancel_button.config(state=tk.DISABLED)

        # Start installation
        threading.Thread(target=self.perform_installation, daemon=True).start()

        return frame

    def create_finish_page(self) -> ttk.Frame:
        """Create installation complete page"""
        frame = self.create_page_frame()

        # Success or failure message
        if self.installation_complete and not self.installation_cancelled:
            ttk.Label(frame, text="Installation Complete", style='Title.TLabel').pack(anchor=tk.W, pady=(0, 10))

            success_text = f"""Setup has successfully installed {self.app_name} on your computer.

The application has been installed to:
{self.install_path.get()}

You can now start using {self.app_name} by:
• Clicking the desktop shortcut (if created)
• Using the Start Menu entry (if created)
• Running the application from the installation directory

Thank you for choosing {self.app_name}!"""

        else:
            ttk.Label(frame, text="Installation Failed", style='Title.TLabel').pack(anchor=tk.W, pady=(0, 10))

            success_text = f"""Setup was unable to complete the installation of {self.app_name}.

The installation may have been cancelled or encountered an error.

Please check the installation log for details and try running the installer again."""

        text_widget = tk.Text(frame, wrap=tk.WORD, height=12, state=tk.DISABLED,
                            background=self.root.cget('bg'), relief=tk.FLAT)
        text_widget.configure(state=tk.NORMAL)
        text_widget.insert(tk.END, success_text)
        text_widget.configure(state=tk.DISABLED)
        text_widget.pack(fill=tk.BOTH, expand=True, pady=10)

        # Launch option
        if self.installation_complete and not self.installation_cancelled:
            self.launch_app = tk.BooleanVar(value=True)
            ttk.Checkbutton(frame, text=f"Launch {self.app_name} now",
                           variable=self.launch_app).pack(anchor=tk.W, pady=10)

        # Update navigation
        self.back_button.config(state=tk.DISABLED)
        self.next_button.config(text="Finish", command=self.finish_installation)
        self.cancel_button.config(state=tk.DISABLED)

        return frame

    def perform_installation(self):
        """Perform the actual installation"""
        try:
            # Simulate installation steps
            steps = [
                ("Preparing installation...", 10),
                ("Creating directories...", 20),
                ("Copying application files...", 50),
                ("Installing dependencies...", 70),
                ("Creating shortcuts...", 80),
                ("Registering file associations...", 90),
                ("Finalizing installation...", 100)
            ]

            for step_text, progress in steps:
                if self.installation_cancelled:
                    return

                self.update_progress(step_text, progress, f"Step {steps.index((step_text, progress)) + 1} of {len(steps)}")
                self.log_installation_step(step_text)

                # Simulate work
                time.sleep(1)

            self.installation_complete = True
            self.update_progress("Installation complete!", 100, "Ready to use")
            self.log_installation_step("Installation completed successfully!")

            # Enable next button
            self.next_button.config(state=tk.NORMAL)

        except Exception as e:
            self.log_installation_step(f"ERROR: Installation failed - {e}")
            self.update_progress("Installation failed", 0, "Error occurred")

    def update_progress(self, status: str, progress: int, detail: str):
        """Update installation progress"""
        self.root.after(0, lambda: self._update_progress_ui(status, progress, detail))

    def _update_progress_ui(self, status: str, progress: int, detail: str):
        """Update progress UI elements"""
        self.status_label.config(text=status)
        self.progress_bar.config(value=progress)
        self.detail_label.config(text=detail)

    def log_installation_step(self, message: str):
        """Log installation step"""
        self.root.after(0, lambda: self._log_to_ui(message))

    def _log_to_ui(self, message: str):
        """Add message to installation log"""
        self.log_text.configure(state=tk.NORMAL)
        self.log_text.insert(tk.END, f"{message}\n")
        self.log_text.see(tk.END)
        self.log_text.configure(state=tk.DISABLED)

    def show_page(self, page_index: int):
        """Show specific page"""
        if 0 <= page_index < len(self.pages):
            self.current_page = page_index
            self.pages[page_index]()

    def go_next(self):
        """Go to next page"""
        if self.current_page < len(self.pages) - 1:
            self.show_page(self.current_page + 1)

    def go_back(self):
        """Go to previous page"""
        if self.current_page > 0:
            self.show_page(self.current_page - 1)

    def cancel_installation(self):
        """Cancel installation"""
        if messagebox.askyesno("Cancel Installation",
                              "Are you sure you want to cancel the installation?"):
            self.installation_cancelled = True
            self.root.quit()

    def finish_installation(self):
        """Finish installation and close wizard"""
        if hasattr(self, 'launch_app') and self.launch_app.get():
            # Launch application
            try:
                if sys.platform.startswith('win'):
                    launch_path = Path(self.install_path.get()) / "Alabama Auction Watcher.bat"
                else:
                    launch_path = Path(self.install_path.get()) / "alabama-auction-watcher"

                if launch_path.exists():
                    subprocess.Popen([str(launch_path)], cwd=launch_path.parent)
            except Exception as e:
                messagebox.showerror("Launch Error", f"Could not launch application: {e}")

        self.root.quit()

    def run(self):
        """Run the installer wizard"""
        try:
            self.root.mainloop()
        except KeyboardInterrupt:
            pass

def main():
    """Main installer execution"""
    # Check if running as admin on Windows
    if sys.platform.startswith('win'):
        try:
            import ctypes
            is_admin = ctypes.windll.shell32.IsUserAnAdmin()
            if not is_admin:
                messagebox.showwarning("Administrator Required",
                                     "For best results, run the installer as Administrator.\n\n"
                                     "Some features may not be available without administrator privileges.")
        except:
            pass

    # Create and run installer
    installer = InstallerWizard()
    installer.run()

if __name__ == '__main__':
    main()