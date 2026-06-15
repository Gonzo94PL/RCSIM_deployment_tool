# 🔌 ESP32 PPM Co-Processor Firmware

Koprocesor oparty na module **ESP32** (np. ESP32 NodeMCU, WROOM w wersji z mikrokontrolerem ESP32-D0WDQ6) służy do precyzyjnego generowania sygnału **PPM (Pulse Position Modulation)** o stałej częstotliwości ramki i zerowym jitterze ze strumienia wejściowego koderów cyfrowych.

## ⚙️ Zasada Działania

1. **Odbiór CRSF**: ESP32 nasłuchuje na porcie szeregowym `Serial1` (Domyślnie piny RX=16, TX=17) ramki telemetryczne i sterujące z Raspberry Pi o wysokiej prędkości (420000 bps) i strukturze bajtowej TBS Crossfire.
2. **Parser Cyfrowy**: Filtruje, parsuje nagłówki oraz rozpakowuje 11-bitowe stałe kanałów do wewnętrznej tablicy `volatile uint16_t channels[PPM_CHANNELS]`.
3. **Sprzętowy Generator Przerwań**: Konfiguruje sprzętowy Hardware Timer (`timerBegin(0, 80, true)`) taktowany z częstotliwością 1 MHz (każdy tick to dokładnie 1 mikrosekunda). Na podstawie obliczonych czasów generuje przerwania IRAM o najwyższym priorytecie:
   * **Puls**: Ustawia stan niski (LOW) na pinie wyjściowym przez stały czas 300 µs.
   * **Wypełnienie**: Ustawia stan wysoki (HIGH) na pinie wyjściowym przez czas wyznaczony z odebranej wartości kanału (pomniejszony o 300 µs pulsu startu).
   * **Zrzut / Synchronizacja (SYNC)**: Generuje przerwę wyrównawczą, aby cała ramka trwała dokładnie 22.5 ms (standard PPM).

## 🚀 Kompilacja i Wgrywanie

### 1. Przez Arduino IDE
* Zainstaluj wsparcie dla platformy **ESP32** (przez Boards Manager).
* Wybierz płytkę, np. **ESP32 Dev Module**.
* Podłącz ESP32 kablem USB do komputera lub modułu Raspberry Pi i kliknij "Upload".

### 2. Automatycznie przez Web UI
Skorzystaj z wbudowanego przycisku **"Wgraj firmware.bin"** w Panelu Sterowania w przeglądarce. 
Aby to zadziałało:
* Skompiluj oprogramowanie Arduino do pliku binarnego (`firmware.bin`)
* Umieść plik w katalogu `/opt/usb_rc_converter/firmware/firmware.bin` na Raspberry Pi.
* Kliknięcie przycisku uruchomi w tle proces `esptool` w bezpiecznych i stabilnych parametrach.
