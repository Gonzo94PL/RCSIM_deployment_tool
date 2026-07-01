# Dokumentacja Wymagań Sprzętowych i Specyfikacja Techniczna: MCS HAT

## 1. Wstęp i Cel Projektu
**MCS (Main Controller Shield)** to dedykowana karta rozszerzenia (HAT) dla minikomputera **Raspberry Pi 5**, pełniąca rolę sprzętowego koprocesora wejścia/wyjścia czasu rzeczywistego (real-time I/O coprocessor). Głównym celem modułu jest konwersja sygnałów sterujących USB HID (pochodzących np. z kierownic Logitech G29, joysticków przemysłowych czy aparatur w trybie symulatora) na profesjonalne modelarskie standardy transmisji radiowej i przewodowej RC o ekstremalnie niskich opóźnieniach i minimalnym jitterze (< 1 ms).

Sercem modułu MCS jest mikrokontroler **Raspberry Pi RP2350**, który dzięki dedykowanym blokom PIO (Programmable I/O) oraz dwurdzeniowej architekturze ARM Cortex-M33 / Hazard3 RISC-V gwarantuje bezkompromisową precyzję generowania sygnałów czasowych.

---

## 2. Format i Parametry Mechaniczne (Form Factor)
Płytka drukowana (PCB) modułu MCS została zaprojektowana w standardzie **Raspberry Pi 5 HAT (Hardware Attached on Top)**, co zapewnia idealną integrację mechaniczną i elektryczną z komputerem hosta.

* **Wymiary fizyczne:** Zgodne ze standardem RPi HAT (65.0 mm x 56.5 mm).
* **Otwory montażowe:** 4 otwory montażowe M2.5 rozmieszczone symetrycznie, umożliwiające stabilne skręcenie z Raspberry Pi 5 przy użyciu dystansów mosiężnych lub nylonowych (wysokość dystansów: 10-12 mm).
* **Złącze systemowe:** Żeńskie złącze kołkowe 2x20 pin (raster 2.54 mm, podwyższone), zapewniające dostęp do magistrali GPIO Raspberry Pi 5.
* **Wycięcie na wentylator:** Projekt uwzględnia strefę wolną od wysokich komponentów w centralnej części, umożliwiając poprawny montaż oficjalnego aktywnego chłodzenia Raspberry Pi 5 Active Cooler.

---

## 3. Architektura Mikrokontrolera (RP2350)
Moduł MCS posiada zintegrowany mikrokontroler **RP2350** (w obudowie QFN60/QFN80 lub jako gotowy moduł montażowy, np. kompatybilny z XIAO RP2350 footprintem).

* **Rdzenie:** Dual ARM Cortex-M33 lub Dual Hazard3 RISC-V (taktowanie do 150 MHz).
* **Pamięć SRAM:** 520 KB pamięci współdzielonej.
* **Pamięć Flash:** Zewnętrzna pamięć QSPI Flash (minimum 4 MB) do przechowywania firmware'u koprocesora.
* **Bloki PIO (Programmable I/O):** 3 bloki PIO (łącznie 12 maszyn stanowych), dedykowane do niezależnego, sprzętowego generowania sygnałów czasowych:
  - Maszyna PIO 1: Koder PPM (Pulse Position Modulation) o rozdzielczości sub-mikrosekundowej.
  - Maszyna PIO 2: Nadajnik/Odbiornik protokołu UART o wysokiej prędkości (CRSF: 420 000 bps, i-BUS: 115 200 bps).
* **Zabezpieczenie przed zawieszeniem:** Wewnętrzny Watchdog RP2350 automatycznie resetujący koprocesor w przypadku wykrycia błędu pętli głównej.

---

## 4. Specyfikacja Interfejsów i Złączy Wyjściowych

### 4.1. Porty AUX (Sygnały SBUS / i-BUS / CRSF)
Wyjścia pomocnicze AUX służą do bezpośredniego przesyłania cyfrowych protokołów szeregowych RC do odbiorników, nadajników zewnętrznych lub kontrolerów lotu.

* **Typ gniazda:** Żeńskie złącze typu **JR** (3-pinowe złącze kołkowe w obudowie zabezpieczającej przed odwrotnym wpięciem, raster 2.54 mm).
* **Wyprowadzenia pinów (Standard JR):**
  1. **S (Signal):** Wyjście sygnału cyfrowego UART TX / PIO TX.
  2. **V+ (Power):** Napięcie zasilania (wybór zworką: +5V z RPi lub +3.3V z LDO).
  3. **GND (Ground):** Masa wspólna.
* **Obsługiwane protokoły:**
  - **SBUS:** Transmisja szeregowa, 100 000 bps, 8E2, sygnał zanegowany sprzętowo (inwerter tranzystorowy na płytce lub wbudowany negator linii GPIO RP2350).
  - **i-BUS:** Transmisja szeregowa, 115 200 bps, 8N1, poziom logiczny 3.3V.
  - **CRSF (Crossfire / ELRS):** Transmisja dwukierunkowa o wysokiej prędkości (420 000 bps), poziom logiczny 3.3V.

