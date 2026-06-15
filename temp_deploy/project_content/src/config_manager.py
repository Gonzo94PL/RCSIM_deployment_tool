"""
src/config_manager.py
Klasa zarządzająca plikami konfiguracyjnymi systemu USB-to-RC.
Wczytuje config.json, a w razie jego braku powraca do default_config.json.
"""
import json
import logging
import os
from typing import Any

logger = logging.getLogger(__name__)

CONFIG_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "config")
CONFIG_PATH = os.path.join(CONFIG_DIR, "config.json")
DEFAULT_CONFIG_PATH = os.path.join(CONFIG_DIR, "default_config.json")

class ConfigManager:
    def __init__(self) -> None:
        self.config: dict[str, Any] = self.load_config()

    def load_config(self) -> dict[str, Any]:
        """Wczytuje konfigurację z config.json lub z default_config.json."""
        if os.path.exists(CONFIG_PATH):
            try:
                with open(CONFIG_PATH, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    logger.info("ConfigManager: Wczytano konfigurację użytkownika z %s", CONFIG_PATH)
                    return data
            except Exception as e:
                logger.error("ConfigManager: Błąd odczytu %s, próba wczytania domyślnego: %s", CONFIG_PATH, e)
        
        if os.path.exists(DEFAULT_CONFIG_PATH):
            try:
                with open(DEFAULT_CONFIG_PATH, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    logger.info("ConfigManager: Wczytano domyślną konfigurację z %s", DEFAULT_CONFIG_PATH)
                    return data
            except Exception as e:
                logger.critical("ConfigManager: Krytyczny błąd odczytu domyślnej konfiguracji: %s", e)
        
        logger.warning("ConfigManager: Brak plików konfiguracyjnych, tworzenie podstawy zintegrowanej.")
        return {
            "api": {"host": "0.0.0.0", "port": 8080},
            "output_protocol": "crsf",
            "output_port": "/dev/ttyAMA0",
            "selected_profile": "quad_5_cal",
            "profiles": {}
        }

    def save_config(self, new_config: dict[str, Any]) -> None:
        """Zapisuje nową konfigurację na dysk."""
        self.config = new_config
        os.makedirs(CONFIG_DIR, exist_ok=True)
        try:
            with open(CONFIG_PATH, "w", encoding="utf-8") as f:
                json.dump(new_config, f, indent=2, ensure_ascii=False)
            logger.info("ConfigManager: Konfiguracja pomyślnie zapisana do %s", CONFIG_PATH)
        except Exception as e:
            logger.error("ConfigManager: Nie udało się zapisać konfiguracji do %s: %s", CONFIG_PATH, e)
            raise e

    def get_current_profile(self) -> dict[str, Any]:
        """Pobiera parametry aktywnego profilu."""
        selected = self.config.get("selected_profile", "quad_5_cal")
        profiles = self.config.get("profiles", {})
        
        if selected in profiles:
            return profiles[selected]
        
        # fallback
        if profiles:
            first_key = list(profiles.keys())[0]
            logger.warning("ConfigManager: Profil '%s' nie istnieje. Używam pierwszego dostępnego: '%s'", selected, first_key)
            return profiles[first_key]
        
        return {
            "name": "Default_Profile",
            "battery_type": "2S",
            "inputs": []
        }
