"""
src/output/base.py
Klasa bazowa dla wątków wysyłających ramki RC (CRSF, IBUS, SBUS itd.) przez port szeregowy UART.
"""
import logging
import threading
import time
from typing import Optional

from src.engine.state import RCState

logger = logging.getLogger(__name__)

class BaseOutput(threading.Thread):
    def __init__(self, rc_state: RCState, port_path: str, baudrate: int, rtscts: bool = False, interval: float = 0.020) -> None:
        super().__init__(daemon=True)
        self.rc_state = rc_state
        self.port_path = port_path
        self.baudrate = baudrate
        self.rtscts = rtscts
        self.interval = interval
        self.running = False
        self._port = None

    def serialize_channels(self, channels: list[int]) -> bytes:
        """Metoda wirtualna do nadpisania w protokołach pochodnych (np. CRSF, IBUS)."""
        raise NotImplementedError("serialize_channels musi być zaimplementowana w klasie pochodnej.")

    def run(self) -> None:
        self.running = True
        logger.info("%s: Uruchomiono wątek wyjściowy na porcie %s (%d baud)", self.__class__.__name__, self.port_path, self.baudrate)
        
        while self.running:
            if self.rc_state.is_paused():
                time.sleep(0.1)
                continue
            try:
                import serial # type: ignore
                self._port = serial.Serial(
                    self.port_path,
                    self.baudrate,
                    timeout=0.1,
                    rtscts=self.rtscts
                )
                try:
                    self._port.dtr = False
                    self._port.rts = False
                except Exception:
                    pass
                logger.info("%s: Pomyślnie otworzono port szeregowy: %s", self.__class__.__name__, self.port_path)
                
                # Cykl wysyłania ramek (np. co 10-20 ms w zależności od protokołu)
                interval = self.interval
                rx_buffer = bytearray()
                while self.running:
                    if self.rc_state.is_paused():
                        logger.info("%s: Wymagane zwolnienie portu (pauza). Zamykam port szeregowy.", self.__class__.__name__)
                        if self._port:
                            try:
                                self._port.close()
                            except Exception:
                                pass
                            self._port = None
                        break
                    t_start = time.perf_counter()
                    
                    channels = self.rc_state.get_channels()
                    frame = self.serialize_channels(channels)
                    
                    if frame and self._port:
                        self._port.write(frame)
                        self._port.flush()
                        
                    # Odczyt logów diagnostycznych z ESP32 (non-blocking)
                    if self._port and self._port.in_waiting > 0:
                        try:
                            data = self._port.read(self._port.in_waiting)
                            if data:
                                rx_buffer.extend(data)
                                while b'\n' in rx_buffer:
                                    line_bytes, rx_buffer = rx_buffer.split(b'\n', 1)
                                    line = line_bytes.decode('utf-8', errors='ignore').strip()
                                    if line:
                                        logger.info("[ESP32] %s", line)
                        except Exception as e:
                            logger.debug("Błąd odczytu UART: %s", e)
                            
                    # Precyzyjne odmierzanie czasu do kolejnej ramki
                    elapsed = time.perf_counter() - t_start
                    to_sleep = interval - elapsed
                    if to_sleep > 0:
                        time.sleep(to_sleep)
                        
            except ImportError:
                logger.error("%s: Pakiet pyserial jest niedostępny. Zainstaluj pip install pyserial.", self.__class__.__name__)
                time.sleep(5.0)
            except Exception as e:
                logger.warning("%s: Błąd portu szeregowego na %s: %s. Re-inicjalizacja za 2 s.", self.__class__.__name__, self.port_path, e)
                if self._port:
                    try:
                        self._port.close()
                    except Exception:
                        pass
                    self._port = None
                time.sleep(2.0)
                
        logger.info("%s: Zakończono wątek wyjściowy.", self.__class__.__name__)

    def stop(self) -> None:
        self.running = False
        if self._port:
            try:
                self._port.close()
            except Exception:
                pass
            self._port = None
