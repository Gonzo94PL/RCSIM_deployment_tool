/**
 * main.cpp - USB-HID to RC Protocol Bridge Firmware for Seeed Studio XIAO RP2350
 * Platform: PlatformIO / Arduino Framework (Earle Philhower pico core)
 *
 * Architektura dwurdzeniowa:
 *   Rdzeń 0 (Core 0): Odbiór i parsowanie ramek USB CDC z RPi5 + Failsafe
 *   Rdzeń 1 (Core 1): Generowanie sygnałów RC (PPM / iBUS / SBUS / CRSF)
 */

#include <Arduino.h>
#include <SerialPIO.h>
#include <hardware/gpio.h>
#include <hardware/sync.h> // Wymagane dla bariery pamięci __dmb()
#include <Adafruit_NeoPixel.h>

// ============================================================================
// Stałe i makra konfiguracyjne
// ============================================================================

#define PPM_CHANNELS       8
#define PPM_FRAME_LENGTH   22500   // Standardowa ramka PPM: 22.5 ms [us]
#define PPM_PULSE_LENGTH   300     // Impuls synchronizujący: 300 us

// Wybór trybu wyjściowego PPM (odkomentowane = Push-Pull, zakomentowane = Open-Drain)
#define PPM_USE_PUSH_PULL

// Nowe, bezpieczne przypisanie pinów 5V-tolerant na płytce Seeed Studio XIAO RP2350
#define PPM_OUT_PIN        2       // Pin D8 (GPIO 2) - Wyjście PPM/CPPM do testu na porcie AUX
#define TX_OUT_PIN         1       // Pin D7 (GPIO 1) - Wyjście iBUS/SBUS/CRSF (tymczasowo)
#define LED_PIN            LED_BUILTIN
#define RGB_LED_PIN        22      // GPIO 22 - Wbudowana dioda RGB WS2812
#define RGB_LED_POWER_PIN  23      // GPIO 23 - Zasilanie diody RGB
#define RGB_LED_COUNT      1

Adafruit_NeoPixel rgb_led(RGB_LED_COUNT, RGB_LED_PIN, NEO_GRB + NEO_KHZ800);

// Rozmiar ramki wejściowej z RPi5
#define FRAME_SIZE         19
#define FRAME_HEADER       0xAA

// Timeout watchdoga failsafe [ms]
#define FAILSAFE_TIMEOUT   500

// Definicja kolejności kanałów (standardy mapowania)
enum ChannelOrder {
    MAP_AETR, // Aileron (1500), Elevator (1500), Throttle (1000), Rudder (1500)
    MAP_TAER, // Throttle (1000), Aileron (1500), Elevator (1500), Rudder (1500)
    MAP_RETA  // Rudder (1500), Elevator (1500), Throttle (1000), Aileron (1500)
};

// Wybrany standard mapowania
const ChannelOrder CURRENT_CHANNEL_MAP = MAP_AETR;

// ============================================================================
// Współdzielone zmienne (Zoptymalizowany podwójny bufor lock-free)
// ============================================================================

// Mechanizm buforowania podwójnego zapobiegający rozrywaniu ramek (tearing)
volatile uint16_t rc_channels_buffer[2][PPM_CHANNELS] = {
    {1500, 1500, 1500, 1500, 1500, 1500, 1500, 1500},
    {1500, 1500, 1500, 1500, 1500, 1500, 1500, 1500}
};
volatile uint8_t rc_buffer_read_idx = 0; // Wskazuje bufor, z którego Core 1 odczytuje dane

volatile uint16_t ppm_working_channels[PPM_CHANNELS] = {
    1500, 1500, 1500, 1500, 1500, 1500, 1500, 1500
};
volatile uint8_t  current_protocol_mode = 1;  // 1=PPM, 2=iBUS, 3=SBUS, 4=CRSF
volatile uint32_t last_rx_time = 0;
volatile bool     failsafe_active = false;

