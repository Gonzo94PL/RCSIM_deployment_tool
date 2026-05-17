import threading
import time
import tkinter as tk
from typing import Any, Optional

from . import deployment_logic


class ServiceMonitor:
    """
    Klasa monitorująca stan usług zdalnych na RPi.
    Class for monitoring remote service status on RPi.

    Attributes:
        config (ConfigManager): Menedżer konfiguracji. / Configuration manager.
        industrial_label (tk.Label): Etykieta statusu usługi Industrial. / Industrial service status label.
        video_label (tk.Label): Etykieta statusu usługi wideo. / Video service status label.
    """

    def __init__(
        self, config_manager: Any, industrial_label: tk.Label, video_label: tk.Label
    ) -> None:
        """
        Inicjalizuje monitor usług.
        Initializes the service monitor.

        Args:
            config_manager (ConfigManager): Menedżer konfiguracji. / Configuration manager.
            industrial_label (tk.Label): Widget etykiety statusu Industrial. / Industrial status label widget.
            video_label (tk.Label): Widget etykiety statusu Video. / Video status label widget.
        """
        self.config = config_manager
        self.industrial_label = industrial_label
        self.video_label = video_label
        self.root = config_manager.root
        self.running = False
        self._monitor_thread: Optional[threading.Thread] = None

    def start(self) -> None:
        """
        Uruchamia wątek monitorujący w tle.
        Starts the background monitoring thread.
        """
        if self.running:
            return
        self.running = True
        self._monitor_thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self._monitor_thread.start()

    def stop(self) -> None:
        """
        Zatrzymuje wątek monitorujący.
        Stops the monitoring thread.
        """
        self.running = False

    def _monitor_loop(self) -> None:
        """
        Główna pętla wątku monitorującego.
        Main loop of the monitoring thread.
        """
        while self.running:
            if self.root.winfo_exists():
                self._check_services_status_silently()
            # Wait 10 seconds, but check self.running frequently for faster stop
            for _ in range(100):
                if not self.running:
                    break
                time.sleep(0.1)

    def _check_services_status_silently(self) -> None:
        """
        Sprawdza stan usług przez SSH bez logowania do głównego okna.
        Checks service status via SSH without logging to the main window.
        """
        conf = self.config.get_deployment_config()
        host = conf["rpi_host"]
        user = conf["rpi_user"]
        password = conf["rpi_pass"]
        key_path = conf["rpi_key_path"]
        key_pass = conf["rpi_key_passphrase"]

        if not host or not (password or key_path):
            return

        try:
            # Use a dummy log function to avoid flooding the main log widget
            ssh = deployment_logic.connect_ssh(
                lambda _msg, _level: None,
                self.config.translate,
                host,
                user,
                password,
                key_path,
                key_pass,
                timeout=2,
            )
            if ssh:
                # Check rcsim_industrial
                ind_status = deployment_logic.check_remote_service_status(
                    ssh, "rcsim_industrial"
                )
                vid_status = deployment_logic.check_remote_service_status(
                    ssh, "mediamtx.service"
                )

                def update_labels() -> None:
                    if self.industrial_label.winfo_exists():
                        self.industrial_label.config(
                            foreground="green" if ind_status else "red",
                            text=f"{self.config.translate('Industrial')}: {'●' if ind_status else '○'}",
                        )
                    if self.video_label.winfo_exists():
                        self.video_label.config(
                            foreground="green" if vid_status else "red",
                            text=f"{self.config.translate('Video')}: {'●' if vid_status else '○'}",
                        )

                self.root.after(0, update_labels)
        except Exception as e:
            # Silent failure for monitor, just log to python console for debugging if needed
            # logging.debug(f"Service monitor check failed: {e}")
            pass
        finally:
            if ssh:
                ssh.close()
