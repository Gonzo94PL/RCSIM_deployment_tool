# Wytyczne i Instrukcje dla Agenta AI — Moduł RCSIM MCS

Ten dokument stanowi instrukcję dla agentów AI (takich jak Antigravity/Codex) pracujących nad rozwojem projektu **RCSIM MCS (Mobile Control Station)**. Opisuje architekturę systemu, przeznaczenie modułu oraz krytyczne zasady pracy.

---

## 1. O Module RCSIM MCS

**RCSIM MCS** (Mobile Control Station) to system zainstalowany na **Raspberry Pi 5** (współpracujący z koprocesorem ESP32, STM32 lub RP2350), który pobiera sygnały z dowolnych urządzeń USB HID oraz kontrolerów bezprzewodowych **Bluetooth** (np. pady Xbox Series X/S, Sony DualSense / DualShock) i konwertuje je w czasie rzeczywistym na sygnały modelarskie RC o bardzo niskiej latencji (Jitter < 1ms):
*   **TBS Crossfire / ExpressLRS (CRSF)** (cyfrowy, 420 000 bps)
*   **FlySky i-BUS** (cyfrowy, 115 200 bps)
*   **PPM (Pulse Position Modulation)** (analogowy, generowany przez koprocesor)

System posiada interfejs Web UI serwowany na porcie `:8080`, który umożliwia pełną konfigurację mikserów, limitów (EPA), nieliniowych krzywych (Expo), a także parowanie urządzeń Bluetooth i programowanie koprocesora przez OTA.

---

## 2. Krytyczne Zasady Kompilacji i Wdrożeń (Złota Reguła)

Gdy modyfikujesz frontend Next.js (pliki w `/app`, `/components`, `/lib` itp.):

1.  **Kompilacja statyczna Next.js**:
    Projekt Next.js jest skonfigurowany pod eksport statyczny (`output: 'export'`). Uruchomienie budowania:
    ```bash
    npm run build
    ```
    generuje spakowane pliki HTML/JS/CSS w katalogu `out/`.

2.  **Serwowanie plików przez Backend (Złota Reguła)**:
    Serwer FastAPI w `src/api/server.py` serwuje pliki statyczne z katalogu **`src/ui/web/`**, a nie bezpośrednio z `out/`. Narzędzie wdrożeniowe (RCSIM Deployment Tool) pakuje i wysyła na RPi 5 pliki właśnie z `src/ui/web/`.
    
    **BEZWZGLĘDNA ZASADA:** Po każdej kompilacji produkcyjnej frontendu, musisz skopiować zawartość katalogu `out/` do `src/ui/web/`.
    
    *   **Windows (PowerShell):**
        ```powershell
        Copy-Item -Path "out/*" -Destination "src/ui/web/" -Recurse -Force
        ```
    *   **Linux (Bash):**
        ```bash
        cp -r out/* src/ui/web/
        ```
    Bez tego kroku wdrożenie na Raspberry Pi nie odzwierciedli żadnych zmian wprowadzonych w kodzie React/Next.js!

---

## 3. Architektura Kodu i Wejścia/Wyjścia

*   **Zarządzanie Bluetooth**:
    Za parowanie i łączenie padów odpowiada `src/hardware/bluetooth_manager.py`. Na Raspberry Pi komunikuje się bezpośrednio z daemonem systemowym poprzez CLI `bluetoothctl`. Na systemach deweloperskich innych niż Linux (np. Windows) manager automatycznie przełącza się w tryb emulatora (mock) i zwraca fikcyjne urządzenia dla ułatwienia debugowania.
*   **Odczyt evdev (Linux)**:
    Odczyt ruchu osi i klawiszy na RPi realizuje `src/input/evdev_reader.py`.
*   **Zapis Konfiguracji**:
    Ustawienia są zapisywane do pliku `config/config.json`. Pola konfiguracji profili (np. przyciski `drive_mode_btn`, `cruise_btn` oraz `arm_btn`) muszą być spójnie przekazywane między interfejsem React (`app/page.tsx` oraz `components/ProfileEditor.tsx`) a backendem Pythona.
*   **Uzbrajanie (Arming)**:
    Wyłączenie nadawania sygnału modelarskiego (Disarmed) reprezentowane jest w stanowym obiekcie `RCState` jako `paused = True`. Za zmianę stanu odpowiada przycisk w nagłówku Web UI, globalny skrót klawiszowy **SPACJA** (Emergency Stop) oraz przycisk przypisany na padzie (obsługiwany przez mapowanie `arm_btn`).

---

## 4. Ostatnio Wdrożone Funkcje i Wskazówki (Aktualizacja)