### 4.2. Wyjście Analogowe PPM
Wyjście sygnału PPM (Pulse Position Modulation) dedykowane do połączenia przewodowego z gniazdem trenera (DSC) tradycyjnych aparatur modelarskich (np. FlySky, FrSky, Radiomaster).

* **Typ gniazda:** Złącze **MiniJack 3.5 mm** (żeńskie, montowane do druku).
* **Wyprowadzenie sygnału:**
  - **Tip (Czubek):** Sygnał PPM (Open-Drain).
  - **Sleeve (Tuleja):** Masa (GND).
* **Zabezpieczenie i architektura Open-Drain:**
  Sygnał wyjściowy PPM z RP2350 steruje bramką tranzystora MOSFET N-channel (np. 2N7002). Wyjście działa w trybie **Open-Drain** (otwarty dren). Stan niski zwiera pin wyjściowy MiniJack do masy, a stan wysoki wprowadza wyjście w stan wysokiej impedancji (Hi-Z). Konfiguracja ta chroni koprocesor i Raspberry Pi przed uszkodzeniem wywołanym napięciem podciągającym (Pull-up) występującym wewnątrz podłączonej aparatury RC (często sięgającym +5V lub napięcia baterii zasilającej aparaturę).

---

## 5. Zasilanie, Bezpieczeństwo i Integracja z RPi 5

### 5.1. Zasilanie
* **Główne źródło:** Magistrala 40-pin GPIO z Raspberry Pi 5 (+5V oraz +3.3V).
* **Stabilizator LDO:** Dodatkowy dedykowany stabilizator LDO +3.3V o niskim poziomie szumów (np. AP2112K-3.3) na płytce MCS, zasilający mikrokontroler RP2350 i eliminujący zakłócenia pochodzące z pracy procesora głównego RPi 5.
* **Filtrowanie:** Kondensatory filtrujące (decoupling) przy pinach zasilających RP2350 oraz przy złączach wyjściowych.

### 5.2. Izolacja i Zabezpieczenia Sprzętowe
* **Zabezpieczenie przed zwarciem:** Rezystory szeregowe (np. 220 Ohm) na liniach sygnałowych SBUS/i-BUS/CRSF w celu ograniczenia prądu w przypadku omyłkowego zwarcia pinu sygnałowego do zasilania lub masy.
* **Separacja zasilania:** Diody Schottky'ego zabezpieczające przed prądem wstecznym w przypadku jednoczesnego zasilania płytki MCS z portu USB-C mikrokontrolera (podczas flashowania/debugowania) oraz z Raspberry Pi 5.
* **Failsafe:** Układ pull-down na linii Enable koprocesora.

### 5.3. Komunikacja RPi 5 <-> RP2350
* **Interfejs szeregowy (Primary UART):** Połączenie pinów GPIO 14 (TXD0) i GPIO 15 (RXD0) Raspberry Pi 5 z odpowiednimi pinami UART RX/TX mikrokontrolera RP2350 w celu dwukierunkowej wymiany danych telemetrycznych i sterujących z prędkością do 921 600 bps.
* **Magistrala I2C:** Połączenie z szyną I2C Raspberry Pi 5 (GPIO 2 - SDA, GPIO 3 - SCL) w celu integracji z układem monitorowania zasilania i stanu baterii pakietu UPS (np. INA219).

---

## 6. Schemat blokowy połączeń sygnałowych (Draft)

```text
 ┌────────────────────────────────────────────────────────┐
 │                   Raspberry Pi 5                       │
 │  [Gospodarz - Obliczenia mikserów, WebUI, Telemetria]  │
 └──────────────────────────┬─────────────────────────────┘
                            │ (Złącze HAT 2x20 Pin)
        +5V / GND / I2C     │ UART (GPIO 14/15 - 921.6 kbps)
                            ▼
 ┌────────────────────────────────────────────────────────┐
 │ 🛡️ MCS BOARD (HAT)                                     │
 │                                                        │
 │  ┌──────────────────────────────────────────────────┐  │
 │  │        Koprocesor Real-Time: RP2350              │  │
 │  └──────┬────────────────────────────┬──────────────┘  │
 │         │ (UART TX - PIO)            │ (PPM GPIO)      │
 │         ▼                            ▼                 │
 │  ┌──────────────┐             ┌──────────────┐         │
 │  │ Konwerter/   │             │ Klucz MOSFET │         │
 │  │ Negator SBUS │             │ (Open-Drain) │         │
 │  └──────┬───────┘             └──────┬───────┘         │
 └─────────┼────────────────────────────┼─────────────────┘
           │                            │
           ▼ (Złącze JR)                ▼ (Gniazdo MiniJack 3.5mm)
     [ AUX Port ]                [ PPM Out ]
 (SBUS / i-BUS / CRSF)        (DSC Trainer Port)
```
