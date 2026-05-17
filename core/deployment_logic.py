# -*- coding: utf-8 -*-
"""
Logika Wdrożenia Aplikacji RCSIM (Deployment Logic).
RCSIM Application Deployment Logic.

Wersja v6.8 Bulletproof - Naprawiona składnia, Tailscale i czyszczenie logów.
Version v6.8 Bulletproof - Fixed syntax, Tailscale, and log cleaning.
"""

import json
import os
import re
import shutil
import subprocess
import time
from typing import Any, Callable, Dict, Optional

import paramiko


def strip_ansi_codes(text: str) -> str:
    """
    Usuwa kody ucieczki ANSI (kolory, ruchy kursora) z tekstu logów Dockera.
    Removes ANSI escape codes (colors, cursor movements) from Docker log text.

    Args:
        text (str): Tekst wejściowy z kodami ANSI. / Input text with ANSI codes.

    Returns:
        str: Tekst pozbawiony kodów ANSI. / Text stripped of ANSI codes.
    """
    ansi_escape = re.compile(r"\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])")
    return ansi_escape.sub("", text)


def generate_mediamtx_config(
    width: int = 1920, height: int = 1080, fps: int = 30, bitrate: int = 5000000
) -> str:
    """
    Generuje konfigurację YAML dla MediaMTX z określoną rozdzielczością, FPS i bitrate.
    Generates MediaMTX YAML configuration with resolution, FPS, and bitrate.
    """
    return f"""# MediaMTX Configuration for RCSIM
logLevel: info
logDestinations: [stdout]

# API
api: yes
apiAddress: 0.0.0.0:9997

# RTSP Server
rtsp: yes
rtspAddress: 0.0.0.0:8554
protocols: [tcp]

# WebRTC
webrtc: yes
webrtcAddress: 0.0.0.0:8889
webrtcICEServers: []

# Internal buffers
readBufferCount: 1024

paths:
  camera_ai:
    source: rpiCamera
    rpiCameraWidth: {width}
    rpiCameraHeight: {height}
    rpiCameraFPS: {fps}
    rpiCameraBitrate: {bitrate}
    rpiCameraVFlip: false
    rpiCameraHFlip: false
    rpiCameraExposure: normal
"""


def detect_cameras(
    log_func: Callable[[str, str], None],
    gettext_func: Callable[[str], str],
    config_data: Dict[str, Any],
    on_complete: Callable[[bool, str], None],
) -> None:
    """
    Wykrywa dostępne kamery na RPi używając 'rpicam-hello --list-cameras'.
    Detects available cameras on RPi using 'rpicam-hello --list-cameras'.

    Args:
        log_func: Funkcja logowania. / Logging function.
        gettext_func: Funkcja tłumaczenia. / Translation function.
        config_data: Słownik konfiguracji z danymi połączenia RPi.
        on_complete: Funkcja zwrotna (sukces: bool, dane: str).
    """
    _ = gettext_func
    ssh = None
    try:
        log_func(_("Connecting to RPi..."), "info")
        ssh = connect_ssh(
            log_func,
            _,
            config_data.get("rpi_host", ""),
            config_data.get("rpi_user", ""),
            config_data.get("rpi_pass"),
            config_data.get("rpi_key_path"),
            config_data.get("rpi_key_passphrase"),
        )

        if not ssh:
            on_complete(False, "SSH connection failed")
            return

        log_func(_("Running camera detection..."), "info")
        stdin, stdout, stderr = ssh.exec_command("rpicam-hello --list-cameras")
        camera_output = stdout.read().decode("utf-8")
        error_output = stderr.read().decode("utf-8")

        if camera_output:
            log_func(_("Camera detection successful!"), "success")
            on_complete(True, camera_output)
        elif error_output:
            log_func(f"Camera detection returned error: {error_output}", "warning")
            on_complete(True, error_output)
        else:
            log_func(_("No camera output received"), "warning")
            on_complete(True, "No output from camera detection command")

    except Exception as e:
        log_func(f"Camera detection error: {e}", "error")
        on_complete(False, str(e))
    finally:
        if ssh:
            ssh.close()


def scan_hardware_rpi(
    log_func: Callable[[str, str], None],
    gettext_func: Callable[[str], str],
    config_data: Dict[str, Any],
    on_complete: Callable[[bool, Dict[str, Any]], None],
) -> None:
    """
    Skanuje RPi w poszukiwaniu sprzętu I2C i UART (Ulepszone).
    """
    _ = gettext_func
    ssh = None
    try:
        log_func(_("Connecting to RPi for deep hardware scan..."), "info")
        ssh = connect_ssh(
            log_func,
            _,
            config_data.get("rpi_host", ""),
            config_data.get("rpi_user", ""),
            config_data.get("rpi_pass"),
            config_data.get("rpi_key_path"),
            config_data.get("rpi_key_passphrase"),
        )

        if not ssh:
            on_complete(False, {})
            return

        # 1. Enable I2C and ensure tools
        log_func(_("Attempting Runtime Overlay Activation..."), "info")
        ssh.exec_command(
            "sudo dtoverlay i2c-arm && "
            "sudo dtoverlay uart3 && "
            "sudo modprobe i2c-dev i2c-designware-core i2c-designware-platform && "
            "sudo pinctrl set 2 a0 && sudo pinctrl set 3 a0 && "
            "sudo pinctrl set 4 a3 && sudo pinctrl set 5 a3"
        )
        time.sleep(1)
        ssh.exec_command("sudo apt-get install -y -qq i2c-tools")

        results = {
            "i2c": [],
            "uart": {},
            "camera": "NONE"
        }

        # 2. Scan ALL I2C buses (Brute Force)
        log_func(_("Brute-forcing all I2C buses..."), "info")
        stdin, stdout, stderr = ssh.exec_command("ls /sys/class/i2c-adapter")
        bus_entries = stdout.read().decode().strip().split()
        
        found_addresses = set()
        for bus_entry in bus_entries:
            try:
                bus_num = bus_entry.replace("i2c-", "")
                log_func(f"Scanning i2c-{bus_num}...", "verbose")
                # Use -r for safer/faster probing on some RPi 5 controllers
                stdin, stdout, stderr = ssh.exec_command(f"sudo i2cdetect -y -r {bus_num}")
                output = stdout.read().decode("utf-8")
                
                for line in output.splitlines():
                    if ":" in line:
                        parts = line.split(":")[1].split()
                        for p in parts:
                            if p != "--" and p != "UU":
                                found_addresses.add(p.lower())
            except Exception:
                continue

        results["i2c"] = list(found_addresses)
        if "40" in found_addresses: log_func("Detected PCA9685 (0x40)", "success")
        if "68" in found_addresses: log_func("Detected IMU (0x68)", "success")

        # 3. Scan UART/USB ports (with DTR reset)
        log_func(_("Scanning UART/USB with DTR reset..."), "info")
        ports = ["/dev/ttyUSB0", "/dev/serial0", "/dev/ttyAMA0", "/dev/ttyAMA3"]
        for port in ports:
            stdin, stdout, stderr = ssh.exec_command(f"[ -e {port} ] && echo 1 || echo 0")
            if stdout.read().decode().strip() == "1":
                log_func(f"Probing {port}...", "verbose")
                # Reset DTR and set baudrate
                ssh.exec_command(f"sudo stty -F {port} 115200 raw -echo hupcl 2>/dev/null || true")
                time.sleep(0.2)
                stdin, stdout, stderr = ssh.exec_command(f"sudo timeout 1.5s cat {port} | head -c 256")
                raw_data = stdout.read()
                
                if raw_data:
                    hex_head = raw_data.hex()[:32]
                    log_func(f"Data from {port}: {hex_head}", "verbose")
                    if b"$GP" in raw_data or b"$GN" in raw_data:
                        results["uart"]["gps"] = port
                        log_func(f"Detected GPS on {port}", "success")
                    elif b"\x54\x2c" in raw_data or hex_head.startswith("542c"):
                        results["uart"]["lidar"] = port
                        log_func(f"Detected Lidar on {port}", "success")

        # 4. USB Audit
        stdin, stdout, stderr = ssh.exec_command("lsusb")
        log_func(f"USB Devices:\n{stdout.read().decode()}", "verbose")

        # 5. Final I2C check for specific addresses
        i2c_check = results.get("i2c", [])
        if "40" in i2c_check:
            log_func("Detected PCA9685 PWM Controller (0x40)", "success")
        if "68" in i2c_check or "69" in i2c_check:
            log_func("Detected IMU Sensor (0x68/0x69)", "success")

        # 4. Diagnostics if nothing found
        if not results["i2c"] and not results["uart"]:
            log_func(_("Debian 13 Hardware Audit..."), "warning")
            
            # Kernel and Modules
            stdin, stdout, stderr = ssh.exec_command("uname -a")
            log_func(f"Kernel: {stdout.read().decode().strip()}", "verbose")
            
            stdin, stdout, stderr = ssh.exec_command("lsmod | grep -iE 'ftdi|cp210x|ch341|i2c_rp1'")
            log_func(f"Serial/I2C Modules:\n{stdout.read().decode()}", "verbose")

            # Check if ftdi_sio is missing for the FT232 found in lsusb
            if "ftdi_sio" not in stdout.read().decode() and "FT232" in config_data.get("lsusb_output", ""):
                log_func("Loading ftdi_sio module...", "info")
                ssh.exec_command("sudo modprobe ftdi_sio")

            # Check dmesg for FTDI binding
            stdin, stdout, stderr = ssh.exec_command("dmesg | grep -i 'ttyUSB' | tail -n 5")
            log_func(f"UART-USB Logs:\n{stdout.read().decode()}", "verbose")

            # Try to see if I2C-1 is actually "dead" or just hidden
            stdin, stdout, stderr = ssh.exec_command("sudo i2cdetect -y -a 1") # All addresses
            log_func("I2C-1 Raw Grid Attempted.", "verbose")
            
            # Alternative Pinctrl for RP1
            log_func("Attempting alternative pin muxing for RPi 5...", "verbose")
            ssh.exec_command("sudo pinctrl -c 0 set 2 a0 && sudo pinctrl -c 0 set 3 a0")

        # 4. Detect Camera
        stdin, stdout, stderr = ssh.exec_command("rpicam-hello --list-cameras")
        cam_out = stdout.read().decode("utf-8")
        if "imx219" in cam_out: results["camera"] = "imx219"
        elif "imx708" in cam_out: results["camera"] = "imx708"
        elif "ov5647" in cam_out: results["camera"] = "ov5647"
        elif "imx477" in cam_out: results["camera"] = "imx477"

        on_complete(True, results)

    except Exception as e:
        log_func(f"Hardware scan error: {e}", "error")
        on_complete(False, {})
    finally:
        if ssh:
            ssh.close()


