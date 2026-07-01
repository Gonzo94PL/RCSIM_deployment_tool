# Instrukcja obsługi MCS (Mobile Control Station / USB to RC Converter)

Niniejszy dokument opisuje instalację, konfigurację, uruchomienie oraz połączenia sprzętowe systemu **RCSIM MCS (Mobile Control Station)**. System ten służy do konwersji sygnałów z kontrolerów USB HID (np. joysticki, kontrolery gier) na cyfrowe protokoły modelarskie (CRSF, i-BUS) oraz analogowy sygnał PPM o wysokiej precyzji i minimalnym opóźnieniu (jitter < 1 ms) za pośrednictwem Raspberry Pi 5 oraz koprocesora ESP32.

---

## 1. Architektura Połączeń Sprzętowych (RPi 5 ↔ ESP32 ↔ Odbiornik/Nadajnik)

Aby system działał poprawnie, należy połączyć ze sobą Raspberry Pi 5, koprocesor ESP32 oraz opcjonalny moduł nadawczy (np. ELRS, Crossfire) lub gniazdo PPM w aparaturze.

### 🔌 Schemat Połączeń Pinów (Wiring Diagram)

Poniższa tabela przedstawia wymagane połączenia fizyczne:

| Urządzenie Źródłowe (RPi 5) | Urządzenie Docelowe (ESP32) | Typ Sygnału / Rola | Opis |
| :--- | :--- | :--- | :--- |
| **GND** (np. Pin 6) | **GND** | Wspólna masa | Bezwzględnie wymagana do prawidłowej transmisji szeregowej |
| **GPIO 14 (TXD0)** (Pin 8) | **GPIO 16 (RX2 / RX1)** | UART (CRSF / i-BUS) | Wysyłanie cyfrowych ramek z RPi 5 do ESP32 |
| **GPIO 15 (RXD0)** (Pin 10) | **GPIO 17 (TX2 / TX1)** | UART (Telemetria) | Odbiór logów i statusu z koprocesora ESP32 do RPi 5 |
| **USB Port** | **Micro-USB / USB-C** | UART USB / Zasilanie | Opcjonalne połączenie do monitorowania logów (`/dev/ttyUSB0`) oraz wgrywania oprogramowania |
| **5V / 3.3V** | **5V / VIN / 3V3** | Zasilanie koprocesora | Wspólne zasilanie (zaleca się zasilanie ESP32 ze stabilnego źródła 5V) |

> [!WARNING]
> Pamiętaj o połączeniu pinów masy (**GND**). Bez wspólnej masy komunikacja UART na wysokich prędkościach (np. 420 000 bps dla CRSF) będzie niestabilna lub w ogóle nie zostanie nawiązana.

### 📡 Wyjście Sygnału z ESP32 (do modułu nadawczego/odbiornika)

Koprocesor ESP32 generuje precyzyjny sygnał PPM na dedykowanym pinie:

| Pin ESP32 | Urządzenie Zewnętrzne | Typ Sygnału | Opis |
| :--- | :--- | :--- | :--- |
| **GPIO 14** (klasyczne ESP32)<br>**GPIO 13** (tryb ESP32-CAM) | Wejście PPM (np. moduł ELRS, gniazdo Trainer) | **PPM (Pulse Position Modulation)** | Sygnał wyjściowy 8 kanałów (ramka 22.5 ms, impuls 300 µs) |
| **GND** | Masa modułu nadawczego / aparatury | Masa sygnałowa | Odniesienie dla sygnału PPM |

---

## 2. Architektura Przepływu Danych

```text
 ┌──────────────────────┐      ┌─────────────────────────┐      ┌────────────────────────┐
 │   Kontroler USB HID  │ ───> │  Skaner Linux (evdev)   │ ───> │ Silnik Mikserów & Expo │
 │   (Joystick)         │      │    [Wątki odbiorcze]    │      │  [Zastosowanie mapowań]│
 └──────────────────────┘      └─────────────────────────┘      └────────────────────────┘
                                                                             │
 ┌──────────────────────┐      ┌─────────────────────────┐                   ▼
 │ Przekaźnik modelarski│ <─── │   Koprocesor ESP32      │ <─── ┌────────────────────────┐
 │  (PPM / CRSF / ELRS) │      │ [Hardware Timer Output] │      │ Nadawca Serial (UART)  │
 └──────────────────────┘      └─────────────────────────┘      │    [Ramki cyfrowe]     │
                                                                └────────────────────────┘
```

