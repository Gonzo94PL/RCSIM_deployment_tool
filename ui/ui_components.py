import tkinter as tk
from tkinter import scrolledtext, ttk
from typing import Any, Callable

from .theme import DARK_THEME as DT


class BaseFrame(ttk.LabelFrame):
    """
    Bazowa klasa ramki z obsługą konfiguracji i tłumaczeń.
    Base frame class with configuration and translation support.
    """

    def __init__(self, master: tk.Widget, config_manager: Any, **kwargs: Any) -> None:
        """
        Inicjalizuje bazową ramkę.
        Initializes the base frame.
        """
        super().__init__(master, **kwargs)
        self.cfg = config_manager
        self._translate = config_manager.translate

    def update_texts(self) -> None:
        """
        Aktualizuje teksty w interfejsie (do nadpisania).
        """

    def _toggle_password_visibility(self, entry: tk.Entry, button: tk.Button) -> None:
        """Przełącza maskowanie hasła (oczko)."""
        if entry.cget("show") == "*":
            entry.config(show="")
            button.config(text="🔒")
        else:
            entry.config(show="*")
            button.config(text="👁")


class ConnectionFrame(BaseFrame):
    """
    Ramka konfiguracji połączenia z Raspberry Pi.
    Rabbit Pi connection configuration frame.
    """

    def __init__(
        self,
        master: tk.Widget,
        config_manager: Any,
        on_ping_schedule: Callable,
        on_key_toggle: Callable,
        on_browse_key: Callable,
        on_auto_scan: Callable,
    ) -> None:
        """
        Inicjalizuje ramkę połączenia.
        """
        super().__init__(master, config_manager, padding="15", style="Bold.TLabelframe")
        self.on_ping_schedule = on_ping_schedule
        self.on_key_toggle = on_key_toggle
        self.on_browse_key = on_browse_key
        self.on_auto_scan = on_auto_scan
        self.columnconfigure(1, weight=1)
        self._create_widgets()

    def _create_widgets(self) -> None:
        # IP / Host
        self.ip_label = ttk.Label(self)
        self.ip_label.grid(row=0, column=0, sticky="e", padx=5, pady=5)
        self.ip_entry = ttk.Entry(self, textvariable=self.cfg.rpi_host_var)
        self.ip_entry.grid(row=0, column=1, padx=5, pady=5, sticky="ew")
        self.ip_entry.bind("<KeyRelease>", self.on_ping_schedule)

        # Status indicator canvas (larger glow dot)
        self.status_indicator = tk.Canvas(
            self, width=20, height=20, bd=0, highlightthickness=0, bg=DT["surface"]
        )
        self.status_indicator.grid(row=0, column=2, padx=5, sticky="w")
        # Outer glow
        self.status_glow = self.status_indicator.create_oval(
            1, 1, 19, 19, fill="", outline="#333333", width=1
        )
        self.status_dot = self.status_indicator.create_oval(
            4, 4, 16, 16, fill="grey", outline="grey"
        )

        # User
        self.user_label = ttk.Label(self)
        self.user_label.grid(row=1, column=0, sticky="e", padx=5, pady=5)
        ttk.Entry(self, textvariable=self.cfg.rpi_user_var).grid(
            row=1, column=1, padx=5, pady=5, sticky="ew"
        )

        # Initial Password
        self.pass_label = ttk.Label(self)
        self.pass_label.grid(row=2, column=0, sticky="e", padx=5, pady=5)
        self.rpi_pass_entry = ttk.Entry(
            self, textvariable=self.cfg.rpi_pass_var, show="*"
        )
        self.rpi_pass_entry.grid(row=2, column=1, padx=5, pady=5, sticky="ew")
        self.rpi_pass_toggle = ttk.Button(
            self,
            text="👁",
            width=3,
            command=lambda: self._toggle_password_visibility(
                self.rpi_pass_entry, self.rpi_pass_toggle
            ),
        )
        self.rpi_pass_toggle.grid(row=2, column=2, padx=5, pady=5)

        # New Password
        self.new_pass_label = ttk.Label(self)
        self.new_pass_label.grid(row=3, column=0, sticky="e", padx=5, pady=5)
        self.new_ssh_pass_entry = ttk.Entry(
            self, textvariable=self.cfg.new_ssh_pass_var, show="*"
        )
        self.new_ssh_pass_entry.grid(row=3, column=1, padx=5, pady=5, sticky="ew")
        self.new_ssh_pass_toggle = ttk.Button(
            self,
            text="👁",
            width=3,
            command=lambda: self._toggle_password_visibility(
                self.new_ssh_pass_entry, self.new_ssh_pass_toggle
            ),
        )
        self.new_ssh_pass_toggle.grid(row=3, column=2, padx=5, pady=5)

        # SSH Key
        self.use_key_check = ttk.Checkbutton(
            self, variable=self.cfg.rpi_use_key_var, command=self.on_key_toggle
        )
        self.use_key_check.grid(
            row=4, column=0, columnspan=2, sticky="w", padx=5, pady=5
        )

        self.key_path_label = ttk.Label(self)
        self.key_path_label.grid(row=5, column=0, sticky="e", padx=5, pady=5)
        self.key_path_entry = ttk.Entry(self, textvariable=self.cfg.rpi_key_path_var)
        self.key_path_entry.grid(row=5, column=1, padx=5, pady=5, sticky="ew")
        self.key_browse_button = ttk.Button(self, command=self.on_browse_key)
        self.key_browse_button.grid(row=5, column=2, padx=5, pady=5)

        self.key_pass_label = ttk.Label(self)
        self.key_pass_label.grid(row=6, column=0, sticky="e", padx=5, pady=5)
        self.key_pass_entry = ttk.Entry(
            self, textvariable=self.cfg.rpi_key_passphrase_var, show="*"
        )
        self.key_passphrase_var = self.cfg.rpi_key_passphrase_var
        self.key_pass_entry.grid(row=6, column=1, padx=5, pady=5, sticky="ew")
        self.key_pass_toggle = ttk.Button(
            self,
            text="👁",
            width=3,
            command=lambda: self._toggle_password_visibility(
                self.key_pass_entry, self.key_pass_toggle
            ),
        )
        self.key_pass_toggle.grid(row=6, column=2, padx=5, pady=5)

        # Auto-Scan Button (NEW)
        self.auto_scan_button = ttk.Button(
            self, command=self.on_auto_scan
        )
        self.auto_scan_button.grid(row=7, column=1, pady=10, sticky="ew")

    def update_texts(self) -> None:
        self.configure(
            text=self._translate("🔗  1. Raspberry Pi Connection Details")
        )
        self.ip_label.config(text=self._translate("IP Address / Host:"))
        self.user_label.config(text=self._translate("User:"))
        self.pass_label.config(text=self._translate("Password (initial):"))
        self.new_pass_label.config(text=self._translate("New Password (optional):"))
        self.use_key_check.config(
            text=self._translate("🔑 Use SSH Key instead of password")
        )
        self.key_path_label.config(text=self._translate("SSH Key Path:"))
        self.key_browse_button.config(text=self._translate("📂 Browse..."))
        self.key_pass_label.config(text=self._translate("Key Passphrase (optional):"))
        self.auto_scan_button.config(text=self._translate("🔍 Auto-Scan Hardware"))