def get_setup_script(
    user: str,
    home: str,
    new_pass: str,
    camera_port: str = "cam0",
    camera_type: str = "AUTO",
    fast_mode: bool = False,
) -> str:
    """
    Generuje skrypt Bash do pełnej konfiguracji RPi.
    Generates a Bash script for full RPi configuration.

    Args:
        user (str): Nazwa użytkownika SSH. / SSH username.
        home (str): Katalog domowy użytkownika. / User home directory.
        new_pass (str): Nowe hasło SSH (opcjonalne). / New SSH password (optional).
        camera_port (str): Port kamery (cam0 lub cam1). / Camera port (cam0 or cam1).

    Returns:
        str: Treść skryptu Bash. / The Bash script contents.
    """
    script_params = {
        "user": user,
        "home": f"/home/{user}",
        "new_pass": new_pass if new_pass is not None else "",
        "camera_port": camera_port,
        "camera_type": camera_type,
        "fast_mode": "1" if fast_mode else "0",
    }
    script_template = r"""
#!/bin/bash
set -e
USER_NAME="{user}"
HOME_DIR="{home}"
LOG_FILE="$HOME_DIR/rpi_setup_docker.log"
# HYBRID: Build on RAM disk (fast), export to SD (stable)
RCSIM_BUILD_DIR="/dev/shm/rcsim_build"    # Temporary build location
RCSIM_PROJECT_DIR="$HOME_DIR/rcsim_project"  # Final stable location for Docker
FAST_MODE="{fast_mode}"
NEW_SSH_PASS="{new_pass}"
CAMERA_PORT="{camera_port}"
CAMERA_TYPE="{camera_type}"

# Funkcja logowania / Logging function
log() {{
    echo "[$(date '+%H:%M:%S')] $1" | sudo tee -a "$LOG_FILE"
}}

check_exit_code() {{
    if [ $? -ne 0 ]; then
        log "CRITICAL ERROR: Last operation failed. Aborting."
        exit 1
    fi
}}

sudo rm -f "$LOG_FILE" && sudo touch "$LOG_FILE"
sudo chown $USER_NAME:$USER_NAME "$LOG_FILE"

log "--- STARTING RCSIM INDUSTRIAL CONFIGURATION (v7.1 OPTIMIZED) ---"

if [ "$FAST_MODE" == "1" ]; then
    log ">>> FAST MODE ACTIVE: Skipping system configuration steps <<<"
fi

log "[Step 1/7] System Update & Parallel Tasks Initialization..."
export DEBIAN_FRONTEND=noninteractive

# 1. Fix and clean APT cache thoroughly (prevent corruption)
if [ "$FAST_MODE" != "1" ]; then
    log "Aggressive APT cache cleanup..."
    sudo dpkg --configure -a || true
    sudo rm -rf /var/lib/apt/lists/*
    sudo rm -rf /var/lib/apt/lists.old*
    sudo rm -rf /var/lib/apt/lists/partial/*
    sudo mkdir -p /var/lib/apt/lists/partial
    sudo apt-get clean
    sudo apt-get autoclean

    # Fix GPG keys
    log "Refreshing GPG keys..."
    sudo apt-key update 2>/dev/null || true

    log "Running apt-get update with retry logic..."
else
    log "Fast Mode: Skipping APT cleanup and update."
fi
# Retry logic with aggressive cleanup between attempts
if [ "$FAST_MODE" != "1" ]; then
    for i in {{1..3}}; do
        if sudo apt-get update -y 2>&1 | tee -a "$LOG_FILE"; then
            log "apt-get update succeeded."
            break
        else
            log "apt-get update failed (attempt $i/3). Deep cleaning..."
            sudo killall -9 apt-get apt dpkg 2>/dev/null || true
            sudo rm -rf /var/lib/apt/lists/*
            sudo rm -rf /var/lib/apt/lists.old*
            sudo rm -rf /var/lib/apt/lists/partial/*
            sudo rm -rf /var/cache/apt/*.bin
            sudo mkdir -p /var/lib/apt/lists/partial
            sleep 3
        fi
    done
    sudo apt-get install -y eatmydata || true
fi

# 2. Start Parallel Downloads (Background Jobs)
log "Starting background downloads..."
(
    if ! command -v tailscale &> /dev/null; then
        curl -fsSL https://tailscale.com/install.sh -o /tmp/install_tailscale.sh
    fi
) &
PID_TAILSCALE=$!

(
    if [ ! -d "$HOME_DIR/hailo-apps-infra" ]; then
        git clone https://github.com/hailo-ai/hailo-apps-infra.git \
            "$HOME_DIR/hailo-apps-infra" || true
    fi
) &
PID_HAILO_CLONE=$!

# 3. Main Installation Block (Fast Mode with eatmydata)
log "Installing system packages (Fast Mode)..."
# Combine all packages into one transaction to save time
# Added: dkms, hailo-all dependencies
PKGS="curl git unzip libcamera-apps-lite v4l-utils vlc ffmpeg dkms"

# Check if hailo-all exists in repo, otherwise fallback (handled in smart logic below)
# We just install base deps here. Hailo specific logic follows.

if command -v eatmydata &> /dev/null; then
    APT_CMD="sudo eatmydata apt-get"
else
    APT_CMD="sudo apt-get"
fi

$APT_CMD install -y -qq --no-install-recommends $PKGS
check_exit_code

log "[Step 1a/7] Hailo Drivers..."
# Smart Hailo Install - Skip if already present
if ! dpkg -l | grep -q hailo-all; then
    # Try install hailo-all or fallback
    if apt-cache show hailo-all &> /dev/null; then
        $APT_CMD install -y hailo-all || true
    else
        log "Installing legacy Hailo packages..."
        $APT_CMD install -y hailo-firmware hailort-service || true
    fi
else
    log "Hailo drivers already installed. Skipping."
fi

# Wait for background clones
wait $PID_HAILO_CLONE
log "Hailo apps infra cloned (if needed)."

# Install Hailo Apps Infra (only if not installed)
if [ ! -f "/usr/bin/hailortcli" ] && [ -d "$HOME_DIR/hailo-apps-infra" ]; then
    log "Installing Hailo Apps Infrastructure..."
    cd "$HOME_DIR/hailo-apps-infra"
    sudo ./scripts/cleanup_installation.sh || true
    sudo ./install.sh || true
    cd "$HOME_DIR"
else
    log "Hailo Apps Infra verification passed (Skipping install)."
fi

log "[Step 2/7] Tailscale Installation..."
if [ "$FAST_MODE" != "1" ]; then
    wait $PID_TAILSCALE
    if ! command -v tailscale &> /dev/null; then
        if [ -f "/tmp/install_tailscale.sh" ]; then
            sudo sh /tmp/install_tailscale.sh
            check_exit_code
            log "Tailscale installed."
        else
            log "Tailscale installer not found. Retrying curl..."
            curl -fsSL https://tailscale.com/install.sh | sh
        fi
    else
        log "Tailscale already installed."
    fi
else
    log "Fast Mode: Skipping Tailscale install check."
fi

log "[Step 3/7] Tailscale Authentication (Background)..."
# Always run to ensure config/connection, but in background to not block
(
    # Give the service a moment to start if just installed
    sudo systemctl enable --now tailscaled 2>/dev/null || true
    sleep 3

    nohup sudo tailscale up --reset --accept-dns=false > /tmp/ts_up.log 2>&1 &

    for i in {{1..60}}; do
        if grep -q "https://login.tailscale.com" /tmp/ts_up.log; then
            URL=$(grep -o "https://login.tailscale.com[^ ]*" /tmp/ts_up.log | head -n1)
            log "ACTION_REQUIRED: Tailscale Login Link: $URL"
            break
        fi
        # Check if tailscaled wasn't ready and command aborted immediately
        if grep -q "failed to connect to local tailscaled" /tmp/ts_up.log; then
            sleep 2
            nohup sudo tailscale up --reset --accept-dns=false > /tmp/ts_up.log 2>&1 &
        fi
        sleep 1
    done
) &
log "Tailscale setup backgrounded. Proceeding..."

log "[Step 4/7] Hardware & Camera Config..."
if [ "$FAST_MODE" != "1" ]; then
    sudo raspi-config nonint do_i2c 0
    sudo raspi-config nonint do_serial_hw 0
else
    log "Fast Mode: Skipping hardware config."
fi

if [ "$FAST_MODE" != "1" ]; then
    # Optimized Config Editing
    CONFIG_TXT="/boot/firmware/config.txt"
    CHANGED=0

    manage_config() {{
        KEY=$1
        VAL=$2
        if [ "$KEY" == "dtoverlay" ]; then
            log "ERROR: Use manage_overlay for dtoverlay!"
            return
        fi
        if grep -q "^$KEY=" "$CONFIG_TXT"; then
            CURRENT=$(grep "^$KEY=" "$CONFIG_TXT" | cut -d= -f2 | head -n1)
            if [ "$CURRENT" != "$VAL" ]; then
                sudo sed -i "s/^$KEY=.*/$KEY=$VAL/" "$CONFIG_TXT"
                CHANGED=1
            fi
        else
            echo "$KEY=$VAL" | sudo tee -a "$CONFIG_TXT" > /dev/null
            CHANGED=1
        fi
    }}

    manage_overlay() {{
        OVERLAY=$1
        if ! grep -q "^dtoverlay=$OVERLAY" "$CONFIG_TXT"; then
            echo "dtoverlay=$OVERLAY" | sudo tee -a "$CONFIG_TXT" > /dev/null
            log "Added overlay: $OVERLAY"
            CHANGED=1
        else
            log "Overlay $OVERLAY already present."
        fi
    }}

    # RPi 5 Camera Setup (Optimized for Waveshare / Industrial sensors)
    if [ "$CAMERA_TYPE" == "AUTO" ]; then
        log "Camera mode: AUTO - Ensuring auto-detect is active."
        manage_config "camera_auto_detect" "1"
        # Remove hardcoded imx219 if it exists to avoid conflicts in AUTO mode
        sudo sed -i '/^dtoverlay=imx219/d' "$CONFIG_TXT" || true
    elif [ "$CAMERA_TYPE" == "imx219" ]; then
        log "Camera mode: imx219 (RPi 5 Special) - Disabling auto-detect + manual overlay."
        manage_config "camera_auto_detect" "0"
        manage_overlay "imx219,$CAMERA_PORT"
    else
        log "Camera mode: $CAMERA_TYPE - Ensuring overlay and auto-detect."
        manage_config "camera_auto_detect" "1"
        manage_overlay "$CAMERA_TYPE,$CAMERA_PORT"
    fi

    # MAVLink / Nomad UART (GPIO8=TX, GPIO9=RX)
    manage_overlay "uart3"

    # Optimization: PCIe Gen 3 (optional but good for Hailo)
    if ! grep -q "dtparam=pciex1_gen=3" "$CONFIG_TXT"; then
        echo "dtparam=pciex1_gen=3" | sudo tee -a "$CONFIG_TXT" > /dev/null
        CHANGED=1
    fi

    # Diagnostic: Check cameras
    log "Diagnostic: Detecting cameras..."
    rpicam-hello --list-cameras || true

    # Install Docker if missing
    if ! command -v docker &> /dev/null; then
        curl -sSL https://get.docker.com | sh
        sudo usermod -aG docker $USER_NAME
        sudo usermod -aG video $USER_NAME
        sudo usermod -aG render $USER_NAME
    fi
else
    log "Fast Mode: Skipping config.txt and Docker installation check."
fi

log "[Step 5/6] Building RCSIM Container (High Performance Mode)..."

# 1. SETUP HOST CAMERA SERVICE
# Stop legacy service
if systemctl is-active --quiet rtsp-camera.service; then
    sudo systemctl stop rtsp-camera.service
    sudo systemctl disable rtsp-camera.service
fi

# Extract to RAM disk for fast build
log "Extracting project to RAM disk (fast build)..."
if ! command -v unzip &> /dev/null; then
    log "Emergency: unzip not found, attempting install..."
    sudo apt-get update -y && sudo apt-get install -y unzip
fi
sudo rm -rf "$RCSIM_BUILD_DIR"
mkdir -p "$RCSIM_BUILD_DIR"
set +e
unzip -o -q "{home}/rcsim_project.zip" -d "$RCSIM_BUILD_DIR"
UNZIP_EXIT=$?
set -e
if [ $UNZIP_EXIT -ne 0 ] && [ $UNZIP_EXIT -ne 1 ]; then
    log "CRITICAL ERROR: unzip failed with code $UNZIP_EXIT"
    exit 1
fi

# Fix Windows CRLF line endings on all shell scripts
find "$RCSIM_BUILD_DIR" -name "*.sh" -exec sed -i 's/\r$//' {{}} +

# NOTE: run_camera_direct.sh is NO LONGER USED (deprecated 2026-02-03)
# MediaMTX now uses native 'rpiCamera' source configured in mediamtx.yml
# No external camera scripts are needed

if ! systemctl list-unit-files | grep -q mediamtx.service; then
   log "MediaMTX service NOT found. Installing..."
   sudo chmod +x "$RCSIM_BUILD_DIR/tools/install/install-mediamtx.sh"
   cd "$RCSIM_BUILD_DIR"
   sudo "$RCSIM_BUILD_DIR/tools/install/install-mediamtx.sh"
fi

# Update config
if [ -f "$RCSIM_BUILD_DIR/mediamtx.yml" ]; then
    sudo cp "$RCSIM_BUILD_DIR/mediamtx.yml" /etc/mediamtx.yml
    sudo systemctl restart mediamtx
fi

# 2. DOCKER BUILD (on RAM disk)
cd "$RCSIM_BUILD_DIR"

log "Building Docker image (Parallel Build)..."

# Clean temp directories (prevent "no space left" errors)
log "Cleaning temp directories..."
sudo rm -rf /tmp/* || true
sudo docker system prune -f || true

# Restart Docker to fix potential network/DNS issues
sudo systemctl restart docker

# Use /dev/shm (RAM) for Docker build temp files to maximize speed
DOCKER_TMP="/dev/shm/docker_tmp"
sudo mkdir -p "$DOCKER_TMP"
sudo chmod 1777 "$DOCKER_TMP"
export TMPDIR="$DOCKER_TMP"
export DOCKER_BUILDKIT=1

BUILD_LOG="$HOME_DIR/docker_build.log"
log "Build process started. Output redirected to $BUILD_LOG"
log "Please wait, this may take a few minutes..."

# Run build in background redirecting output
sudo -E docker compose build --parallel > "$BUILD_LOG" 2>&1 &
BUILD_PID=$!

# Visual progress indicator
while kill -0 $BUILD_PID 2>/dev/null; do
    echo -n "."
    sleep 5
done
echo "" # New line after dots

# Retrieve exit code
wait $BUILD_PID
BUILD_EXIT=$?

if [ $BUILD_EXIT -ne 0 ]; then
    log "!!! BUILD FAILED (Exit Code: $BUILD_EXIT) !!!"
    log "Dumping last 100 lines of build log:"
    tail -n 100 "$BUILD_LOG"
    exit 1
else
    log "Build completed successfully."

    # Export to SD card for Docker volumes
    log "Exporting to SD card (stable location)..."
    sudo rm -rf "$RCSIM_PROJECT_DIR"
    sudo cp -r "$RCSIM_BUILD_DIR" "$RCSIM_PROJECT_DIR"
    log "Project exported to $RCSIM_PROJECT_DIR"

    # Cleanup RAM disk after copy
    sudo rm -rf "$RCSIM_BUILD_DIR"
    log "RAM disk cleaned up."
fi

log "Starting containers (from SD location)..."
cd "$RCSIM_PROJECT_DIR"
sudo docker compose down --remove-orphans
sudo docker compose up -d 2>&1 | tee -a "$LOG_FILE"
check_exit_code

log "Waiting for initialization (Polling)..."
# Polling loop instead of sleep
MAX_RETRIES=120
for i in $(seq 1 $MAX_RETRIES); do
    if sudo docker ps --format '{{{{.Names}}}}' | grep -q "rcsim_industrial"; then
        log "Container detected running after $i seconds."
        break
    fi
    sleep 1
done

log "Checking system status..."
set +e
RCSIM_RUNNING=$(sudo docker ps --format '{{{{.Names}}}}' | grep "rcsim_industrial")
CAMERA_SERVICE=$(systemctl is-active mediamtx.service)
set -e

if [ ! -z "$RCSIM_RUNNING" ] && [ "$CAMERA_SERVICE" == "active" ]; then
    log "✓ Docker App is RUNNING!"
    log "✓ MediaMTX Service is ACTIVE!"
else
    log "✗ Deployment Check Failed."
    exit 1
fi

log "[Step 6/6] Finalizing..."
if [ ! -z "$NEW_SSH_PASS" ]; then
    echo "$USER_NAME:$NEW_SSH_PASS" | sudo chpasswd
    log "SSH password changed."
fi
sudo rm -f "{home}/rcsim_project.zip"

log "--- DEPLOYMENT COMPLETED SUCCESSFULLY! ---"
log "RPi Tailscale IP: $(tailscale ip -4)"
exit 0
"""
    return script_template.format(**script_params)