1. **Raspberry Pi 5** odpytuje kontroler USB HID za pomocą biblioteki `evdev` (wątki w czasie rzeczywistym).
2. Silnik mikserów przetwarza wychylenia, nakłada krzywe nieliniowe (**Expo**), rewersy oraz parametry **Sub-Trim**.
3. RPi 5 generuje ramki cyfrowe protokołu **TBS Crossfire (CRSF)** (420 000 bps) lub **FlySky i-BUS** (115 200 bps) i wysyła je przez port szeregowy (`/dev/ttyAMA0`).
4. **ESP32** odbiera ramki, dekoduje je i za pomocą sprzętowego timera generuje stabilny sygnał **PPM** na pinie **GPIO 14** (lub **GPIO 13** dla ESP32-CAM).

---

## 3. Instalacja i Konfiguracja na Raspberry Pi 5

Instalacja systemu MCS odbywa się automatycznie przy pomocy dostarczonych skryptów.

### Krok 1: Klonowanie i Przygotowanie
Zaloguj się na Raspberry Pi i przejdź do katalogu projektu:
```bash
chmod +x scripts/*.sh
```

### Krok 2: Instalacja Usług
Uruchom instalator usług systemowych z uprawnieniami administratora:
```bash
sudo ./scripts/install_services.sh
```
Skrypt ten automatycznie:
1. Skopiuje kod aplikacji do bezpiecznego katalogu `/opt/usb_rc_converter`.
2. Stworzy wirtualne środowisko Pythona (`venv`) i zainstaluje zależności.
3. Przypisze uprawnienia do portów szeregowych i magistrali I2C (dla monitora baterii).
4. Zarejestruje i uruchomi usługi systemowe w `systemd` z priorytetem czasu rzeczywistego (RT: `CPUSchedulingPolicy=fifo`, `CPUAffinity=3`).

---

## 4. Oprogramowanie Koprocesora (ESP32)

Kod koprocesora znajduje się w folderze `firmware/co_processor/`.

### Konfiguracja Pinów w ESP32:
* **RX UART (CRSF):** GPIO 16 (dla klasycznego ESP32) lub GPIO 3 / RX0 (dla ESP32-CAM podłączonego współdzielonym portem UART0)
* **TX UART (Diagnostyka):** GPIO 17 (dla klasycznego ESP32) lub GPIO 1 / TX0 (dla ESP32-CAM)
* **Wyjście PPM:** GPIO 14 (dla klasycznego ESP32) lub **GPIO 13** (dla ESP32-CAM ze względu na konflikty sprzętowe z kartą MicroSD na GPIO 14)

### Wgrywanie oprogramowania i Resetowanie:
1. **Przez Arduino IDE:** Otwórz plik `firmware/co_processor/co_processor.ino`, wybierz właściwy profil płytki (np. **ESP32 Dev Module** lub **AI Thinker ESP32-CAM**) i wgraj oprogramowanie.
2. **Automatycznie przez Web UI:** W panelu administracyjnym MCS (przeglądarka) w zakładce **Baza ESP32 / OTA** dostępna jest funkcja aktualizacji oprogramowania koprocesora.

> [!IMPORTANT]
> **Procedura Auto-Reset (Wgrywanie OTA):**
> Podczas flashowania przez Web UI, system automatycznie steruje stanem linii BOOT (RPi GPIO 24 -> ESP32 GPIO 0).
> 1. Web UI poprosi o krótki reset ESP32 (kliknięcie przycisku RESET na płytce) przed rozpoczęciem wgrywania.
> 2. Po zakończeniu flashowania (osiągnięciu 100%), **należy ponownie krótko nacisnąć fizyczny przycisk RESET na płytce ESP32**, aby mikrokontroler wyszedł z trybu bootloadera i uruchomił nowo wgrany program. Bez tego kroku ESP32 pozostanie zawieszone i nie zacznie generować sygnału PPM.

---

## 5. Panel Administracyjny (Web UI)

