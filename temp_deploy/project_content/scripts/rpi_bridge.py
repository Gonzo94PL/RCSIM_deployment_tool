#!/usr/bin/env python3
"""
rpi_bridge.py
Skrypt dla Raspberry Pi 5 obsługujący odczyt z kontrolera USB (evdev),
mapowanie na 8 kanałów RC (1000-2000 us) i wysyłanie ramek przez UART
do koprocesora STM32F103 Blue Pill.
"""

import os
import sys
import time
import serial
import logging
import threading

# Obsługa evdev (wymaga pip install evdev)
try:
    import evdev
    from evdev import ecodes
    HAS_EVDEV = True
except ImportError:
    HAS_EVDEV = False

logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')
logger = logging.getLogger("RPiBridge")

# Stan kanałów (domyślnie 1500 us)
channels = [1500] * 8
channels_lock = threading.Lock()

# Konfiguracja trybu protokołu:
# 1 = PPM, 2 = iBUS, 3 = SBUS, 4 = CRSF
PROTOCOL_MODE = 1  # Domyślnie PPM. Zmień w zależności od potrzeb.
SERIAL_PORT = "/dev/ttyACM0"  # XIAO RP2350 USB-C CDC (lub /dev/ttyAMA0 dla BluePill UART)
BAUDRATE = 115200

def find_controller(keyword="controller") -> str:
    """Wyszukuje ścieżkę do kontrolera evdev na podstawie słowa kluczowego."""
    if not HAS_EVDEV:
        logger.error("Biblioteka evdev nie jest zainstalowana!")
        return ""
    devices = [evdev.InputDevice(path) for path in evdev.list_devices()]
    for device in devices:
        logger.info(f"Wykryto urządzenie: {device.name} na {device.path}")
        if keyword.lower() in device.name.lower():
            logger.info(f"Wybrano: {device.name} -> {device.path}")
            return device.path
    if devices:
        logger.warning(f"Nie znaleziono urządzenia ze słowem '{keyword}', wybieram pierwsze dostępne: {devices[0].name}")
        return devices[0].path
    return ""

def read_evdev_loop(device_path: str):
    """Pętla odczytu zdarzeń z kontrolera evdev i mapowanie osi/przycisków."""
    global channels
    if not device_path:
        logger.error("Brak ścieżki do urządzenia do odczytu!")
        return

    try:
        device = evdev.InputDevice(device_path)
    except Exception as e:
        logger.error(f"Nie można otworzyć urządzenia {device_path}: {e}")
        return

    logger.info(f"Rozpoczęto nasłuch zdarzeń na {device.name}")
    
    # Przykładowe proste mapowanie dla kontrolera Xbox/kierownicy
    # ABS_X (0) -> Kanał 1 (Skręt)
    # ABS_Y (1) -> Kanał 2 (Wysokość/Gaz)
    # ABS_RZ (5) / ABS_GAS -> Kanał 3 (Gaz)
    # ABS_Z (2) / ABS_BRAKE -> Kanał 4 (Hamulec)
    # Przyciski mapowane na kanały 5-8 (np. 1000 lub 2000 us)
    
    for event in device.read_loop():
        if event.type == ecodes.EV_ABS:
            # Mapowanie osi analogowych
            # Zakładamy standardowy zakres evdev [0, 65535] lub [-32768, 32767]
            # Uproszczona kalibracja/normalizacja:
            val = event.value
            
            # Pobranie info o osi w celu dynamicznej normalizacji
            abs_info = device.capabilities().get(ecodes.EV_ABS, [])
            info = None
            for code, i in abs_info:
                if code == event.code:
                    info = i
                    break
            
            if info:
                val_min = info.min
                val_max = info.max
            else:
                val_min, val_max = -32768, 32767  # fallback

            # Skalowanie do zakresu [1000, 2000]
            norm_val = 1500
            span = val_max - val_min
            if span > 0:
                norm_val = int(1000 + ((val - val_min) / span) * 1000)

            with channels_lock:
                if event.code == ecodes.ABS_X:
                    channels[0] = norm_val
                elif event.code == ecodes.ABS_Y:
                    channels[1] = norm_val
                elif event.code in (ecodes.ABS_RZ, ecodes.ABS_GAS):
                    channels[2] = norm_val
                elif event.code in (ecodes.ABS_Z, ecodes.ABS_BRAKE):
                    channels[3] = norm_val

        elif event.type == ecodes.EV_KEY:
            # Mapowanie przycisków
            # event.value: 1 (wciśnięty), 0 (zwolniony)
            val = 2000 if event.value else 1000
            with channels_lock:
                if event.code == ecodes.BTN_A:
                    channels[4] = val
                elif event.code == ecodes.BTN_B:
                    channels[5] = val
                elif event.code == ecodes.BTN_X:
                    channels[6] = val
                elif event.code == ecodes.BTN_Y:
                    channels[7] = val