def create_project_archive(
    log_func: Callable[[str, str], None],
    gettext_func: Callable[[str], str],
    project_source_dir: str,
    pc_tailscale_ip: str,
    use_rtk: bool,
    ntrip_user: str,
    ntrip_pass: str,
    ntrip_host: str,
    ntrip_port: str,
    ntrip_mount: str,
    full_config_payload: Dict[str, Any],
) -> Optional[str]:
    """
    Tworzy archiwum ZIP projektu z wygenerowanym plikiem konfiguracyjnym.
    Creates a project ZIP archive with a generated configuration file.

    Args:
        log_func: Funkcja do logowania zdarzeń. / Function for event logging.
        gettext_func: Funkcja do tłumaczenia tekstów. / Function for translation.
        project_source_dir: Ścieżka do katalogu źródłowego projektu.
        pc_tailscale_ip: Adres IP Tailscale komputera PC.
        use_rtk: Czy używać nawigacji RTK.
        ntrip_user: Nazwa użytkownika NTRIP.
        ntrip_pass: Hasło NTRIP.
        ntrip_host: Adres hosta NTRIP.
        ntrip_port: Port NTRIP.
        ntrip_mount: Punkt montowania NTRIP.
        full_config_payload: Pełna konfiguracja z interfejsu GUI.

    Returns:
        Optional[str]: Ścieżka do utworzonego archiwum lub None w przypadku błędu.
                      / Path to the created archive or None on error.
    """
    _ = gettext_func
    if not os.path.isdir(project_source_dir):
        # Using print or log_func since messagebox is UI specific.
        # Following existing pattern assuming caller handles UI.
        # Actually this function is logic only, so log_func is correct.
        if log_func:
            log_func(f"Directory not found: {project_source_dir}", "error")
        return None

    # Base config merged with payload from GUI
    config_data: Dict[str, Any] = {
        "pc_ip": pc_tailscale_ip,
        "ntrip": {"enabled": use_rtk},
        "slam": {"map_size_pixels": 800, "map_size_meters": 20},
    }
    # Verify basics exist
    if "hardware" not in full_config_payload:
        full_config_payload["hardware"] = {}

    # Merge top-level keys (hardware, camera, video)
    config_data.update(full_config_payload)

    # 🔧 FIX: RPi expects 'comm_mode' at root.
    # The UI (ConfigTab) now places it at root, but we keep this check for
    # backward compatibility with older profiles.
    conn_settings = full_config_payload.get("connection_settings", {})
    if "comm_mode" in conn_settings and "comm_mode" not in config_data:
        config_data["comm_mode"] = conn_settings["comm_mode"]

    if use_rtk:
        try:
            config_data["ntrip"].update(
                {
                    "user": ntrip_user,
                    "password": ntrip_pass,
                    "host": ntrip_host,
                    "port": int(ntrip_port),
                    "mountpoint": ntrip_mount,
                }
            )
        except ValueError:
            if log_func:
                log_func(_("NTRIP port must be an integer."), "error")
            return None

    temp_dir = "temp_deploy"
    shutil.rmtree(temp_dir, ignore_errors=True)
    os.makedirs(temp_dir, exist_ok=True)

    try:
        temp_project_path = os.path.join(temp_dir, "project_content")
        ignore = shutil.ignore_patterns(
            ".idea",
            "__pycache__",
            "*.pyc",
            "*.tmp",
            ".git",
            "PySide6",
            ".venv",
            "venv",
            ".pytest_cache",
            ".vscode",
            "logs",
            "temp_deploy",
            "node_modules",
            "*.zip",
            "*.tar.gz",
        )
        shutil.copytree(project_source_dir, temp_project_path, ignore=ignore)

        config_file_path = os.path.join(temp_project_path, "config.json")

        # Load existing config to ensure we don't obliterate keys
        # (like 'ai' and 'autonomous_navigation')
        existing_config = {}
        if os.path.exists(config_file_path):
            try:
                with open(config_file_path, "r", encoding="utf-8") as f:
                    existing_config = json.load(f)
            except Exception as e:
                if log_func:
                    log_func(f"Failed to read existing config.json: {e}", "warning")

        # Merge existing config with new settings from UI.
        # Perform shallow update for base keys and deep update for known nested.
        # But simple top-level update handles most:
        merged_config = existing_config.copy()

        for k, v in config_data.items():
            if isinstance(v, dict) and isinstance(merged_config.get(k), dict):
                merged_config[k].update(v)
            else:
                merged_config[k] = v

        with open(config_file_path, "w", encoding="utf-8") as f:
            json.dump(merged_config, f, indent=4)

        log_func(_("Generated config.json (preserved original keys)."), "success")

        # [FIX] Enhanced masking for sensitive data in verbose logs
        def mask_recursive(d: Any) -> Any:
            if isinstance(d, dict):
                new_d = {}
                for k, v in d.items():
                    if any(secret in k.lower() for secret in ["pass", "user", "key"]):
                        new_d[k] = "***"
                    else:
                        new_d[k] = mask_recursive(v)
                return new_d
            elif isinstance(d, list):
                return [mask_recursive(x) for x in d]
            return d

        safe_config = mask_recursive(config_data)
        log_func(
            f"DEBUG CONFIG: {json.dumps(safe_config, indent=2)}", "verbose"
        )  # Secure debug print

        # --- GENERATE DYNAMIC MEDIAMTX.YML ---
        camera_resolution = full_config_payload.get("camera", {}).get(
            "resolution", [1920, 1080]
        )
        camera_fps = full_config_payload.get("camera", {}).get("fps", 30)
        camera_bitrate_raw = full_config_payload.get("camera", {}).get(
            "bitrate", 5000000
        )
        # Support both int (new) and string (legacy)
        if isinstance(camera_bitrate_raw, int):
            camera_bitrate = camera_bitrate_raw
        else:
            try:
                camera_bitrate = int(str(camera_bitrate_raw).split()[0]) * 1000000
            except (ValueError, IndexError):
                camera_bitrate = 5000000

        log_msg = (
            f"Generating dynamic MediaMTX ({camera_resolution[0]}x"
            f"{camera_resolution[1]} @ {camera_fps}fps, "
            f"{camera_bitrate / 1000000:.1f} Mbps)..."
        )
        log_func(log_msg, "info")
        mediamtx_content = generate_mediamtx_config(
            width=camera_resolution[0],
            height=camera_resolution[1],
            fps=camera_fps,
            bitrate=camera_bitrate,
        )

        with open(os.path.join(temp_project_path, "mediamtx.yml"), "w") as f:
            f.write(mediamtx_content)
        # -------------------------------------

        archive_base_path = os.path.join(temp_dir, "rcsim_project")
        return shutil.make_archive(archive_base_path, "zip", temp_project_path)
    except Exception as e:
        log_func(f"Archive error: {e}", "error")
        return None