System MCS uruchamia nowoczesny interfejs webowy dostępny pod portem `:8080`.

* **Dostęp lokalny:** `http://localhost:8080`
* **Dostęp na polu (Hotspot AP):**
  Aby zmienić ustawienia na smartfonie bezpośrednio na lotnisku (jednocześnie zachowując połączenie klienckie Wi-Fi skonfigurowane w RPi Imager), uruchom skrypt punktu dostępowego na RPi:
  ```bash
  sudo /opt/usb_rc_converter/scripts/setup_ap.sh
  ```
  Następnie połącz się z siecią Wi-Fi **RCSIM_MCS** (hasło: `RCSIM_GORIDE`) i otwórz w przeglądarce adres:
  `http://10.42.0.1:8080` (dla NetworkManager) lub `http://192.168.4.1:8080` (dla hostapd).

### Główne funkcje Web UI:
1. **Wizualizacja kanałów:** Podgląd na żywo wychyleń wszystkich 16 kanałów aparatury.
2. **Dynamiczny Edytor Profili:** Zmiana przypisania osi (ABS_X, ABS_Y itp.), rewersów, limitów (Min/Max) oraz Expo bezpośrednio z poziomu przeglądarki bez restartu systemu.
3. **Monitor Telemetrii Zasilania:** Wyświetlanie napięcia i poziomu naładowania akumulatora zasilającego (obsługa nakładek Waveshare UPS Hat po I2C).
4. **Logi Koprocesora:** Podgląd na żywo diagnostyki wysyłanej z ESP32.

---

## 6. Przewodnik: Integracja ESP32 i Generowanie Sygnałów RC (PPM / i-BUS / CRSF / s-BUS)

### 🔌 1. Szczegółowe podłączenie ESP32 do Raspberry Pi 5
Zaleca się równoległe podłączenie GPIO (do przesyłu niskopoziomowych danych sterujących o niskim jitterze) oraz USB (do wgrywania oprogramowania i diagnostyki):

* **Połączenie magistrali GPIO**:
  * **RPi TXD0 (Pin 8 / GPIO 14)** ───> **ESP32 RX2 (Pin 16 / RX2)** (Cyfrowe ramki sterujące CRSF)
  * **RPi RXD0 (Pin 10 / GPIO 15)** <─── **ESP32 TX2 (Pin 17 / TX2)** (Logi diagnostyczne i status z ESP32)
  * **RPi GND (Pin 6)** <───> **ESP32 GND** (Wspólna masa – **bezwzględnie wymagana** dla stabilności!)
* **Połączenie USB**:
  * Połącz wolny port USB w Raspberry Pi 5 z gniazdem Micro-USB / USB-C na płytce ESP32 przy użyciu sprawnego kabla do transmisji danych.

### 💾 2. Wgrywanie oprogramowania na ESP32
Firmware koprocesora znajduje się w `firmware/co_processor/co_processor.ino`.

* **Metoda A (Zalecana - Przez Web UI)**:
  1. Podłącz ESP32 kablem USB do Raspberry Pi.
  2. Otwórz panel Web UI w przeglądarce (`http://IP_MALINY:8080`).
  3. W sekcji diagnostycznej ESP32 kliknij przycisk **"Wgraj firmware.bin"**. System automatycznie zlokalizuje port szeregowy `/dev/ttyUSB0` i wgra kod za pomocą narzędzia `esptool`.
* **Metoda B (Ręczna - Przez Arduino IDE)**:
  1. Podłącz ESP32 bezpośrednio do komputera.
  2. Otwórz plik `co_processor.ino` w Arduino IDE.
  3. Zainstaluj pakiet wsparcia dla płytek `esp32` (Espressif).
  4. Wybierz płytkę **ESP32 Dev Module**, wybierz właściwy port szeregowy COM i kliknij **Upload**.

### 📡 3. Konfiguracja i Generowanie Sygnałów Wyjściowych

