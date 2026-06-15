"""
src/output/ibus.py
Implementacja protokołu i-BUS (FlySky) na porcie szeregowym.
Standardowa częstotliwość odświeżania: ~110 Hz lub 50 Hz, prędkość: 115200 bps.
"""
import logging
from src.output.base import BaseOutput
from src.engine.state import RCState

logger = logging.getLogger(__name__)

class IBUSOutput(BaseOutput):
    def __init__(self, rc_state: RCState, port_path: str = "/dev/ttyAMA0") -> None:
        # Standardowa prędkość FlySky i-BUS to 115200 bps
        # i-BUS pracuje zazwyczaj z interwałem ok 7ms do 10ms (używamy 0.010s = 100 Hz)
        super().__init__(rc_state, port_path, baudrate=115200, interval=0.010)

    def serialize_channels(self, channels: list[int]) -> bytes:
        """
        Pakuje wartości kanałów do ramki i-BUS (32 bajty, max 14 kanałów).
        Suma bajtów ramki:
            Byte 0: 0x20 (długość ramki = 32)
            Byte 1: 0x40 (kod polecenia kanałów)
            Byte 2..29: 14 kanałów w postaci 16-bit Little Endian, wartości w µs [1000..2000]
            Byte 30..31: 16-bitowa suma kontrolna przekazywana jako Little Endian (Wzór: 0xFFFF - Suma poprz. 30 bajtów)
        """
        frame = bytearray(32)
        frame[0] = 0x20
        frame[1] = 0x40

        # Przypisanie 14 kanałów (i-BUS obsługuje maksymalnie 14 w pojedynczej ramce)
        for i in range(14):
            val = channels[i] if i < len(channels) else 1500
            val = max(1000, min(2000, val)) # Twarde granice RC
            
            # Little Endian zapis do bajtów ramki
            offset = 2 + (i * 2)
            frame[offset] = val & 0xFF
            frame[offset + 1] = (val >> 8) & 0xFF

        # Obliczenie sumy kontrolnej
        checksum = 0xFFFF
        for i in range(30):
            checksum -= frame[i]

        frame[30] = checksum & 0xFF
        frame[31] = (checksum >> 8) & 0xFF

        return bytes(frame)
