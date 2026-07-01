# ✈️ USB HID to RC Model Signal Converter (CRSF/i-BUS/PPM)

A comprehensive, ultra-stable, and real-time optimized system designed for **Raspberry Pi 5** and **microcontrollers**. The project allows connecting any USB HID controllers (e.g., transmitters, joysticks, yokes, game controllers, or RC radios in USB simulator mode) and converting their inputs into professional, low-latency RC radio protocols (Jitter < 1 ms).

---

## 🏗️ System Architecture

The data flow within the device is presented in the block diagram below:

```text
 ┌──────────────────────┐      ┌─────────────────────────┐      ┌────────────────────────┐
 │  USB HID Controller  │ ───> │  Linux Scanner (evdev)  │ ───> │   Mixer & Expo Engine  │
 │ (e.g., TX16s, Joy)   │      │    [Receiver Threads]   │      │  [Mappings Application]│
 └──────────────────────┘      └─────────────────────────┘      └────────────────────────┘
                                                                             │
 ┌──────────────────────┐      ┌─────────────────────────┐                   ▼
 │   RC Transmitter /   │ <─── │ Coprocessor (STM32/     │ <─── ┌────────────────────────┐
 │  Relay (PPM/CRSF/    │      │ RP2350 / optional ESP32)│      │  Serial Sender (UART)  │
 │  ELRS)               │      │                         │      │     [Digital Frames]   │
 └──────────────────────┘      └─────────────────────────┘      └────────────────────────┘
```

1. **Input Layer (Python / evdev)**: System threads listen to events from `/dev/input/event*` interfaces. They handle dynamic mappings, channel reversing, sub-trim correction, and non-linear stick response curves (**Expo**).
2. **Mixer Engine**: Calculates and mixes stick positions on the fly, including dedicated modes for flying wings (Elevon / Delta) or V-tail surfaces.
3. **Transmission Layer (Python Serial)**: Generates precise TBS Crossfire digital frames (CRSF, baud rate 420000 bps) or FlySky i-BUS frames (baud rate 115200 bps) and transmits them directly via UART pins (GPIO 14/15) on the Raspberry Pi.
4. **Coprocessor Generating PPM/Serial RC**: When a classic analog PPM signal or high-precision serial signals are required, a dedicated coprocessor (STM32 Blue Pill or Seeed Studio XIAO RP2350) receives digital frames from the RPi via the serial/USB port, converts them using hardware timers/high-accuracy PIO state machines, and outputs a crystal-clear PPM signal (e.g., PA0/D0) or serial RC signal (e.g., PA9/D1).

---

## 🛠️ Installation and System Services Registration

All control and monitoring services are registered in the `systemd` manager with real-time priorities assigned (CPUSchedulingPolicy=fifo, priority=50) and core affinity (CPUAffinity=3) to eliminate Linux kernel overhead.

### Installation steps on Raspberry Pi 5:

1. **Clone the repository** to your working directory.
2. **Grant execution permissions** to the installation scripts:
   ```bash
   chmod +x scripts/*.sh
   ```
3. **Run the system service installer**:
   ```bash
   sudo ./scripts/install_services.sh
   ```

The script will automatically set up an isolated Python virtual environment (`venv`), install libraries from `requirements.txt`, assign the required permissions for managing the I2C bus (UPS LiPo hat), and register the system as an autostart service.

---

## 📡 On-the-Fly Management and Configuration (Web UI)

The system features a built-in modern Web UI served directly from port `8080` on the Raspberry Pi:

* **Joystick Scanning**: Preview of physically connected USB controllers with their exact system path.
* **Real-Time Channel Indicator**: Aesthetic bars visualizing the movement of each of the 16 radio channels (preview frequency 10 Hz).
* **In-Browser JSON Editor**: Instant model profile switching, modification of endpoints, sub-trims, limits, expo, and key mapping without rebooting the computer. After clicking "Save", the engine automatically reloads the input threads.
* **Per-Channel Failsafe Configuration**: Ability to set failsafe behavior for each control channel individually (Center, Hold, or Custom value e.g., brake 1000us) in case the physical input controller is disconnected.
* **Auto-Center FFB & Soft-lock**: Support for FFB steering wheels and joysticks (e.g., Logitech G29/G27/G920) including adjustment of hardware centering spring force (0-100%), hardware steering angle range reduction (via sysfs) with hardware soft-lock `FF_SPRING`, and software scaling fallback.
* **Telemetry Power Monitor**: Integration with INA219 chips (Waveshare UPS Hat, etc.) monitoring the charge level of the onboard 2S LiPo battery pack.
* **Coprocessor Diagnostic & Flash Console**: Ability to flash the coprocessor firmware with a single click directly through the browser, thanks to integration with appropriate tools (`openocd` for STM32, `picotool` for XIAO RP2350, `esptool` for ESP32).

---

## 📱 Use at the FPV / RC Flying Field

To change settings directly from your phone in the field:
1. Run the Hotspot configuration script:
   ```bash
   sudo ./scripts/setup_ap.sh
   ```
2. Raspberry Pi will create a Wi-Fi network named **RCSIM_MCS** (Password: `RCSIM_GORIDE`).
3. Connect with your phone and open the following address in your browser: **`http://10.42.0.1:8080`** (or `http://192.168.4.1:8080`).