#### A. Sygnał PPM (Analogowy)
Sygnał PPM jest generowany **za pomocą koprocesora ESP32**:
1. W Web UI (lub pliku `config.json`) ustaw parametr `"output_protocol": "crsf"`.
2. Raspberry Pi zacznie generować ramki cyfrowe CRSF i wysyłać je przez UART do ESP32.
3. ESP32 odbierze ramki i dzięki wbudowanemu sprzętowemu timerowi wygeneruje stabilny, pozbawiony jitteru sygnał PPM na pinie **GPIO 14** (lub **GPIO 13** na ESP32-CAM).
4. Podłącz pin **GPIO 14 / GPIO 13 w ESP32** oraz **GND** do wejścia PPM Twojego odbiornika lub modułu nadawczego.

#### B. Sygnał cyfrowy i-BUS (FlySky)
Sygnał i-BUS jest generowany **bezpośrednio przez Raspberry Pi 5** (ESP32 nie jest używane):
1. W Web UI lub `config.json` ustaw parametr `"output_protocol": "ibus"`.
2. Podłącz pin **TXD0 (Pin 8 / GPIO 14) w Raspberry Pi** bezpośrednio do wejścia RX i-BUS modułu radiowego (prędkość transmisji wynosi 115 200 bps).

#### C. Sygnał cyfrowy CRSF (TBS Crossfire / ExpressLRS)
Sygnał CRSF jest generowany **bezpośrednio przez Raspberry Pi 5** (ESP32 nie jest używane):
1. W Web UI lub `config.json` ustaw parametr `"output_protocol": "crsf"`.
2. Podłącz pin **TXD0 (Pin 8 / GPIO 14) w Raspberry Pi** bezpośrednio do wejścia RX modułu nadawczego kompatybilnego z CRSF (np. moduł JR ExpressLRS). Transmisja odbywa się z prędkością 420 000 bps.

#### D. Ograniczenie dla sygnału s-BUS (Futaba / FrSky)
Protokół s-BUS wymaga sprzętowej inwersji stanów logicznych. Standardowe porty szeregowe Raspberry Pi oraz ESP32 pracują w logice niezanegowanej (3.3V). Bez zastosowania zewnętrznego inwertera sprzętowego (np. prostego układu z tranzystorem NPN), bezpośrednie podłączenie pinu TX do odbiornika s-BUS nie będzie działać. W celu uproszczenia konstrukcji zaleca się korzystanie z protokołów **CRSF** lub **i-BUS**, które nie wymagają inwersji sygnału.

---

## 7. Integracja mikrokontrolera STM32F103C8T6 (Blue Pill)

Przejście na mikrokontroler **STM32F103C8T6 (Blue Pill)** w połączeniu z **Raspberry Pi 5** pozwala na precyzyjne generowanie wielu protokołów RC (PPM, iBUS, SBUS, CRSF) w czasie rzeczywistym z minimalnym opóźnieniem.

### 🔌 Schemat Połączeń Fizycznych (RPi 5 ↔ STM32F103)

| Raspberry Pi 5 (GPIO) | STM32F103C8T6 (Blue Pill) | Funkcja / Opis |
| :--- | :--- | :--- |
| **Pin 1 (3.3V)** | **3.3V** | Zasilanie mikrokontrolera |
| **Pin 6 (GND)** | **GND** | Wspólna masa sygnałowa (bezwzględnie wymagana) |
| **Pin 18 (GPIO 24)** | **SWCLK** | Interfejs programowania SWD (SWCLK) |
| **Pin 22 (GPIO 25)** | **SWDIO** | Interfejs programowania SWD (SWDIO) |
| **Pin 8 (TXD0 / GPIO 14)** | **PA3 (RX2)** | Odbiór danych sterujących z Raspberry Pi 5 (115200 bps) |

### 📡 Wyjścia Sygnałowe z STM32 do aparatury/odbiornika

W zależności od wybranego trybu protokołu, wyjście sygnału RC jest realizowane na następujących pinach STM32:

