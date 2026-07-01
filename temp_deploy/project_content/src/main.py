"""
src/main.py
Główny punkt wejścia aplikacji USB→RC Converter.
Zarządza wątkami wejścia (EvdevReader), wyjścia (CRSF/IBUS)
oraz serwerem API (FastAPI/Uvicorn) uruchamianym jako osobny wątek.
Obsługuje dynamiczne przeładowanie wątków wejściowych po zmianie konfiguracji
przez API (sygnał reload_event).
"""
import logging
import logging.handlers
import threading
import time
from typing import Optional

import uvicorn  # type: ignore

from src.api.server import create_app
from src.config_manager import ConfigManager
from src.engine.state import RCState
from src.input.input_manager import InputManager
from src.output.bridge import BridgeOutput

# ------------------------------------------------------------------ #
#  Konfiguracja logowania                                             #
# ------------------------------------------------------------------ #
def _setup_logging() -> None:
    root = logging.getLogger()
    root.setLevel(logging.INFO)

    fmt = logging.Formatter(
        "%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%dT%H:%M:%S",
    )

    # Handler konsolowy
    ch = logging.StreamHandler()
    ch.setFormatter(fmt)
    root.addHandler(ch)

    # Handler plikowy z rotacją (5 MB × 3 kopii)
    try:
        fh = logging.handlers.RotatingFileHandler(
            "/var/log/rcsim_mcs.log",
            maxBytes=5 * 1024 * 1024,
            backupCount=3,
            encoding="utf-8",
        )
        fh.setFormatter(fmt)
        root.addHandler(fh)
    except PermissionError:
        logging.warning("Brak uprawnień do /var/log/ — logowanie tylko do konsoli.")


logger = logging.getLogger(__name__)


def _notify_systemd(status: str) -> None:
    """Wysyła status do gniazda systemd NOTIFY_SOCKET (sd_notify)."""
    import os
    import socket
    notify_socket = os.environ.get("NOTIFY_SOCKET")
    if not notify_socket:
        return
    if notify_socket.startswith("@"):
        notify_socket = "\0" + notify_socket[1:]
    try:
        with socket.socket(socket.AF_UNIX, socket.SOCK_DGRAM) as sock:
            sock.connect(notify_socket)
            sock.sendall(status.encode("utf-8"))
    except Exception:
        pass


# ------------------------------------------------------------------ #
#  Pomocnicze: wyszukiwanie urządzenia evdev po nazwie               #
# ------------------------------------------------------------------ #
def _find_device_path(target_name: str) -> Optional[str]:
    try:
        import evdev  # type: ignore
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
        logger.error("Błąd skanowania urządzeń wejściowych: %s", exc)
    return None


# ------------------------------------------------------------------ #
#  Uruchamianie / zatrzymywanie wątków wejściowych                   #
# ------------------------------------------------------------------ #
def _start_input_threads(
    config_mgr: ConfigManager, rc_state: RCState
) -> list:
    from src.input.evdev_reader import EvdevReader

    readers: list = []
    profile = config_mgr.get_current_profile()
    for input_cfg in profile.get("inputs", []):
        dev_name = input_cfg.get("device_name", "")
        mappings = input_cfg.get("mappings", [])
        dev_path = _find_device_path(dev_name)
        if dev_path:
            reader = EvdevReader(dev_path, mappings, rc_state, profile)
            reader.start()
            readers.append(reader)
            logger.info("Wątek wejściowy: '%s' → %s", dev_name, dev_path)
        else:
            logger.warning("Urządzenie '%s' nie zostało wykryte.", dev_name)
    return readers


def _stop_input_threads(readers: list) -> None:
    for r in readers:
        try:
            r.stop()
        except Exception as exc:
            logger.warning("Błąd zatrzymania wątku wejściowego: %s", exc)


