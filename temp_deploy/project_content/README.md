# ✈️ Konwerter USB HID na Sygnał Modelarski RC (CRSF/i-BUS/PPM)

Kompleksowy, ultra-stabilny i zoptymalizowany pod kątem czasu rzeczywistego system przeznaczony dla **Raspberry Pi 5** oraz **mikrokontrolera**. Projekt pozwala na podłączenie dowolnych kontrolerów USB HID (np. drążków sterowniczych, joysticków, wolantów, a także kontrolerów gier czy aparatur RC w trybie symulatora USB) i przekonwertowanie ich wychyleń na profesjonalne protokoły radiowe RC o niskim opóźnieniu (Jitter < 1 ms).

---

## 🏗️ Architektura Systemu

Przepływ danych w urządzeniu prezentuje poniższy schemat blokowy:

```text
 ┌──────────────────────┐      ┌─────────────────────────┐      ┌────────────────────────┐
 │   Kontroler USB HID  │ ───> │  Skaner Linux (evdev)   │ ───> │ Silnik Mikserów & Expo │
 │ (np. TX16s, Joystick)│      │    [Wątki odbiorcze]    │      │  [Zastosowanie mapowań]│
 └──────────────────────┘      └─────────────────────────┘      └────────────────────────┘
                                                                             │
 ┌──────────────────────┐      ┌─────────────────────────┐                   ▼
 │ Przekaźnik modelarski│ <─── │ Koprocesor (STM32/RP2350│ <─── ┌────────────────────────┐
 │  (PPM / CRSF / ELRS) │      │ / opcjonalnie ESP32)    │      │ Nadawca Serial (UART)  │
 └──────────────────────┘      └─────────────────────────┘      │    [Ramki cyfrowe]     │
                                                                └────────────────────────┘
```

1. **Warstwa Wejściowa (Python / evdev)**: Wątki systemowe nasłuchują zdarzeń z interfejsów`/dev/input/event*`. Obsługują one dynamiczne mapowania, odwracanie kanałów, korekcję sub-trims oraz nieliniowe krzywe reakcji drążków (**Expo**).
2. **Silnik Mikserów**: Oblicza i miksuje pozycje drążków w locie, włączając w to dedykowane tryby skrzydeł lamiastych (Elevon / Delta) czy usterzenia typu V-tail.
3. **Warstwa Nadawcza (Python Serial)**: Generuje precyzyjne ramki cyfrowe TBS Crossfire (CRSF, prędkość 420000 bps) lub FlySky i-BUS (prędkość 115200 bps) i przesyła je bezpośrednio przez piny UART (GPIO 14/15) w Raspberry Pi.
4. **Koprocesor Generujący PPM/Serial RC**: W przypadku konieczności wyprowadzenia klasycznego sygnału analogowego PPM lub precyzyjnych sygnałów szeregowych, dedykowany koprocesor (STM32 Blue Pill lub Seeed Studio XIAO RP2350) odbiera ramki cyfrowe z RPi przez port szeregowy/USB, konwertuje je przy użyciu sprzętowych timerów/maszyn PIO o wysokiej dokładności i wyprowadza krystalicznie czysty sygnał PPM (np. PA0/D0) lub szeregowy RC (np. PA9/D1).

---

## 🛠️ Instalacja i Rejestracja Usług w Systemie

Wszystkie usługi sterujące i monitorujące rejestrowane są w menedżerze `systemd` z przydzielonymi priorytetami czasu rzeczywistego (CPUSchedulingPolicy=fifo, priority=50) i powinowactwem rdzeni (CPUAffinity=3) w celu wyeliminowania narzutów jądra Linux.

### Kroki instalacji na Raspberry Pi 5:

1. **Skopiowanie repozytorium** do katalogu roboczego.
2. **Nadanie uprawnień** skryptom instalacyjnym:
   ```bash
   chmod +x scripts/*.sh
   ```
3. **Uruchomienie instalatora usługi systemowej**:
   ```bash
   sudo ./scripts/install_services.sh
   ```

Skrypt automatycznie założy izolowane środowisko wirtualne Python (`venv`), zainstaluje biblioteki z `requirements.txt`, przydzieli wymagane uprawnienia do obsługi magistrali I2C (nakładki UPS LiPo) i zarejestruje system jako usługę autostartu.

---

## 📡 Zarządzanie i Konfiguracja w Locie (Web UI)

System posiada wbudowany nowoczesny Web UI serwowany bezpośrednio z portu `8080` na Raspberry Pi:

* **Skanowanie Joysticków**: Podgląd podłączonych fizycznie kontrolerów USB z dokładną ścieżką systemową.
* **Wskaźnik Kanałów w Czasie Rzeczywistym**: Estetyczne paski wizualizujące ruch każdego z 16 kanałów aparatury (częstotliwość podglądu 10 Hz).
* **Edytor JSON w przeglądarce**: Możliwość natychmiastowej zmiany profilu modelu, modyfikacji punktów końcowych, sub-trimów, limitów, expo, oraz przyporządkowania klawiszy bez restartu komputera. Po kliknięciu "Zapisz", silnik automatycznie przeładowuje wątki wejściowe.
* **Telemetryczny Monitor Zasilania**: Integracja z układami INA219 ( Waveshare UPS Hat itp.) monitorująca poziom naładowania pakietu 2S LiPo na pokładzie kontrolera.
* **Konsola Diagnostyczna Koprocesora & Flash**: Możliwość przefleszowania oprogramowania koprocesora jednym kliknięciem myszy bezpośrednio przez przeglądarkę dzięki integracji z odpowiednimi narzędziami (`openocd` dla STM32, `picotool` dla XIAO RP2350, `esptool` dla ESP32).

---

## 📱 Użycie na Lotnisku FPV / Modelarskim

Aby móc zmieniać parametry bezpośrednio z telefonu na polu:
1. Uruchom skrypt konfiguracji Hotspotu:
   ```bash
   sudo ./scripts/setup_ap.sh
   ```
2. Raspberry Pi utworzy sieć Wi-Fi o nazwie **RC_Converter_Field** (Hasło: `flysafe123`).
3. Połącz się telefonem i otwórz w przeglądarce adres: **`http://10.42.0.1:8080`**.