// Flaga sygnalizująca Core 1, że port wymaga rekonfiguracji
volatile bool     port_reconfig_pending = false;
volatile uint8_t  port_reconfig_mode = 1;

// Statyczny obiekt szeregowy oparty o maszyny stanowe PIO (brak alokacji dynamicznej)
SerialPIO RC_SerialOut(TX_OUT_PIN, NOPIN, 32);

// ============================================================================
// Funkcje pomocnicze pobierania kanałów (Lock-Free i Failsafe-Safe)
// ============================================================================

/**
 * Bezpieczne pobranie kanałów RC z podwójnego bufora.
 * W przypadku aktywnego failsafe, wymusza bezpieczne położenia mechaniczne.
 */
static void get_rc_channels(uint16_t *dest) {
    if (failsafe_active) {
        // Wszystkie kanały domyślnie na środek (1500 us)
        for (uint8_t i = 0; i < PPM_CHANNELS; i++) {
            dest[i] = 1500;
        }
        
        // Przypisanie bezpiecznej wartości minimalnej dla gazu (Throttle)
        if (CURRENT_CHANNEL_MAP == MAP_AETR) {
            dest[2] = 1000; // Gaz na kanale 3 (indeks 2)
        } else if (CURRENT_CHANNEL_MAP == MAP_TAER) {
            dest[0] = 1000; // Gaz na kanale 1 (indeks 0)
        } else if (CURRENT_CHANNEL_MAP == MAP_RETA) {
            dest[2] = 1000; // Gaz na kanale 3 (indeks 2)
        }
    } else {
        uint8_t read_idx = rc_buffer_read_idx;
        __dmb(); // Bariera pamięci (Data Memory Barrier) gwarantuje odczyt spójnego indeksu
        for (uint8_t i = 0; i < PPM_CHANNELS; i++) {
            dest[i] = rc_channels_buffer[read_idx][i];
        }
    }
}

// ============================================================================
// Tabela CRC8 dla protokołu CRSF (wielomian: x^8+x^2+x+1, 0xD5)
// ============================================================================