| Wyjście protokołu | Pin STM32F103 | Opis / Parametry elektryczne |
| :--- | :--- | :--- |
| **Tryb 1 (PPM)** | **PA0** (Timer 2 CH1) | Ramka PPM (22.5 ms, impulsy 300 us, 1000-2000 us) podłączana do DSC Port w aparaturze (Jack 3.5mm). |
| **Tryb 2 (iBUS)** | **PA9** (TX1) | Nieodwrócony sygnał cyfrowy FlySky iBUS (115200 bps, 8N1). |
| **Tryb 3 (SBUS)** | **PA9** (TX1) | **Brak sprzętowej inwersji:** Oprogramowanie realizuje programowy, emulowany UART (bit-banging) z odwróconą logiką (100000 bps, 8E2). Dzięki temu można bezpośrednio podłączyć pin `PA9` do aparatury MT12 (port AUX) lub klasycznego odbiornika SBUS bez zewnętrznego tranzystora NPN. |
| **Tryb 4 (CRSF)** | **PA9** (TX1) | Sygnał cyfrowy TBS Crossfire (400000 bps, 8N1) z sumą kontrolną CRC8. |

### 🛠️ Programowanie przez OpenOCD na Raspberry Pi 5

Ze względu na nową architekturę układu wejścia/wyjścia **RP1** w Raspberry Pi 5, klasyczne metody bezpośredniego dostępu do GPIO nie działają. Programowanie STM32 z poziomu Raspberry Pi realizowane jest za pomocą narzędzia OpenOCD z nowoczesnym sterownikiem **linuxgpiod** za pośrednictwem pętli GPIO:

1. Podłącz linie SWD zgodnie z tabelą połączeń fizycznych.
2. Upewnij się, że posiadasz odpowiedni plik konfiguracyjny `openocd.cfg` ze zdefiniowanym adapterem:
   ```text
   adapter driver linuxgpiod
   linuxgpiod gpiochip 4
   linuxgpiod swd_nums 24 25
   transport select swd
   source [find target/stm32f1x.cfg]
   ```
3. Wykonaj wgranie pliku binarnego za pomocą polecenia:
   ```bash
   openocd -f firmware/bluepill/openocd.cfg -c "program firmware.bin verify reset exit"
   ```

---

## 8. Funkcje Bezpieczeństwa (Failsafe) oraz Asysta FFB / Soft-lock

System MCS posiada zaawansowane mechanizmy zabezpieczeń przed utratą sygnału oraz funkcje wsparcia dla kierownic i joysticków z Force Feedback.

### 🛡️ Indywidualne ustawienia Failsafe (dla każdego kanału)
Dla każdego zmapowanego kanału sterowania operator może skonfigurować indywidualne zachowanie w przypadku awarii (np. odłączenie kontrolera USB, utrata zasilania):
* **Center (Środkowanie):** Kanał zostanie automatycznie ustawiony w bezpiecznej pozycji środkowej (`1500 us + sub_trim`). Tryb ten jest zalecany dla kanału skrętu (kierownicy).
* **Hold (Przytrzymanie):** System zatrzyma ostatnią poprawnie odebraną pozycję drążka.
* **Custom (Niestandardowy):** Pozwala zdefiniować dokładną wartość sygnału w mikrosekundach (np. `1000 us` dla kanału przepustnicy/gazu jako wymuszenie hamowania lub `1500 us` jako neutral).

*Wątek odczytu wejść (`EvdevReader`) automatycznie aplikuje procedurę failsafe w pętli obsługi wyjątków przy nagłym rozłączeniu urządzenia oraz podczas czyszczenia wątku przy wyłączaniu serwera.*

### 🎡 Auto-Center FFB & Soft-lock (Dla kierownic/joysticków)
W zakładce *Definicje* Web UI można aktywować asystę sprzężenia zwrotnego dla podłączonych kontrolerów:
* **Auto-Center (Centrowanie sprzętowe):** Włącza sprężynę powrotną FFB o określonej sile (0–100%).
* **Programowy i Sprzętowy Soft-lock:** 
  Dla kierownic (np. Logitech G29/G27/G920) system wysyła komendy zapisu do interfejsu `sysfs` w celu dopasowania fizycznego kąta skrętu (np. do 360 lub 540 stopni zamiast pełnych 900 stopni). 
  Jeśli urządzenie obsługuje sprzężenie zwrotne siłowe (FFB), system generuje na nim sprzętowy efekt blokady `FF_SPRING` poza wyznaczonym kątem skrętu. W przypadku braku sprzętowej obsługi FFB, system automatycznie stosuje skalowanie programowe (software fallback scaling), co gwarantuje pełny zakres wychylenia wirtualnego kanału skrętu (Aileron/Rudder) przy fizycznym ograniczeniu ruchu.