def serial_tx_loop():
    """Wysyła ramki z kanałami co 10 ms przez UART."""
    logger.info(f"Uruchamianie pętli nadawczej UART na {SERIAL_PORT} ({BAUDRATE} bps)")
    try:
        ser = serial.Serial(SERIAL_PORT, BAUDRATE, timeout=0.1)
    except Exception as e:
        logger.error(f"Nie udało się otworzyć portu szeregowego: {e}")
        return

    while True:
        t_start = time.perf_counter()
        
        with channels_lock:
            ch_snapshot = list(channels)
            
        # Budowanie ramki:
        # [Start (0xAA)] [Tryb (1-4)] [CH1_H] [CH1_L] ... [CH8_H] [CH8_L] [XOR Checksum]
        frame = bytearray()
        frame.append(0xAA)
        frame.append(PROTOCOL_MODE)
        
        for ch in ch_snapshot:
            # Upewnienie się, że wartości mieszczą się w zakresie
            ch_val = max(1000, min(2000, ch))
            frame.append((ch_val >> 8) & 0xFF)
            frame.append(ch_val & 0xFF)
            
        # XOR checksum nad całą dotychczasową ramką (bez bajtu startu lub z nim)
        # Standard: XOR nad bajtami od trybu do kanałów włącznie
        checksum = 0
        for b in frame[1:]:
            checksum ^= b
        frame.append(checksum)
        
        try:
            ser.write(frame)
            ser.flush()
        except Exception as e:
            logger.warning(f"Błąd podczas wysyłania ramki UART: {e}")
            
        # Dokładne odmierzanie 10 ms
        elapsed = time.perf_counter() - t_start
        sleep_time = 0.010 - elapsed
        if sleep_time > 0:
            time.sleep(sleep_time)

def main():
    logger.info("Inicjalizacja mostka USB-HID to RC...")
    
    if not HAS_EVDEV:
        logger.warning("Uruchomiono bez obsługi evdev (tryb demo z symulowanymi danymi).")
        # Wątek demo aktualizacji kanałów
        def demo_loop():
            t = 0
            while True:
                with channels_lock:
                    channels[0] = int(1500 + 500 * time.sin(t))
                    channels[1] = int(1500 + 500 * time.cos(t))
                t += 0.05
                time.sleep(0.02)
        threading.Thread(target=demo_loop, daemon=True).start()
    else:
        dev_path = find_controller()
        if dev_path:
            threading.Thread(target=read_evdev_loop, args=(dev_path,), daemon=True).start()
        else:
            logger.warning("Brak podłączonego kontrolera USB-HID. Uruchamianie trybu demo.")
            
    # Uruchomienie wątku UART
    tx_thread = threading.Thread(target=serial_tx_loop, daemon=True)
    tx_thread.start()
    
    # Oczekiwanie na zakończenie (lub Ctrl+C)
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        logger.info("Zamykanie mostka...")

if __name__ == "__main__":
    main()