static const uint8_t crsf_crc8_table[256] = {
    0x00, 0xD5, 0x7F, 0xAA, 0xFE, 0x2B, 0x81, 0x54,
    0x29, 0xFC, 0x56, 0x83, 0xD7, 0x02, 0xA8, 0x7D,
    0x52, 0x87, 0x2D, 0xF8, 0xAC, 0x79, 0xD3, 0x06,
    0x7B, 0xAE, 0x04, 0xD1, 0x85, 0x50, 0xFA, 0x2F,
    0xA4, 0x71, 0xDB, 0x0E, 0x5A, 0x8F, 0x25, 0xF0,
    0x8D, 0x58, 0xF2, 0x27, 0x73, 0xA6, 0x0C, 0xD9,
    0xF6, 0x23, 0x89, 0x5C, 0x08, 0xDD, 0x77, 0xA2,
    0xDF, 0x0A, 0xA0, 0x75, 0x21, 0xF4, 0x5E, 0x8B,
    0x9D, 0x48, 0xE2, 0x37, 0x63, 0xB6, 0x1C, 0xC9,
    0xB4, 0x61, 0xCB, 0x1E, 0x4A, 0x9F, 0x35, 0xE0,
    0xCF, 0x1A, 0xB0, 0x65, 0x31, 0xE4, 0x4E, 0x9B,
    0xE6, 0x33, 0x99, 0x4C, 0x18, 0xCD, 0x67, 0xB2,
    0x39, 0xEC, 0x46, 0x93, 0xC7, 0x12, 0xB8, 0x6D,
    0x10, 0xC5, 0x6F, 0xBA, 0xEE, 0x3B, 0x91, 0x44,
    0x6B, 0xBE, 0x14, 0xC1, 0x95, 0x40, 0xEA, 0x3F,
    0x42, 0x97, 0x3D, 0xE8, 0xBC, 0x69, 0xC3, 0x16,
    0xEF, 0x3A, 0x90, 0x45, 0x11, 0xC4, 0x6E, 0xBB,
    0xC6, 0x13, 0xB9, 0x6C, 0x38, 0xED, 0x47, 0x92,
    0xBD, 0x68, 0xC2, 0x17, 0x43, 0x96, 0x3C, 0xE9,
    0x94, 0x41, 0xEB, 0x3E, 0x6A, 0xBF, 0x15, 0xC0,
    0x4B, 0x9E, 0x34, 0xE1, 0xB5, 0x60, 0xCA, 0x1F,
    0x62, 0xB7, 0x1D, 0xC8, 0x9C, 0x49, 0xE3, 0x36,
    0x19, 0xCC, 0x66, 0xB3, 0xE7, 0x32, 0x98, 0x4D,
    0x30, 0xE5, 0x4F, 0x9A, 0xCE, 0x1B, 0xB1, 0x64,
    0x72, 0xA7, 0x0D, 0xD8, 0x8C, 0x59, 0xF3, 0x26,
    0x5B, 0x8E, 0x24, 0xF1, 0xA5, 0x70, 0xDA, 0x0F,
    0x20, 0xF5, 0x5F, 0x8A, 0xDE, 0x0B, 0xA1, 0x74,
    0x09, 0xDC, 0x76, 0xA3, 0xF7, 0x22, 0x88, 0x5D,
    0xD6, 0x03, 0xA9, 0x7C, 0x28, 0xFD, 0x57, 0x82,
    0xFF, 0x2A, 0x80, 0x55, 0x01, 0xD4, 0x7E, 0xAB,
    0x84, 0x51, 0xFB, 0x2E, 0x7A, 0xAF, 0x05, 0xD0,
    0xAD, 0x78, 0xD2, 0x07, 0x53, 0x86, 0x2C, 0xF9
};

static uint8_t get_crsf_crc8(const uint8_t *data, uint8_t len) {
    uint8_t crc = 0;
    for (uint8_t i = 0; i < len; i++) {
        crc = crsf_crc8_table[crc ^ data[i]];
    }
    return crc;
}

// ============================================================================
// Rekonfiguracja wyjścia PIO UART (wywoływana WYŁĄCZNIE z Core 1!)
// ============================================================================

static bool serial_port_active = false;

static void apply_port_configuration(uint8_t mode) {
    // Bezpieczne zatrzymanie pętli bez usuwania obiektu statycznego
    if (serial_port_active) {
        RC_SerialOut.end();
        serial_port_active = false;
    }

    // Przywrócenie domyślnego stanu GPIO override (bez inwersji)
    gpio_set_outover(TX_OUT_PIN, GPIO_OVERRIDE_NORMAL);

    if (mode == 1) {
        // PPM: Wyjście nieaktywne dla szeregowego, oba piny skonfigurowane dla PPM/CPPM
#ifdef PPM_USE_PUSH_PULL
        pinMode(PPM_OUT_PIN, OUTPUT);
        digitalWrite(PPM_OUT_PIN, HIGH);
        pinMode(TX_OUT_PIN, OUTPUT);
        digitalWrite(TX_OUT_PIN, HIGH);
#else
        pinMode(PPM_OUT_PIN, INPUT);
        pinMode(TX_OUT_PIN, INPUT);
#endif
    }
    else if (mode == 2) {
        // iBUS: 115200 bps, 8N1, logika normalna
        RC_SerialOut.setInvertTX(false);
        RC_SerialOut.begin(115200, SERIAL_8N1);
        serial_port_active = true;
    }
    else if (mode == 3) {
        // SBUS: 100000 bps, 8E2, logika odwrócona (inwersja programowa dla bezpośredniego wpięcia do AUX1)
        RC_SerialOut.setInvertTX(true);
        RC_SerialOut.begin(100000, SERIAL_8E2);
        serial_port_active = true;
    }
    else if (mode == 4) {
        // CRSF: 420000 bps, 8N1, logika normalna
        RC_SerialOut.setInvertTX(false);
        RC_SerialOut.begin(420000, SERIAL_8N1);
        serial_port_active = true;
    }
}

