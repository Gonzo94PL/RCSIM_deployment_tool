"""
src/ui/local_display.py
Sterownik lokalnego fizycznego ekranu OLED (np. SSD1306 I2C 128x64).
Służy do szybkiego podglądu parametrów modelu bez konieczności uruchamiania laptopa:
Wyświetla wybrany profil, napięcie LiPo i aktywność sygnału.
"""
import logging
import threading
import time

from src.config_manager import ConfigManager
from src.engine.state import RCState
from src.hardware.battery import BatteryMonitor

logger = logging.getLogger(__name__)

class LocalOledDisplay(threading.Thread):
    def __init__(self, config_mgr: ConfigManager, rc_state: RCState, battery_monitor: BatteryMonitor) -> None:
        super().__init__(daemon=True, name="LocalOledDisplay")
        self.config_mgr = config_mgr
        self.rc_state = rc_state
        self.battery_monitor = battery_monitor
        self.running = False
        self._device = None
        self._try_init()

    def _try_init(self) -> None:
        """Próbuje zainicjalizować ekran SSD1306 przez magistralę I2C."""
        try:
            # Próba wczytania powszechnej biblioteki luma.oled / luma.core
            from luma.core.interface.serial import i2c # type: ignore
            from luma.oled.device import ssd1306 # type: ignore
            
            serial = i2c(port=1, address=0x3C)
            self._device = ssd1306(serial)
            logger.info("LocalOledDisplay: Wykryto i zainicjalizowano ekran SSD1306 I2C!")
        except Exception as exc:
            logger.debug("LocalOledDisplay: Fizyczny ekran OLED niepodłączony / brak bibliotek: %s (Tryb pasywny)", exc)

    def run(self) -> None:
        # Jeśli nie ma fizycznego urządzenia, wątek nie musi cyklicznie odświeżać grafiki
        if not self._device:
            logger.info("LocalOledDisplay: Brak sprzętu OLED. Wątek przechodzi w tryb uśpienia.")
            return

        self.running = True
        logger.info("LocalOledDisplay: Uruchomiono cykl rysowania danych na ekranie.")
        
        from luma.core.render import canvas # type: ignore
        
        while self.running:
            try:
                profile = self.config_mgr.get_current_profile()
                profile_name = profile.get("name", "N/A")
                
                bat_status = self.battery_monitor.get_status()
                v_str = f"LiPo: {bat_status['voltage']:.2f}V"
                p_str = f"({bat_status['percentage']}%)"
                
                proto_str = f"Proto: {self.config_mgr.config.get('output_protocol', 'CRSF').upper()}"
                
                # Odczyt stanów kluczowych osi do szybkich wskaźników
                ch1 = self.rc_state.get_channel(1)
                ch2 = self.rc_state.get_channel(2)
                ch3 = self.rc_state.get_channel(3)
                ch4 = self.rc_state.get_channel(4)
                
                with canvas(self._device) as draw:
                    # 1. Nagłówek systemowy
                    draw.text((0, 0), "=== RPi USB->RC ===", fill="white")
                    
                    # 2. Nazwa profilu lotu
                    draw.text((0, 16), f"Profile: {profile_name}", fill="white")
                    
                    # 3. Status zasilania i bateria
                    draw.text((0, 28), f"{v_str} {p_str}", fill="white")
                    
                    # 4. Aktywny protokół radiowy
                    draw.text((0, 40), proto_str, fill="white")
                    
                    # 5. Podgląd rudymentarny pierwszej czwórki drążków (Wizualizacja słupkowa pozioma)
                    visual = f"C1:{ch1} C3:{ch3}"
                    draw.text((0, 52), visual, fill="white")
                    
                time.sleep(0.5) # Odświeżanie 2 Hz jest idealne i oszczędza CPU RPi 5
                
            except Exception as e:
                logger.error("LocalOledDisplay: Błąd pętli wyświetlania: %s", e)
                time.sleep(5.0)

    def stop(self) -> None:
        self.running = False