def connect_ssh(
    log_func: Callable[[str, str], None],
    gettext_func: Callable[[str], str],
    rpi_host: str,
    rpi_user: str,
    rpi_pass: Optional[str] = None,
    rpi_key_path: Optional[str] = None,
    rpi_key_passphrase: Optional[str] = None,
    timeout: int = 15,
) -> Optional[paramiko.SSHClient]:
    """
    Nawiązuje połączenie SSH z Raspberry Pi.
    Establishes an SSH connection with Raspberry Pi.

    Args:
        log_func: Funkcja do logowania. / Logging function.
        gettext_func: Funkcja do tłumaczenia. / Translation function.
        rpi_host: Adres IP lub nazwa hosta RPi.
        rpi_user: Nazwa użytkownika SSH.
        rpi_pass: Hasło SSH.
        rpi_key_path: Ścieżka do klucza prywatnego SSH.
        rpi_key_passphrase: Hasło do klucza (jeśli jest).

    Returns:
        Optional[paramiko.SSHClient]: Obiekt klienta SSH lub None w przypadku błędu.
                                     / SSH client object or None on error.
    """
    _ = gettext_func
    try:
        client = paramiko.SSHClient()
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

        # Determine authentication method
        if rpi_key_path and os.path.exists(rpi_key_path):
            log_func(
                _("Connecting using SSH key: {0}").format(
                    os.path.basename(rpi_key_path)
                ),
                "info",
            )
            client.connect(
                hostname=rpi_host,
                username=rpi_user,
                key_filename=rpi_key_path,
                passphrase=rpi_key_passphrase,
                timeout=timeout,
            )
        else:
            client.connect(
                hostname=rpi_host, username=rpi_user, password=rpi_pass, timeout=timeout
            )

        log_func(_("SSH connection established."), "success")
        return client
    except Exception as e:
        log_func(f"SSH connection error: {e}", "error")
        return None