Podczas ostatnich prac do modułu MCS zostały wdrożone następujące funkcjonalności:

### A. Obsługa Protokołu NOMAD (ExpressLRS TX Direct)
*   **Zasada działania:** Wybór protokołu `NOMAD` w konfiguracji powoduje ominięcie koprocesora (`BridgeOutput`) i bezpośrednie przesyłanie surowych ramek CRSF przez port USB/szeregowy RPi 5 z prędkością **420 000 bps** (klasa `CRSFOutput`).
*   **Zapobieganie resetom:** W klasie bazowej `BaseOutput` wyłączone zostały linie sterujące `DTR` oraz `RTS` portu szeregowego. Jest to krytyczne dla modułów nadawczych opartych o ESP32 (jak RadioMaster Nomad TX), które w przeciwnym razie resetowałyby się podczas otwierania portu szeregowego.

### B. Tryb Jasny (Light Mode)
*   **Mechanizm:** Zaimplementowano dynamiczne przełączanie motywu (`theme === 'light' ? 'light-theme' : ''`) kontrolowane przez przycisk w nagłówku strony. Stan motywu jest zapisywany w `localStorage` pod kluczem `rcsim_theme`.
*   **Stylizacja:** Nadpisania kolorystyczne (dla jasnego tła bieli/szarości) znajdują się na końcu pliku `app/globals.css` pod selektorem `.light-theme`.

### C. Współpraca z XIAO RP2350 i RadioMaster MT12 (SBUS Trainer)
*   **Poprawne pakowanie bitowe SBUS:** Naprawiono strukturę pakowania bitowego (11 bitów na kanał) dla kanałów od 9 do 16. Wcześniej powielała ona niepoprawnie układ CRSF.
*   **Logika inwersji (EdgeTX / MT12):** Porty wejściowe AUX (np. AUX1 w RadioMaster MT12) pracujące pod systemem EdgeTX jako wejście Trainer Master/SBUS oczekują fizycznie odwróconego sygnału (standard SBUS, gdzie stan spoczynkowy to logiczne `0` / LOW). Koprocesor XIAO RP2350 realizuje to sprzętowo poprzez wywołanie `RC_SerialOut->setInvertTX(true)` przed inicjalizacją portu PIO UART (`begin(100000, SERIAL_8E2)`).
*   **Automatyczna aktualizacja (Hands-Free Flash):** Aktualizacja oprogramowania XIAO RP2350 odbywa się zdalnie na RPi 5 poprzez:
    1. Zatrzymanie usług `usb_rc` w celu zwolnienia portu `/dev/ttyACM0`.
    2. Otwarcie portu na prędkości `1200` bps i jego zamknięcie, co wymusza przejście mikrokontrolera w tryb bootloadera (BOOTSEL).
    3. Wgranie pliku `firmware.uf2` komendą `picotool load -f -x`.
    4. Ponowne uruchomienie usług.

### D. Sygnalizacja trybu pracy za pomocą diody LED RGB (WS2812)
*   **Wbudowana dioda RGB:** Płytka Seeed Studio XIAO RP2350 posiada wbudowaną diodę LED WS2812 podłączoną do pinu **GPIO 22**.
*   **Kolory trybów pracy:** Dioda świeci ciągłym światłem o kolorze odpowiadającym aktywnemu protokołowi:
    - **PPM**: 🔴 Czerwony
    - **iBUS**: 🟢 Zielony
    - **SBUS**: 🔵 Niebieski
    - **CRSF**: 🟣 Fioletowy / Magenta
*   **Wskaźnik Failsafe:** W przypadku braku ramek z RPi5 przez ponad 500 ms, dioda RGB miga szybko na czerwono (częstotliwość 5 Hz), ułatwiając szybką diagnostykę sprzętową bez konieczności analizy logów systemowych.

### E. Wielojęzyczność (i18n) i Wybór Języka w GUI
*   **System tłumaczeń:** Zaimplementowano centralny słownik tłumaczeń w pliku `lib/translations.ts` obsługujący języki polski (`pl`) i angielski (`en`).
*   **Hook `useTranslation`:** Użycie niestandardowego hooka w `hooks/useTranslation.ts` zapewnia reaktywne pobieranie tłumaczeń w komponentach klienckich oraz fallback na język angielski.
*   **Persystencja:** Wybrany język zapisywany jest w `localStorage` przeglądarki oraz synchronizowany z konfiguracją backendu (`config.json`, klucz `"language"`).
*   **Wybór w GUI:** Do nagłówka aplikacji (`app/page.tsx`) dodano selektor języka (`<select>`), który automatycznie przełącza interfejs bez potrzeby pełnego przeładowania strony.
