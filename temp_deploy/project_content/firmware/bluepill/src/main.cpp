//**
 * main.cpp - USB-to-RC Protocol Bridge Firmware for STM32F103C8T6 (Blue Pill)
 * Platform: PlatformIO / Arduino Framework (STM32duino)
 */

#include <Arduino.h>

#define PPM_CHANNELS 8
#define PPM_FRAME_LENGTH 22500  // Standard PPM frame: 22.5 ms
#define PPM_PULSE_LENGTH 300    // Sync pulse: 300 us
#define PPM_OUT_PIN PA0         // Timer 2 CH1 equivalent output pin
#define TX_OUT_PIN PA9          // Serial1 TX pin
#define LED_PIN PC13            // Wbudowana dioda (active LOW na Blue Pill)

// Używamy USART2 do komunikacji z Raspberry Pi
// (PA3 = RX, PA2 = TX)
HardwareSerial Serial2(USART2);

// ============================================================================
// Współdzielone zmienne
// ============================================================================
volatile uint16_t rc_channels[PPM_CHANNELS] = {
    1500, 1500, 1500, 1500, 1500, 1500, 1500, 1500
};
volatile uint16_t ppm_working_channels[PPM_CHANNELS] = {
    1500, 1500, 1500, 1500, 1500, 1500, 1500, 1500
};

volatile uint8_t current_protocol_mode = 1; // 1=PPM, 2=iBUS, 3=SBUS, 4=CRSF
volatile uint32_t last_rx_time = 0;
bool failsafe_active = false;

// CRC8 Table for CRSF
const uint8_t crsf_crc8_table[256] = {
    0x00, 0xD5, 0x7F, 0xAA, 0xFE, 0x2B, 0x81, 0x54, 0x29, 0xFC, 0x56, 0x83, 0xD7, 0x02, 0xA8, 0x7D,
    0x52, 0x87, 0x2D, 0xF8, 0xAC, 0x79, 0xD3, 0x06, 0x7B, 0xAE, 0x04, 0xD1, 0x85, 0x50, 0xFA, 0x2F,
    0xA4, 0x71, 0xDB, 0x0E, 0x5A, 0x8F, 0x25, 0xF0, 0x8D, 0x58, 0xF2, 0x27, 0x73, 0xA6, 0x0C, 0xD9,
    0xF6, 0x23, 0x89, 0x5C, 0x08, 0xDD, 0x77, 0xA2, 0xDF, 0x0A, 0xA0, 0x75, 0x21, 0xF4, 0x5E, 0x8B,
    0x9D, 0x48, 0xE2, 0x37, 0x63, 0xB6, 0x1C, 0xC9, 0xB4, 0x61, 0xCB, 0x1E, 0x4A, 0x9F, 0x35, 0xE0,
    0xCF, 0x1A, 0xB0, 0x65, 0x31, 0xE4, 0x4E, 0x9B, 0xE6, 0x33, 0x99, 0x4C, 0x18, 0xCD, 0x67, 0xB2,
    0x39, 0xEC, 0x46, 0x93, 0xC7, 0x12, 0xB8, 0x6D, 0x10, 0xC5, 0x6F, 0xBA, 0xEE, 0x3B, 0x91, 0x44,
    0x6B, 0xBE, 0x14, 0xC1, 0x95, 0x40, 0xEA, 0x3F, 0x42, 0x97, 0x3D, 0xE8, 0xBC, 0x69, 0xC3, 0x16,
    0xEF, 0x3A, 0x90, 0x45, 0x11, 0xC4, 0x6E, 0xBB, 0xC6, 0x13, 0xB9, 0x6C, 0x38, 0xED, 0x47, 0x92,
    0xBD, 0x68, 0xC2, 0x17, 0x43, 0x96, 0x3C, 0xE9, 0x94, 0x41, 0xEB, 0x3E, 0x6A, 0xBF, 0x15, 0xC0,
    0x4B, 0x9E, 0x34, 0xE1, 0xB5, 0x60, 0xCA, 0x1F, 0x62, 0xB7, 0x1D, 0xC8, 0x9C, 0x49, 0xE3, 0x36,
    0x19, 0xCC, 0x66, 0xB3, 0xE7, 0x32, 0x98, 0x4D, 0x30, 0xE5, 0x4F, 0x9A, 0xCE, 0x1B, 0xB1, 0x64,
    0x72, 0xA7, 0x0D, 0xD8, 0x8C, 0x59, 0xF3, 0x26, 0x5B, 0x8E, 0x24, 0xF1, 0xA5, 0x70, 0xDA, 0x0F,
    0x20, 0xF5, 0x5F, 0x8A, 0xDE, 0x0B, 0xA1, 0x74, 0x09, 0xDC, 0x76, 0xA3, 0xF7, 0x22, 0x88, 0x5D,
    0xD6, 0x03, 0xA9, 0x7C, 0x28, 0xFD, 0x57, 0x82, 0xFF, 0x2A, 0x80, 0x55, 0x01, 0xD4, 0x7E, 0xAB,
    0x84, 0x51, 0xFB, 0x2E, 0x7A, 0xAF, 0x05, 0xD0, 0xAD, 0x78, 0xD2, 0x07, 0x53, 0x86, 0x2C, 0xF9
};