def run_full_deployment(
    log_func: Callable[[str, str], None],
    gettext_func: Callable[[str], str],
    progress_callback: Callable[[int], None],
    config_data: Dict[str, Any],
    on_complete: Optional[Callable[[bool, str], None]] = None,
    fast_mode: bool = False,
) -> None:
    """
    Uruchamia pełny proces wdrożenia aplikacji na Raspberry Pi.
    Starts the full process of application deployment on Raspberry Pi.

    Args:
        log_func: Funkcja do logowania. / Logging function.
        gettext_func: Funkcja do tłumaczenia. / Translation function.
        progress_callback: Callback aktualizacji paska postępu.
        config_data: Dane konfiguracyjne do wdrożenia.
        on_complete: Callback wywoływany po zakończeniu.
    """
    _ = gettext_func
    log_func(_("\n--- Starting Docker-based deployment ---"), "header")
    progress_callback(5)

    ssh = None
    sftp = None
    try:
        # 1. Archive
        full_config = config_data.get("full_config_payload", {})

        # Camera Port
        camera_port = full_config.get("camera", {}).get("port", "cam0")
        camera_resolution = full_config.get("camera", {}).get("resolution", [1280, 720])
        camera_fps = full_config.get("camera", {}).get("fps", 30)

        # DEBUG VERSION CHECK
        log_func("!!! DEBUG: USING NEW CAMERA_AI URL (Date: 2026-01-29) !!!", "header")

        full_config.setdefault("video", {}).update(
            {
                "engine": "native",
                "resolution": camera_resolution,
                "fps": camera_fps,
            }
        )
        full_config.setdefault("camera", {}).update(
            {
                "mode": "rtsp",
                "rtsp_url": "rtsp://127.0.0.1:8554/camera_ai",
                "resolution": camera_resolution,
                "fps": camera_fps,
                "port": camera_port,
            }
        )

        archive_path = create_project_archive(
            log_func,
            _,
            config_data.get("project_source_dir"),
            config_data.get("pc_tailscale_ip"),
            config_data.get("use_rtk"),
            config_data.get("ntrip_user"),
            config_data.get("ntrip_pass"),
            config_data.get("ntrip_host"),
            config_data.get("ntrip_port"),
            config_data.get("ntrip_mount"),
            full_config,
        )
        if not archive_path:
            error_msg = (
                "Failed to create archive from: "
                f"{config_data.get('project_source_dir')}"
            )
            log_func(error_msg, "error")
            if on_complete:
                on_complete(False, error_msg)
            return
        progress_callback(20)

        # 2. Connect
        ssh = connect_ssh(
            log_func,
            _,
            config_data.get("rpi_host"),
            config_data.get("rpi_user"),
            config_data.get("rpi_pass"),
            config_data.get("rpi_key_path"),
            config_data.get("rpi_key_passphrase"),
        )
        if not ssh:
            if on_complete:
                on_complete(False, "Failed to connect via SSH")
            return
        progress_callback(30)

        # 3. SFTP Upload
        sftp = ssh.open_sftp()
        remote_archive_path = f"/home/{config_data.get('rpi_user')}/rcsim_project.zip"
        sftp.put(archive_path, remote_archive_path)
        log_func(_("Archive upload complete."), "success")

        setup_script_content = get_setup_script(
            config_data.get("rpi_user"),
            f"/home/{config_data.get('rpi_user')}",
            config_data.get("new_ssh_pass"),
            camera_port,
            camera_type=full_config.get("camera", {}).get("type", "AUTO"),
            fast_mode=fast_mode,
        )
        remote_script_path = f"/home/{config_data.get('rpi_user')}/auto_setup.sh"
        with sftp.file(remote_script_path, "w") as f:
            f.write(setup_script_content)
        sftp.chmod(remote_script_path, 0o755)
        progress_callback(50)

        # 4. Execute and Monitor
        log_func(_("\n--- Running setup script on RPi ---"), "header")
        channel = ssh.get_transport().open_session()
        channel.get_pty()
        channel.exec_command(f"bash {remote_script_path}")

        sent_pass = False
        password = config_data.get("rpi_pass")

        while not channel.exit_status_ready():
            if channel.recv_ready():
                raw_chunk = channel.recv(4096).decode("utf-8", "ignore")
                clean_chunk = strip_ansi_codes(raw_chunk)
                for line in clean_chunk.splitlines():
                    if line.strip():
                        log_func(line, "normal")

                        # Auto-send sudo password if requested
                        if "[sudo] password for" in line and not sent_pass and password:
                            log_func("Auto-sending sudo password...", "verbose")
                            channel.send(password + "\n")
                            sent_pass = True

                        match = re.search(r"\[Step (\d+)/(\d+)\]", line)
                        if match:
                            # Rough progress mapping: 50 + (step/total * 40)
                            step = int(match.group(1))
                            total = int(match.group(2))
                            p = 50 + int((step / total) * 40)
                            progress_callback(p)

                        # Parser logowania Tailscale
                        if "ACTION_REQUIRED: Tailscale Login Link:" in line:
                            url_match = re.search(
                                r"(https://login\.tailscale\.com[^\s]+)", line
                            )
                            if url_match:
                                url = url_match.group(1)
                                log_func(
                                    f"Opening Tailscale URL in browser: {url}",
                                    "warning",
                                )
                                import webbrowser

                                webbrowser.open(url)
            time.sleep(0.1)

        exit_status = channel.recv_exit_status()
        progress_callback(100)

        if exit_status == 0:
            if on_complete:
                on_complete(True, "Deployment successful!")
        else:
            if on_complete:
                on_complete(False, f"Script failed with exit code {exit_status}")

    except Exception as e:
        log_func(f"Deployment error: {e}", "error")
        if on_complete:
            on_complete(False, str(e))
    finally:
        if sftp:
            sftp.close()
        if ssh:
            ssh.close()