// ============================================================================
// Generator PPM — precyzyjna pętla czasowa na Core 1
// ============================================================================

static void ppm_init_gpio() {
    gpio_init(PPM_OUT_PIN);
    gpio_init(TX_OUT_PIN);
#ifdef PPM_USE_PUSH_PULL
    gpio_set_dir(PPM_OUT_PIN, GPIO_OUT);
    gpio_put(PPM_OUT_PIN, true);
    gpio_set_drive_strength(PPM_OUT_PIN, GPIO_DRIVE_STRENGTH_12MA);
    gpio_set_slew_rate(PPM_OUT_PIN, GPIO_SLEW_RATE_FAST);

    gpio_set_dir(TX_OUT_PIN, GPIO_OUT);
    gpio_put(TX_OUT_PIN, true);
    gpio_set_drive_strength(TX_OUT_PIN, GPIO_DRIVE_STRENGTH_12MA);
    gpio_set_slew_rate(TX_OUT_PIN, GPIO_SLEW_RATE_FAST);
#else
    gpio_put(PPM_OUT_PIN, false);       // Przygotowanie do wymuszania stanu niskiego
    gpio_set_dir(PPM_OUT_PIN, GPIO_IN); // Hi-Z (stan wysoki dzięki pull-up)
    gpio_pull_up(PPM_OUT_PIN);          // Wewnętrzny pull-up gwarantujący stabilne HIGH

    gpio_put(TX_OUT_PIN, false);
    gpio_set_dir(TX_OUT_PIN, GPIO_IN);
    gpio_pull_up(TX_OUT_PIN);
#endif
}

/**
 * Precyzyjne wygenerowanie pełnej ramki PPM w pętli opóźnień.
 * Ponieważ Core 1 zajmuje się wyłącznie generowaniem sygnałów RC,
 * metoda ta eliminuje potrzebę stosowania przerwań timera, chroniąc przed jitterem.
 */
static void generate_ppm_frame() {
    uint32_t ints = save_and_disable_interrupts();

    uint16_t temp_channels[PPM_CHANNELS];
    get_rc_channels(temp_channels);

    uint32_t accumulated_time = 0;

    for (uint8_t i = 0; i < PPM_CHANNELS; i++) {
        // Impuls LOW (rozpoczęcie kanału)
#ifdef PPM_USE_PUSH_PULL
        gpio_put(PPM_OUT_PIN, false);
        gpio_put(TX_OUT_PIN, false);
#else
        gpio_set_dir(PPM_OUT_PIN, GPIO_OUT);
        gpio_set_dir(TX_OUT_PIN, GPIO_OUT);
#endif
        uint32_t pulse_start = time_us_32();
        while (time_us_32() - pulse_start < PPM_PULSE_LENGTH) {
            if (port_reconfig_pending) {
                restore_interrupts(ints);
                return;
            }
        }

        // Stan wysoki (HIGH) - czas trwania kanału
#ifdef PPM_USE_PUSH_PULL
        gpio_put(PPM_OUT_PIN, true);
        gpio_put(TX_OUT_PIN, true);
#else
        gpio_set_dir(PPM_OUT_PIN, GPIO_IN);
        gpio_set_dir(TX_OUT_PIN, GPIO_IN);
#endif
        uint16_t duration = temp_channels[i];
        if (duration < 1000) duration = 1000;
        if (duration > 2000) duration = 2000;

        uint32_t high_time = duration - PPM_PULSE_LENGTH;
        accumulated_time += duration;

        pulse_start = time_us_32();
        while (time_us_32() - pulse_start < high_time) {
            if (port_reconfig_pending) {
                restore_interrupts(ints);
                return;
            }
        }
    }

    // Impuls synchronizujący (LOW) na końcu ramki
#ifdef PPM_USE_PUSH_PULL
    gpio_put(PPM_OUT_PIN, false);
    gpio_put(TX_OUT_PIN, false);
#else
    gpio_set_dir(PPM_OUT_PIN, GPIO_OUT);
    gpio_set_dir(TX_OUT_PIN, GPIO_OUT);
#endif
    uint32_t pulse_start = time_us_32();
    while (time_us_32() - pulse_start < PPM_PULSE_LENGTH) {
        if (port_reconfig_pending) {
            restore_interrupts(ints);
            return;
        }
    }

    // Stan wysoki (HIGH) dla przerwy synchronizacyjnej (uzupełnienie do PPM_FRAME_LENGTH)
#ifdef PPM_USE_PUSH_PULL
    gpio_put(PPM_OUT_PIN, true);
    gpio_put(TX_OUT_PIN, true);
#else
    gpio_set_dir(PPM_OUT_PIN, GPIO_IN);
    gpio_set_dir(TX_OUT_PIN, GPIO_IN);
#endif
    uint32_t sync_time = PPM_FRAME_LENGTH - (accumulated_time + PPM_PULSE_LENGTH);
    if (sync_time < PPM_PULSE_LENGTH) sync_time = PPM_PULSE_LENGTH;

    pulse_start = time_us_32();
    while (time_us_32() - pulse_start < sync_time) {
        if (port_reconfig_pending) {
            restore_interrupts(ints);
            return;
        }
    }

    restore_interrupts(ints);
}

