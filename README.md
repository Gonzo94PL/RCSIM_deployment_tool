# RCSIM RPi5 Deployment Tool (Narzędzie Wdrożeniowe)

## Overview (Przegląd)
This application facilitates the deployment of the RCSIM software stack to a Raspberry Pi 5. It handles SSH connections, project archiving, file uploads, and remote configuration including Docker container management and hardware setup.
Ta aplikacja ułatwia wdrażanie oprogramowania RCSIM na Raspberry Pi 5. Obsługuje połączenia SSH, archiwizację projektu, przesyłanie plików oraz zdalną konfigurację, w tym zarządzanie kontenerami Docker i konfigurację sprzętową.

## Key Features (Główne Funkcje)
*   **Automated Deployment (Automatyczne Wdrażanie):** Archives the project, uploads it to RPi, builds Docker images, and starts services. / Archiwizuje projekt, przesyła go na RPi, buduje obrazy Docker i uruchamia usługi.
*   **Hardware Configuration (Konfiguracja Sprzętowa):** Configure IMU, GPS, LiDAR, and Camera settings via GUI. / Konfiguracja IMU, GPS, LiDAR i Kamery przez GUI.
*   **Network Setup (Ustawienia Sieci):** Integrates with Tailscale for secure remote access. / Integracja z Tailscale dla bezpiecznego dostępu zdalnego.
*   **Diagnostics (Diagnostyka):** Built-in tools to check system status, logs, and service health. / Wbudowane narzędzia do sprawdzania stanu systemu, logów i usług.
*   **Bilingual Interface (Dwujęzyczny Interfejs):** Supports English and Polish. / Obsługuje język angielski i polski.

## File Structure (Struktura Plików)
*   `RCsimRPi5deploymentapp.py`: Main entry point and GUI controller. / Główny punkt wejścia i kontroler GUI.
*   `deployment_logic.py`: Core logic for SSH, SFTP, and script execution. / Główna logika dla SSH, SFTP i wykonywania skryptów.
*   `config_manager.py`: Manages settings persistence and translation. / Zarządza trwałością ustawień i tłumaczeniami.
*   `ui_components.py`: Reusable Tkinter UI components. / Komponenty interfejsu Tkinter wielokrotnego użytku.
*   `service_monitor.py`: Background thread for monitoring RPi services. / Wątek w tle do monitorowania usług RPi.
*   `build_deployment.py`: PyInstaller script for building the executable. / Skrypt PyInstaller do budowania pliku wykonywalnego.

## Requirements (Wymagania)
*   Python 3.8+
*   Libraries: `tkinter`, `paramiko`, `requests` (standard libs mostly)
*   Raspberry Pi 5 with Hailo-8L (for AI features) / Raspberry Pi 5 z Hailo-8L (dla funkcji AI)

## Usage (Użycie)
1.  Run `python RCsimRPi5deploymentapp.py`.
2.  Configure Connection details (IP, User, Password/Key).
3.  Select Project Source Directory.
4.  Configure Hardware and click "Start Deployment".
