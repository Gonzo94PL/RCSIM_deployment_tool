"""
src/api/server.py
Serwer FastAPI dla konwertera USB→RC.
Endpointy: /api/status, /api/devices, /api/config (GET/POST),
           /api/firmware/flash (POST — wgrywanie firmware na ESP32 przez esptool),
           /api/firmware/logs  (GET  — logi diagnostyczne z koprocesora ESP32).
BatteryMonitor inicjalizowany lokalnie wewnątrz fabryki create_app.
CoProcessorMonitor przekazywany z main.py i przechowywany w app.state.
"""
import logging
import os
import subprocess
import threading
import time
import sys
import asyncio
from contextlib import asynccontextmanager
from typing import Any

# Conditional import for evdev (Linux only)
try:
    import evdev  # type: ignore
    HAS_EVDEV = True
except ImportError:
    evdev = None  # type: ignore
    HAS_EVDEV = False

from fastapi import FastAPI, HTTPException, UploadFile, File, Form
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from src.config_manager import ConfigManager
from src.engine.state import RCState
from src.hardware.battery import BatteryMonitor
from src.hardware.coprocessor_monitor import CoProcessorMonitor
from src.hardware.bluetooth_manager import BluetoothManager
from src.input.evdev_reader import EV_ABS_MAP

logger = logging.getLogger(__name__)

# Ścieżka do statycznych plików Web UI
_WEB_DIR = "src/ui/web"