// ============================================================================
// RDZEŃ 0: Obsługa portu USB CDC (Odbiór z RPi5 i Failsafe)
// ============================================================================

void setup() {
    pinMode(LED_PIN, OUTPUT);
    digitalWrite(LED_PIN, HIGH); // XIAO RP2350 user LED ma logikę ujemną (HIGH = wyłączona)

    // Inicjalizacja zasilania i diody RGB WS2812
    pinMode(RGB_LED_POWER_PIN, OUTPUT);
    digitalWrite(RGB_LED_POWER_PIN, HIGH);

    rgb_led.begin();
    rgb_led.setBrightness(30);
    rgb_led.show();

    Serial.begin(115200);
    last_rx_time = millis();
}

static void update_rgb_led() {
    static uint32_t last_update = 0;
    uint32_t now = millis();
    if (now - last_update < 50) return;
    last_update = now;

    if (failsafe_active) {
        if ((now % 200) < 100) {
            rgb_led.setPixelColor(0, rgb_led.Color(255, 0, 0));
        } else {
            rgb_led.setPixelColor(0, rgb_led.Color(0, 0, 0));
        }
    } else {
        switch (current_protocol_mode) {
            case 1: rgb_led.setPixelColor(0, rgb_led.Color(255, 0, 0));   break; // PPM: Czerwony
            case 2: rgb_led.setPixelColor(0, rgb_led.Color(0, 255, 0));   break; // iBUS: Zielony
            case 3: rgb_led.setPixelColor(0, rgb_led.Color(0, 0, 255));   break; // SBUS: Niebieski
            case 4: rgb_led.setPixelColor(0, rgb_led.Color(255, 0, 255)); break; // CRSF: Fioletowy
            default: rgb_led.setPixelColor(0, rgb_led.Color(0, 0, 0));    break;
        }
    }
    rgb_led.show();
}

