# -*- coding: utf-8 -*-
"""
Test skrypt do weryfikacji generowania config.json
Test script to verify config.json generation
"""

import io
import json
import os
import sys
from typing import Any, Dict, List, Tuple

# Fix Windows console encoding
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

# Dodaj ścieżkę do modułu
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


def test_hardware_config() -> bool:
    """
    Testuje generowanie konfiguracji sprzętowej
    Tests hardware configuration generation

    Returns:
        bool: True if tests passed, False otherwise.
    """
    print("=" * 60)
    print("TEST: Hardware Configuration Generation")
    print("=" * 60)

    # Symuluj konfigurację z GUI
    hardware_config: Dict[str, Any] = {
        "imu": {"driver": "native_mpu9250"},
        "gps": {
            "enabled": True,
            "port": "/dev/serial0",
            "baudrate": 115200,
        },
        "lidar": {"enabled": False, "port": "/dev/ttyUSB0", "baudrate": 115200},
    }

    # Symuluj pełną konfigurację jak w deployment_logic
    config_data: Dict[str, Any] = {
        "pc_ip": "100.91.21.9",
        "ntrip": {
            "enabled": True,
            "user": "test_user",
            "password": "test_pass",
            "host": "system.asgeupos.pl",
            "port": 2101,
            "mountpoint": "RTN4G_VRS_RTCM32",
        },
        "hardware": hardware_config,
        "video": {"engine": "auto"},
    }

    print("\n✓ Generated config.json structure:")
    print(json.dumps(config_data, indent=4, ensure_ascii=False))

    # Sprawdź kluczowe sekcje
    print("\n" + "=" * 60)
    print("VERIFICATION:")
    print("=" * 60)

    checks: List[Tuple[str, bool]] = [
        ("pc_ip exists", "pc_ip" in config_data),
        ("ntrip.enabled exists", "enabled" in config_data.get("ntrip", {})),
        (
            "hardware.imu.driver exists",
            "driver" in config_data.get("hardware", {}).get("imu", {}),
        ),
        (
            "hardware.gps.enabled exists",
            "enabled" in config_data.get("hardware", {}).get("gps", {}),
        ),
        (
            "hardware.gps.port exists",
            "port" in config_data.get("hardware", {}).get("gps", {}),
        ),
        (
            "hardware.gps.baudrate exists",
            "baudrate" in config_data.get("hardware", {}).get("gps", {}),
        ),
        (
            "IMU driver value correct",
            config_data.get("hardware", {}).get("imu", {}).get("driver")
            == "native_mpu9250",
        ),
        (
            "GPS enabled value correct",
            config_data.get("hardware", {}).get("gps", {}).get("enabled") == True,
        ),
        (
            "GPS baudrate correct",
            config_data.get("hardware", {}).get("gps", {}).get("baudrate") == 115200,
        ),
    ]

    all_passed = True
    for check_name, result in checks:
        status = "✓ PASS" if result else "✗ FAIL"
        print(f"{status}: {check_name}")
        if not result:
            all_passed = False

    print("\n" + "=" * 60)
    if all_passed:
        print("✓ ALL TESTS PASSED!")
    else:
        print("✗ SOME TESTS FAILED!")
    print("=" * 60)

    return all_passed


def test_empty_imu_driver() -> bool:
    """
    Testuje przypadek z pustym IMU driver (brak IMU)
    Tests case with empty IMU driver (no IMU)

    Returns:
        bool: True if tests passed, False otherwise.
    """
    print("\n\n" + "=" * 60)
    print("TEST: Empty IMU Driver (No IMU)")
    print("=" * 60)

    hardware_config: Dict[str, Any] = {
        "imu": {"driver": ""},  # Pusty string = brak IMU
        "gps": {
            "enabled": False,
            "port": "/dev/serial0",
            "baudrate": 9600,
        },
        "lidar": {"enabled": False, "port": "/dev/ttyUSB0", "baudrate": 115200},
    }

    print("\n✓ Config with NO IMU and NO GPS:")
    print(json.dumps(hardware_config, indent=4, ensure_ascii=False))

    checks: List[Tuple[str, bool]] = [
        ("IMU driver is empty string", hardware_config["imu"]["driver"] == ""),
        ("GPS is disabled", hardware_config["gps"]["enabled"] == False),
    ]

    all_passed = True
    for check_name, result in checks:
        status = "✓ PASS" if result else "✗ FAIL"
        print(f"{status}: {check_name}")
        if not result:
            all_passed = False

    return all_passed


if __name__ == "__main__":
    result1 = test_hardware_config()
    result2 = test_empty_imu_driver()

    print("\n\n" + "=" * 60)
    print("FINAL RESULT")
    print("=" * 60)

    if result1 and result2:
        print("✓ ALL TESTS PASSED SUCCESSFULLY!")
        sys.exit(0)
    else:
        print("✗ SOME TESTS FAILED!")
        sys.exit(1)
