"""
src/input/input_manager.py
Klasa zarządzająca wątkami wejściowymi urządzeń USB HID.
Automatycznie skanuje aktualne systemowe joysticki i tworzy EvdevReader dla zmapowanych urządzeń.
"""
import logging
from typing import Optional

from src.config_manager import ConfigManager
from src.engine.state import RCState
from src.input.evdev_reader import EvdevReader

logger = logging.getLogger(__name__)

class InputManager:
    def __init__(self, config_mgr: ConfigManager, rc_state: RCState) -> None:
        self.config_mgr = config_mgr
        self.rc_state = rc_state
        self.readers: list[EvdevReader] = []

    def _find_device_path(self, target_name: str) -> Optional[str]:
        """Wyszukuje ścieżkę evdev dla zadanej nazwy kontrolera."""
        try:
            import evdev # type: ignore
            for path in evdev.list_devices():
                try:
                    dev = evdev.InputDevice(path)
                    found = target_name.lower() in dev.name.lower()
                    dev.close()
                    if found:
                        return path
                except Exception:
                    pass
        except Exception as exc:
            logger.error("InputManager: Błąd skanowania urządzeń: %s", exc)
        return None

    def start_all(self) -> None:
        """Uruchamia wszystkie wątki wejściowe dla aktualnie aktywnego profilu."""
        self.stop_all()
        profile = self.config_mgr.get_current_profile()
        inputs = profile.get("inputs", [])
        
        logger.info("InputManager: Uruchamianie wątków wejściowych... Detekcja urządzeń z profilu '%s'", profile.get("name"))
        for input_cfg in inputs:
            dev_name = input_cfg.get("device_name", "")
            mappings = input_cfg.get("mappings", [])
            dev_path = self._find_device_path(dev_name)
            
            if dev_path:
                reader = EvdevReader(dev_path, mappings, self.rc_state, profile)
                reader.start()
                self.readers.append(reader)
                logger.info("InputManager: Przypisano urządzenie '%s' do wątku odczytu na porcie %s", dev_name, dev_path)
            else:
                logger.warning("InputManager: Nie znaleziono urządzenia '%s'. Oczekiwanie na podłączenie.", dev_name)

    def stop_all(self) -> None:
        """Bezpiecznie zatrzymuje wszystkie wątki odczytu."""
        if self.readers:
            logger.info("InputManager: Zatrzymywanie %d wątków wejściowych...", len(self.readers))
            for reader in self.readers:
                try:
                    reader.stop()
                except Exception as exc:
                    logger.error("InputManager: Błąd przy zatrzymywaniu wątku: %s", exc)
            self.readers.clear()

    def reload(self) -> None:
        """Przeładowuje wątki po zmianie aktywnego profilu lub konfiguracji."""
        logger.info("InputManager: Przeładowanie konfiguracji...")
        self.start_all()
