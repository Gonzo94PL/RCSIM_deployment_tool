"""
src/hardware/coprocessor_monitor.py
Wątek monitorujący port szeregowy (UART) ko-procesora ESP32.
Odczytuje linie diagnostyczne wysyłane przez Serial.print() na ESP32
i przechowuje je w kołowym buforze (ostatnie max_logs wpisów).
"""
import logging
import threading
import time

import serial  # type: ignore

logger = logging.getLogger(__name__)


class CoProcessorMonitor(threading.Thread):
    """
    Daemon-thread nasłuchujący portu szeregowego ko-procesora ESP32.
    Przy braku/utracie połączenia USB automatycznie ponawia próbę co 2 s.
    Bezpieczny dostęp do bufora logów przez threading.Lock.
    """

    def __init__(self, port_path: str = "/dev/ttyUSB0", baudrate: int = 115200) -> None:
        super().__init__(daemon=True, name="CoProcessorMonitor")
        self.port_path = port_path
        self.baudrate = baudrate
        self.running: bool = False
        self._logs: list[str] = []
        self.max_logs: int = 50  # Kołowy bufor — ostatnie 50 linii
        self._lock = threading.Lock()

    # ------------------------------------------------------------------ #
    #  Główna pętla wątku                                                 #
    # ------------------------------------------------------------------ #
    def run(self) -> None:
        self.running = True
        while self.running:
            try:
                with serial.Serial(self.port_path, self.baudrate, timeout=1.0) as ser:
                    logger.info(
                        "CoProcessorMonitor: połączono z konsolą ESP32 na %s (%d baud).",
                        self.port_path, self.baudrate,
                    )
                    while self.running:
                        raw = ser.readline()
                        if not raw:
                            continue
                        line = raw.decode("utf-8", errors="ignore").strip()
                        if line:
                            entry = f"[{time.strftime('%H:%M:%S')}] {line}"
                            with self._lock:
                                self._logs.append(entry)
                                if len(self._logs) > self.max_logs:
                                    self._logs.pop(0)

            except serial.SerialException as exc:
                logger.warning(
                    "CoProcessorMonitor: utracono połączenie z %s: %s — ponowna próba za 2 s.",
                    self.port_path, exc,
                )
                time.sleep(2.0)
            except Exception as exc:
                logger.error(
                    "CoProcessorMonitor: nieoczekiwany błąd: %s — ponowna próba za 2 s.", exc,
                )
                time.sleep(2.0)

        logger.info("CoProcessorMonitor: wątek zatrzymany.")

    # ------------------------------------------------------------------ #
    #  Publiczne API                                                      #
    # ------------------------------------------------------------------ #
    def get_logs(self) -> list[str]:
        """Zwraca kopię bufora logów (thread-safe)."""
        with self._lock:
            return list(self._logs)

    def stop(self) -> None:
        """Sygnalizuje wątkowi zatrzymanie przy następnej iteracji."""
        self.running = False
