"""
src/hardware/bluetooth_manager.py
Klasa zarządzająca połączeniami urządzeń Bluetooth (np. pady Xbox/PlayStation)
za pomocą systemowego bluetoothctl na Raspberry Pi 5.
"""
import logging
import re
import subprocess
import sys
import threading
import time
from typing import Any, Dict, List

logger = logging.getLogger(__name__)

class BluetoothManager:
    def __init__(self) -> None:
        self.is_scanning = False
        self.scan_results: List[Dict[str, str]] = []
        self._scan_thread: threading.Thread | None = None
        self._lock = threading.Lock()

        # Mockowane urządzenia do testów na Windows
        self._mock_devices = [
            {"mac": "11:22:33:44:55:66", "name": "Xbox Wireless Controller", "paired": True, "connected": True, "trusted": True},
            {"mac": "AA:BB:CC:DD:EE:FF", "name": "Wireless Controller (PS5 DualSense)", "paired": True, "connected": False, "trusted": True},
            {"mac": "99:88:77:66:55:44", "name": "Nintendo Switch Pro Controller", "paired": False, "connected": False, "trusted": False},
        ]

    def _is_linux(self) -> bool:
        return sys.platform.startswith("linux")

    def get_devices(self) -> List[Dict[str, Any]]:
        """Zwraca listę sparowanych oraz aktualnie wykrytych urządzeń Bluetooth."""
        if not self._is_linux():
            logger.info("BluetoothManager: Wykryto system inny niż Linux. Zwracam mockowane dane.")
            return self._mock_devices

        devices: Dict[str, Dict[str, Any]] = {}

        # 1. Pobierz sparowane urządzenia
        try:
            res = subprocess.run(["bluetoothctl", "paired-devices"], capture_output=True, text=True, timeout=5)
            if res.returncode == 0:
                for line in res.stdout.splitlines():
                    match = re.search(r"Device\s+([0-9A-Fa-f:]{17})\s+(.*)", line)
                    if match:
                        mac, name = match.group(1), match.group(2)
                        devices[mac] = {
                            "mac": mac,
                            "name": name,
                            "paired": True,
                            "connected": False,
                            "trusted": False
                        }
        except Exception as e:
            logger.error("BluetoothManager: Błąd podczas pobierania sparowanych urządzeń: %s", e)

        # 2. Pobierz szczegóły (połączony, zaufany) dla każdego ze znanych urządzeń
        for mac in list(devices.keys()):
            try:
                res = subprocess.run(["bluetoothctl", "info", mac], capture_output=True, text=True, timeout=3)
                if res.returncode == 0:
                    out = res.stdout
                    devices[mac]["connected"] = "Connected: yes" in out
                    devices[mac]["trusted"] = "Trusted: yes" in out
            except Exception as e:
                logger.error("BluetoothManager: Błąd pobierania info dla %s: %s", mac, e)

        # 3. Dodaj ostatnio zeskanowane urządzenia, które nie są jeszcze sparowane
        with self._lock:
            for dev in self.scan_results:
                mac = dev["mac"]
                if mac not in devices:
                    devices[mac] = {
                        "mac": mac,
                        "name": dev["name"],
                        "paired": False,
                        "connected": False,
                        "trusted": False
                    }

        return list(devices.values())

    def start_scan(self) -> bool:
        """Uruchamia skanowanie w tle (trwające 8 sekund)."""
        with self._lock:
            if self.is_scanning:
                return False
            self.is_scanning = True
            self.scan_results.clear()

        if not self._is_linux():
            def mock_scan():
                logger.info("BluetoothManager: Skanowanie w tle (mock)...")
                time.sleep(3)
                with self._lock:
                    self.is_scanning = False
                logger.info("BluetoothManager: Zakończono skanowanie (mock).")

            threading.Thread(target=mock_scan, daemon=True).start()
            return True

        def run_scan():
            logger.info("BluetoothManager: Uruchamianie skanowania bluetoothctl...")
            try:
                # Skanowanie przez 8 sekund
                subprocess.run(["bluetoothctl", "--timeout", "8", "scan", "on"], capture_output=True, text=True)
                
                # Pobierz wszystkie wykryte urządzenia z pamięci podręcznej bluetoothctl
                res = subprocess.run(["bluetoothctl", "devices"], capture_output=True, text=True, timeout=5)
                if res.returncode == 0:
                    found_devs = []
                    for line in res.stdout.splitlines():
                        match = re.search(r"Device\s+([0-9A-Fa-f:]{17})\s+(.*)", line)
                        if match:
                            mac, name = match.group(1), match.group(2)
                            # Pomiń urządzenia bez nazwy lub z generyczną nazwą
                            if name and not name.startswith("Unknown"):
                                found_devs.append({"mac": mac, "name": name})
                    with self._lock:
                        self.scan_results = found_devs
            except Exception as e:
                logger.error("BluetoothManager: Błąd podczas skanowania Bluetooth: %s", e)
            finally:
                with self._lock:
                    self.is_scanning = False
                logger.info("BluetoothManager: Zakończono skanowanie Bluetooth.")

        self._scan_thread = threading.Thread(target=run_scan, daemon=True)
        self._scan_thread.start()
        return True

    def pair_device(self, mac: str) -> bool:
        """Paruje i ustawia jako zaufane urządzenie o podanym MAC."""
        # Walidacja wejścia (boundary check)
        if not re.match(r"^([0-9A-Fa-f]{2}:){5}[0-9A-Fa-f]{2}$", mac):
            logger.error("BluetoothManager: Niepoprawny format adresu MAC: %s", mac)
            return False

        if not self._is_linux():
            logger.info("BluetoothManager: Parowanie %s (mock).", mac)
            for dev in self._mock_devices:
                if dev["mac"] == mac:
                    dev["paired"] = True
                    dev["trusted"] = True
            return True

        try:
            # Uruchom parowanie
            res_pair = subprocess.run(["bluetoothctl", "pair", mac], capture_output=True, text=True, timeout=15)
            # Uruchom zaufanie (trust)
            res_trust = subprocess.run(["bluetoothctl", "trust", mac], capture_output=True, text=True, timeout=10)
            return "Failed to pair" not in res_pair.stdout and "Changing trust succeeded" in res_trust.stdout
        except Exception as e:
            logger.error("BluetoothManager: Błąd parowania urządzenia %s: %s", mac, e)
            return False

    def connect_device(self, mac: str) -> bool:
        """Łączy z urządzeniem o podanym MAC."""
        if not re.match(r"^([0-9A-Fa-f]{2}:){5}[0-9A-Fa-f]{2}$", mac):
            logger.error("BluetoothManager: Niepoprawny format adresu MAC: %s", mac)
            return False

        if not self._is_linux():
            logger.info("BluetoothManager: Łączenie z %s (mock).", mac)
            for dev in self._mock_devices:
                if dev["mac"] == mac:
                    dev["connected"] = True
            return True

        try:
            res = subprocess.run(["bluetoothctl", "connect", mac], capture_output=True, text=True, timeout=15)
            return "Connection successful" in res.stdout or "Connection: yes" in res.stdout or res.returncode == 0
        except Exception as e:
            logger.error("BluetoothManager: Błąd łączenia z urządzeniem %s: %s", mac, e)
            return False

    def disconnect_device(self, mac: str) -> bool:
        """Rozłącza urządzenie o podanym MAC."""
        if not re.match(r"^([0-9A-Fa-f]{2}:){5}[0-9A-Fa-f]{2}$", mac):
            logger.error("BluetoothManager: Niepoprawny format adresu MAC: %s", mac)
            return False

        if not self._is_linux():
            logger.info("BluetoothManager: Rozłączanie %s (mock).", mac)
            for dev in self._mock_devices:
                if dev["mac"] == mac:
                    dev["connected"] = False
            return True

        try:
            res = subprocess.run(["bluetoothctl", "disconnect", mac], capture_output=True, text=True, timeout=10)
            return res.returncode == 0
        except Exception as e:
            logger.error("BluetoothManager: Błąd rozłączania urządzenia %s: %s", mac, e)
            return False

    def remove_device(self, mac: str) -> bool:
        """Usuwa (rozparowuje) urządzenie o podanym MAC."""
        if not re.match(r"^([0-9A-Fa-f]{2}:){5}[0-9A-Fa-f]{2}$", mac):
            logger.error("BluetoothManager: Niepoprawny format adresu MAC: %s", mac)
            return False

        if not self._is_linux():
            logger.info("BluetoothManager: Usuwanie %s (mock).", mac)
            self._mock_devices = [d for d in self._mock_devices if d["mac"] != mac]
            return True

        try:
            res = subprocess.run(["bluetoothctl", "remove", mac], capture_output=True, text=True, timeout=10)
            return res.returncode == 0
        except Exception as e:
            logger.error("BluetoothManager: Błąd usuwania urządzenia %s: %s", mac, e)
            return False
