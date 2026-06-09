# -*- coding: utf-8 -*-
"""
Aplikacja Wdrożeniowa RCSIM RPi5 (Deployment Tool).
RCSIM RPi5 Deployment Application.

Wersja v2.0.0 (2026-06-09)
Author: RCSIM / Mateusz 
"""

import logging
import threading
import time
import tkinter as tk
import webbrowser
from tkinter import filedialog, messagebox, ttk
from typing import Any, Callable, Dict, Optional

from core import deployment_logic
# Import Modules
from core.config_manager import SUPPORTED_LANGUAGES, ConfigManager
from core.service_monitor import ServiceMonitor
from ui.theme import DARK_THEME as DT
from ui.ui_components import (ActionsFrame, AdvancedActionsFrame,
                              ConfigurationFrame, ConnectionFrame, LogFrame,
                              SourceFrame)


class DeploymentApp:
    """
    Główna klasa aplikacji wdrożeniowej.
    Main deployment application class.
    """

    def __init__(self, root: tk.Tk) -> None:
        """
        Inicjalizuje główne okno aplikacji.
        Initializes the main application window.

            root (tk.Tk): Główny obiekt okna Tkinter. / Main Tkinter window object.
        """
        self.root = root
        self.root.title("RCSIM RPi5 Deployment Tool v7.1.0")

        # Dynamic sizing based on screen resolution
        screen_w = self.root.winfo_screenwidth()
        screen_h = self.root.winfo_screenheight()
        win_w = max(1280, int(screen_w * 0.90))
        win_h = max(768, int(screen_h * 0.90))
        self.root.geometry(f"{win_w}x{win_h}")
        self.root.minsize(1280, 768)

        # 1. Config Manager
        self.config_manager = ConfigManager(self.root)
        self.config_manager.load_settings()

        # 2. Setup Style
        self._setup_styles()

        # 3. Build UI
        self._create_menu()
        self._create_main_layout()

        # 4. Service Monitor
        self.service_monitor = ServiceMonitor(
            self.config_manager,
            self.advanced_actions_frame.industrial_status_label,
            self.advanced_actions_frame.video_status_label,
        )

        # Initial Text Update
        self._update_ui_texts()
        self.root.protocol("WM_DELETE_WINDOW", self._on_closing)

    def _on_closing(self) -> None:
        """
        Obsługuje bezpieczne zamykanie aplikacji.
        Handles safe application termination.
        """
        self._log("Shutting down...", "info")
        try:
            if hasattr(self, "service_monitor") and self.service_monitor.running:
                self.service_monitor.stop()
        except Exception as e:
            logging.error(f"Error during service_monitor teardown: {e}")
        finally:
            self.root.destroy()

    def _setup_styles(self) -> None:
        """Configures ttk styles for the application (premium dark theme)."""
        style = ttk.Style()
        style.theme_use("clam")

        bg = DT["bg"]
        surface = DT["surface"]
        surface2 = DT["surface2"]
        border = DT["border"]
        accent = DT["accent"]
        text = DT["text"]
        text_m = DT["text_muted"]
        text_dis = DT["text_disabled"]

        # Root window
        self.root.configure(bg=bg)

        # Base widgets
        style.configure("TFrame", background=bg)
        style.configure(
            "TLabel", background=bg, foreground=text, font=("Segoe UI", 10)
        )

        # ── Card-style LabelFrames ──
        style.configure(
            "TLabelframe",
            background=surface,
            foreground=text,
            bordercolor=DT["border_accent"],
            relief="groove",
            borderwidth=2,
        )
        style.configure(
            "TLabelframe.Label",
            background=surface,
            foreground=DT["text_accent"],
            font=("Segoe UI", 10, "bold"),
        )
        style.configure(
            "Bold.TLabelframe.Label",
            background=surface,
            foreground=DT["text_accent"],
            font=("Segoe UI", 11, "bold"),
        )

        # ── Card surface style ──
        style.configure("Card.TFrame", background=surface)
        style.configure("Card.TLabel", background=surface, foreground=text)

        # ── Section Header Labels ──
        style.configure(
            "SectionHeader.TLabel",
            background=bg,
            foreground=accent,
            font=("Segoe UI", 13, "bold"),
        )

        # ── Entry ──
        style.configure(
            "TEntry",
            fieldbackground=surface2,
            foreground=text,
            insertcolor=accent,
            bordercolor=border,
            lightcolor=surface2,
            darkcolor=surface2,
            font=("Segoe UI", 10),
        )
        style.map(
            "TEntry",
            fieldbackground=[("disabled", surface)],
            foreground=[("disabled", text_dis)],
            bordercolor=[("focus", accent)],
        )

        # ── Standard Button ──
        style.configure(
            "TButton",
            background=surface2,
            foreground=text,
            bordercolor=border,
            lightcolor=surface2,
            darkcolor=surface2,
            relief="flat",
            font=("Segoe UI", 10),
            padding=(12, 6),
        )
        style.map(
            "TButton",
            background=[
                ("active", DT["surface_hover"]),
                ("disabled", surface),
            ],
            foreground=[("disabled", text_dis)],
            bordercolor=[("active", accent)],
        )

        # ── Deploy Button (Emerald) ──
        style.configure(
            "Accent.TButton",
            background=DT["deploy_bg"],
            foreground="white",
            bordercolor=DT["deploy_bg"],
            lightcolor=DT["deploy_bg"],
            darkcolor=DT["deploy_bg"],
            relief="flat",
            font=("Segoe UI", 11, "bold"),
            padding=(16, 8),
        )
        style.map(
            "Accent.TButton",
            background=[
                ("active", DT["deploy_hover"]),
                ("disabled", surface),
            ],
            foreground=[("disabled", text_dis)],
            bordercolor=[("active", DT["deploy_hover"])],
        )

        # ── Hot Deploy Button (Amber) ──
        style.configure(
            "HotDeploy.TButton",
            background=DT["hot_deploy_bg"],
            foreground="white",
            bordercolor=DT["hot_deploy_bg"],
            lightcolor=DT["hot_deploy_bg"],
            darkcolor=DT["hot_deploy_bg"],
            relief="flat",
            font=("Segoe UI", 10, "bold"),
            padding=(12, 6),
        )
        style.map(
            "HotDeploy.TButton",
            background=[
                ("active", DT["hot_deploy_hover"]),
                ("disabled", surface),
            ],
            foreground=[("disabled", text_dis)],
        )

        # ── Checkbutton ──
        style.configure(
            "TCheckbutton",
            background=surface,
            foreground=text,
            font=("Segoe UI", 10),
            padding=(6, 4),
            focuscolor="none",
            indicatorsize=16,
            indicatorcolor=surface2,
            indicatorrelief="flat",
        )
        style.map(
            "TCheckbutton",
            background=[("active", surface), ("pressed", surface)],
            foreground=[("disabled", text_dis)],
            indicatorcolor=[
                ("selected", accent),
                ("disabled", text_dis),
            ],
        )

        # ── Combobox ──
        style.configure(
            "TCombobox",
            fieldbackground=surface2,
            background=surface2,
            foreground=text,
            arrowcolor=accent,
            bordercolor=border,
            lightcolor=surface2,
            darkcolor=surface2,
            font=("Segoe UI", 10),
        )
        style.map(
            "TCombobox",
            fieldbackground=[("readonly", surface2), ("disabled", surface)],
            foreground=[("disabled", text_dis)],
            bordercolor=[("focus", accent)],
        )
        self.root.option_add("*TCombobox*Listbox.background", surface2)
        self.root.option_add("*TCombobox*Listbox.foreground", text)
        self.root.option_add("*TCombobox*Listbox.selectBackground", accent)
        self.root.option_add("*TCombobox*Listbox.selectForeground", "white")

        # ── Progressbar ──
        style.configure(
            "TProgressbar",
            background=accent,
            troughcolor=surface2,
            bordercolor=surface2,
            lightcolor=DT["accent_hover"],
            darkcolor=accent,
            thickness=6,
        )

        # ── Scrollbar ──
        style.configure(
            "TScrollbar",
            background=surface2,
            troughcolor=bg,
            arrowcolor=text_m,
            bordercolor=bg,
            lightcolor=surface2,
            darkcolor=surface2,
            width=10,
        )
        style.map(
            "TScrollbar",
            background=[("active", border)],
        )

        # ── Separator ──
        style.configure("TSeparator", background=border)

        # ── PanedWindow ──
        style.configure(
            "TPanedwindow",
            background=bg,
        )

    def _create_menu(self) -> None:
        """Tworzy pasek menu głównego."""
        menu_cfg = {
            "bg": DT["surface"],
            "fg": DT["text"],
            "activebackground": DT["accent"],
            "activeforeground": "white",
            "relief": "flat",
            "bd": 0,
        }
        menubar = tk.Menu(self.root, **menu_cfg)
        self.root.config(menu=menubar)

        # File Menu
        file_menu = tk.Menu(menubar, tearoff=0, **menu_cfg)
        menubar.add_cascade(label="  File  ", menu=file_menu)
        file_menu.add_command(
            label="  💾 Save Settings", command=self.config_manager.save_settings
        )
        file_menu.add_command(label="  🔄 Reload Settings", command=self._reload_settings)
        file_menu.add_separator()
        file_menu.add_command(label="  ❌ Exit", command=self.root.quit)

        # Language Menu
        lang_menu = tk.Menu(menubar, tearoff=0, **menu_cfg)
        menubar.add_cascade(label="  Language  ", menu=lang_menu)
        for lang_name, lang_code in SUPPORTED_LANGUAGES.items():
            lang_menu.add_radiobutton(
                label=f"  {lang_name}",
                variable=self.config_manager.language_var,
                value=lang_name,
                command=lambda lc=lang_code: self._change_language(lc),
            )

        # Help Menu
        help_menu = tk.Menu(menubar, tearoff=0, **menu_cfg)
        menubar.add_cascade(label="  Help  ", menu=help_menu)
        help_menu.add_command(
            label="  📖 Documentation",
            command=lambda: webbrowser.open("https://github.com/..."),
        )
        help_menu.add_command(label="  ℹ️ About", command=self._show_about)

    def _create_main_layout(self) -> None:
        """Tworzy główny układ interfejsu z nagłówkiem i PanedWindow."""
        # Configure root grid
        self.root.rowconfigure(1, weight=1)
        self.root.columnconfigure(0, weight=1)

        # ── Accent line under menu ──
        accent_line = tk.Frame(self.root, bg=DT["accent"], height=2)
        accent_line.grid(row=0, column=0, sticky="ew")

        # ── Main content area ──
        outer_frame = ttk.Frame(self.root, padding="10")
        outer_frame.grid(row=1, column=0, sticky="nsew")
        outer_frame.rowconfigure(0, weight=1)
        outer_frame.columnconfigure(0, weight=1)

        # --- PanedWindow for adjustable left/right proportions ---
        self.main_paned = ttk.Panedwindow(
            outer_frame,
            orient=tk.HORIZONTAL,
        )
        self.main_paned.grid(row=0, column=0, sticky="nsew")

        # --- Left Pane (Config) with Scrollbar ---
        left_frame_container = ttk.Frame(self.main_paned)
        left_frame_container.rowconfigure(0, weight=1)
        left_frame_container.columnconfigure(0, weight=1)

        # Canvas with scrollbar for left column
        left_canvas = tk.Canvas(
            left_frame_container, bg=DT["bg"], highlightthickness=0, relief="flat"
        )
        left_scrollbar = ttk.Scrollbar(
            left_frame_container, orient="vertical", command=left_canvas.yview
        )
        left_frame = ttk.Frame(left_canvas, padding="0")

        left_canvas.create_window((0, 0), window=left_frame, anchor="nw")
        left_canvas.configure(yscrollcommand=left_scrollbar.set)

        # Pack canvas and scrollbar
        left_canvas.grid(row=0, column=0, sticky="nsew")
        left_scrollbar.grid(row=0, column=1, sticky="ns")

        # Update scroll region when frame changes
        def on_left_frame_configure(event):
            left_canvas.configure(scrollregion=left_canvas.bbox("all"))
            # Make canvas window width match canvas width
            canvas_width = left_canvas.winfo_width()
            if canvas_width > 1:
                left_canvas.itemconfig(left_canvas_window_id, width=canvas_width)

        left_canvas_window_id = left_canvas.create_window(
            (0, 0), window=left_frame, anchor="nw"
        )
        left_frame.bind("<Configure>", on_left_frame_configure)
        left_canvas.bind(
            "<MouseWheel>",
            lambda e: left_canvas.yview_scroll(-1 if e.delta > 0 else 1, "units"),
        )
        left_canvas.bind(
            "<Button-4>", lambda e: left_canvas.yview_scroll(-1, "units")
        )  # Linux scroll up
        left_canvas.bind(
            "<Button-5>", lambda e: left_canvas.yview_scroll(1, "units")
        )  # Linux scroll down

        # --- Right Pane (Actions & Logs) ---
        right_frame = ttk.Frame(self.main_paned)
        right_frame.columnconfigure(0, weight=1)

        # Add panes with ~55%/45% default split
        self.main_paned.add(left_frame_container, weight=55)
        self.main_paned.add(right_frame, weight=45)

        # --- Left Column Content ---
        self.connection_frame = ConnectionFrame(
            left_frame,
            self.config_manager,
            self._schedule_ping,
            self._toggle_ssh_key_mode,
            self._browse_ssh_key,
            self._auto_scan_hardware_thread,
        )
        self.connection_frame.pack(fill=tk.X, pady=(0, 8))

        self.source_frame = SourceFrame(
            left_frame, self.config_manager, self._browse_project_dir, self._on_app_type_change
        )
        self.source_frame.pack(fill=tk.X, pady=(0, 8))

        self.config_frame = ConfigurationFrame(
            left_frame,
            self.config_manager,
            self._fetch_pc_ip,
            self._toggle_rtk_fields,
            self._toggle_lidar_field,
            self._detect_cameras,
        )
        self.config_frame.pack(fill=tk.X, pady=(0, 8))

        # Initial GUI state update
        self._toggle_ssh_key_mode()
        self._toggle_rtk_fields()
        self._toggle_lidar_field()

        # --- Right Column Content ---
        self.actions_frame = ActionsFrame(
            right_frame,
            self.config_manager,
            self._start_deployment_thread,
        )
        self.actions_frame.pack(fill=tk.X, pady=(0, 8))

        self.advanced_actions_frame = AdvancedActionsFrame(
            right_frame,
            self.config_manager,
            self._restart_service_thread,
            self._reboot_pi_thread,
            # Developer-mode callbacks
            self._show_logs_thread,
            self._show_build_logs_thread,
            self._run_diagnostics_thread,
            self._fast_camera_update,
            self._backup_docker,
            self._start_docker_update_thread,
            self._test_connection_thread,
            self._start_hot_deploy_thread,
        )
        self.advanced_actions_frame.pack(fill=tk.X, pady=(0, 8))

        self.log_frame = LogFrame(right_frame, self.config_manager)
        self.log_frame.pack(fill=tk.BOTH, expand=True)

        # ── Progress Bar at bottom with label ──
        progress_container = ttk.Frame(outer_frame)
        progress_container.grid(row=1, column=0, sticky="ew", pady=(8, 0))
        progress_container.columnconfigure(0, weight=1)

        self.progress_var = tk.DoubleVar()
        self.progress_bar = ttk.Progressbar(
            progress_container,
            variable=self.progress_var,
            maximum=100,
            mode="determinate",
        )
        self.progress_bar.grid(row=0, column=0, sticky="ew")

        # Apply initial application type layout rules
        self._on_app_type_change()

    # --- Actions & Logic ---

    def _log(self, message: str, level: str = "info") -> None:
        """
        Loguje wiadomość do konsoli GUI.
        Logs a message to the GUI console.
        """
        self.root.after(0, lambda: self._log_safe(message, level))

    def _log_safe(self, message: str, level: str) -> None:
        """Bezpieczne wątkowo logowanie."""
        if not hasattr(self, "log_frame"):
            return
        widget = self.log_frame.log_widget
        widget.configure(state="normal")
        widget.insert(tk.END, f"[{time.strftime('%H:%M:%S')}] {message}\n", level)
        widget.see(tk.END)
        widget.configure(state="disabled")

    def _update_progress(self, value: int) -> None:
        """Aktualizuje pasek postępu (bezpiecznie wątkowo)."""
        self.root.after(0, lambda: self.progress_var.set(value))

    def _change_language(self, lang_code: str) -> None:
        """Zmienia język interfejsu."""
        self.config_manager.switch_language(lang_code)
        self._update_ui_texts()
        self.config_manager.save_settings()

    def _update_ui_texts(self) -> None:
        """Odświeża teksty w interfejsie po zmianie języka."""
        self.connection_frame.update_texts()
        self.source_frame.update_texts()
        self.config_frame.update_texts()
        self.actions_frame.update_texts()
        self.advanced_actions_frame.update_texts()
        self.log_frame.update_texts()

    def _reload_settings(self) -> None:
        self.config_manager.load_settings()
        self._log("Settings reloaded.", "verbose")

    def _show_about(self) -> None:
        self._log(
            "RCSIM Deployment Tool v7.1.0 - Optimized for RPi 5 & Hailo-8L", "info"
        )

    # --- Frame Callbacks ---

    def _browse_ssh_key(self) -> None:
        path = filedialog.askopenfilename(
            title="Select SSH Private Key", filetypes=[("All Files", "*.*")]
        )
        if path:
            self.config_manager.rpi_key_path_var.set(path)

    def _browse_project_dir(self) -> None:
        path = filedialog.askdirectory(title="Select Project Source Directory")
        if path:
            self.config_manager.project_source_dir_var.set(path)

    def _fetch_pc_ip(self) -> None:
        try:
            # Simple heuristic
            import socket

            hostname = socket.gethostname()
            ip = socket.gethostbyname(hostname)
            # Try to find Tailscale specifically if possible, else just local
            # Logic from original code used os.popen('tailscale ip -4'),
            # keep it simple here or try to run cli
            try:
                import subprocess

                ts_ip = (
                    subprocess.check_output(["tailscale", "ip", "-4"]).decode().strip()
                )
                if ts_ip:
                    ip = ts_ip
            except Exception as e:
                self._log(f"Tailscale IP fetch failed: {e}", "warning")
            self.config_manager.pc_tailscale_ip_var.set(ip)
            self._log(f"Fetched IP: {ip}", "info")
        except Exception as e:
            self._log(f"Error fetching IP: {e}", "error")

    def _toggle_rtk_fields(self) -> None:
        enable = self.config_manager.use_rtk_var.get()
        state = "normal" if enable else "disabled"
        for child in self.config_frame.rtk_fields_frame.winfo_children():
            if isinstance(child, (ttk.Entry, ttk.Button, ttk.Combobox)):
                child.configure(state=state)

    def _toggle_lidar_field(self) -> None:
        enable = self.config_manager.lidar_enabled_var.get()
        state = "normal" if enable else "disabled"
        self.config_frame.lidar_port_entry.configure(state=state)

    def _on_app_type_change(self, event: Any = None) -> None:
        """Dynamicznie dostosowuje interfejs w zależności od typu aplikacji."""
        app_type = self.config_manager.app_type_var.get()
        if app_type == "RCSIM_MCS":
            # Wyłączenie/Ukrycie sekcji wideo, RTK i komunikacji niepotrzebnych dla MCS
            self.config_frame.video_frame.pack_forget()
            self.config_frame.rtk_check.pack_forget()
            self.config_frame.rtk_fields_frame.pack_forget()
            
            # Zmiana etykiet statusu w monitorze usług
            self.advanced_actions_frame.industrial_status_label.config(
                text=f"{self.config_manager.translate('Core Service')}: ○"
            )
            self.advanced_actions_frame.video_status_label.config(
                text=f"{self.config_manager.translate('Web Service')}: ○"
            )
            
            # Wyłączenie akcji developerskich specyficznych dla Dockera
            self.advanced_actions_frame.backup_button.config(state="disabled")
            self.advanced_actions_frame.update_docker_button.config(state="disabled")
            self.advanced_actions_frame.hot_deploy_button.config(state="disabled")
            self.advanced_actions_frame.fast_update_button.config(state="disabled")
        else:
            # Przywrócenie widoczności sekcji dla standardowego RCSIM (Docker)
            self.config_frame.video_frame.pack(fill=tk.X, pady=(10, 5))
            self.config_frame.rtk_check.pack(anchor="w", pady=(5, 5))
            self._toggle_rtk_fields()
            
            # Przywrócenie etykiet statusu
            self.advanced_actions_frame.industrial_status_label.config(
                text=f"{self.config_manager.translate('Industrial')}: ○"
            )
            self.advanced_actions_frame.video_status_label.config(
                text=f"{self.config_manager.translate('Video')}: ○"
            )
            
            # Włączenie akcji developerskich dla Dockera
            self.advanced_actions_frame.backup_button.config(state="normal")
            self.advanced_actions_frame.update_docker_button.config(state="normal")
            self.advanced_actions_frame.hot_deploy_button.config(state="normal")
            self.advanced_actions_frame.fast_update_button.config(state="normal")

    def _toggle_ssh_key_mode(self) -> None:
        use_key = self.config_manager.rpi_use_key_var.get()
        if use_key:
            self.connection_frame.rpi_pass_entry.config(state="disabled")
            self.connection_frame.rpi_pass_toggle.config(state="disabled")
            self.connection_frame.key_path_entry.config(state="normal")
            self.connection_frame.key_browse_button.config(state="normal")
            self.connection_frame.key_pass_entry.config(state="normal")
            self.connection_frame.key_pass_toggle.config(state="normal")
        else:
            self.connection_frame.rpi_pass_entry.config(state="normal")
            self.connection_frame.rpi_pass_toggle.config(state="normal")
            self.connection_frame.key_path_entry.config(state="disabled")
            self.connection_frame.key_browse_button.config(state="disabled")
            self.connection_frame.key_pass_entry.config(state="disabled")
            self.connection_frame.key_pass_toggle.config(state="disabled")

    def _schedule_ping(self, event: Any = None) -> None:
        if hasattr(self, "_ping_job"):
            self.root.after_cancel(self._ping_job)
        self._ping_job = self.root.after(1000, self._perform_ping)

    def _perform_ping(self) -> None:
        host = self.config_manager.rpi_host_var.get()
        if deployment_logic.ping_host(host):
            self.connection_frame.status_indicator.itemconfig(
                self.connection_frame.status_dot, fill="green", outline="green"
            )
        else:
            self.connection_frame.status_indicator.itemconfig(
                self.connection_frame.status_dot, fill="red", outline="red"
            )

    def _lock_ui(self) -> None:
        self.actions_frame.deploy_button.config(state="disabled")
        self.advanced_actions_frame.set_state("disabled")
        self.progress_bar.start(10)

    def _unlock_ui(self) -> None:
        self.actions_frame.deploy_button.config(state="normal")
        self.advanced_actions_frame.set_state("normal")
        self.progress_bar.stop()

    # --- Threading Wrappers ---

    def _run_threaded(self, target: Callable, *args: Any, **kwargs: Any) -> None:
        self._lock_ui()
        threading.Thread(
            target=self._thread_wrapper,
            args=(target, *args),
            kwargs=kwargs,
            daemon=True,
        ).start()

    def _thread_wrapper(self, target: Callable, *args: Any, **kwargs: Any) -> None:
        try:
            target(*args, **kwargs)
        finally:
            self.root.after(0, self._unlock_ui)

    def _start_deployment_thread(self) -> None:
        self.config_manager.save_settings()
        self._run_threaded(
            deployment_logic.run_full_deployment,
            self._log,
            self.config_manager.translate,
            self._update_progress,
            self.config_manager.get_deployment_config(),
            self._on_action_complete,
            fast_mode=self.config_manager.fast_mode_var.get(),
        )

    def _start_docker_update_thread(self) -> None:
        self.config_manager.save_settings()
        self._run_threaded(
            deployment_logic.run_docker_update,
            self._log,
            self.config_manager.translate,
            self._update_progress,
            self.config_manager.get_deployment_config(),
            self._on_action_complete,
        )

    def _start_hot_deploy_thread(self) -> None:
        """Hot Deploy: podmiana kodu bez Docker rebuild (~30-60s)."""
        self.config_manager.save_settings()
        self._run_threaded(
            deployment_logic.run_hot_deploy,
            self._log,
            self.config_manager.translate,
            self._update_progress,
            self.config_manager.get_deployment_config(),
            self._on_action_complete,
        )

    def _test_connection_thread(self) -> None:
        self._run_threaded(
            deployment_logic.test_ssh,
            self._log,
            self.config_manager.translate,
            self.config_manager.get_deployment_config(),
            self._on_action_complete,
        )

    def _detect_cameras(self) -> None:
        self.config_frame.detect_cameras_button.config(state="disabled")
        threading.Thread(target=self._detect_cameras_logic, daemon=True).start()

    def _detect_cameras_logic(self) -> None:
        deployment_logic.detect_cameras(
            self._log,
            self.config_manager.translate,
            self.config_manager.get_deployment_config(),
            self._on_detect_complete,
        )

    def _on_detect_complete(self, success: bool, message: str) -> None:
        self.root.after(
            0, lambda: self.config_frame.detect_cameras_button.config(state="normal")
        )
        if success:
            self._log(message, "success")
        else:
            self._log(message, "error")

    def _on_action_complete(self, success: bool, message: str) -> None:
        if success:
            self._log(message, "success")
            # Start monitoring after success if not running
            if not self.service_monitor.running:
                self.service_monitor.start()
            # Auto-show deployment logs after successful deployment
            self._auto_fetch_deployment_logs()
        else:
            self._log(message, "error")

    def _auto_fetch_deployment_logs(self) -> None:
        """Automatycznie pobiera logi z RPi po zakończeniu wdrożenia."""

        def task() -> None:
            ssh = None
            try:
                ssh = deployment_logic.connect_ssh(
                    self._log, self.config_manager.translate, **self._get_creds()
                )
                if ssh:
                    app_type = self.config_manager.app_type_var.get()
                    logs = deployment_logic.fetch_logs(ssh, app_type=app_type)
                    if logs:
                        for line in logs.splitlines():
                            self._log(line, "verbose")
            except Exception as e:
                self._log(f"Could not fetch deployment logs: {e}", "warning")
            finally:
                if ssh:
                    ssh.close()

        threading.Thread(target=task, daemon=True).start()

    # --- Advanced Action Wrappers ---

    def _restart_service_thread(self) -> None:
        def task() -> None:
            ssh = None
            try:
                ssh = deployment_logic.connect_ssh(
                    self._log, self.config_manager.translate, **self._get_creds()
                )
                if ssh:
                    app_type = self.config_manager.app_type_var.get()
                    if deployment_logic.restart_service(ssh, app_type=app_type):
                        self._log("Service restarted.", "success")
                    else:
                        self._log("Failed to restart service.", "error")
            except Exception as e:
                self._log(f"Restart error: {e}", "error")
            finally:
                if ssh:
                    ssh.close()

        self._run_threaded(task)

    def _show_logs_thread(self) -> None:
        def task() -> None:
            ssh = None
            try:
                ssh = deployment_logic.connect_ssh(
                    self._log, self.config_manager.translate, **self._get_creds()
                )
                if ssh:
                    app_type = self.config_manager.app_type_var.get()
                    logs = deployment_logic.fetch_logs(ssh, app_type=app_type)
                    if logs:
                        # Show in separate window
                        self.root.after(0, lambda: self._open_log_window(logs))
                    else:
                        self._log("Failed to fetch logs.", "error")
            except Exception as e:
                self._log(f"Logs error: {e}", "error")
            finally:
                if ssh:
                    ssh.close()

        self._run_threaded(task)

    def _show_build_logs_thread(self) -> None:
        def task() -> None:
            ssh = None
            try:
                ssh = deployment_logic.connect_ssh(
                    self._log, self.config_manager.translate, **self._get_creds()
                )
                if ssh:
                    app_type = self.config_manager.app_type_var.get()
                    logs = deployment_logic.fetch_build_logs(ssh, app_type=app_type)
                    if logs:
                        # Show in separate window
                        self.root.after(
                            0,
                            lambda: self._open_log_window(
                                logs, title="Build/Installation Logs"
                            ),
                        )
                    else:
                        self._log("Failed to fetch logs.", "error")
            except Exception as e:
                self._log(f"Build/Installation logs error: {e}", "error")
            finally:
                if ssh:
                    ssh.close()

        self._run_threaded(task)

    def _reboot_pi_thread(self) -> None:
        if not messagebox.askyesno("Confirm", "Reboot Raspberry Pi?"):
            return

        def task() -> None:
            ssh = None
            try:
                ssh = deployment_logic.connect_ssh(
                    self._log, self.config_manager.translate, **self._get_creds()
                )
                if ssh:
                    deployment_logic.reboot_pi(ssh)
                    self._log("Reboot command sent.", "success")
            except Exception as e:
                self._log(f"Reboot error: {e}", "error")
            finally:
                if ssh:
                    ssh.close()

        self._run_threaded(task)

    def _run_diagnostics_thread(self) -> None:
        self._run_threaded(
            deployment_logic.run_diagnostics,
            self._log,
            self.config_manager.translate,
            self.config_manager.get_deployment_config(),
            self._on_action_complete,
        )

    def _fast_camera_update(self) -> None:
        self._run_threaded(
            deployment_logic.run_camera_update,
            self._log,
            self.config_manager.translate,
            self._update_progress,
            self.config_manager.get_deployment_config(),
            self._on_action_complete,
        )

    def _backup_docker(self) -> None:
        path = filedialog.asksaveasfilename(
            defaultextension=".tar.gz", filetypes=[("GZIP Archive", "*.tar.gz")]
        )
        if not path:
            return
        self._run_threaded(
            deployment_logic.run_backup,
            self._log,
            self.config_manager.translate,
            self._update_progress,
            self.config_manager.get_deployment_config(),
            path,
            self._on_action_complete,
        )

    def _open_log_window(self, content: str, title: str = "Remote Logs") -> None:
        win = tk.Toplevel(self.root)
        win.title(title)
        win.geometry("900x650")
        win.configure(bg=DT["bg"])
        # Header
        header = tk.Label(
            win,
            text=f"📋 {title}",
            font=("Segoe UI", 12, "bold"),
            fg=DT["text"],
            bg=DT["surface"],
            anchor="w",
            padx=15,
            pady=10,
        )
        header.pack(fill=tk.X)
        tk.Frame(win, bg=DT["accent"], height=2).pack(fill=tk.X)
        st = tk.Text(
            win,
            wrap=tk.WORD,
            font=("Cascadia Code", 10),
            bg=DT["surface2"],
            fg=DT["text"],
            insertbackground=DT["accent"],
            selectbackground=DT["selection"],
            selectforeground="white",
            relief="flat",
            bd=0,
            padx=12,
            pady=8,
        )
        st.pack(fill=tk.BOTH, expand=True, padx=8, pady=8)
        # Clean ansi codes just in case
        clean = deployment_logic.strip_ansi_codes(content)
        st.insert(tk.END, clean)
        st.config(state="disabled")

    def _get_creds(self) -> Dict[str, Any]:
        c = self.config_manager.get_deployment_config()
        return {
            "rpi_host": c["rpi_host"],
            "rpi_user": c["rpi_user"],
            "rpi_pass": c["rpi_pass"],
            "rpi_key_path": c["rpi_key_path"],
            "rpi_key_passphrase": c["rpi_key_passphrase"],
        }

    def _auto_scan_hardware_thread(self) -> None:
        """Uruchamia wątek automatycznego skanowania sprzętu na RPi."""
        self.config_manager.save_settings()
        self._run_threaded(
            deployment_logic.scan_hardware_rpi,
            self._log,
            self.config_manager.translate,
            self.config_manager.get_deployment_config(),
            self._on_scan_complete,
        )

    def _on_scan_complete(self, success: bool, results: Dict[str, Any]) -> None:
        """Obsługuje wyniki skanowania i aktualizuje pola GUI."""

        def update_ui():
            if not success:
                self._log("Hardware scan failed or cancelled.", "error")
                return

            self._log("Hardware scan completed successfully!", "success")

            # 1. IMU Detection
            i2c = results.get("i2c", [])
            if "68" in i2c or "69" in i2c:
                if "77" in i2c:
                    self.config_manager.imu_driver_var.set("native_bmx160_bmp388")
                    self._log("Detected IMU: BMX160 + BMP388 (0x68, 0x77)", "info")
                else:
                    self.config_manager.imu_driver_var.set("native_mpu6050")
                    self._log("Detected IMU: MPU6050/9250 (0x68)", "info")

            # 2. GPS Detection
            uart = results.get("uart", {})
            if "gps" in uart:
                self.config_manager.gps_enabled_var.set(True)
                self.config_manager.gps_port_var.set(uart["gps"])
                self._log(f"GPS auto-configured on {uart['gps']}", "info")

            # 3. Lidar Detection
            if "lidar" in uart:
                self.config_manager.lidar_enabled_var.set(True)
                self.config_manager.lidar_port_var.set(uart["lidar"])
                self._log(f"Lidar auto-configured on {uart['lidar']}", "info")
                self._toggle_lidar_field()

            # 4. Camera Detection
            cam = results.get("camera", "NONE")
            if cam != "NONE":
                self.config_manager.camera_type_var.set(cam)
                self._log(f"Camera auto-detected: {cam}", "info")

        self.root.after(0, update_ui)


if __name__ == "__main__":
    try:
        import ctypes

        ctypes.windll.shcore.SetProcessDpiAwareness(1)
    except Exception:
        pass

    root = tk.Tk()
    root.title("RCSIM RPi5 Deployment Tool")
    
    app = DeploymentApp(root)

    root.state("zoomed")  # Start maximized
    root.mainloop()
