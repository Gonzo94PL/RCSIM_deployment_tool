"""
src/output/serial_out.py
Pomocnicze moduły wyjścia szeregowego dla specyficznych układów sprzętowych.
"""
import logging

logger = logging.getLogger(__name__)

def scan_serial_ports() -> list[str]:
    """Wyszukuje dostępne porty szeregowe w systemie Linux np. /dev/ttyUSB*, /dev/ttyAMA*."""
    import glob
    ports = glob.glob("/dev/ttyUSB*") + glob.glob("/dev/ttyACM*") + glob.glob("/dev/ttyAMA*")
    return sorted(ports)