# ------------------------------------------------------------------ #
#  Wątek serwera API (Uvicorn)                                        #
# ------------------------------------------------------------------ #
def _run_api_server(
    config_mgr: ConfigManager,
    rc_state: RCState,
    reload_event: threading.Event,
    host: str,
    port: int,
) -> None:
    app = create_app(config_mgr, rc_state, reload_event)
    uvicorn.run(app, host=host, port=port, log_level="warning")


# ------------------------------------------------------------------ #
#  Inicjalizacja wyjścia RC                                           #
# ------------------------------------------------------------------ #
def _build_output(config: dict, rc_state: RCState):
    protocol = config.get("output_protocol", "crsf").lower()
    port = config.get("output_port", "/dev/ttyAMA0")
    if protocol == "nomad":
        from src.output.crsf import CRSFOutput
        return CRSFOutput(rc_state, port)
    elif protocol in ("crsf", "ppm", "ibus", "sbus"):
        return BridgeOutput(rc_state, port, protocol)
    logger.error("Nieznany protokół wyjściowy: '%s'. Wyjście zablokowane.", protocol)
    return None



# ------------------------------------------------------------------ #
#  Punkt wejścia                                                      #
# ------------------------------------------------------------------ #
def main() -> None:
    _setup_logging()
    logger.info("=== RCSIM MCS — Uruchamianie ===")

    config_mgr = ConfigManager()
    rc_state = RCState()
    
    # Załaduj konfigurację wirtualnej skrzyni biegów z aktywnego profilu
    active_profile = config_mgr.get_current_profile()
    rc_state.gearbox.load_config(active_profile.get("gearbox_config", {}))

    reload_event = threading.Event()

    # --- Wyjście RC ---
    output_thread = _build_output(config_mgr.config, rc_state)
    if output_thread:
        output_thread.start()

    # --- Wątki wejściowe ---
    readers = _start_input_threads(config_mgr, rc_state)

    # --- Serwer API w osobnym wątku ---
    api_host = config_mgr.config.get("api", {}).get("host", "0.0.0.0")
    api_port = int(config_mgr.config.get("api", {}).get("port", 8080))

    api_thread = threading.Thread(
        target=_run_api_server,
        args=(config_mgr, rc_state, reload_event, api_host, api_port),
        daemon=True,
        name="ApiServer",
    )
    api_thread.start()
    logger.info("Serwer API uruchomiony na http://%s:%d", api_host, api_port)

    # --- Pętla główna z obsługą przeładowania konfiguracji ---
    logger.info("System uruchomiony. Naciśnij Ctrl+C, aby zakończyć.")
    _notify_systemd("READY=1\nSTATUS=System uruchomiony i gotowy")
    try:
        while True:
            _notify_systemd("WATCHDOG=1")
            if reload_event.is_set():
                logger.info("Wykryto zmianę konfiguracji — przeładowuję wątki wejściowe i wyjściowe...")
                _stop_input_threads(readers)
                if output_thread:
                    output_thread.stop()
                config_mgr.config = config_mgr.load_config()  # odczyt z dysku
                
                # Załaduj nową konfigurację wirtualnej skrzyni biegów
                active_profile = config_mgr.get_current_profile()
                rc_state.gearbox.load_config(active_profile.get("gearbox_config", {}))

                # Budujemy nowe wyjście na podstawie aktualnej konfiguracji
                output_thread = _build_output(config_mgr.config, rc_state)
                if output_thread:
                    output_thread.start()
                readers = _start_input_threads(config_mgr, rc_state)
                reload_event.clear()
                logger.info("Wątki wejściowe i wyjściowe przeładowane pomyślnie.")
            time.sleep(0.5)

    except KeyboardInterrupt:
        logger.info("Przerwanie przez użytkownika — bezpieczne wyłączanie...")

    finally:
        _stop_input_threads(readers)
        if output_thread:
            output_thread.stop()
        logger.info("=== RCSIM MCS — Wyłączono ===")


if __name__ == "__main__":
    main()