void loop() {
    static uint8_t buffer[32];
    static uint8_t index = 0;

    // --- Parsowanie ramek z RPi5 ---
    while (Serial.available() > 0) {
        uint8_t b = Serial.read();
        Serial.write(b); // Echo dla diagnostyki szeregowej
        buffer[index++] = b;

        if (index == 1 && b != FRAME_HEADER) {
            index = 0;
            continue;
        }

        if (index == FRAME_SIZE) {
            uint8_t calculated_xor = 0;
            for (uint8_t i = 1; i < 18; i++) {
                calculated_xor ^= buffer[i];
            }

            if (calculated_xor == buffer[18]) {
                uint8_t new_mode = buffer[1];
                
                // Wybór nieaktywnego bufora do zapisu danych
                uint8_t write_idx = 1 - rc_buffer_read_idx;

                for (uint8_t ch = 0; ch < PPM_CHANNELS; ch++) {
                    uint16_t ch_val = (buffer[2 + ch * 2] << 8) | buffer[2 + ch * 2 + 1];
                    rc_channels_buffer[write_idx][ch] = ch_val;
                }

                __dmb(); // Gwarancja, że dane zostaną zapisane w pamięci przed zmianą indeksu
                rc_buffer_read_idx = write_idx; // Atomowe przełączenie aktywnego bufora

                last_rx_time = millis();

                if (new_mode != current_protocol_mode && new_mode >= 1 && new_mode <= 4) {
                    port_reconfig_mode = new_mode;
                    __dmb();
                    port_reconfig_pending = true;
                }
            }
            index = 0;
        }
    }

    // --- Watchdog / Failsafe (z uwzględnieniem logiki ujemnej diody LED) ---
    if (millis() - last_rx_time > FAILSAFE_TIMEOUT) {
        failsafe_active = true;
        digitalWrite(LED_PIN, (millis() % 200 < 100) ? LOW : HIGH); // Szybkie miganie (active LOW)
    } else {
        failsafe_active = false;
        digitalWrite(LED_PIN, (millis() % 2000 < 1000) ? LOW : HIGH); // Wolne miganie (active LOW)
    }

    update_rgb_led();
}

// ============================================================================
// RDZEŃ 1: Generowanie i wypychanie ramek RC
// ============================================================================

void setup1() {
    apply_port_configuration(1);
    ppm_init_gpio();
}