uint8_t get_crsf_crc8(uint8_t *data, uint8_t len) {
    uint8_t crc = 0;
    for (uint8_t i = 0; i < len; i++) {
        crc = crsf_crc8_table[crc ^ data[i]];
    }
    return crc;
}

// ============================================================================
// Obsługa sprzętowa generatora PPM (Timer 2)
// ============================================================================
HardwareTimer *MyTimer;

enum PPMState { PPM_START_PULSE, PPM_CHANNEL_SPACE, PPM_SYNC_SPACE };
volatile PPMState ppm_state = PPM_START_PULSE;
volatile uint8_t ppm_channel_idx = 0;
volatile uint32_t ppm_accumulated_time = 0;

void ppm_timer_handler() {
    if (current_protocol_mode != 1) return;

    if (ppm_state == PPM_START_PULSE) {
        digitalWrite(PPM_OUT_PIN, LOW); // Startowy impuls (ściągnięcie do masy)
        ppm_state = PPM_CHANNEL_SPACE;
        MyTimer->setOverflow(PPM_PULSE_LENGTH, MICROSEC_FORMAT);
    } 
    else if (ppm_state == PPM_CHANNEL_SPACE) {
        digitalWrite(PPM_OUT_PIN, HIGH); // Stan wysoki (Open-Drain: Hi-Z)
        if (ppm_channel_idx < PPM_CHANNELS) {
            uint16_t duration = ppm_working_channels[ppm_channel_idx];
            if (duration < 1000) duration = 1000;
            if (duration > 2000) duration = 2000;
            
            uint32_t active_duration = duration - PPM_PULSE_LENGTH;
            ppm_accumulated_time += duration;
            ppm_channel_idx++;
            ppm_state = PPM_START_PULSE;
            MyTimer->setOverflow(active_duration, MICROSEC_FORMAT);
        } else {
            ppm_state = PPM_SYNC_SPACE;
            uint32_t sync_duration = PPM_FRAME_LENGTH - ppm_accumulated_time;
            if (sync_duration < PPM_PULSE_LENGTH) sync_duration = PPM_PULSE_LENGTH;
            MyTimer->setOverflow(sync_duration, MICROSEC_FORMAT);
        }
    } 
    else if (ppm_state == PPM_SYNC_SPACE) {
        ppm_channel_idx = 0;
        ppm_accumulated_time = 0;
        ppm_state = PPM_START_PULSE;
        
        // Bezpieczne skopiowanie kanałów na starcie ramki
        for (uint8_t i = 0; i < PPM_CHANNELS; i++) {
            ppm_working_channels[i] = rc_channels[i];
        }
        
        MyTimer->setOverflow(1, MICROSEC_FORMAT); // Przejdź natychmiast
    }
}