def create_app(
    config_mgr: ConfigManager,
    rc_state: RCState,
    reload_event: threading.Event,
    coprocessor_monitor: CoProcessorMonitor | None = None,
) -> FastAPI:
    """
    Fabryka aplikacji FastAPI.
    BatteryMonitor tworzony lokalnie — w pełni izolowany w wątku serwera API.
    CoProcessorMonitor przekazywany z main.py i zapisywany w app.state.
    """
    # Lokalna inicjalizacja monitora baterii
    battery_monitor = BatteryMonitor()
    bluetooth_mgr = BluetoothManager()

    # Modern FastAPI lifecycle management
    @asynccontextmanager
    async def _lifespan(app: FastAPI):
        yield
        # Shutdown cleanup
        battery_monitor.close()
        logger.info("API: serwer wyłączony, zasoby zwolnione.")

    app = FastAPI(
        title="USB to RC Converter API",
        version="1.0.0",
        description="API sterujące konwerterem USB HID → sygnał RC (CRSF/IBUS).",
        lifespan=_lifespan,
    )

    # Referencja do monitora koprocesora (może być None gdy ESP32 nie podłączony)
    app.state.coprocessor_monitor = coprocessor_monitor

    # ------------------------------------------------------------------ #
    #  Serwowanie statycznych plików Web UI                               #
    # ------------------------------------------------------------------ #
    app.mount("/_next", StaticFiles(directory=f"{_WEB_DIR}/_next"), name="next_static")
    app.mount("/static", StaticFiles(directory=_WEB_DIR), name="static")

    @app.get("/", include_in_schema=False)
    def serve_index() -> FileResponse:
        return FileResponse(f"{_WEB_DIR}/index.html")

    # ------------------------------------------------------------------ #
    #  GET /api/status — stan kanałów RC + bateria                        #
    # ------------------------------------------------------------------ #
    @app.get("/api/status")
    def get_status() -> dict[str, Any]:
        ups_i2c = config_mgr.config.get("ups_i2c", "0x42")
        battery_monitor.update_config(ups_i2c)
        
        # Symulacja telemetrycznych RSSI i LQ z lekkimi wahaniami
        import random
        rssi = max(-105, min(-30, -65 + random.randint(-2, 2)))
        lq = max(90, min(100, 100 - (1 if random.random() < 0.1 else 0)))
        rc_state.set_telemetry(rssi, lq)
        
        cruise_active, cruise_throttle = rc_state.get_cruise()
        
        return {
            "channels": rc_state.get_channels(),
            "selected_profile": config_mgr.config.get("selected_profile"),
            "battery": battery_monitor.get_status(),
            "paused": rc_state.is_paused(),
            "gear": rc_state.gearbox.current_gear,
            "drive_mode": rc_state.get_drive_mode(),
            "cruise_active": cruise_active,
            "cruise_throttle_us": cruise_throttle,
            "rssi": rssi,
            "link_quality": lq,
        }

    # ------------------------------------------------------------------ #
    #  POST /api/status/arm — uzbrój/rozbrój nadawanie sygnału RC        #
    # ------------------------------------------------------------------ #
    @app.post("/api/status/arm")
    def post_arm(arm: bool) -> dict[str, Any]:
        # Uzbrojenie sygnału oznacza wznowienie nadawania (paused=False)
        rc_state.set_paused(not arm)
        logger.info("Sygnał RC %s przez interfejs API.", "UZBROJONY (ARMED)" if arm else "ROZBROJONY (DISARMED)")
        return {
            "status": "ok",
            "paused": rc_state.is_paused(),
        }

    # ------------------------------------------------------------------ #
    #  POST /api/status/gear — ustaw aktualny wirtualny bieg             #
    # ------------------------------------------------------------------ #
    @app.post("/api/status/gear")
    def post_gear(gear: int) -> dict[str, Any]:
        rc_state.gearbox.current_gear = gear
        logger.info("Bieg ustawiony ręcznie przez API na: %d", gear)
        return {
            "status": "ok",
            "gear": rc_state.gearbox.current_gear,
        }

    # ------------------------------------------------------------------ #
    #  POST /api/status/drive_mode — zmień wirtualny tryb jazdy          #
    # ------------------------------------------------------------------ #
    @app.post("/api/status/drive_mode")
    def post_drive_mode(mode: str) -> dict[str, Any]:
        rc_state.set_drive_mode(mode)
        logger.info("Tryb jazdy ustawiony ręcznie przez API na: %s", mode)
        return {
            "status": "ok",
            "drive_mode": rc_state.get_drive_mode(),
        }

    # ------------------------------------------------------------------ #
    #  POST /api/status/cruise — włącz/wyłącz wirtualny tempomat         #
    # ------------------------------------------------------------------ #
    @app.post("/api/status/cruise")
    def post_cruise(active: bool, throttle_us: int = 1650) -> dict[str, Any]:
        rc_state.set_cruise(active, throttle_us)
        logger.info("Tempomat ustawiony przez API: aktywny=%s, gaz=%d us", active, throttle_us)
        cruise_active, cruise_throttle = rc_state.get_cruise()
        return {
            "status": "ok",
            "cruise_active": cruise_active,
            "cruise_throttle_us": cruise_throttle,
        }

    # ------------------------------------------------------------------ #
    #  GET /api/devices — lista podłączonych urządzeń USB HID             #
    # ------------------------------------------------------------------ #
    @app.get("/api/devices")
    def get_devices() -> list[dict[str, str]]:
        result: list[dict[str, str]] = []
        if not HAS_EVDEV:
            logger.warning("get_devices: evdev niedostępny, zwracam pustą listę.")
            return result
        try:
            for path in evdev.list_devices():
                try:
                    dev = evdev.InputDevice(path)
                    result.append({
                        "name": dev.name,
                        "path": dev.path,
                        "phys": dev.phys or "",
                    })
                    dev.close()
                except Exception:
                    pass
        except Exception as exc:
            logger.error("get_devices: błąd skanowania: %s", exc)
        return result

    # ------------------------------------------------------------------ #
    #  GET /api/devices/state — odczytaj stan osi i przycisków urządzenia#
    # ------------------------------------------------------------------ #
    @app.get("/api/devices/state")
    def get_device_state(path: str) -> dict[str, Any]:
        if not HAS_EVDEV:
            import math
            t = time.time()
            return {
                "axes": [
                    {"code": i, "name": f"ABS_{i}", "value": int(math.sin(t + i) * 500), "min": -1000, "max": 1000} 
                    for i in range(6)
                ],
                "buttons": [i for i in range(16) if (int(t * 2.5) % 16) == i]
            }
        try:
            dev = evdev.InputDevice(path)
            axes = []
            try:
                for code, info in dev.capabilities().get(evdev.ecodes.EV_ABS, []):
                    try:
                        abs_val = dev.absinfo(code).value
                        axes.append({
                            "code": code,
                            "name": evdev.ecodes.ABS.get(code, f"ABS_{code}"),
                            "value": abs_val,
                            "min": info.min,
                            "max": info.max
                        })
                    except Exception:
                        pass
            except Exception:
                pass

            buttons = []
            try:
                buttons = dev.active_keys()
            except Exception:
                pass

            dev.close()
            return {"axes": axes, "buttons": buttons}
        except (FileNotFoundError, OSError) as exc:
            # Nie spamujmy logów błędami o odłączeniu urządzenia
            logger.debug("get_device_state: urządzenie odłączone lub brak pliku: %s", exc)
            raise HTTPException(status_code=404, detail=f"Urządzenie odłączone: {exc}")
        except Exception as exc:
            logger.error("get_device_state: błąd: %s", exc)
            raise HTTPException(status_code=500, detail=str(exc))

    # ------------------------------------------------------------------ #
    #  GET /api/config — pobierz aktywną konfigurację                     #
    # ------------------------------------------------------------------ #
    @app.get("/api/config")
    def get_config() -> dict[str, Any]:
        return config_mgr.config

    # ------------------------------------------------------------------ #
    #  POST /api/config — zapisz i zainicjuj ponowne ładowanie wątków     #
    # ------------------------------------------------------------------ #
    @app.post("/api/config")
    def post_config(payload: dict[str, Any]) -> dict[str, str]:
        try:
            config_mgr.save_config(payload)
            reload_event.set()  # Sygnał do main.py: przeładuj wątki wejściowe
            logger.info("Konfiguracja zapisana, wątki wejściowe zostaną przeładowane.")
            return {"status": "ok", "message": "Konfiguracja zapisana i przeładowana."}
        except Exception as exc:
            logger.error("post_config: błąd zapisu: %s", exc)
            raise HTTPException(status_code=500, detail=str(exc)) from exc

    def toggle_gpio_flash_mode(enable: bool):
        try:
            # GPIO 24 na RPi 5 odpowiada fizycznemu pinowi sterującemu GPIO 0 koprocesora
            if enable:
                # Ustaw GPIO 24 jako wyjście o stanie niskim (LOW)
                subprocess.run(["pinctrl", "set", "24", "op", "dl"], check=True)
                logger.info("Auto-Reset: RPi GPIO 24 (ESP32 GPIO 0) ustawiony w stan LOW.")
            else:
                # Ustaw GPIO 24 z powrotem jako wejście (wysoka impedancja)
                subprocess.run(["pinctrl", "set", "24", "ip"], check=True)
                logger.info("Auto-Reset: RPi GPIO 24 (ESP32 GPIO 0) zwolniony (INPUT).")
        except Exception as e:
            logger.warning("Auto-Reset: Błąd pinctrl dla GPIO 24: %s", e)

    # ------------------------------------------------------------------ #
    #  POST /api/firmware/prepare — przygotowanie do flashowania         #
    # ------------------------------------------------------------------ #
    @app.post("/api/firmware/prepare")
    def prepare_flash() -> dict[str, str]:
        """Wstrzymuje nadawanie RC i ściąga GPIO 24 (ESP32 GPIO 0) do LOW."""
        logger.info("prepare_flash: Przygotowanie do flashowania. Wstrzymuję RC i aktywuję GPIO 0 LOW.")
        rc_state.set_paused(True)
        time.sleep(0.5)
        toggle_gpio_flash_mode(True)
        return {"status": "success", "message": "GPIO 0 ściągnięty do LOW. Wciśnij krótko przycisk RESET na ESP32."}

    # ------------------------------------------------------------------ #
    #  POST /api/firmware/resume — wznowienie po anulowaniu              #
    # ------------------------------------------------------------------ #
    @app.post("/api/firmware/resume")
    def resume_transmission() -> dict[str, str]:
        """Zwalnia GPIO 24 (ESP32 GPIO 0) i wznawia nadawanie RC."""
        logger.info("resume_transmission: Anulowanie flashowania. Wznawiam RC i zwalniam GPIO 0.")
        toggle_gpio_flash_mode(False)
        rc_state.set_paused(False)
        return {"status": "success", "message": "Transmisja RC została wznowiona."}

    # ------------------------------------------------------------------ #
    #  POST /api/firmware/flash — wgrywanie firmware (ESP32/STM32)       #
    # ------------------------------------------------------------------ #
    @app.post("/api/firmware/flash")
    async def flash_firmware(
        port: str = "/dev/ttyUSB0",
        filename: str = "firmware.bin",
        target: str = "esp32",
        file: UploadFile = None
    ) -> dict[str, str]:
        """
        Wgrywa oprogramowanie (firmware) do wybranego mikrokontrolera (ESP32 przez esptool lub STM32 przez OpenOCD).
        Obsługuje przesyłanie pliku z dysku komputera klienta.
        """
        async def run_async_cmd(cmd_list: list[str], timeout_s: float) -> tuple[int, str, str]:
            proc = await asyncio.create_subprocess_exec(
                *cmd_list,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            stdout_bytes, stderr_bytes = await asyncio.wait_for(proc.communicate(), timeout=timeout_s)
            return (
                proc.returncode if proc.returncode is not None else -1,
                stdout_bytes.decode('utf-8', errors='ignore'),
                stderr_bytes.decode('utf-8', errors='ignore')
            )

        project_root = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
        firmware_dir = os.path.join(project_root, "firmware")
        os.makedirs(firmware_dir, exist_ok=True)

        # 1. Zapis przesłanego pliku (jeśli został dodany i jest odpowiedniego typu)
        use_uploaded = False
        if file is not None and file.filename:
            # Sprawdzenie zgodności rozszerzenia z celem
            ext_ok = True
            if target == "xiao_rp2350" and not file.filename.endswith(".uf2"):
                ext_ok = False
            elif target == "stm32" and not (file.filename.endswith(".bin") or file.filename.endswith(".hex")):
                ext_ok = False
            elif target == "esp32" and not file.filename.endswith(".bin"):
                ext_ok = False
                
            if ext_ok:
                use_uploaded = True
                uploaded_filename = f"uploaded_{file.filename}"
                bin_path = os.path.join(firmware_dir, uploaded_filename)
                logger.info("flash_firmware: Zapisywanie przesłanego pliku: %s", bin_path)
                try:
                    content = await file.read()
                    with open(bin_path, "wb") as f:
                        f.write(content)
                except Exception as e:
                    logger.error("flash_firmware: Błąd zapisu przesłanego pliku: %s", e)
                    raise HTTPException(status_code=500, detail=f"Błąd zapisu pliku: {e}")
            else:
                logger.warning("flash_firmware: Przesłany plik %s ma niepoprawne rozszerzenie dla celu %s. Ignoruję upload.", file.filename, target)

        if not use_uploaded:
            # Użyj pliku lokalnego z serwera
            if target == "xiao_rp2350":
                # Dla XIAO RP2350 zawsze szukamy skompilowanego firmware.uf2
                bin_path = os.path.join(firmware_dir, "firmware.uf2")
                if not os.path.exists(bin_path):
                    bin_path = os.path.join(firmware_dir, "xiao_rp2350", ".pio", "build", "seeed_xiao_rp2350", "firmware.uf2")
                if not os.path.exists(bin_path):
                    # Jeśli nie znaleziono skompilowanego uf2, spróbuj użyć wybranego pliku z UI (tylko jeśli kończy się na .uf2)
                    if filename.endswith(".uf2"):
                        bin_path = os.path.join(firmware_dir, filename)
            else:
                bin_path = os.path.join(firmware_dir, filename)

            if not os.path.exists(bin_path):
                # Ostateczny fallback
                fallback_name = "firmware.uf2" if target == "xiao_rp2350" else "firmware.bin"
                bin_path = os.path.join(firmware_dir, fallback_name)
                
            if not os.path.exists(bin_path):
                logger.error("flash_firmware: brak pliku firmware %s", bin_path)
                raise HTTPException(
                    status_code=404,
                    detail=f"Brak pliku firmware w katalogu firmware/ ({bin_path}). Upewnij się, że kod został skompilowany.",
                )

        # Wstrzymanie nadawania RC
        rc_state.set_paused(True)
        time.sleep(0.5)

        try:
            if target == "xiao_rp2350":
                # XIAO RP2350: wgrywanie pliku .uf2 przez picotool
                # picotool musi być zainstalowane na RPi5 (sudo apt install picotool)
                # XIAO musi być w trybie BOOTSEL (przytrzymaj BOOT + naciśnij RESET)
                import shutil as _sh
                picotool_bin = _sh.which("picotool")
                if not picotool_bin:
                    raise HTTPException(
                        status_code=500,
                        detail="picotool nie jest zainstalowane. Uruchom: sudo apt install picotool"
                    )

                # Wyzwolenie restartu do trybu BOOTSEL przez otwarcie portu szeregowego na 1200 bps (standard Arduino)
                import serial
                import glob
                ports_to_reset = []
                # Dla XIAO RP2350 sprawdzamy port z konfiguracji oraz automatycznie wykryte ttyACM*
                if port and os.path.exists(port):
                    ports_to_reset.append(port)
                for p in glob.glob("/dev/ttyACM*"):
                    if p not in ports_to_reset:
                        ports_to_reset.append(p)

                for p in ports_to_reset:
                    try:
                        logger.info("flash_firmware (XIAO RP2350): Soft-Reset -> Otwieranie %s na 1200 bps...", p)
                        ser = serial.Serial(p, 1200, timeout=1.0)
                        ser.close()
                        logger.info("flash_firmware (XIAO RP2350): Wysłano sygnał wejścia w tryb BOOTSEL do portu %s.", p)
                    except Exception as e:
                        logger.debug("flash_firmware (XIAO RP2350): Pętla soft-resetu pominęła port %s: %s", p, e)

                # Poczekaj chwilę na restart mikrokontrolera i wykrycie go jako urządzenie masowe USB
                time.sleep(2.5)

                # Budowanie polecenia picotool (dodajemy sudo jeśli nie jesteśmy rootem dla pełnych uprawnień USB)
                cmd = []
                if hasattr(os, "getuid") and os.getuid() != 0:
                    cmd.append("sudo")
                cmd.extend([
                    picotool_bin,
                    "load", bin_path,
                    "-f",  # Force (nadpisz istniejący firmware)
                    "-x",  # Execute po wgraniu (auto-reboot)
                ])
                logger.info("flash_firmware (XIAO RP2350): Uruchamianie picotool: %s", " ".join(cmd))

                returncode, stdout, stderr = await run_async_cmd(cmd, 30.0)

                if returncode == 0:
                    logger.info("flash_firmware (XIAO RP2350): Programowanie zakończone sukcesem.")
                    return {"status": "success", "log": stdout + "\n" + stderr}
                else:
                    logger.error("flash_firmware (XIAO RP2350): Błąd picotool.\n%s", stderr)
                    return {
                        "status": "error",
                        "message": "Błąd picotool. Upewnij się, że XIAO RP2350 jest w trybie BOOTSEL (przytrzymaj BOOT + naciśnij RESET).",
                        "log": stderr or stdout,
                    }
            elif target == "stm32":
                # Konfiguracja OpenOCD dla STM32 Blue Pill
                cfg_path = os.path.join(firmware_dir, "bluepill", "openocd.cfg")
                if not os.path.exists(cfg_path):
                    # Fallback do pliku w root/firmware/openocd.cfg
                    cfg_path = os.path.join(firmware_dir, "openocd.cfg")

                cmd = [
                    "openocd",
                    "-f", cfg_path,
                    "-c", f"program {bin_path} verify reset exit"
                ]
                logger.info("flash_firmware: Uruchamianie OpenOCD dla STM32: %s", " ".join(cmd))
                
                returncode, stdout, stderr = await run_async_cmd(cmd, 60.0)
                
                # Zwrócenie wyniku
                if returncode == 0:
                    logger.info("flash_firmware (STM32): Programowanie zakończone sukcesem.")
                    return {"status": "success", "log": stdout + "\n" + stderr}
                else:
                    logger.error("flash_firmware (STM32): Błąd OpenOCD.\n%s", stderr)
                    return {
                        "status": "error",
                        "message": "Błąd OpenOCD podczas wgrywania kodu do STM32. Sprawdź połączenia SWD.",
                        "log": stderr or stdout,
                    }
            else:
                # Domyślnie ESP32 (esptool)
                # Aktywacja GPIO 0 -> LOW
                toggle_gpio_flash_mode(True)
                time.sleep(0.1)

                cmd = [
                    sys.executable, "-m", "esptool",
                    "--port", port,
                    "--baud", "921600",
                    "write_flash", "-z", "0x10000", bin_path,
                ]
                logger.info("flash_firmware (ESP32): Uruchamianie esptool na porcie %s", port)
                
                returncode, stdout, stderr = await run_async_cmd(cmd, 60.0)
                
                toggle_gpio_flash_mode(False)

                if returncode == 0:
                    logger.info("flash_firmware (ESP32): Wgrywanie zakończone sukcesem.")
                    return {"status": "success", "log": stdout}
                else:
                    logger.error("flash_firmware (ESP32): esptool zwrócił błąd.\n%s", stderr)
                    return {
                        "status": "error",
                        "message": "Błąd esptool podczas wgrywania kodu do ESP32. Upewnij się, że ESP32 jest podłączone.",
                        "log": stderr or stdout,
                    }

        except asyncio.TimeoutError:
            logger.error("flash_firmware: Przekroczono limit czasu wgrywania.")
            raise HTTPException(status_code=504, detail="Limit czasu wgrywania przekroczony.")
        except FileNotFoundError as e:
            logger.error("flash_firmware: Brak narzędzia (OpenOCD lub esptool): %s", e)
            raise HTTPException(
                status_code=500,
                detail=f"Brak zainstalowanego narzędzia w systemie: {e}. Upewnij się, że openocd/esptool są dostępne."
            )
        except Exception as exc:
            logger.error("flash_firmware: Nieoczekiwany błąd: %s", exc)
            raise HTTPException(status_code=500, detail=str(exc))
        finally:
            # Wznawiamy nadawanie RC
            rc_state.set_paused(False)


    # ------------------------------------------------------------------ #
    #  POST /api/firmware/compile — kompilacja kodu STM32                #
    # ------------------------------------------------------------------ #
    @app.post("/api/firmware/compile")
    def compile_firmware(target: str = "stm32") -> dict[str, str]:
        """
        Kompiluje kod mikrokontrolera bezpośrednio na Raspberry Pi 5 przy użyciu PlatformIO.
        Obsługiwane cele: 'stm32' (Blue Pill), 'xiao_rp2350' (Seeed Studio XIAO RP2350).
        Jeśli PlatformIO nie jest zainstalowane, automatycznie próbuje je zainstalować.
        """
        project_root = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
        if target == "xiao_rp2350":
            cwd = os.path.join(project_root, "firmware", "xiao_rp2350")
        else:
            cwd = os.path.join(project_root, "firmware", "bluepill")
        
        # 1. Lista potencjalnych ścieżek do pliku wykonywalnego 'pio'
        # Uwzględniamy bezpośrednio ścieżki dla użytkownika 'pi' na wypadek, gdyby usługa działała jako root.
        pio_bin = None
        possible_paths = [
            "/home/pi/.local/bin/pio",
            "/home/pi/.platformio-env/bin/pio",
            os.path.expanduser("~/.local/bin/pio"),
            os.path.expanduser("~/.platformio-env/bin/pio"),
            "/opt/usb_rc_converter/venv/bin/pio",
        ]
        
        # Sprawdzenie w systemowym PATH
        import shutil
        system_pio = shutil.which("pio")
        if system_pio:
            pio_bin = system_pio
        else:
            for path in possible_paths:
                if os.path.exists(path):
                    pio_bin = path
                    break

        # 2. Jeśli pio nie jest zainstalowane, spróbuj zainstalować je automatycznie
        install_log = ""
        if not pio_bin:
            logger.info("compile_firmware: PlatformIO nie zostało znalezione. Rozpoczynanie automatycznej instalacji...")
            install_cmd = [sys.executable, "-m", "pip", "install", "-U", "platformio"]
            
            # W systemach Debian/Ubuntu (PEP 668) może być wymagana flaga break-system-packages przy instalacji globalnej
            # (poza wirtualnym środowiskiem venv)
            is_venv = sys.prefix != sys.base_prefix
            if not is_venv:
                install_cmd.append("--break-system-packages")
                
            try:
                install_result = subprocess.run(
                    install_cmd,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                    timeout=90
                )
                install_log = f"--- INSTALACJA PLATFORMIO ---\nStdout: {install_result.stdout}\nStderr: {install_result.stderr}\n\n"
                
                # Po instalacji spróbuj ponownie odnaleźć pio
                system_pio = shutil.which("pio")
                if system_pio:
                    pio_bin = system_pio
                else:
                    for path in possible_paths:
                        if os.path.exists(path):
                            pio_bin = path
                            break
                            
                # Sprawdzenie w folderze venv (jeśli jesteśmy w venv)
                if not pio_bin and is_venv:
                    venv_pio = os.path.join(sys.prefix, "bin", "pio")
                    if os.path.exists(venv_pio):
                        pio_bin = venv_pio
                        
            except Exception as e:
                logger.error("compile_firmware: Błąd podczas automatycznej instalacji PlatformIO: %s", e)
                raise HTTPException(
                    status_code=500,
                    detail=f"Błąd automatycznej instalacji PlatformIO: {e}"
                )

        if not pio_bin:
            logger.error("compile_firmware: Nie udało się zainstalować ani zlokalizować PlatformIO.")
            return {
                "status": "error",
                "message": "PlatformIO nie jest zainstalowane i automatyczna instalacja się nie powiodła.",
                "log": install_log + "Uruchom w terminalu RPi: pip install -U platformio --break-system-packages"
            }

        # 3. Uruchomienie właściwej kompilacji (pio run)
        cmd = [pio_bin, "run"]
        logger.info("compile_firmware: Uruchamianie kompilacji w %s za pomocą %s", cwd, pio_bin)
        
        try:
            # Ponieważ pierwsze uruchomienie ściąga toolchain, dajemy większy limit czasu (450 s)
            result = subprocess.run(
                cmd,
                cwd=cwd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                timeout=450,
            )
            
            combined_log = install_log + result.stdout
            if result.returncode == 0:
                logger.info("compile_firmware: Kompilacja zakończona sukcesem.")
                
                # Kopiowanie wygenerowanych plików do katalogu głównego firmware/
                try:
                    if target == "xiao_rp2350":
                        src_uf2 = os.path.join(cwd, ".pio", "build", "seeed_xiao_rp2350", "firmware.uf2")
                        dest_uf2 = os.path.join(firmware_dir, "firmware.uf2")
                        if os.path.exists(src_uf2):
                            import shutil
                            shutil.copy2(src_uf2, dest_uf2)
                            logger.info("compile_firmware: Skopiowano %s -> %s", src_uf2, dest_uf2)
                    elif target == "stm32":
                        src_bin = os.path.join(cwd, ".pio", "build", "bluepill_f103c8", "firmware.bin")
                        dest_bin = os.path.join(firmware_dir, "firmware.bin")
                        if os.path.exists(src_bin):
                            import shutil
                            shutil.copy2(src_bin, dest_bin)
                            logger.info("compile_firmware: Skopiowano %s -> %s", src_bin, dest_bin)
                except Exception as cp_err:
                    logger.warning("compile_firmware: Błąd podczas kopiowania plików binarnych: %s", cp_err)

                return {"status": "success", "log": combined_log}
            else:
                logger.error("compile_firmware: Błąd kompilacji (PlatformIO).\n%s", result.stderr)
                return {
                    "status": "error",
                    "message": "Błąd kompilacji kodu za pomocą PlatformIO.",
                    "log": combined_log + "\n" + result.stderr,
                }
        except subprocess.TimeoutExpired:
            logger.error("compile_firmware: Przekroczono limit czasu kompilacji (450 s).")
            raise HTTPException(status_code=504, detail="Przekroczono limit czasu kompilacji (450 s).")
        except Exception as exc:
            logger.error("compile_firmware: Nieoczekiwany błąd: %s", exc)
            raise HTTPException(status_code=500, detail=str(exc))

    # ------------------------------------------------------------------ #
    #  GET /api/wizard/detect — automatyczna detekcja ruchu kontrolera   #
    # ------------------------------------------------------------------ #
    @app.get("/api/wizard/detect")
    def detect_axis(timeout: float = 3.0) -> dict[str, Any]:
        """
        Nasłuchuje ruch na urządzeniach wejściowych przez `timeout` sekund.
        Zwraca pierwsze urządzenie i oś/przycisk, na którym wykryto zmianę.
        """
        if not HAS_EVDEV:
            raise HTTPException(
                status_code=400,
                detail="Biblioteka evdev jest niedostępna na tym systemie operacyjnym."
            )

        import select

        # 1. Otwieramy wszystkie dostępne urządzenia
        devices = []
        permission_denied = False
        
        try:
            device_paths = evdev.list_devices()
        except Exception as exc:
            logger.error("Błąd listowania urządzeń evdev: %s", exc)
            return {"detected": False, "message": f"Błąd systemowy evdev: {exc}"}

        for path in device_paths:
            try:
                dev = evdev.InputDevice(path)
                devices.append(dev)
            except PermissionError:
                permission_denied = True
                logger.warning("Brak uprawnień do otwarcia urządzenia evdev: %s (Uruchom MCS jako root / dodaj do grupy input)", path)
            except Exception as exc:
                logger.debug("Pominięto urządzenie %s: %s", path, exc)

        if permission_denied and not devices:
            raise HTTPException(
                status_code=403,
                detail="Brak uprawnień do odczytu urządzeń wejściowych (/dev/input/event*). Uruchom usługę MCS jako root lub dodaj użytkownika do grupy 'input'."
            )

        if not devices:
            return {"detected": False, "message": "Brak wykrytych lub dostępnych urządzeń USB HID."}

        # Słownik do śledzenia początkowych wartości osi (w celu wykrycia zmiany delta)
        initial_states = {}
        for dev in devices:
            initial_states[dev.path] = {}
            try:
                for code, info in dev.capabilities().get(evdev.ecodes.EV_ABS, []):
                    # Zapisujemy obecny stan osi (bezpieczny odczyt z try-except)
                    try:
                        initial_states[dev.path][code] = dev.absinfo(code).value
                    except Exception:
                        pass
            except Exception:
                pass

        logger.info("Rozpoczynanie detekcji osi (timeout: %s s)...", timeout)
        start_time = time.time()
        detected_event = None

        # Używamy select do monitorowania deskryptorów plików bez blokowania wątku na stałe
        try:
            while time.time() - start_time < timeout:
                r, _, _ = select.select(devices, [], [], 0.1)
                for dev in r:
                    for event in dev.read():
                        # Detekcja ruchu osi analogowej
                        if event.type == evdev.ecodes.EV_ABS:
                            code = event.code
                            val = event.value
                            init_val = initial_states.get(dev.path, {}).get(code)
                            
                            if init_val is not None:
                                # Sprawdzamy czy zmiana pozycji jest znacząca (próg delta 10% zakresu)
                                try:
                                    info = dev.absinfo(code)
                                    span = info.max - info.min
                                    delta = abs(val - init_val)
                                    # Obniżony próg czułości detekcji (3% zakresu zamiast 15%)
                                    if span > 0 and (delta / span) > 0.03:
                                        axis_name = EV_ABS_MAP.get(code, f"ABS_{code}")
                                        detected_event = {
                                            "detected": True,
                                            "device_name": dev.name,
                                            "axis": axis_name,
                                            "type": "axis",
                                            "value": val
                                        }
                                        break
                                except Exception:
                                    pass
                        # Detekcja naciśnięcia przycisku
                        elif event.type == evdev.ecodes.EV_KEY and event.value == 1:
                            detected_event = {
                                "detected": True,
                                "device_name": dev.name,
                                "axis": f"BTN_{event.code}",
                                "type": "button",
                                "value": event.value
                            }
                            break
                    if detected_event:
                        break
                if detected_event:
                    break
        except Exception as exc:
            logger.error("Błąd podczas detekcji kreatora: %s", exc)
        finally:
            for dev in devices:
                try:
                    dev.close()
                except Exception:
                    pass

        if detected_event:
            return detected_event
        return {"detected": False, "message": "Nie wykryto żadnego ruchu."}

    # ------------------------------------------------------------------ #
    #  GET /api/firmware/logs — logi diagnostyczne z koprocesora ESP32   #
    # ------------------------------------------------------------------ #
    @app.get("/api/firmware/logs")
    def get_coprocessor_logs() -> dict[str, list[str]]:
        """Zwraca ostatnie logi diagnostyczne odebrane z koprocesora ESP32."""
        monitor: CoProcessorMonitor | None = app.state.coprocessor_monitor
        if monitor is not None:
            return {"logs": monitor.get_logs()}
        return {"logs": ["Brak aktywnego wątku monitorowania koprocesora."]}

    # ------------------------------------------------------------------ #
    #  API Bluetooth                                                     #
    # ------------------------------------------------------------------ #
    @app.get("/api/bluetooth/devices")
    def get_bluetooth_devices() -> list[dict[str, Any]]:
        return bluetooth_mgr.get_devices()

    @app.post("/api/bluetooth/scan")
    def start_bluetooth_scan() -> dict[str, Any]:
        success = bluetooth_mgr.start_scan()
        return {
            "status": "success" if success else "error",
            "scanning": bluetooth_mgr.is_scanning
        }

    @app.get("/api/bluetooth/status")
    def get_bluetooth_status() -> dict[str, Any]:
        return {
            "scanning": bluetooth_mgr.is_scanning
        }

    @app.post("/api/bluetooth/pair")
    def pair_bluetooth_device(mac: str) -> dict[str, Any]:
        success = bluetooth_mgr.pair_device(mac)
        return {"status": "success" if success else "error"}

    @app.post("/api/bluetooth/connect")
    def connect_bluetooth_device(mac: str) -> dict[str, Any]:
        success = bluetooth_mgr.connect_device(mac)
        return {"status": "success" if success else "error"}

    @app.post("/api/bluetooth/disconnect")
    def disconnect_bluetooth_device(mac: str) -> dict[str, Any]:
        success = bluetooth_mgr.disconnect_device(mac)
        return {"status": "success" if success else "error"}

    @app.post("/api/bluetooth/remove")
    def remove_bluetooth_device(mac: str) -> dict[str, Any]:
        success = bluetooth_mgr.remove_device(mac)
        return {"status": "success" if success else "error"}

    return app
