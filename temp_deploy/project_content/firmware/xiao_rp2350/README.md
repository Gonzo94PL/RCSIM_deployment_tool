# Oprogramowanie Układowe Seeed Studio XIAO RP2350 — Bridge USB do RC

Oprogramowanie układowe (firmware) przeznaczone dla nowoczesnej mikropłytki **Seeed Studio XIAO RP2350** opartej na mikrokontrolerze **RP2350** (ARM Cortex-M33). Projekt został zaimplementowany w środowisku **PlatformIO** z użyciem dedykowanego rdzenia **Earle Philhower (arduino-pico)**.

Pełni rolę wysoce stabilnego, sprzętowego mostka (bridge) konwertującego sygnały sterujące z Raspberry Pi 5 na standardy RC. Dzięki dwurdzeniowej architekturze RP2350, parsowanie wejścia oraz krytyczne czasowo generowanie sygnałów wyjściowych są w pełni odseparowane.

---

## 🏗️ Architektura Dwurdzeniowa

- **Rdzeń 0 (Core 0)**:
  - Odbiór i parsowanie ramek danych przez natywny port USB CDC (`/dev/ttyACM0`).
  - Obsługa watchdoga i detekcja trybu awaryjnego (Failsafe).
  - Przekazywanie stanów i żądań rekonfiguracji do Rdzenia 1.
- **Rdzeń 1 (Core 1)**:
  - Generowanie sygnałów wyjściowych RC o precyzyjnych zależnościach czasowych.
  - Generowanie sygnału **PPM** przy użyciu precyzyjnych alarmów sprzętowych SDK (`alarm_pool`).
  - Generowanie sygnałów szeregowych za pomocą programowalnych maszyn stanowych **PIO (SerialPIO)**, co zapewnia brak jitteru.

---

## 🛠️ Funkcjonalność i Obsługiwane Protokoły

- **Wieloprotokołowość**: dynamiczne przełączanie wyjścia w locie:
  - **PPM (Pulse Position Modulation)**: 8 kanałów, generowanie sprzętowe na pinie **D7 (GPIO 1)** (pin w pełni tolerujący 5V FT).
  - **iBUS (Flysky)**: 115200 bps, 8N1 na pinie **D8 (GPIO 2)** (pin w pełni tolerujący 5V FT).
  - **SBUS (Futaba/FrSky)**: 100000 bps, 8E2 na pinie **D8 (GPIO 2)**. Dzięki rejestrom GPIO mikrokontrolera RP2350 inwersja sygnału odbywa się sprzętowo (`gpio_set_outover`) na poziomie pinu, co **eliminuje potrzebę stosowania zewnętrznego inwertera logicznego**.
  - **CRSF (TBS Crossfire)**: 420000 bps, 8N1 na pinie **D8 (GPIO 2)** z sumą kontrolną CRC8.
- **Wbudowane Zabezpieczenie (Failsafe)**: automatyczne wykrywanie utraty łączności z RPi 5. Brak poprawnej ramki przez **500 ms** skutkuje:
  - Wyłączeniem generowania PPM (stan wysoki na pinie).
  - Wstrzymaniem wysyłania ramek szeregowych.
  - Szybszym miganiem wbudowanej diody LED (`LED_BUILTIN`).
- **Sygnalizacja Stanu LED**:
  - *Spokojne miganie (1s świecenia / 1s wygaszenia)*: Stan prawidłowy.
  - *Szybkie miganie (100ms świecenia / 100ms wygaszenia)*: Stan awaryjny (Failsafe).

---

## 🔌 Schemat Połączeń (Wiring)

| Pin XIAO RP2350 | Funkcja | Połączenie z urządzeniem docelowym | Uwagi |
| :--- | :--- | :--- | :--- |
| **GND** | Wspólna masa | GND (RPi 5) / GND (Odbiornik RC) | Niezbędna do poprawnej transmisji |
| **5V** | Zasilanie wejściowe | Port USB-C z Raspberry Pi 5 | Zasilanie całego układu mostka |
| **D7 (GPIO 1)** | Wyjście PPM | Port trenera (DSC) / Wejście PPM odbiornika | Generowany sprzętowo za pomocą Alarm Pool, w pełni toleruje standard 5V (FT) |
| **D8 (GPIO 2)** | Wyjście Serial RC | Wejście iBUS / SBUS / CRSF w odbiorniku | Generowany sprzętowo za pomocą maszyn PIO, w pełni toleruje standard 5V (FT) |

---

## 📊 Format Ramki Szeregowej USB (RPi 5 ➡️ XIAO RP2350)

Komunikacja z RPi 5 odbywa się poprzez wirtualny port szeregowy USB CDC (w systemie widoczny jako `/dev/ttyACM0`). Długość ramki to **19 bajtów**:

```
[0xAA] [Tryb] [CH1_H] [CH1_L] ... [CH8_H] [CH8_L] [Checksum XOR]
```

- **Bajt 0**: Bajt startu (`0xAA`)
- **Bajt 1**: Tryb pracy / Wybrany protokół wyjściowy (`1` = PPM, `2` = iBUS, `3` = SBUS, `4` = CRSF)
- **Bajty 2–17**: Wartości 8 kanałów RC (każdy jako 16-bitowa wartość Big-Endian w zakresie 1000–2000 ms).
- **Bajt 18**: Suma kontrolna XOR obliczana z bajtów 1 do 17.

---

## 🚀 Kompilacja i Wgrywanie Oprogramowania

### Wgrywanie przez USB Bootloader (UF2)

1. Podłącz płytkę Seeed Studio XIAO RP2350 do komputera lub Raspberry Pi za pomocą kabla USB-C.
2. Wprowadź mikrokontroler w tryb bootloadera:
   - Przytrzymaj przycisk **BOOT**.
   - Naciśnij i zwolnij przycisk **RESET**.
   - Puść przycisk **BOOT**.
   - Płytka zgłosi się w systemie jako pamięć masowa o nazwie **RPI-RP2**.
3. Uruchom proces kompilacji i wgrywania przy użyciu PlatformIO:
   ```bash
   pio run --target upload
   ```
PlatformIO automatycznie odnajdzie napęd `RPI-RP2` za pomocą narzędzia `picotool` i wgra skompilowany plik binarny.

Zainicjalizowano obsługę diody RGB na pinie 22 (z bezpiecznym poziomem jasności 30).
Zaimplementowano funkcję update_rgb_led(), która w pętli głównej Rdzenia 0 aktualizuje kolor diody w zależności od wybranego protokołu:
PPM: 🔴 Czerwony
iBUS: 🟢 Zielony
SBUS: 🔵 Niebieski
CRSF: 🟣 Fioletowy / Magenta
Failsafe (brak sygnału z RPi5): 🔴 Miganie na czerwono (częstotliwość 5Hz)