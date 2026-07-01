"""
src/engine/gearbox.py
Logika wirtualnej skrzyni biegów (Virtual Gearbox) dla MCS.
"""
import logging
import time
from typing import Any

logger = logging.getLogger(__name__)

class GearboxManager:
    def __init__(self) -> None:
        self.config: dict[str, Any] = {
            "mode": "none",
            "num_forward_gears": 3,
            "reverse_throttle_limit": 0.3,
            "btn_up": "",
            "btn_down": "",
        }
        self.current_gear: int = 1
        self.last_gear_change_time: float = 0.0

    def load_config(self, config_data: dict[str, Any]) -> None:
        self.config = config_data
        # Jeśli skrzynia jest wyłączona, upewnij się, że jesteśmy na 1. biegu
        if self.config.get("mode", "none") == "none":
            self.current_gear = 1
        else:
            # Upewnij się, że aktualny bieg mieści się w zdefiniowanym zakresie
            max_gears = self.config.get("num_forward_gears", 3)
            if self.current_gear > max_gears:
                self.current_gear = max_gears
            elif self.current_gear < -1:
                self.current_gear = -1
        logger.info(f"Gearbox: załadowano konfigurację. Tryb: {self.config.get('mode')}, Biegi do przodu: {self.config.get('num_forward_gears')}")

    def change_gear(self, direction: int) -> None:
        now = time.time()
        if now - self.last_gear_change_time < 0.25: # Debounce
            return
        
        max_gears = self.config.get("num_forward_gears", 3)
        new_gear = self.current_gear + direction
        self.current_gear = max(-1, min(max_gears, new_gear))
        self.last_gear_change_time = now
        logger.info(f"Gearbox: Zmiana biegu na: {self.current_gear}")

    def get_current_throttle_limit(self) -> float:
        if self.config.get("mode", "none") == "none":
            return 1.0
        
        if self.current_gear == 0:
            return 0.0
            
        if self.current_gear == -1:
            return self.config.get("reverse_throttle_limit", 0.3)
            
        num_gears = self.config.get("num_forward_gears", 3)
        if num_gears > 0:
            return min(1.0, self.current_gear / float(num_gears))
            
        return 1.0