// ============================================================================
// Inicjalizacja portu szeregowego USART1 / Pinów
// ============================================================================
void configure_output_port(uint8_t mode) {
    Serial1.end();
    
    // Konfiguracja natywnego sprzętowego Open-Drain dla PPM na STM32
    if (mode == 1) {
        pinMode(PPM_OUT_PIN, OUTPUT_OPEN_DRAIN);
        digitalWrite(PPM_OUT_PIN, HIGH); // Stan spoczynkowy: podciąganie przez aparaturę
    } 
    else if (mode == 2) {
        // iBUS: 115200 bps, 8N1
        Serial1.begin(115200, SERIAL_8N1);
    } 
    else if (mode == 3) {
        // SBUS: 100000 bps, 8E2
        // UWAGA: Wymaga ZEWNĘTRZNEGO INWERTERA (np. NPN) podłączonego do pinu PA9.
        Serial1.begin(100000, SERIAL_8E2);
    } 
    else if (mode == 4) {
        // CRSF: 420000 bps, 8N1 (STM32 bez problemu obsługuje taką prędkość)
        Serial1.begin(420000, SERIAL_8N1);
    }
}

// ============================================================================
// Setup
// ============================================================================
void setup() {
    pinMode(LED_PIN, OUTPUT);
    digitalWrite(LED_PIN, HIGH); // Wyłącz LED (Active LOW)

    // Komunikacja z RPi5 (Format Little-Endian w Pythonie: struct.pack('<B8H'))
    Serial2.begin(115200);

    // Inicjalizacja Timera dla PPM
    MyTimer = new HardwareTimer(TIM2);
    MyTimer->setMode(1, TIMER_OUTPUT_COMPARE);
    MyTimer->attachInterrupt(ppm_timer_handler);
    
    // Inicjalna kopia wartości dla PPM
    for (uint8_t i = 0; i < PPM_CHANNELS; i++) {
        ppm_working_channels[i] = rc_channels[i];
    }
    
    configure_output_port(current_protocol_mode);
    if (current_protocol_mode == 1) {
        MyTimer->resume();
    }
    
    last_rx_time = millis();
}

// ============================================================================
// GŁÓWNA PĘTLA - Parsowanie wejścia
// ============================================================================
void parse_rpi_frame() {
    static uint8_t buffer[32];
    static uint8_t index = 0;

    while (Serial2.available() > 0) {
        uint8_t b = Serial2.read();
        buffer[index++] = b;

        if (index == 1 && b != 0xAA) {
            index = 0;
            continue;
        }

        if (index == 19) {
            uint8_t calculated_xor = 0;
            for (uint8_t i = 1; i < 18; i++) {
                calculated_xor ^= buffer[i];
            }

            if (calculated_xor == buffer[18]) {
                uint8_t new_mode = buffer[1];
                
                // Aktualizacja kanałów (Poprawiony Endianness pod RPi/ARM)
                for (uint8_t ch = 0; ch < PPM_CHANNELS; ch++) {
                    uint16_t ch_val = (buffer[2 + ch * 2 + 1] << 8) | buffer[2 + ch * 2];
                    rc_channels[ch] = ch_val;
                }

                last_rx_time = millis();

                // Dynamiczna zmiana protokołu w locie
                if (new_mode != current_protocol_mode && new_mode >= 1 && new_mode <= 4) {
                    if (current_protocol_mode == 1) {
                        MyTimer->pause();
                        digitalWrite(PPM_OUT_PIN, HIGH);
                    }
                    current_protocol_mode = new_mode;
                    configure_output_port(current_protocol_mode);
                    
                    if (current_protocol_mode == 1) {
                        ppm_channel_idx = 0;
                        ppm_accumulated_time = 0;
                        ppm_state = PPM_START_PULSE;
                        MyTimer->resume();
                    }
                }
            }
            index = 0;
        }
    }
}