void loop1() {
    static uint32_t last_tx_time = 0;
    uint32_t now = millis();

    // --- Obsługa rekonfiguracji portu (zleconej przez Core 0) ---
    if (port_reconfig_pending) {
        __dmb();
        port_reconfig_pending = false;
        uint8_t new_mode = port_reconfig_mode;

        apply_port_configuration(new_mode);
        current_protocol_mode = new_mode;

        if (new_mode == 1) {
            ppm_init_gpio();
        }

        last_tx_time = now;
        return;
    }

    // --- Failsafe: zatrzymanie sygnałów dla PPM, iBUS i CRSF ---
    if (failsafe_active) {
        if (current_protocol_mode == 1) {
            // PPM w trybie failsafe wymusza stan spoczynkowy (HIGH) na obu pinach
#ifdef PPM_USE_PUSH_PULL
            gpio_put(PPM_OUT_PIN, true);
            gpio_put(TX_OUT_PIN, true);
#else
            gpio_set_dir(PPM_OUT_PIN, GPIO_IN);
            gpio_set_dir(TX_OUT_PIN, GPIO_IN);
#endif
            delay(2);
            return;
        }
        if (current_protocol_mode == 4 || current_protocol_mode == 2) {
            delay(2);
            return;
        }
        // SBUS: generuje dalej ramki z flagą failsafe
    }

    // W trybie PPM wywołujemy precyzyjny generator pętlowy
    if (current_protocol_mode == 1) {
        generate_ppm_frame();
        return;
    }

    // Pobranie spójnej, niemodyfikowanej w trakcie odczytu paczki kanałów
    uint16_t temp_channels[PPM_CHANNELS];
    get_rc_channels(temp_channels);

    // --- Generowanie ramek protokołów szeregowych ---
    if (current_protocol_mode == 2) {
        // iBUS: Ramka 32 bajty co 7 ms
        if (now - last_tx_time >= 7) {
            uint8_t ibus_packet[32];
            ibus_packet[0] = 0x20;
            ibus_packet[1] = 0x40;

            for (uint8_t i = 0; i < 14; i++) {
                uint16_t val = (i < PPM_CHANNELS) ? temp_channels[i] : 1500;
                ibus_packet[2 + i * 2]     = val & 0xFF;
                ibus_packet[2 + i * 2 + 1] = (val >> 8) & 0xFF;
            }

            uint16_t checksum = 0xFFFF;
            for (uint8_t i = 0; i < 30; i++) {
                checksum -= ibus_packet[i];
            }
            ibus_packet[30] = checksum & 0xFF;
            ibus_packet[31] = (checksum >> 8) & 0xFF;

            RC_SerialOut.write(ibus_packet, 32);
            last_tx_time = now;
        }
    }
    else if (current_protocol_mode == 3) {
        // SBUS: Ramka 25 bajtów co 14 ms
        if (now - last_tx_time >= 14) {
            uint8_t sbus_packet[25];
            sbus_packet[0] = 0x0F;

            // Zoptymalizowana, precyzyjna konwersja 1000-2000 us -> SBUS 11-bit (173-1811)
            uint16_t sc[16];
            for (uint8_t i = 0; i < 16; i++) {
                uint16_t val = (i < PPM_CHANNELS) ? temp_channels[i] : 1500;
                if (val < 1000) val = 1000;
                if (val > 2000) val = 2000;
                
                // Mnożnik 1.638 (819/500) mapuje zakres 1000-2000us na pełne pasmo SBUS 173-1811
                int32_t sbus_val = ((int32_t)(val - 1500) * 819 / 500) + 992;
                if (sbus_val < 0) sbus_val = 0;
                if (sbus_val > 2047) sbus_val = 2047;
                sc[i] = (uint16_t)sbus_val;
            }

            // Pakowanie bitowe SBUS 11-bit
            sbus_packet[1]  = (uint8_t)(sc[0] & 0xFF);
            sbus_packet[2]  = (uint8_t)((sc[0] >> 8)   | (sc[1] << 3));
            sbus_packet[3]  = (uint8_t)((sc[1] >> 5)   | (sc[2] << 6));
            sbus_packet[4]  = (uint8_t)((sc[2] >> 2)   & 0xFF);
            sbus_packet[5]  = (uint8_t)((sc[2] >> 10)  | (sc[3] << 1));
            sbus_packet[6]  = (uint8_t)((sc[3] >> 7)   | (sc[4] << 4));
            sbus_packet[7]  = (uint8_t)((sc[4] >> 4)   | (sc[5] << 7));
            sbus_packet[8]  = (uint8_t)((sc[5] >> 1)   & 0xFF);
            sbus_packet[9]  = (uint8_t)((sc[5] >> 9)   | (sc[6] << 2));
            sbus_packet[10] = (uint8_t)((sc[6] >> 6)   | (sc[7] << 5));
            sbus_packet[11] = (uint8_t)((sc[7] >> 3)   & 0xFF);
            sbus_packet[12] = (uint8_t)(sc[8] & 0xFF);
            sbus_packet[13] = (uint8_t)((sc[8] >> 8)   | (sc[9] << 3));
            sbus_packet[14] = (uint8_t)((sc[9] >> 5)   | (sc[10] << 6));
            sbus_packet[15] = (uint8_t)((sc[10] >> 2)  & 0xFF);
            sbus_packet[16] = (uint8_t)((sc[10] >> 10) | (sc[11] << 1));
            sbus_packet[17] = (uint8_t)((sc[11] >> 7)  | (sc[12] << 4));
            sbus_packet[18] = (uint8_t)((sc[12] >> 4)  | (sc[13] << 7));
            sbus_packet[19] = (uint8_t)((sc[13] >> 1)  & 0xFF);
            sbus_packet[20] = (uint8_t)((sc[13] >> 9)  | (sc[14] << 2));
            sbus_packet[21] = (uint8_t)((sc[14] >> 6)  | (sc[15] << 5));
            sbus_packet[22] = (uint8_t)((sc[15] >> 3)  & 0xFF);

            uint8_t flags = 0x00;
            if (failsafe_active) {
                flags |= 0x08; // Flaga failsafe SBUS
            }
            sbus_packet[23] = flags;
            sbus_packet[24] = 0x00;

            RC_SerialOut.write(sbus_packet, 25);
            last_tx_time = now;
        }
    }
    else if (current_protocol_mode == 4) {
        // CRSF: Ramka 26 bajtów co 6 ms
        if (now - last_tx_time >= 6) {
            uint8_t crsf_packet[26];
            crsf_packet[0] = 0xC8; // Flight Controller
            crsf_packet[1] = 24;   // Długość payload + type + crc
            crsf_packet[2] = 0x16; // RC Channels Packed

            // Zoptymalizowana, precyzyjna konwersja do CRSF (173-1811)
            uint16_t cc[16];
            for (uint8_t i = 0; i < 16; i++) {
                uint16_t val = (i < PPM_CHANNELS) ? temp_channels[i] : 1500;
                if (val < 1000) val = 1000;
                if (val > 2000) val = 2000;
                
                int32_t crsf_val = ((int32_t)(val - 1500) * 819 / 500) + 992;
                if (crsf_val < 0) crsf_val = 0;
                if (crsf_val > 2047) crsf_val = 2047;
                cc[i] = (uint16_t)crsf_val;
            }

            // Pakowanie bitowe CRSF 11-bit
            crsf_packet[3]  = (uint8_t)(cc[0] & 0xFF);
            crsf_packet[4]  = (uint8_t)((cc[0] >> 8)  | (cc[1] << 3));
            crsf_packet[5]  = (uint8_t)((cc[1] >> 5)  | (cc[2] << 6));
            crsf_packet[6]  = (uint8_t)((cc[2] >> 2));
            crsf_packet[7]  = (uint8_t)((cc[2] >> 10) | (cc[3] << 1));
            crsf_packet[8]  = (uint8_t)((cc[3] >> 7)  | (cc[4] << 4));
            crsf_packet[9]  = (uint8_t)((cc[4] >> 4)  | (cc[5] << 7));
            crsf_packet[10] = (uint8_t)((cc[5] >> 1));
            crsf_packet[11] = (uint8_t)((cc[5] >> 9)  | (cc[6] << 2));
            crsf_packet[12] = (uint8_t)((cc[6] >> 6)  | (cc[7] << 5));
            crsf_packet[13] = (uint8_t)((cc[7] >> 3));
            crsf_packet[14] = (uint8_t)(cc[8] & 0xFF);
            crsf_packet[15] = (uint8_t)((cc[8] >> 8)  | (cc[9] << 3));
            crsf_packet[16] = (uint8_t)((cc[9] >> 5)  | (cc[10] << 6));
            crsf_packet[17] = (uint8_t)((cc[10] >> 2));
            crsf_packet[18] = (uint8_t)((cc[10] >> 10) | (cc[11] << 1));
            crsf_packet[19] = (uint8_t)((cc[11] >> 7)  | (cc[12] << 4));
            crsf_packet[20] = (uint8_t)((cc[12] >> 4)  | (cc[13] << 7));
            crsf_packet[21] = (uint8_t)((cc[13] >> 1));
            crsf_packet[22] = (uint8_t)((cc[13] >> 9)  | (cc[14] << 2));
            crsf_packet[23] = (uint8_t)((cc[14] >> 6)  | (cc[15] << 5));
            crsf_packet[24] = (uint8_t)((cc[15] >> 3));

            crsf_packet[25] = get_crsf_crc8(&crsf_packet[2], 23);

            RC_SerialOut.write(crsf_packet, 26);
            last_tx_time = now;
        }
    }
}