def run_docker_update(
    log_func: Callable[[str, str], None],
    gettext_func: Callable[[str], str],
    progress_callback: Callable[[int], None],
    config_data: Dict[str, Any],
    on_complete: Optional[Callable[[bool, str], None]] = None,
) -> None:
    """
    Uruchamia tylko aktualizację kontenera Docker (bez pełnej reinstalacji systemu).
    Runs only the Docker container update (without full system reinstallation).
    Używa trybu szybkiego (fast_mode), pomijając kroki systemowe.
    """
    run_full_deployment(
        log_func,
        gettext_func,
        progress_callback,
        config_data,
        on_complete,
        fast_mode=True,
    )


def run_hot_deploy(
    log_func: Callable[[str, str], None],
    gettext_func: Callable[[str], str],
    progress_callback: Callable[[int], None],
    config_data: Dict[str, Any],
    on_complete: Optional[Callable[[bool, str], None]] = None,
) -> None:
    """
    Hot Deploy: Podmienia pliki Python i config bezpośrednio w kontenerze.
    Hot Deploy: Replaces Python and config files directly in the running container.

    Pomija pełny Docker rebuild — zajmuje ~30-60 sekund zamiast 12 minut.
    Skips full Docker rebuild — takes ~30-60 seconds instead of 12 minutes.
    Wymaga, aby kontener 'rcsim_industrial' już istniał (po pierwszym full deployu).
    Requires 'rcsim_industrial' container to already exist (after first full deploy).
    """
    _ = gettext_func
    log_func(
        _("\n--- HOT DEPLOY: Quick Code Update (no Docker rebuild) ---"),
        "header",
    )
    progress_callback(5)

    ssh = None
    sftp = None
    try:
        # 1. Create archive (same as full deploy)
        full_config = config_data.get("full_config_payload", {})

        camera_port = full_config.get("camera", {}).get("port", "cam0")
        camera_resolution = full_config.get("camera", {}).get("resolution", [1280, 720])
        camera_fps = full_config.get("camera", {}).get("fps", 30)

        full_config.setdefault("video", {}).update(
            {
                "engine": "native",
                "resolution": camera_resolution,
                "fps": camera_fps,
            }
        )
        full_config.setdefault("camera", {}).update(
            {
                "mode": "rtsp",
                "rtsp_url": "rtsp://127.0.0.1:8554/camera_ai",
                "resolution": camera_resolution,
                "fps": camera_fps,
                "port": camera_port,
            }
        )

        archive_path = create_project_archive(
            log_func,
            _,
            config_data.get("project_source_dir"),
            config_data.get("pc_tailscale_ip"),
            config_data.get("use_rtk"),
            config_data.get("ntrip_user"),
            config_data.get("ntrip_pass"),
            config_data.get("ntrip_host"),
            config_data.get("ntrip_port"),
            config_data.get("ntrip_mount"),
            full_config,
        )
        if not archive_path:
            error_msg = (
                "Failed to create archive from: "
                f"{config_data.get('project_source_dir')}"
            )
            log_func(error_msg, "error")
            if on_complete:
                on_complete(False, error_msg)
            return
        progress_callback(15)

        # 2. Connect SSH
        ssh = connect_ssh(
            log_func,
            _,
            config_data.get("rpi_host"),
            config_data.get("rpi_user"),
            config_data.get("rpi_pass"),
            config_data.get("rpi_key_path"),
            config_data.get("rpi_key_passphrase"),
        )
        if not ssh:
            if on_complete:
                on_complete(False, "Failed to connect via SSH")
            return
        progress_callback(25)

        # 3. SFTP Upload
        sftp = ssh.open_sftp()
        user = config_data.get("rpi_user", "pi")
        home = f"/home/{user}"
        remote_zip = f"{home}/rcsim_hotdeploy.zip"
        sftp.put(archive_path, remote_zip)
        log_func(_("Archive uploaded for hot deploy."), "success")
        progress_callback(40)

        # 4. Extract, copy to container, restart
        hot_script = """#!/bin/bash
CONTAINER="rcsim_industrial"
HOT_DIR="/dev/shm/rcsim_hotdeploy"
ZIP_PATH="{remote_zip}"
RCSIM_DIR="{home}/rcsim_project"
NEED_RECREATE=0

echo "[HOT] Extracting to RAM disk..."
rm -rf "$HOT_DIR"
mkdir -p "$HOT_DIR"
unzip -o -q "$ZIP_PATH" -d "$HOT_DIR"
echo "[HOT] Extracted files:"
ls -la "$HOT_DIR/" | head -20

# Check container exists
if ! sudo docker ps -a --format '{{{{.Names}}}}' | grep -q "$CONTAINER"; then
    echo "[HOT] ERROR: Container $CONTAINER not found! Run full deploy first."
    exit 1
fi

# Check if docker-compose.yml changed (needs recreate for device mapping)
if [ -f "$HOT_DIR/docker-compose.yml" ] && [ -f "$RCSIM_DIR/docker-compose.yml" ]; then
    if ! diff -q "$HOT_DIR/docker-compose.yml" "$RCSIM_DIR/docker-compose.yml" > /dev/null 2>&1; then
        echo "[HOT] docker-compose.yml CHANGED - will recreate container!"
        NEED_RECREATE=1
    fi
fi

echo "[HOT] Stopping container..."
sudo docker stop "$CONTAINER" 2>/dev/null || true

# Update host-side files FIRST (before potential recreate)
echo "[HOT] Updating host-side files..."
if [ -f "$HOT_DIR/config.json" ]; then
    sudo cp "$HOT_DIR/config.json" "$RCSIM_DIR/config.json" && \
        echo "[HOT]   ✓ config.json updated (volume mount)" || \
        echo "[HOT]   ✗ Failed to update config.json on host"
fi

if [ -f "$HOT_DIR/docker-compose.yml" ]; then
    sudo cp "$HOT_DIR/docker-compose.yml" "$RCSIM_DIR/docker-compose.yml" && \
        echo "[HOT]   ✓ docker-compose.yml updated on host" || \
        echo "[HOT]   ✗ Failed to update docker-compose.yml"
fi

# Update mediamtx if present
if [ -f "$HOT_DIR/mediamtx.yml" ]; then
    sudo cp "$HOT_DIR/mediamtx.yml" /etc/mediamtx.yml
    sudo systemctl restart mediamtx 2>/dev/null || true
    echo "[HOT]   ✓ mediamtx.yml updated and restarted"
fi

# If docker-compose changed, recreate container FIRST (new volume mounts/devices)
if [ "$NEED_RECREATE" == "1" ]; then
    echo "[HOT] Recreating container (docker compose) for new config..."
    cd "$RCSIM_DIR"
    sudo docker compose down --remove-orphans 2>/dev/null || true
fi

# Copy source code to HOST project directory (volumes are mounted!)
echo "[HOT] Syncing source code to host project directory..."
for DIR in core logic modules tools models web_assets; do
    if [ -d "$HOT_DIR/$DIR" ]; then
        sudo rm -rf "$RCSIM_DIR/$DIR"
        sudo cp -r "$HOT_DIR/$DIR" "$RCSIM_DIR/$DIR" && \
            echo "[HOT]   ✓ Synced $DIR/ to host" || \
            echo "[HOT]   ✗ Failed to sync $DIR/"
    fi
done

# Copy individual files to host
for FILE in entrypoint.sh main.py supervisor.py; do
    if [ -f "$HOT_DIR/$FILE" ]; then
        sudo cp "$HOT_DIR/$FILE" "$RCSIM_DIR/$FILE" && \
            echo "[HOT]   ✓ Synced $FILE to host" || \
            echo "[HOT]   ✗ Failed to sync $FILE"
    fi
done

# Start/recreate container (volumes auto-mount latest code from host)
if [ "$NEED_RECREATE" == "1" ]; then
    echo "[HOT] Starting container with docker compose..."
    cd "$RCSIM_DIR"
    sudo docker compose up -d 2>&1
    echo "[HOT] Container recreated with new config + new code (via volumes)."
else
    echo "[HOT] Restarting container (volumes auto-mount new code)..."
    sudo docker restart "$CONTAINER"
fi

# Wait for container to be healthy
for i in $(seq 1 30); do
    if sudo docker ps --format '{{{{.Names}}}}' | grep -q "$CONTAINER"; then
        echo "[HOT] Container is running after $i seconds."
        break
    fi
    sleep 1
done

# Cleanup
rm -rf "$HOT_DIR"
rm -f "$ZIP_PATH"

echo "[HOT] ✅ HOT DEPLOY COMPLETED SUCCESSFULLY!"
"""
        # Upload and execute script
        remote_script = f"{home}/hot_deploy.sh"
        with sftp.file(remote_script, "w") as f:
            f.write(hot_script.format(remote_zip=remote_zip, home=home).replace("\r\n", "\n"))
        sftp.chmod(remote_script, 0o755)
        progress_callback(50)

        log_func(_("Executing hot deploy on RPi..."), "info")
        channel = ssh.get_transport().open_session()
        channel.get_pty()
        channel.exec_command(f"bash {remote_script}")

        sent_pass = False
        password = config_data.get("rpi_pass")

        while not channel.exit_status_ready():
            if channel.recv_ready():
                raw = channel.recv(4096).decode("utf-8", "ignore")
                clean = strip_ansi_codes(raw)
                for line in clean.splitlines():
                    if line.strip():
                        log_func(line, "normal")

                        # Auto-send sudo password if requested
                        if "[sudo] password for" in line and not sent_pass and password:
                            log_func("Auto-sending sudo password for hot deploy...", "verbose")
                            channel.send(password + "\n")
                            sent_pass = True

                        if "[HOT] Copying" in line:
                            progress_callback(65)
                        elif "[HOT] Starting" in line:
                            progress_callback(80)
                        elif "[HOT] Container is running" in line:
                            progress_callback(95)
            time.sleep(0.1)

        exit_status = channel.recv_exit_status()
        progress_callback(100)

        if exit_status == 0:
            if on_complete:
                on_complete(True, "Hot Deploy successful!")
        else:
            if on_complete:
                on_complete(
                    False,
                    f"Hot deploy script failed (exit code {exit_status})",
                )

    except Exception as e:
        log_func(f"Hot deploy error: {e}", "error")
        if on_complete:
            on_complete(False, str(e))
    finally:
        if sftp:
            sftp.close()
        if ssh:
            ssh.close()


