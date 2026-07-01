"""
src/output/bridge.py
Implementacja protokołu komunikacji z mostkiem szeregowym koprocesora (STM32/ESP32).
Prędkość: 115200 bps, ramka: 19 bajtów.
"""
import logging
from src.output.base import BaseOutput
from src.engine.state import RCState

logger = logging.getLogger(__name__)

class BridgeOutput(BaseOutput):
    def __init__(self, rc_state: RCState, port_path: str = "/dev/ttyAMA0", protocol: str = "ppm") -> None:
        # Komunikacja RPi z koprocesorem odbywa się zawsze z prędkością 115200 bps
        super().__init__(rc_state, port_path, baudrate=115200)
        
        # Mapowanie nazwy protokołu na numer trybu oczekiwany przez koprocesor
        protocol_modes = {
            "ppm": 1,
            "ibus": 2,
            "sbus": 3,
            "crsf": 4
        }
        self.mode_byte = protocol_modes.get(protocol.lower(), 1)
        self.protocol_name = protocol.lower()
        logger.info("BridgeOutput: Inicjalizacja z protokołem %s (tryb %d) na porcie %s", protocol, self.mode_byte, port_path)

    def serialize_channels(self, channels: list[int]) -> bytes:
        """
        Pakuje wartości 8 kanałów do ramki mostka:
        [0xAA] [Tryb] [CH1_H] [CH1_L] ... [CH8_H] [CH8_L] [XOR Checksum]
        Łączna długość ramki = 19 bajtów.
        """
        frame = bytearray(19)
        frame[0] = 0xAA
        frame[1] = self.mode_byte
        
        # Zapis 8 kanałów (16-bit Big Endian)
        for i in range(8):
            val = channels[i] if i < len(channels) else 1500
            val = max(1000, min(2000, val)) # Twardy limit wartości kanałów RC
            
            offset = 2 + (i * 2)
            frame[offset] = (val >> 8) & 0xFF
            frame[offset + 1] = val & 0xFF
            
        # Obliczenie sumy kontrolnej XOR nad bajtami [1..17]
        xor_sum = 0
        for i in range(1, 18):
            xor_sum ^= frame[i]
        frame[18] = xor_sum
        
        return bytes(frame)