class SourceFrame(BaseFrame):
    """
    Ramka wyboru katalogu źródłowego projektu.
    Project source directory selection frame.
    """

    def __init__(
        self, master: tk.Widget, config_manager: Any, on_browse: Callable
    ) -> None:
        """
        Inicjalizuje ramkę źródłową.
        """
        super().__init__(master, config_manager, padding="15", style="Bold.TLabelframe")
        self.on_browse = on_browse
        self.columnconfigure(1, weight=1)
        self._create_widgets()

    def _create_widgets(self) -> None:
        self.project_dir_label = ttk.Label(self)
        self.project_dir_label.grid(row=0, column=0, sticky="e", padx=5, pady=5)
        ttk.Entry(self, textvariable=self.cfg.project_source_dir_var).grid(
            row=0, column=1, padx=5, pady=5, sticky="ew"
        )
        self.browse_button = ttk.Button(self, command=self.on_browse)
        self.browse_button.grid(row=0, column=2, padx=5, pady=5)

    def update_texts(self) -> None:
        self.configure(text=self._translate("📁  2. Project Source for RPi"))
        self.project_dir_label.config(text=self._translate("Project Directory:"))
        self.browse_button.config(text=self._translate("📂 Browse..."))


class ConfigurationFrame(BaseFrame):
    """
    Ramka konfiguracji sprzętowej i sieciowej (Tailscale, RTK, Hardware).
    Hardware and network configuration frame (Tailscale, RTK, Hardware).
    """

    def __init__(
        self,
        master: tk.Widget,
        config_manager: Any,
        on_fetch_ip: Callable,
        on_rtk_toggle: Callable,
        on_lidar_toggle: Callable,
        on_detect_cameras: Callable,
    ) -> None:
        """
        Inicjalizuje ramkę konfiguracji.
        Initializes the configuration frame.
        """
        super().__init__(master, config_manager, padding="15", style="Bold.TLabelframe")
        self.on_fetch_ip = on_fetch_ip
        self.on_rtk_toggle = on_rtk_toggle
        self.on_lidar_toggle = on_lidar_toggle
        self.on_detect_cameras = on_detect_cameras
        self._create_widgets()

    def _create_widgets(self) -> None:
        # PC Tailscale IP
        pc_ip_frame = ttk.Frame(self)
        pc_ip_frame.pack(fill=tk.X, pady=(0, 10))
        self.pc_ip_label = ttk.Label(pc_ip_frame)
        self.pc_ip_label.pack(side=tk.LEFT, padx=(0, 5))
        ttk.Entry(
            pc_ip_frame, textvariable=self.cfg.pc_tailscale_ip_var, width=25
        ).pack(side=tk.LEFT, padx=5)
        self.fetch_ip_button = ttk.Button(pc_ip_frame, command=self.on_fetch_ip)
        self.fetch_ip_button.pack(side=tk.LEFT, padx=5)

        # Network Ports (UDP)
        net_ports_frame = ttk.Frame(self)
        net_ports_frame.pack(fill=tk.X, pady=(0, 10))

        self.pc_port_label = ttk.Label(net_ports_frame)
        self.pc_port_label.pack(side=tk.LEFT, padx=(0, 5))
        ttk.Entry(
            net_ports_frame, textvariable=self.cfg.pc_udp_port_var, width=10
        ).pack(side=tk.LEFT, padx=5)

        self.rpi_port_label = ttk.Label(net_ports_frame)
        self.rpi_port_label.pack(side=tk.LEFT, padx=(10, 5))
        ttk.Entry(
            net_ports_frame, textvariable=self.cfg.rpi_udp_port_var, width=10
        ).pack(side=tk.LEFT, padx=5)

        # --- New Communication Section ---
        comm_section_frame = ttk.LabelFrame(self, padding="10")
        comm_section_frame.pack(fill=tk.X, pady=(10, 5))

        self.comm_mode_label = ttk.Label(comm_section_frame)
        self.comm_mode_label.grid(row=0, column=0, sticky="e", padx=5, pady=2)
        ttk.Combobox(
            comm_section_frame,
            textvariable=self.cfg.comm_mode_var,
            values=["AUTO", "WEBRTC", "UDP"],
            state="readonly",
            width=10,
        ).grid(row=0, column=1, padx=5, pady=2, sticky="w")

        self.comm_protocol_label = ttk.Label(comm_section_frame)
        self.comm_protocol_label.grid(row=0, column=2, sticky="e", padx=5, pady=2)

        ttk.Combobox(
            comm_section_frame,
            textvariable=self.cfg.comm_protocol_var,
            values=["NATIVE", "MAVLINK"],
            state="readonly",
            width=10,
        ).grid(row=0, column=3, padx=5, pady=2, sticky="w")

        self.mavlink_sysid_label = ttk.Label(comm_section_frame)
        self.mavlink_sysid_label.grid(row=1, column=0, sticky="e", padx=5, pady=2)
        ttk.Entry(
            comm_section_frame,
            textvariable=self.cfg.mavlink_system_id_var,
            width=5,
        ).grid(row=1, column=1, padx=5, pady=2, sticky="w")

        self.mavlink_hz_label = ttk.Label(comm_section_frame)
        self.mavlink_hz_label.grid(row=1, column=2, sticky="e", padx=5, pady=2)
        ttk.Combobox(
            comm_section_frame,
            textvariable=self.cfg.mavlink_throttle_hz_var,
            values=["1", "2", "5", "10", "20", "50"],
            state="readonly",
            width=5,
        ).grid(row=1, column=3, padx=5, pady=2, sticky="w")

        # RTK
        self.rtk_check = ttk.Checkbutton(
            self, variable=self.cfg.use_rtk_var, command=self.on_rtk_toggle
        )
        self.rtk_check.pack(anchor="w", pady=(5, 5))
        self.rtk_fields_frame = ttk.Frame(self)
        self.rtk_fields_frame.pack(fill=tk.X, padx=20)

        # Grid RTK
        self.ntrip_user_label = ttk.Label(self.rtk_fields_frame)
        self.ntrip_user_label.grid(row=0, column=0, sticky="e", padx=5, pady=2)
        ttk.Entry(
            self.rtk_fields_frame, textvariable=self.cfg.ntrip_user_var, width=20
        ).grid(row=0, column=1, padx=5, pady=2, sticky="w")

        self.ntrip_pass_label = ttk.Label(self.rtk_fields_frame)
        self.ntrip_pass_label.grid(row=0, column=2, sticky="e", padx=5, pady=2)
        self.ntrip_pass_entry = ttk.Entry(
            self.rtk_fields_frame,
            textvariable=self.cfg.ntrip_pass_var,
            show="*",
            width=20,
        )
        self.ntrip_pass_entry.grid(row=0, column=3, padx=5, pady=2, sticky="w")
        self.ntrip_pass_toggle = ttk.Button(
            self.rtk_fields_frame,
            text="👁",
            width=3,
            command=lambda: self._toggle_password_visibility(
                self.ntrip_pass_entry, self.ntrip_pass_toggle
            ),
        )
        self.ntrip_pass_toggle.grid(row=0, column=4, padx=5, pady=2)

        self.ntrip_host_label = ttk.Label(self.rtk_fields_frame)
        self.ntrip_host_label.grid(row=1, column=0, sticky="e", padx=5, pady=2)
        ttk.Entry(
            self.rtk_fields_frame, textvariable=self.cfg.ntrip_host_var, width=20
        ).grid(row=1, column=1, padx=5, pady=2, sticky="w")

        self.ntrip_port_label = ttk.Label(self.rtk_fields_frame)
        self.ntrip_port_label.grid(row=1, column=2, sticky="e", padx=5, pady=2)
        ttk.Entry(
            self.rtk_fields_frame, textvariable=self.cfg.ntrip_port_var, width=10
        ).grid(row=1, column=3, padx=5, pady=2, sticky="w")

        self.ntrip_mount_label = ttk.Label(self.rtk_fields_frame)
        self.ntrip_mount_label.grid(row=2, column=0, sticky="e", padx=5, pady=2)
        ttk.Entry(
            self.rtk_fields_frame, textvariable=self.cfg.ntrip_mount_var, width=20
        ).grid(row=2, column=1, padx=5, pady=2, sticky="w")

        # Hardware
        self.hardware_frame = ttk.LabelFrame(self, padding="10")
        self.hardware_frame.pack(fill=tk.X, pady=(15, 5))

        self.imu_driver_label = ttk.Label(self.hardware_frame)
        self.imu_driver_label.grid(row=0, column=0, sticky="e", padx=5, pady=2)
        ttk.Combobox(
            self.hardware_frame,
            textvariable=self.cfg.imu_driver_var,
            values=[
                "native_mpu9250",
                "native_mpu6050",
                "native_gy91",
                "native_bmx160_bmp388",
                "native_bmx160",
                "native_bno08x",
            ],
            state="readonly",
            width=25,
        ).grid(row=0, column=1, padx=5, pady=2, sticky="w")

        self.gps_enabled_check = ttk.Checkbutton(
            self.hardware_frame, variable=self.cfg.gps_enabled_var
        )
        self.gps_enabled_check.grid(
            row=1, column=0, columnspan=2, sticky="w", padx=5, pady=(5, 2)
        )

        self.gps_port_label = ttk.Label(self.hardware_frame)
        self.gps_port_label.grid(row=2, column=0, sticky="e", padx=5, pady=2)
        ttk.Entry(
            self.hardware_frame, textvariable=self.cfg.gps_port_var, width=22
        ).grid(row=2, column=1, padx=5, pady=2, sticky="w")

        self.gps_baudrate_label = ttk.Label(self.hardware_frame)
        self.gps_baudrate_label.grid(row=2, column=2, sticky="e", padx=5, pady=2)
        ttk.Combobox(
            self.hardware_frame,
            textvariable=self.cfg.gps_baudrate_var,
            values=["9600", "38400", "57600", "115200"],
            state="readonly",
            width=15,
        ).grid(row=2, column=3, padx=5, pady=2, sticky="w")

        self.lidar_enabled_check = ttk.Checkbutton(
            self.hardware_frame,
            variable=self.cfg.lidar_enabled_var,
            command=self.on_lidar_toggle,
        )
        self.lidar_enabled_check.grid(
            row=3, column=0, columnspan=2, sticky="w", padx=5, pady=(5, 2)
        )

        self.lidar_port_label = ttk.Label(self.hardware_frame)
        self.lidar_port_label.grid(row=4, column=0, sticky="e", padx=5, pady=2)
        self.lidar_port_entry = ttk.Entry(
            self.hardware_frame, textvariable=self.cfg.lidar_port_var, width=22
        )
        self.lidar_port_entry.grid(row=4, column=1, padx=5, pady=2, sticky="w")

        self.lidar_baud_label = ttk.Label(self.hardware_frame)
        self.lidar_baud_label.grid(row=4, column=2, sticky="e", padx=5, pady=2)
        ttk.Combobox(
            self.hardware_frame,
            textvariable=self.cfg.lidar_baudrate_var,
            values=["9600", "38400", "57600", "115200", "230400", "460800", "921600"],
            state="readonly",
            width=15,
        ).grid(row=4, column=3, padx=5, pady=2, sticky="w")

        self.elrs_enabled_check = ttk.Checkbutton(
            self.hardware_frame, variable=self.cfg.elrs_enabled_var
        )
        self.elrs_enabled_check.grid(
            row=5, column=0, columnspan=2, sticky="w", padx=5, pady=(5, 0)
        )
        self.elrs_port_label = ttk.Label(self.hardware_frame)
        self.elrs_port_label.grid(row=6, column=0, sticky="e", padx=5, pady=2)
        self.elrs_port_entry = ttk.Entry(
            self.hardware_frame, textvariable=self.cfg.elrs_port_var, width=22
        )
        self.elrs_port_entry.grid(row=6, column=1, padx=5, pady=2, sticky="w")

        self.elrs_baud_label = ttk.Label(self.hardware_frame)
        self.elrs_baud_label.grid(row=6, column=2, sticky="e", padx=5, pady=2)
        ttk.Combobox(
            self.hardware_frame,
            textvariable=self.cfg.elrs_baudrate_var,
            values=["9600", "38400", "57600", "115200", "420000"],
            state="readonly",
            width=15,
        ).grid(row=6, column=3, padx=5, pady=2, sticky="w")

        # Video
        self.video_frame = ttk.LabelFrame(self, padding="10")
        self.video_frame.pack(fill=tk.X, pady=(10, 5))

        # Camera Port
        self.cam_port_label = ttk.Label(self.video_frame)
        self.cam_port_label.grid(row=0, column=0, sticky="e", padx=5, pady=2)
        ttk.Combobox(
            self.video_frame,
            textvariable=self.cfg.camera_port_var,
            values=["cam0", "cam1", "/dev/video0", "/dev/video1"],
            width=12,
        ).grid(row=0, column=1, sticky="w", padx=5)

        # Camera Type
        self.cam_type_label = ttk.Label(self.video_frame)
        self.cam_type_label.grid(row=0, column=2, sticky="e", padx=5, pady=2)
        ttk.Combobox(
            self.video_frame,
            textvariable=self.cfg.camera_type_var,
            values=["AUTO", "imx219", "imx708", "ov5647", "imx477", "imx519"],
            state="readonly",
            width=10,
        ).grid(row=0, column=3, sticky="w", padx=5)

        # Resolution
        self.cam_resolution_label = ttk.Label(self.video_frame)
        self.cam_resolution_label.grid(row=0, column=4, sticky="e", padx=5, pady=2)
        self.cam_resolution_combo = ttk.Combobox(
            self.video_frame,
            textvariable=self.cfg.camera_resolution_var,
            values=[
                "640x480",
                "800x600",
                "1280x720",
                "1640x1232",
                "1920x1080",
                "3280x2464",
            ],
            state="readonly",
            width=12,
        )
        self.cam_resolution_combo.grid(row=0, column=5, sticky="w", padx=5)

        # FPS
        self.cam_fps_label = ttk.Label(self.video_frame)
        self.cam_fps_label.grid(row=0, column=6, sticky="e", padx=5, pady=2)
        ttk.Combobox(
            self.video_frame,
            textvariable=self.cfg.camera_fps_var,
            values=["15", "20", "30"],
            state="readonly",
            width=6,
        ).grid(row=0, column=7, sticky="w", padx=5)

        # Detect Cameras Button
        self.detect_cameras_button = ttk.Button(
            self.video_frame,
            text="🔍 Detect",
            width=10,
            command=self.on_detect_cameras,
        )
        self.detect_cameras_button.grid(row=1, column=6, padx=10)

        # Bitrate (New Row)
        self.bitrate_label = ttk.Label(self.video_frame)
        self.bitrate_label.grid(row=1, column=0, sticky="e", padx=5, pady=2)

        self.bitrate_combo = ttk.Combobox(
            self.video_frame,
            textvariable=self.cfg.camera_bitrate_var,
            values=[
                "1 Mbps",
                "2 Mbps",
                "5 Mbps",
                "8 Mbps",
                "10 Mbps",
                "15 Mbps",
                "20 Mbps",
            ],
            state="readonly",
            width=10,
        )
        self.bitrate_combo.grid(
            row=1, column=1, columnspan=2, sticky="w", padx=5, pady=2
        )

        # Low Latency Button
        self.low_latency_button = ttk.Button(
            self.video_frame,
            text="Low Latency Profile",
            command=self._apply_low_latency,
        )
        self.low_latency_button.grid(
            row=1, column=4, columnspan=3, padx=5, pady=2, sticky="ew"
        )

    def _apply_low_latency(self) -> None:
        """Applies the Low Latency Profile (800x600, 30fps, 2Mbps)."""
        self.cfg.camera_resolution_var.set("800x600")
        self.cfg.camera_fps_var.set("30")
        self.cfg.camera_bitrate_var.set("2 Mbps")

    def update_texts(self) -> None:
        t = self._translate
        self.configure(text=t("⚙️  3. Project Configuration (generates config.json)"))
        self.pc_ip_label.config(text=t("Tailscale PC IP:"))
        self.fetch_ip_button.config(text=t("🌐 Fetch My IP"))
        self.pc_port_label.config(text=t("GCS UDP Port:"))
        self.rpi_port_label.config(text=t("RPi UDP Port:"))
        self.comm_mode_label.config(text=t("Comm Mode:"))
        self.comm_protocol_label.config(text=t("Protocol:"))
        self.mavlink_sysid_label.config(text=t("MAVLink SysID:"))
        self.mavlink_hz_label.config(text=t("Telemetry Rate (Hz):"))
        self.rtk_check.config(text=t("📡 Use RTK Positioning (NTRIP)"))
        self.ntrip_user_label.config(text=t("NTRIP User:"))
        self.ntrip_pass_label.config(text=t("NTRIP Password:"))
        self.ntrip_host_label.config(text=t("NTRIP Host:"))
        self.ntrip_port_label.config(text=t("NTRIP Port:"))
        self.ntrip_mount_label.config(text=t("NTRIP Mountpoint:"))
        self.hardware_frame.config(text=t("🔧 Hardware"))
        self.imu_driver_label.config(text=t("IMU Driver:"))
        self.gps_enabled_check.config(text=t("📍 Enable GPS"))
        self.gps_port_label.config(text=t("Port:"))
        self.gps_baudrate_label.config(text=t("Baudrate:"))
        self.video_frame.config(text=t("🎥 Video & Camera"))
        self.cam_port_label.config(text=t("Camera Port:"))
        self.cam_type_label.config(text=t("Camera Type:"))
        self.cam_resolution_label.config(text=t("Resolution:"))
        self.cam_fps_label.config(text=t("FPS:"))
        self.bitrate_label.config(text=t("Bitrate:"))
        self.detect_cameras_button.config(text=t("🔍 Detect"))
        self.low_latency_button.config(text=t("⚡ Low Latency Profile"))
        self.lidar_enabled_check.config(text=t("📡 Enable Lidar (LD08)"))
        self.lidar_port_label.config(text=t("Lidar Port:"))
        self.lidar_baud_label.config(text=t("Lidar Baudrate:"))
        self.elrs_enabled_check.config(text=t("📻 Enable RF Link (ELRS/MAVLink)"))
        self.elrs_port_label.config(text=t("RF Port:"))
        self.elrs_baud_label.config(text=t("RF Baudrate:"))


