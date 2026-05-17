import gettext
import json
import logging
import os
import sys
import tkinter as tk
from typing import Any, Dict

APP_NAME = "RCSIMDeploymentTool"

# Jeśli aplikacja jest skompilowana za pomocą PyInstallera, sys.frozen będzie True.
# Chcemy wtedy zapisywać ustawienia obok pliku wykonywalnego EXE (sys.executable).
if getattr(sys, "frozen", False):
    application_path = os.path.dirname(sys.executable)
else:
    application_path = os.path.dirname(os.path.abspath(__file__))

SETTINGS_FILE = os.path.join(application_path, "deployment_settings.json")

LOCALE_DIR = os.path.abspath(
    os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "ui", "locales")
)
SUPPORTED_LANGUAGES = {"English": "en", "Polski": "pl"}


class ConfigManager:
    def __init__(self, root: tk.Tk) -> None:
        """
        Inicjalizuje menedżera konfiguracji.
        """
        self.root = root
        self._translate = gettext.gettext

        # UI Variables
        self.language_var = tk.StringVar(value="English")
        self.project_source_dir_var = tk.StringVar(
            value=os.environ.get(
                "RCSIM_DEPLOY_PATH",
                os.path.abspath(
                    os.path.join(
                        os.path.dirname(__file__),
                        "..",
                        "..",
                        "RCSIMDEPLOY",
                        "rpi_project_source",
                    )
                ),
            )
        )
        self.rpi_host_var = tk.StringVar()
        self.rpi_user_var = tk.StringVar()
        self.rpi_pass_var = tk.StringVar()
        self.rpi_use_key_var = tk.BooleanVar(value=False)
        self.rpi_key_path_var = tk.StringVar()
        self.rpi_key_passphrase_var = tk.StringVar()
        self.new_ssh_pass_var = tk.StringVar()
        self.pc_tailscale_ip_var = tk.StringVar()
        self.use_rtk_var = tk.BooleanVar(value=True)
        self.ntrip_user_var = tk.StringVar()
        self.ntrip_pass_var = tk.StringVar()
        self.ntrip_host_var = tk.StringVar()
        self.ntrip_port_var = tk.StringVar()
        self.ntrip_mount_var = tk.StringVar()
        self.pc_udp_port_var = tk.StringVar(value="12347")
        self.rpi_udp_port_var = tk.StringVar(value="12346")

        # Communication Mode & Protocol
        self.comm_mode_var = tk.StringVar(value="AUTO")
        self.comm_protocol_var = tk.StringVar(value="NATIVE")
        self.mavlink_connection_var = tk.StringVar(value="/dev/ttyAMA3:57600")
        self.mavlink_system_id_var = tk.StringVar(value="1")
        self.mavlink_throttle_hz_var = tk.StringVar(value="5")

        # Hardware Configuration
        self.imu_driver_var = tk.StringVar(value="native_mpu9250")
        self.gps_enabled_var = tk.BooleanVar(value=True)
        self.gps_port_var = tk.StringVar(value="/dev/ttyAMA0")
        self.gps_baudrate_var = tk.StringVar(value="115200")
        self.camera_port_var = tk.StringVar(value="cam0")
        self.camera_resolution_var = tk.StringVar(value="1920x1080")
        self.camera_fps_var = tk.StringVar(value="30")
        self.camera_bitrate_var = tk.StringVar(value="5 Mbps")
        self.lidar_enabled_var = tk.BooleanVar(value=False)
        self.lidar_port_var = tk.StringVar(value="/dev/ttyUSB0")
        self.lidar_baudrate_var = tk.StringVar(value="115200")
        self.elrs_enabled_var = tk.BooleanVar(value=True)
        self.elrs_port_var = tk.StringVar(
            value="/dev/ttyAMA3"
        )  # UART 3 (XR4 on GPIO8/9)
        self.elrs_baudrate_var = tk.StringVar(value="57600")
        self.camera_type_var = tk.StringVar(value="AUTO")
        self.fast_mode_var = tk.BooleanVar(value=True)  # Default to True for speed

        # Initial Language Setup
        self.switch_language("en")

    def translate(self, text: str) -> str:
        """Tłumaczy tekst."""
        return self._translate(text)

    def switch_language(self, lang_code: str) -> None:
        """Zmienia język aplikacji."""
        try:
            lang = gettext.translation(
                APP_NAME,
                localedir=LOCALE_DIR,
                languages=[lang_code],
                fallback=True,
            )
            self._translate = lang.gettext
        except Exception as e:
            logging.warning(f"Language '{lang_code}' not found: {e}")
            self._translate = gettext.gettext

    def save_settings(self) -> None:
        """Zapisuje ustawienia do pliku JSON."""
        settings = {
            "rpi_host": self.rpi_host_var.get(),
            "rpi_user": self.rpi_user_var.get(),
            "rpi_pass": self.rpi_pass_var.get(),
            "project_source": self.project_source_dir_var.get(),
            "pc_tailscale_ip": self.pc_tailscale_ip_var.get(),
            "use_rtk": self.use_rtk_var.get(),
            "ntrip_user": self.ntrip_user_var.get(),
            "ntrip_pass": self.ntrip_pass_var.get(),
            "ntrip_host": self.ntrip_host_var.get(),
            "ntrip_port": self.ntrip_port_var.get(),
            "ntrip_mount": self.ntrip_mount_var.get(),
            "imu_driver": self.imu_driver_var.get(),
            "gps_enabled": self.gps_enabled_var.get(),
            "gps_port": self.gps_port_var.get(),
            "gps_baudrate": self.gps_baudrate_var.get(),
            "camera_port": self.camera_port_var.get(),
            "camera_resolution": self.camera_resolution_var.get(),
            "camera_fps": self.camera_fps_var.get(),
            "camera_bitrate": self.camera_bitrate_var.get(),
            "camera_type": self.camera_type_var.get(),
            "lidar_enabled": self.lidar_enabled_var.get(),
            "lidar_port": self.lidar_port_var.get(),
            "elrs_enabled": self.elrs_enabled_var.get(),
            "elrs_port": self.elrs_port_var.get(),
            "language": self.language_var.get(),
            "rpi_use_key": self.rpi_use_key_var.get(),
            "rpi_key_path": self.rpi_key_path_var.get(),
            "rpi_key_passphrase": self.rpi_key_passphrase_var.get(),
            "pc_udp_port": self.pc_udp_port_var.get(),
            "rpi_udp_port": self.rpi_udp_port_var.get(),
            "comm_mode": self.comm_mode_var.get(),
            "comm_protocol": self.comm_protocol_var.get(),
            "lidar_baudrate": self.lidar_baudrate_var.get(),
            "elrs_baudrate": self.elrs_baudrate_var.get(),
            "mavlink_system_id": self.mavlink_system_id_var.get(),
            "mavlink_throttle_hz": self.mavlink_throttle_hz_var.get(),
            "fast_mode": self.fast_mode_var.get(),
        }
        try:
            with open(SETTINGS_FILE, "w", encoding="utf-8") as f:
                json.dump(settings, f, indent=4)
        except Exception as e:
            logging.error(f"Failed to save settings: {e}")

    def load_settings(self) -> None:
        """Wczytuje ustawienia z pliku JSON."""
        if not os.path.exists(SETTINGS_FILE):
            return
        try:
            with open(SETTINGS_FILE, "r", encoding="utf-8") as f:
                settings = json.load(f)

            def safe_set(var: Any, key: str) -> None:
                if key in settings:
                    var.set(settings[key])

            safe_set(self.rpi_host_var, "rpi_host")
            safe_set(self.rpi_user_var, "rpi_user")
            safe_set(self.rpi_pass_var, "rpi_pass")
            safe_set(self.project_source_dir_var, "project_source")
            safe_set(self.pc_tailscale_ip_var, "pc_tailscale_ip")
            safe_set(self.use_rtk_var, "use_rtk")
            safe_set(self.ntrip_user_var, "ntrip_user")
            safe_set(self.ntrip_pass_var, "ntrip_pass")
            safe_set(self.ntrip_host_var, "ntrip_host")
            safe_set(self.ntrip_port_var, "ntrip_port")
            safe_set(self.ntrip_mount_var, "ntrip_mount")
            safe_set(self.imu_driver_var, "imu_driver")
            safe_set(self.gps_enabled_var, "gps_enabled")
            safe_set(self.gps_port_var, "gps_port")
            safe_set(self.gps_baudrate_var, "gps_baudrate")
            safe_set(self.camera_port_var, "camera_port")
            safe_set(self.camera_resolution_var, "camera_resolution")
            safe_set(self.camera_fps_var, "camera_fps")
            safe_set(self.camera_bitrate_var, "camera_bitrate")
            safe_set(self.camera_type_var, "camera_type")
            safe_set(self.lidar_enabled_var, "lidar_enabled")
            safe_set(self.lidar_port_var, "lidar_port")
            safe_set(self.elrs_enabled_var, "elrs_enabled")
            safe_set(self.elrs_port_var, "elrs_port")
            safe_set(self.language_var, "language")
            safe_set(self.rpi_use_key_var, "rpi_use_key")
            safe_set(self.rpi_key_path_var, "rpi_key_path")
            safe_set(self.rpi_key_passphrase_var, "rpi_key_passphrase")
            safe_set(self.pc_udp_port_var, "pc_udp_port")
            safe_set(self.rpi_udp_port_var, "rpi_udp_port")
            safe_set(self.comm_mode_var, "comm_mode")
            safe_set(self.comm_protocol_var, "comm_protocol")
            safe_set(self.lidar_baudrate_var, "lidar_baudrate")
            safe_set(self.elrs_baudrate_var, "elrs_baudrate")
            safe_set(self.mavlink_system_id_var, "mavlink_system_id")
            safe_set(self.mavlink_throttle_hz_var, "mavlink_throttle_hz")
            safe_set(self.fast_mode_var, "fast_mode")

            if self.language_var.get() in SUPPORTED_LANGUAGES:
                l_code = SUPPORTED_LANGUAGES[self.language_var.get()]
                self.switch_language(l_code)

        except Exception as e:
            logging.error(f"Failed to load settings: {e}")

    def get_full_config_payload(self) -> Dict[str, Any]:
        """Zbiera konfigurację dla pliku config.json."""
        gps_baud = 115200
        try:
            gps_baud = int(self.gps_baudrate_var.get())
        except Exception:
            pass

        # Parse camera resolution
        camera_res = [1920, 1080]
        try:
            res_str = self.camera_resolution_var.get()
            if "x" in res_str:
                w, h = res_str.split("x")
                camera_res = [int(w), int(h)]
        except Exception:
            pass

        # Parse camera FPS
        camera_fps = 30
        try:
            camera_fps = int(self.camera_fps_var.get())
        except Exception:
            pass

        # Parse camera bitrate
        camera_bitrate_bps = 5_000_000
        try:
            bitrate_str = self.camera_bitrate_var.get()
            camera_bitrate_bps = int(bitrate_str.split()[0]) * 1_000_000
        except Exception:
            pass

        return {
            "hardware": {
                "imu": {"driver": self.imu_driver_var.get().strip()},
                "gps": {
                    "enabled": self.gps_enabled_var.get(),
                    "port": self.gps_port_var.get().strip(),
                    "baudrate": gps_baud,
                },
                "lidar": {
                    "enabled": self.lidar_enabled_var.get(),
                    "port": (self.lidar_port_var.get().strip()),
                    "baudrate": int(self.lidar_baudrate_var.get()),
                },
                "elrs": {
                    "enabled": self.elrs_enabled_var.get(),
                    "port": self.elrs_port_var.get().strip(),
                    "baudrate": int(self.elrs_baudrate_var.get()),
                },
            },
            "camera": {
                "resolution": camera_res,
                "fps": camera_fps,
                "port": self.camera_port_var.get().strip(),
                "bitrate": camera_bitrate_bps,
                "type": self.camera_type_var.get(),
                "dynamic_bitrate": True,
                "dynamic_resolution": True,
            },
            "video": {
                "resolution": camera_res,
                "fps": camera_fps,
                "dynamic_bitrate": True,
                "dynamic_resolution": True,
            },
            "network": {
                "pc_udp_port": int(self.pc_udp_port_var.get()),
                "rpi_udp_port": int(self.rpi_udp_port_var.get()),
                "adaptive_bitrate_enabled": True,
            },
            "comm_mode": self.comm_mode_var.get(),
            "comm_protocol": self.comm_protocol_var.get(),
            "system_id": int(self.mavlink_system_id_var.get() or 10),
            "mavlink_throttle_hz": int(self.mavlink_throttle_hz_var.get() or 10),
            "mavlink_connection": f"{self.elrs_port_var.get().strip()}:{self.elrs_baudrate_var.get()}",
        }

    def get_deployment_config(self) -> Dict[str, Any]:
        """Zbiera konfigurację wdrożeniową."""
        key_p = self.rpi_key_path_var.get()
        return {
            "rpi_host": self.rpi_host_var.get(),
            "rpi_user": self.rpi_user_var.get(),
            "rpi_pass": self.rpi_pass_var.get(),
            "new_ssh_pass": self.new_ssh_pass_var.get(),
            "project_source_dir": self.project_source_dir_var.get(),
            "pc_tailscale_ip": self.pc_tailscale_ip_var.get(),
            "use_rtk": self.use_rtk_var.get(),
            "ntrip_user": self.ntrip_user_var.get(),
            "ntrip_pass": self.ntrip_pass_var.get(),
            "ntrip_host": self.ntrip_host_var.get(),
            "ntrip_port": self.ntrip_port_var.get(),
            "ntrip_mount": self.ntrip_mount_var.get(),
            "rpi_key_path": key_p if self.rpi_use_key_var.get() else None,
            "rpi_key_passphrase": (
                self.rpi_key_passphrase_var.get()
                if self.rpi_use_key_var.get()
                else None
            ),
            "full_config_payload": self.get_full_config_payload(),
        }
