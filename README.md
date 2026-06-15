# RCSIM RPi5 Deployment Tool (Narzędzie Wdrożeniowe)

## Overview (Przegląd)
This application facilitates the deployment of the RCSIM software stack to a Raspberry Pi 5. It handles SSH connections, project archiving, file uploads, and remote configuration including Docker container management, Tailscale setup, and hardware setup. The interface is served via a Flask web server, allowing control from any modern browser.

Ta aplikacja ułatwia wdrażanie oprogramowania RCSIM na Raspberry Pi 5. Obsługuje połączenia SSH, archiwizację projektu, przesyłanie plików oraz zdalną konfigurację, w tym zarządzanie kontenerami Docker, konfigurację Tailscale i ustawienia sprzętowe. Interfejs jest udostępniany przez serwer Flask, co pozwala na wygodne sterowanie z poziomu dowolnej przeglądarki.

## Key Features (Główne Funkcje)
*   **Automated Deployment (Automatyczne Wdrażanie):** Archives the project, uploads it to RPi, builds Docker images, and starts services. / Archiwizuje projekt, przesyła go na RPi, buduje obrazy Docker i uruchamia usługi.
*   **Hardware Configuration (Konfiguracja Sprzętowa):** Configure IMU, GPS, LiDAR, and Camera settings via Web GUI. / Konfiguracja IMU, GPS, LiDAR i Kamery przez interfejs Web.
*   **Network Setup (Ustawienia Sieci):** Integrates with Tailscale for secure remote access. / Integracja z Tailscale dla bezpiecznego dostępu zdalnego.
*   **Diagnostics (Diagnostyka):** Built-in tools to check system status, logs, and service health. / Wbudowane narzędzia do sprawdzania stanu systemu, logów i usług.
*   **Modern Web UI (Nowoczesny Interfejs Web):** Easy to use, cross-platform interface served locally. / Łatwy w użyciu, wieloplatformowy interfejs serwowany lokalnie.
*   **Bilingual Interface (Dwujęzyczny Interfejs):** Supports English and Polish. / Obsługuje język angielski i polski.

## File Structure (Struktura Plików)
*   `RCsimRPi5deploymentapp.py`: Main entry point / launcher. / Główny punkt wejścia i launcher.
*   `web_server.py`: Flask application handling the Web UI and API. / Aplikacja Flask obsługująca interfejs webowy i API.
*   `core/deployment_logic.py`: Core logic for SSH, SFTP, and remote commands. / Główna logika dla SSH, SFTP i zdalnych komend.
*   `core/config_manager.py`: Manages configuration profiles and settings. / Zarządza profilami konfiguracji i ustawieniami.
*   `core/service_monitor.py`: Background threads for remote service status tracking. / Wątki w tle do śledzenia statusu zdalnych usług.
*   `ui/ui_components.py`: Tkinter-based legacy UI components if fallback is needed. / Komponenty UI oparte na Tkinter (legacy fallback).
*   `web/`: Web UI static templates and frontend assets. / Szablony statyczne i zasoby interfejsu Web.

## Requirements (Wymagania)
*   Python 3.8+
*   Libraries: `flask`, `paramiko`, `requests`
*   Raspberry Pi 5 with Hailo-8L (for AI features) / Raspberry Pi 5 z Hailo-8L (dla funkcji AI)

## Usage (Użycie)
1.  Run `python RCsimRPi5deploymentapp.py`.
2.  Open your browser and navigate to the address shown in the terminal (usually `http://127.0.0.1:5000`).
3.  Configure Connection details (IP, User, Password/Key).
4.  Select Project Source Directory.
5.  Configure Hardware and click "Start Deployment".