class ActionsFrame(ttk.Frame):
    """
    Ramka akcji głównych (Wdrożenie).
    Main actions frame (Deploy).
    """

    def __init__(
        self,
        master: tk.Widget,
        config_manager: Any,
        on_deploy: Callable,
    ) -> None:
        super().__init__(master)
        self.cfg = config_manager
        self._translate = config_manager.translate
        self.inner = ttk.Frame(self)
        self.inner.pack(anchor="center")
        self.deploy_button = ttk.Button(
            self.inner, command=on_deploy, style="Accent.TButton"
        )
        self.deploy_button.pack(side=tk.LEFT, padx=10, ipady=5)
        self.fast_mode_check = ttk.Checkbutton(
            self.inner, variable=self.cfg.fast_mode_var
        )
        self.fast_mode_check.pack(side=tk.LEFT, padx=10)

    def update_texts(self) -> None:
        self.deploy_button.config(
            text=self._translate("🚀  Start Deployment on RPi")
        )
        self.fast_mode_check.config(
            text=self._translate("⚡ Fast Mode (Skip System Setup)")
        )


class AdvancedActionsFrame(BaseFrame):
    """
    Ramka akcji zaawansowanych z trybem developerskim.
    Advanced actions frame with developer mode toggle.
    """

    def __init__(
        self,
        master: tk.Widget,
        config_manager: Any,
        on_restart: Callable,
        on_reboot: Callable,
        on_logs: Callable,
        on_build_logs: Callable,
        on_diag: Callable,
        on_fast_update: Callable,
        on_backup: Callable,
        on_update_docker: Callable,
        on_test_conn: Callable,
        on_hot_deploy: Callable = None,
    ) -> None:
        super().__init__(
            master,
            config_manager,
            padding="15",
            style="Bold.TLabelframe",
        )
        self.columnconfigure(0, weight=1)
        self._create_widgets(
            on_restart,
            on_reboot,
            on_logs,
            on_build_logs,
            on_diag,
            on_fast_update,
            on_backup,
            on_update_docker,
            on_test_conn,
            on_hot_deploy,
        )

    def _create_widgets(
        self,
        on_restart: Callable,
        on_reboot: Callable,
        on_logs: Callable,
        on_build_logs: Callable,
        on_diag: Callable,
        on_fast_update: Callable,
        on_backup: Callable,
        on_update_docker: Callable,
        on_test_conn: Callable,
        on_hot_deploy: Callable = None,
    ) -> None:
        # --- Always-visible buttons ---
        main_btn_frame = ttk.Frame(self)
        main_btn_frame.pack(side=tk.TOP, fill=tk.X, pady=(0, 5))

        self.restart_service_button = ttk.Button(main_btn_frame, command=on_restart)
        self.restart_service_button.pack(side=tk.LEFT, padx=5)
        self.reboot_pi_button = ttk.Button(main_btn_frame, command=on_reboot)
        self.reboot_pi_button.pack(side=tk.LEFT, padx=5)

        # Service indicators (always visible)
        svc_frame = ttk.Frame(main_btn_frame, padding=(10, 0))
        svc_frame.pack(side=tk.RIGHT, fill=tk.Y)
        self.industrial_status_label = ttk.Label(
            svc_frame,
            text="Industrial: \u25cf",
            foreground="grey",
        )
        self.industrial_status_label.pack(side=tk.TOP, anchor="w")
        self.video_status_label = ttk.Label(
            svc_frame,
            text="Video: \u25cf",
            foreground="grey",
        )
        self.video_status_label.pack(side=tk.TOP, anchor="w")

        # --- Developer Mode Toggle ---
        self._dev_mode_var = tk.BooleanVar(value=False)
        self.dev_mode_check = ttk.Checkbutton(
            self,
            text="🔬 Developer Mode",
            variable=self._dev_mode_var,
            command=self._toggle_dev_mode,
        )
        self.dev_mode_check.pack(side=tk.TOP, anchor="w", padx=5, pady=(5, 0))

        # --- Developer buttons (hidden by default) ---
        self.dev_btn_frame = ttk.Frame(self)

        self.show_logs_button = ttk.Button(self.dev_btn_frame, command=on_logs)
        self.show_logs_button.pack(side=tk.LEFT, padx=5, pady=3)
        self.show_build_logs_button = ttk.Button(
            self.dev_btn_frame, command=on_build_logs
        )
        self.show_build_logs_button.pack(side=tk.LEFT, padx=5, pady=3)
        self.diagnostics_button = ttk.Button(self.dev_btn_frame, command=on_diag)
        self.diagnostics_button.pack(side=tk.LEFT, padx=5, pady=3)
        self.fast_update_button = ttk.Button(self.dev_btn_frame, command=on_fast_update)
        self.fast_update_button.pack(side=tk.LEFT, padx=5, pady=3)
        self.backup_button = ttk.Button(self.dev_btn_frame, command=on_backup)
        self.backup_button.pack(side=tk.LEFT, padx=5, pady=3)
        self.update_docker_button = ttk.Button(
            self.dev_btn_frame, command=on_update_docker
        )
        self.update_docker_button.pack(side=tk.LEFT, padx=5, pady=3)
        self.hot_deploy_button = ttk.Button(
            self.dev_btn_frame,
            command=on_hot_deploy,
            style="HotDeploy.TButton",
        )
        self.hot_deploy_button.pack(side=tk.LEFT, padx=5, pady=3)
        self.test_conn_button = ttk.Button(self.dev_btn_frame, command=on_test_conn)
        self.test_conn_button.pack(side=tk.LEFT, padx=5, pady=3)

    def _toggle_dev_mode(self) -> None:
        """Pokazuje/ukrywa przyciski developerskie."""
        if self._dev_mode_var.get():
            self.dev_btn_frame.pack(side=tk.TOP, fill=tk.X, pady=(5, 0))
        else:
            self.dev_btn_frame.pack_forget()

    def update_texts(self) -> None:
        t = self._translate
        self.configure(text=t("🛠️  Advanced Actions"))
        self.restart_service_button.config(text=t("🔄 Restart Service"))
        self.reboot_pi_button.config(text=t("⚡ Reboot RPi"))
        self.show_logs_button.config(text=t("📄 Show Logs"))
        self.show_build_logs_button.config(text=t("🏗️ Build Logs"))
        self.diagnostics_button.config(text=t("🩺 Diagnostics"))
        self.fast_update_button.config(text=t("📸 Camera Update"))
        self.backup_button.config(text=t("💾 Backup Docker"))
        self.update_docker_button.config(text=t("🐳 Update Docker"))
        self.hot_deploy_button.config(text=t("⚡ Hot Deploy"))
        self.test_conn_button.config(text=t("🔌 Test SSH"))

    def set_state(self, state: str) -> None:
        """Włącza/wyłącza widżety interaktywne w ramce."""
        widgets_to_toggle = [
            ttk.Button,
            ttk.Checkbutton,
            ttk.Entry,
            ttk.Combobox,
        ]

        def _recursive_set(parent):
            for child in parent.winfo_children():
                if any(isinstance(child, t) for t in widgets_to_toggle):
                    try:
                        child.config(state=state)
                    except tk.TclError:
                        pass
                if child.winfo_children():
                    _recursive_set(child)

        _recursive_set(self)


