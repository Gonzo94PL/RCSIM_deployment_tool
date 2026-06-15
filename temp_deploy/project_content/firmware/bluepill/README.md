# Oprogramowanie Układowe Blue Pill (STM32F103C8T6) — Bridge USB/UART do RC

Oprogramowanie układowe (firmware) przeznaczone dla mikrokontrolera **STM32F103C8T6** (popularny *Blue Pill*), napisane w środowisku **PlatformIO** z użyciem rdzenia **Arduino (STM32Duino)**. 

Pełni ono funkcję dedykowanego mostka (bridge) konwertującego komendy przesyłane z komputera pokładowego Raspberry Pi 5 na standardowe sygnały sterujące modelami RC (PPM, iBUS, SBUS, CRSF).

---

## 🛠️ Funkcjonalność

- **Wieloprotokołowość**: dynamiczne przełączanie trybu wyjściowego w locie:
  - **PPM (Pulse Position Modulation)**: 8 kanałów, generowanie sprzętowe na pinie `PA0` przy użyciu Timera 2 (ujemne impulsy synchronizujące).
  - **iBUS (Flysky)**: Szeregowy protokół dwukierunkowy (skonfigurowany jako jednokierunkowy wyjściowy), 115200 bps, 8N1 na porcie `USART1` (`PA9`).
  - **SBUS (Futaba/FrSky)**: Szeregowy protokół 100000 bps, 8E2 z odwróconą logiką. Zawiera programową emulację bit-banging na pinie `PA9`, eliminując potrzebę stosowania zewnętrznego inwertera sprzętowego dla płytek Blue Pill.
  - **CRSF (TBS Crossfire)**: Szybki protokół szeregowy 400000 bps, 8N1 na porcie `USART1` (`PA9`) z sumą kontrolną CRC8.
- **Wbudowane Zabezpieczenie (Failsafe)**: automatyczne wykrywanie utraty komunikacji z Raspberry Pi 5. Jeśli w ciągu **500 ms** nie zostanie odebrana poprawna ramka, firmware przechodzi w stan Failsafe:
  - Wyłącza generowanie PPM (stan wysoki na `PA0`).
  - Szybko miga wbudowaną diodą LED (`PC13`).
- **Sygnalizacja Stanu LED (`PC13`)**:
  - *Powolne miganie (1 Hz)*: Prawidłowa komunikacja z RPi 5.
  - *Szybkie miganie (5 Hz)*: Brak komunikacji / aktywny tryb Failsafe.

---

## 🔌 Schemat Połączeń (Wiring)

| Pin Blue Pill | Funkcja | Połączenie z Raspberry Pi 5 / Odbiornikiem | Uwagi |
| :--- | :--- | :--- | :--- |
| **GND** | Masa | GND (RPi 5) & GND (ESC/Odbiornik) | Wspólna masa systemu |
| **5V** / **3.3V** | Zasilanie | Wyjście zasilania z RPi 5 / BEC | Zasilanie mikrokontrolera |
| **PA3 (RX2)** | Wejście USART2 | GPIO 14 (TXD) (RPi 5) | Odbiór ramek sterujących z RPi |
| **PA2 (TX2)** | Wyjście USART2 | GPIO 15 (RXD) (RPi 5) | Komunikacja zwrotna (opcjonalna) |
| **PA0** | Wyjście PPM | Wejście PPM w module RC / ESC | Generowane sprzętowo za pomocą TIM2 |
| **PA9 (TX1)** | Wyjście Serial RC | Wejście iBUS / SBUS / CRSF w odbiorniku | Domyślne wyjście dla protokołów szeregowych |

*Uwaga: W przypadku korzystania ze standardowego SBUS bezpośrednio z USART1 wymagany jest zewnętrzny inwerter sygnału. Domyślna konfiguracja w kodzie korzysta z programowej emulacji na pinie `PA9` z odwróconą logiką, dzięki czemu można połączyć sygnał bezpośrednio.*

---

## 📊 Format Ramki Komunikacyjnej (RPi 5 ➡️ Blue Pill)

Komunikacja z RPi 5 odbywa się po porcie szeregowym USART2 z prędkością **115200 bps**. Ramka ma stałą długość **19 bajtów**:

```
[0xAA] [Tryb] [CH1_H] [CH1_L] ... [CH8_H] [CH8_L] [Checksum XOR]
```

- **Bajt 0**: Bajt startu (`0xAA`)
- **Bajt 1**: Tryb pracy / Protokół wyjściowy:
  - `1` = PPM
  - `2` = iBUS
  - `3` = SBUS
  - `4` = CRSF
- **Bajty 2–17**: Wartości 8 kanałów RC (każdy kanał jako 16-bitowa liczba typu Big-Endian w zakresie 1000–2000 ms).
- **Bajt 18**: Suma kontrolna XOR obliczana na podstawie bajtów od 1 do 17.

---

## 🚀 Kompilacja i Wgrywanie

Projekt jest skonfigurowany pod narzędzie **PlatformIO**. 

### 1. Wgrywanie lokalne (z komputera PC)
Jeśli podłączasz Blue Pill przez programator ST-Link do komputera PC, zmień `upload_protocol` w pliku `platformio.ini` na `stlink` i uruchom:
```bash
pio run --target upload
```

### 2. Wgrywanie bezpośrednio z Raspberry Pi 5 (SWD GPIO)
Plik konfiguracji `openocd.cfg` jest przystosowany do wgrywania oprogramowania bezpośrednio z linii GPIO Raspberry Pi 5 za pomocą magistrali SWD (wykorzystując nowoczesny sterownik `linuxgpiod` obsługujący kontroler RP1 w RPi 5).

**Połączenie SWD RPi 5 ➡️ Blue Pill:**
- **GPIO 24** ➡️ SWCLK
- **GPIO 25** ➡️ SWDIO
- **GND** ➡️ GND

**Komenda wgrania na RPi 5:**
```bash
openocd -f firmware/bluepill/openocd.cfg -c "program .pio/build/bluepill_f103c8/firmware.elf verify reset exit"
```
*(Upewnij się, że ścieżka do pliku `.elf`/`.bin` jest prawidłowa po przeprowadzeniu kompilacji `pio run`).*