// ============================================================================
// GŁÓWNA PĘTLA - Wypychanie wyjścia szeregowego (iBUS / SBUS / CRSF)
// ============================================================================
void process_output() {
    static uint32_t last_tx_time = 0;
    uint32_t now = millis();

    // W trybie failsafe wstrzymujemy wysyłanie iBUS oraz CRSF
    if (failsafe_active && current_protocol_mode != 3) {
        return; 
    }

    if (current_protocol_mode == 2) {
        if (now - last_tx_time >= 7) {
            uint8_t ibus_packet[32];
            ibus_packet[0] = 0x20;
            ibus_packet[1] = 0x40;
            
            for (uint8_t i = 0; i < 14; i++) {
                uint16_t val = (i < PPM_CHANNELS) ? rc_channels[i] : 1500;
                ibus_packet[2 + i * 2] = val & 0xFF;
                ibus_packet[2 + i * 2 + 1] = (val >> 8) & 0xFF;
            }
            
            uint16_t checksum = 0xFFFF;
            for (uint8_t i = 0; i < 30; i++) {
                checksum -= ibus_packet[i];
            }
            ibus_packet[30] = checksum & 0xFF;
            ibus_packet[31] = (checksum >> 8) & 0xFF;

            Serial1.write(ibus_packet, 32);
            last_tx_time = now;
        }
    } 
    else if (current_protocol_mode == 3) {
        // SBUS: Ramka 25 bajtów co ~14 ms (standard)
        if (now - last_tx_time >= 14) {
            uint8_t sbus_packet[25];
            sbus_packet[0] = 0x0F;

            uint16_t sc[16];
            for (uint8_t i = 0; i < 16; i++) {
                uint16_t val = (i < PPM_CHANNELS) ? rc_channels[i] : 1500;
                if (val < 1000) val = 1000;
                if (val > 2000) val = 2000;
                // Matematyka na liczbach całkowitych (zgodnie z CRSF dla spójności)
                int32_t sbus_val = ((int32_t)(val - 1500) * 8 / 5) + 992;
                if (sbus_val < 0) sbus_val = 0;
                if (sbus_val > 2047) sbus_val = 2047;
                sc[i] = (uint16_t)sbus_val;
            }

            // Pakowanie
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

            // Flagi SBUS (Failsafe)
            uint8_t flags = 0x00;
            if (failsafe_active) {
                flags |= 0x08;
            }
            sbus_packet[23] = flags;
            sbus_packet[24] = 0x00;

            Serial1.write(sbus_packet, 25);
            last_tx_time = now;
        }
    } 
    else if (current_protocol_mode == 4) {
        if (now - last_tx_time >= 6) {
            uint8_t crsf_packet[26];
            crsf_packet[0] = 0xEE; 
            crsf_packet[1] = 24;   
            crsf_packet[2] = 0x16; 

            uint16_t cc[16];
            for (uint8_t i = 0; i < 16; i++) {
                uint16_t val = (i < PPM_CHANNELS) ? rc_channels[i] : 1500;
                if (val < 1000) val = 1000;
                if (val > 2000) val = 2000;
                // Matematyka na liczbach całkowitych - wielokrotnie szybsza
                int32_t crsf_val = ((int32_t)(val - 1500) * 8 / 5) + 992;
                if (crsf_val < 0) crsf_val = 0;
                if (crsf_val > 2047) crsf_val = 2047;
                cc[i] = (uint16_t)crsf_val;
            }

            // Pakowanie
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

            Serial1.write(crsf_packet, 26);
            last_tx_time = now;
        }
    }
}

void loop() {
    parse_rpi_frame();
    process_output();

    // Watchdog
    if (millis() - last_rx_time > 500) {
        if (!failsafe_active) {
            failsafe_active = true;
            if (current_protocol_mode == 1) {
                MyTimer->pause();
                digitalWrite(PPM_OUT_PIN, HIGH);
            }
        }
        digitalWrite(LED_PIN, (millis() % 200 < 100) ? LOW : HIGH); // Szybkie miganie
    } else {
        if (failsafe_active) {
            failsafe_active = false;
            if (current_protocol_mode == 1) {
                ppm_channel_idx = 0;
                ppm_accumulated_time = 0;
                ppm_state = PPM_START_PULSE;
                MyTimer->resume();
            }
        }
        digitalWrite(LED_PIN, (millis() % 2000 < 1000) ? LOW : HIGH); // Wolne miganie
    }
}