def test_ssh(
    log_func: Callable[[str, str], None],
    gettext_func: Callable[[str], str],
    config_data: Dict[str, Any],
    on_complete: Optional[Callable[[bool, str], None]] = None,
) -> None:
    """
    Testuje połączenie SSH.
    Tests SSH connection.
    """
    ssh = None
    try:
        ssh = connect_ssh(
            log_func,
            gettext_func,
            config_data.get("rpi_host"),
            config_data.get("rpi_user"),
            config_data.get("rpi_pass"),
            config_data.get("rpi_key_path"),
            config_data.get("rpi_key_passphrase"),
        )
        if ssh:
            if on_complete:
                on_complete(True, "Connection OK")
        else:
            if on_complete:
                on_complete(False, "Connection Failed")
    finally:
        if ssh:
            ssh.close()


def ping_host(host: str) -> bool:
    """
    Sprawdza dostępność hosta pomocą systemowego polecenia ping.
    Checks host availability using system ping command.
    """
    if not host:
        return False
    try:
        # Windows ping -n 1, Linux/Mac ping -c 1
        param = "-n" if os.name == "nt" else "-c"
        # Timeout 500ms if possible? Not standard in all pings, use -w on windows (ms)
        args = ["ping", param, "1", host]
        if os.name == "nt":
            args.extend(["-w", "500"])
        else:
            args.extend(["-W", "1"])

        res = subprocess.call(
            args, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
        )
        return res == 0
    except Exception:
        return False