class LogFrame(BaseFrame):
    """
    Ramka wyświetlająca logi aplikacji.
    Frame displaying application logs.
    """

    def __init__(self, master: tk.Widget, config_manager: Any) -> None:
        super().__init__(master, config_manager, padding="15", style="Bold.TLabelframe")
        self._create_widgets()

    def _create_widgets(self) -> None:
        self.log_widget = scrolledtext.ScrolledText(
            self,
            wrap=tk.WORD,
            height=30,
            font=("Cascadia Code", 9),
            bg=DT["surface2"],
            fg=DT["text"],
            insertbackground=DT["accent"],
            selectbackground=DT["selection"],
            selectforeground="white",
            relief="flat",
            bd=0,
            padx=10,
            pady=8,
        )
        self.log_widget.tag_configure("info", foreground=DT["text"])
        self.log_widget.tag_configure(
            "verbose", foreground=DT["text_muted"], font=("Cascadia Code", 8)
        )
        self.log_widget.tag_configure(
            "warning", foreground=DT["warning"], font=("Cascadia Code", 9, "bold")
        )
        self.log_widget.tag_configure(
            "error", foreground=DT["error"], font=("Cascadia Code", 9, "bold")
        )
        self.log_widget.tag_configure(
            "success", foreground=DT["success"], font=("Cascadia Code", 9, "bold")
        )
        self.log_widget.tag_configure(
            "header",
            foreground=DT["accent"],
            font=("Cascadia Code", 10, "bold"),
            spacing3=5,
        )
        self.log_widget.tag_configure(
            "highlight", background=DT["surface"], foreground=DT["text"]
        )
        self.log_widget.pack(fill=tk.BOTH, expand=True)

    def update_texts(self) -> None:
        self.configure(text=self._translate("📋  Deployment Logs"))
