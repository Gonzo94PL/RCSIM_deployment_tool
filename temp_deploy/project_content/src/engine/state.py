"""
src/engine/state.py
Thread-safe stan kanałów wyjściowych systemu RC.
"""
import threading
from src.engine.gearbox import GearboxManager

class RCState:
    def __init__(self, num_channels: int = 16) -> None:
        self.num_channels = num_channels
        self._channels = [1500] * num_channels # Domyślnie 1500 us dla wszystkich kanałów
        self.paused = False
        self.gearbox = GearboxManager()
        self.drive_mode = "sport"
        self.cruise_active = False
        self.cruise_throttle_us = 1500
        self.rssi = -65
        self.link_quality = 100
        self._lock = threading.Lock()

    def set_paused(self, paused: bool) -> None:
        with self._lock:
            self.paused = paused
            if paused:
                self.cruise_active = False

    def is_paused(self) -> bool:
        with self._lock:
            return self.paused

    def set_drive_mode(self, mode: str) -> None:
        if mode in ("sport", "eco", "crawler", "wet"):
            with self._lock:
                self.drive_mode = mode

    def get_drive_mode(self) -> str:
        with self._lock:
            return self.drive_mode

    def set_cruise(self, active: bool, throttle_us: int = 1500) -> None:
        with self._lock:
            self.cruise_active = active
            self.cruise_throttle_us = max(1000, min(2000, throttle_us))

    def get_cruise(self) -> tuple[bool, int]:
        with self._lock:
            return self.cruise_active, self.cruise_throttle_us

    def set_telemetry(self, rssi: int, link_quality: int) -> None:
        with self._lock:
            self.rssi = rssi
            self.link_quality = max(0, min(100, link_quality))

    def get_telemetry(self) -> tuple[int, int]:
        with self._lock:
            return self.rssi, self.link_quality

    def set_channel(self, channel_num: int, val_us: int) -> None:
        """
        Zmienia wartość okresu mikrosekundowego kanału wyjściowego.
        Kanały są liczone od 1 do num_channels.
        """
        index = channel_num - 1
        if 0 <= index < self.num_channels:
            val_us = max(1000, min(2000, val_us))
            with self._lock:
                self._channels[index] = val_us

    def get_channels(self) -> list[int]:
        """Zwraca kopię tablicy wszystkich kanałów w mikrosekundach."""
        with self._lock:
            return list(self._channels)

    def get_channel(self, channel_num: int) -> int:
        """Odczytuje konkretny kanał."""
        index = channel_num - 1
        if 0 <= index < self.num_channels:
            with self._lock:
                return self._channels[index]
        return 1500