def run_camera_update(
    log_func: Callable[[str, str], None],
    gettext_func: Callable[[str], str],
    progress_callback: Callable[[int], None],
    config_data: Dict[str, Any],
    on_complete: Optional[Callable[[bool, str], None]] = None,
) -> None:
    """
    Aktualizuje konfigurację kamery (plik mediamtx.yml).
    Updates camera configuration (mediamtx.yml file).
    """
    _ = gettext_func
    log_func(_("--- Quick Camera Update ---"), "header")

    # 1. Generate new config content
    full_config = config_data.get("full_config_payload", {})
    camera_resolution = full_config.get("camera", {}).get("resolution", [1920, 1080])
    camera_fps = full_config.get("camera", {}).get("fps", 30)
    camera_bitrate_raw = full_config.get("camera", {}).get("bitrate", 5000000)
    if isinstance(camera_bitrate_raw, int):
        camera_bitrate = camera_bitrate_raw
    else:
        try:
            camera_bitrate = int(str(camera_bitrate_raw).split()[0]) * 1000000
        except (ValueError, IndexError, AttributeError):
            camera_bitrate = 5000000

    log_msg = (
        f"Generating dynamic MediaMTX ({camera_resolution[0]}x"
        f"{camera_resolution[1]} @ {camera_fps}fps, "
        f"{camera_bitrate / 1000000:.1f} Mbps)..."
    )
    log_func(log_msg, "info")

    new_yaml = generate_mediamtx_config(
        width=camera_resolution[0],
        height=camera_resolution[1],
        fps=camera_fps,
        bitrate=camera_bitrate,
    )

    ssh = None
    sftp = None
    try:
        # 2. Upload via SSH
        ssh = connect_ssh(
            log_func,
            _,
            config_data.get("rpi_host"),
            config_data.get("rpi_user"),
            config_data.get("rpi_pass"),
            config_data.get("rpi_key_path"),
            config_data.get("rpi_key_passphrase"),
        )
        if not ssh:
            if on_complete:
                on_complete(False, "SSH Fail")
            return

        sftp = ssh.open_sftp()
        with sftp.file("/tmp/mediamtx.yml", "w") as f:
            f.write(new_yaml)

        # 3. Apply
        log_func(_("Applying configuration..."), "info")
        stdin, stdout, stderr = ssh.exec_command(
            "sudo mv /tmp/mediamtx.yml /etc/mediamtx.yml && "
            "sudo systemctl restart mediamtx"
        )
        exit_status = stdout.channel.recv_exit_status()

        if exit_status == 0:
            log_func(_("Camera updated successfully."), "success")
            if on_complete:
                on_complete(True, "OK")
        else:
            err = stderr.read().decode()
            log_func(f"Update failed: {err}", "error")
            if on_complete:
                on_complete(False, f"Fail: {err}")

    except Exception as e:
        log_func(f"Error: {e}", "error")
        if on_complete:
            on_complete(False, str(e))
    finally:
        if sftp:
            try:
                sftp.close()
            except Exception:
                pass
        if ssh:
            ssh.close()


def run_backup(
    log_func: Callable[[str, str], None],
    gettext_func: Callable[[str], str],
    progress_callback: Callable[[int], None],
    config_data: Dict[str, Any],
    local_save_path: str,
    on_complete: Optional[Callable[[bool, str], None]] = None,
) -> None:
    """
    Tworzy kopię zapasową projektu z RPi i pobiera ją na PC.
    Creates a backup of the project from RPi and downloads it to PC.
    """
    _ = gettext_func
    log_func(_("--- Starting Backup ---"), "header")
    ssh = None
    sftp = None
    try:
        ssh = connect_ssh(
            log_func,
            _,
            config_data.get("rpi_host"),
            config_data.get("rpi_user"),
            config_data.get("rpi_pass"),
            config_data.get("rpi_key_path"),
            config_data.get("rpi_key_passphrase"),
        )
        if not ssh:
            if on_complete:
                on_complete(False, "SSH Fail")
            return

        # 1. Create Tar on RPi
        log_func(_("Creating remote archive..."), "info")
        cmd = (
            "tar -czf /tmp/rcsim_backup.tar.gz -C "
            f"/home/{config_data.get('rpi_user')} rcsim_project"
        )
        stdin, stdout, stderr = ssh.exec_command(cmd)
        if stdout.channel.recv_exit_status() != 0:
            log_func(f"Remote tar failed: {stderr.read().decode()}", "error")
            if on_complete:
                on_complete(False, "Remote tar failed")
            return

        # 2. Download
        log_func(_("Downloading to PC..."), "info")
        sftp = ssh.open_sftp()
        sftp.get("/tmp/rcsim_backup.tar.gz", local_save_path)

        # 3. Cleanup
        ssh.exec_command("rm /tmp/rcsim_backup.tar.gz")

        log_func(_("Backup saved to: ") + local_save_path, "success")
        if on_complete:
            on_complete(True, "OK")

    except Exception as e:
        log_func(f"Backup error: {e}", "error")
        if on_complete:
            on_complete(False, str(e))
    finally:
        if sftp:
            try:
                sftp.close()
            except Exception:
                pass
        if ssh:
            ssh.close()


def run_diagnostics(
    log_func: Callable[[str, str], None],
    gettext_func: Callable[[str], str],
    config_data: Dict[str, Any],
    on_complete: Optional[Callable[[bool, str], None]] = None,
) -> None:
    """
    Uruchamia diagnostykę systemu na RPi.
    Runs system diagnostics on RPi.
    """
    _ = gettext_func
    log_func(_("--- System Diagnostics ---"), "header")
    ssh = None
    try:
        ssh = connect_ssh(
            log_func,
            _,
            config_data.get("rpi_host"),
            config_data.get("rpi_user"),
            config_data.get("rpi_pass"),
            config_data.get("rpi_key_path"),
            config_data.get("rpi_key_passphrase"),
        )
        if not ssh:
            if on_complete:
                on_complete(False, "SSH Fail")
            return

        cmds = [
            ("Uptime", "uptime"),
            ("Disk Usage", "df -h | grep root"),
            ("Memory", "free -h"),
            ("Docker Status", "sudo docker ps"),
            ("MediaMTX Status", "sudo systemctl status mediamtx --no-pager"),
            ("MediaMTX Logs", "sudo journalctl -u mediamtx -n 20 --no-pager"),
            ("Throttle Status", "vcgencmd get_throttled"),
            ("Temperature", "vcgencmd measure_temp"),
            ("Tailscale", "tailscale status"),
        ]

        for name, cmd in cmds:
            log_func(f"[{name}]:", "info")
            stdin, stdout, stderr = ssh.exec_command(cmd)
            out = stdout.read().decode().strip()
            log_func(out, "normal")
            log_func("-" * 20, "normal")

        if on_complete:
            on_complete(True, "OK")
    except Exception as e:
        log_func(f"Diag Error: {e}", "error")
        if on_complete:
            on_complete(False, str(e))
    finally:
        if ssh:
            ssh.close()


def reboot_pi(ssh: paramiko.SSHClient) -> bool:
    """
    Restartuje RPi.
    Reboots RPi.
    """
    try:
        ssh.exec_command("sudo reboot")
        return True
    except Exception:
        return False


def check_remote_service_status(ssh: paramiko.SSHClient, service_name: str) -> bool:
    """
    Sprawdza, czy nazwany serwis (systemd lub kontener docker) działa.
    Checks if a named service (systemd or docker container) is running.
    """
    try:
        # Check if it's a docker container first
        stdin, stdout, stderr = ssh.exec_command(
            f"sudo docker ps --format '{{{{.Names}}}}' | grep -w {service_name}"
        )
        if stdout.read().decode().strip():
            return True

        # Fallback to systemd
        stdin, stdout, stderr = ssh.exec_command(f"systemctl is-active {service_name}")
        if stdout.read().decode().strip() == "active":
            return True

        return False
    except Exception:
        return False


def restart_service(ssh: paramiko.SSHClient) -> bool:
    """
    Restartuje główny kontener aplikacji.
    Restarts the main application container.
    """
    try:
        ssh.exec_command("sudo docker restart rcsim_industrial")
        return True
    except Exception:
        return False


def fetch_logs(ssh: paramiko.SSHClient) -> Optional[str]:
    """
    Pobiera ostatnie 100 linii logów kontenera.
    Fetches the last 100 lines of container logs.
    """
    try:
        stdin, stdout, stderr = ssh.exec_command(
            "sudo docker logs --tail 100 rcsim_industrial"
        )
        return stdout.read().decode()
    except Exception:
        return None


def fetch_build_logs(ssh: paramiko.SSHClient) -> Optional[str]:
    """
    Pobiera log z budowania środowiska Docker.
    Fetches the docker build log.
    """
    try:
        stdin, stdout, stderr = ssh.exec_command("cat ~/docker_build.log")
        content = stdout.read().decode()
        if not content:
            return "No build logs found (docker_build.log is empty or missing)."
        return content
    except Exception:
        return None
