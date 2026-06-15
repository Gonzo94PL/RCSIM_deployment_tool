#include <Arduino.h>

#define PPM_CHANNELS 8
#define PPM_FRAME_LENGTH 22500  // Standardowa ramka PPM: 22.5 ms [us]
#define PPM_PULSE_LENGTH 300    // Długość impulsu startowego: 300 us
#define OUTPUT_PIN 13           // Pin wyjściowy PPM (GPIO 13 na ESP32)
#define LED_PIN 33              // Wbudowana czerwona dioda (Active LOW na ESP32-CAM)

// Wybór płytki: odkomentuj właściwą linię
//#define BOARD_WROOM_DEV  // Klasyczny ESP32 (WROOM-32, NodeMCU-32S) - komunikacja przez Serial1 (GPIO 16/17)
#define BOARD_ESP32_CAM  // ESP32-CAM (AI-Thinker) - komunikacja współdzielona na Serial (GPIO 1/3)

// Konfiguracja makr do logowania (aby nie zaśmiecać portu współdzielonego na ESP-CAM)
#ifdef BOARD_ESP32_CAM
  #define RC_SERIAL Serial
  #define DEBUG_PRINT(x)
  #define DEBUG_PRINTLN(x)
#else
  #define RC_SERIAL Serial1
  #define DEBUG_PRINT(x)    Serial.print(x)
  #define DEBUG_PRINTLN(x)  Serial.println(x)
#endif

// ============================================================================
// Pamięć współdzielona i zmienne globalne
// ============================================================================
volatile uint16_t channels[PPM_CHANNELS] = {1500, 1500, 1500, 1500, 1500, 1500, 1500, 1500};
volatile uint16_t working_channels[PPM_CHANNELS] = {1500, 1500, 1500, 1500, 1500, 1500, 1500, 1500};

volatile uint32_t lastCRSFTime = 0;
bool isFailsafeActive = false;

// Zmienne obsługi Hardware Timer (ESP32)
hw_timer_t *timer = NULL;
portMUX_TYPE timerMux = portMUX_INITIALIZER_UNLOCKED;

enum PPMState { PPM_PULSE, PPM_FILL, PPM_SYNC };
volatile PPMState ppmState = PPM_PULSE;
volatile uint8_t currentChannel = 0;
volatile uint32_t currentFrameSum = 0;
volatile uint32_t isrCount = 0;

// ============================================================================
// Przerwanie Timera (Generowanie PPM)
// ============================================================================
void IRAM_ATTR onTimer() {
    portENTER_CRITICAL_ISR(&timerMux);
    isrCount++;
    
    if (ppmState == PPM_PULSE) {
        digitalWrite(OUTPUT_PIN, LOW); // Impuls startowy (zwarcie do masy / Open-Drain)
        ppmState = PPM_FILL;
        timerAlarm(timer, PPM_PULSE_LENGTH, true, 0);
    } 
    else if (ppmState == PPM_FILL) {
        digitalWrite(OUTPUT_PIN, HIGH); // Stan wysoki (Hi-Z, podciągane przez aparaturę)
        
        if (currentChannel < PPM_CHANNELS) {
            // Czytamy z bezpiecznej kopii roboczej, aby uniknąć rwania ramki
            uint16_t value = working_channels[currentChannel];
            uint32_t fillTime = value - PPM_PULSE_LENGTH;
            currentFrameSum += value;
            currentChannel++;
            ppmState = PPM_PULSE;
            timerAlarm(timer, fillTime, true, 0);
        } else {
            // Wszystkie kanały wysłane - czas na przerwę synchronizacyjną (SYNC)
            ppmState = PPM_SYNC;
            uint32_t syncTime = PPM_FRAME_LENGTH - currentFrameSum;
            if (syncTime < PPM_PULSE_LENGTH) syncTime = PPM_PULSE_LENGTH; // Zabezpieczenie
            timerAlarm(timer, syncTime, true, 0);
        }
    } 
    else if (ppmState == PPM_SYNC) {
        currentChannel = 0;
        currentFrameSum = 0;
        ppmState = PPM_PULSE;
        
        // Bezpieczne przekopiowanie kanałów ułamek milisekundy przed startem nowej ramki
        for (uint8_t i = 0; i < PPM_CHANNELS; i++) {
            working_channels[i] = channels[i];
        }
        
        timerAlarm(timer, 1, true, 0); // Natychmiastowe przejście
    }
    
    portEXIT_CRITICAL_ISR(&timerMux);
}

// ============================================================================
// Odbiór i dekodowanie protokołu CRSF
// ============================================================================
void parseCRSF() {
    static uint8_t buffer[64];
    static uint8_t index = 0;
    
    while (RC_SERIAL.available()) {
        uint8_t b = RC_SERIAL.read();
        buffer[index++] = b;
        
        // Wykrywanie nagłówka CRSF (0xEE = Nadajnik, 0xC8 = Kontroler lotu)
        if (index == 1 && b != 0xEE && b != 0xC8) {
            index = 0;
            continue;
        }
        
        // Sprawdzenie długości ramki (bajt 1)
        if (index > 2) {
            uint8_t length = buffer[1];
            if (index == length + 2) { // Pełna ramka odebrana
                if (buffer[2] == 0x16) { // Typ ramki: RC Channels Packed
                    
                    uint16_t temp_channels[8];
                    
                    // Dekodowanie 11-bitowych kanałów CRSF
                    temp_channels[0] = (uint16_t)((buffer[3]       | buffer[4] << 8)                       & 0x07FF);
                    temp_channels[1] = (uint16_t)((buffer[4] >> 3  | buffer[5] << 5)                       & 0x07FF);
                    temp_channels[2] = (uint16_t)((buffer[5] >> 6  | buffer[6] << 2  | buffer[7] << 10)    & 0x07FF);
                    temp_channels[3] = (uint16_t)((buffer[7] >> 1  | buffer[8] << 7)                       & 0x07FF);
                    temp_channels[4] = (uint16_t)((buffer[8] >> 4  | buffer[9] << 4)                       & 0x07FF);
                    temp_channels[5] = (uint16_t)((buffer[9] >> 7  | buffer[10] << 1 | buffer[11] << 9)    & 0x07FF);
                    temp_channels[6] = (uint16_t)((buffer[11] >> 2 | buffer[12] << 6)                      & 0x07FF);
                    temp_channels[7] = (uint16_t)((buffer[12] >> 5 | buffer[13] << 3)                      & 0x07FF);
                    
                    // Bezpieczna aktualizacja po przeliczeniu matematyki
                    portENTER_CRITICAL(&timerMux);
                    for (int i = 0; i < PPM_CHANNELS; i++) {
                        // Integer math: znacznie szybsze niż (val - 992) / 1.6
                        uint16_t val_us = (uint16_t)(((temp_channels[i] - 992) * 5) / 8 + 1500);
                        
                        if (val_us < 1000) val_us = 1000;
                        if (val_us > 2000) val_us = 2000;
                        
                        channels[i] = val_us;
                    }
                    lastCRSFTime = millis();
                    portEXIT_CRITICAL(&timerMux);
                }
                index = 0; // Reset bufora
            }
        }
        
        if (index >= sizeof(buffer)) {
            index = 0;
        }
    }
}

// ============================================================================
// Inicjalizacja (Setup)
// ============================================================================
void setup() {
#ifdef BOARD_ESP32_CAM
    RC_SERIAL.begin(420000); 
#else
    Serial.begin(115200); 
    Serial1.begin(420000, SERIAL_8N1, 16, 17); 
#endif

    // Sprzętowy Open-Drain – zabezpiecza starsze aparatury RC!
    pinMode(OUTPUT_PIN, OUTPUT_OPEN_DRAIN);
    digitalWrite(OUTPUT_PIN, HIGH);
    
    pinMode(LED_PIN, OUTPUT);
    digitalWrite(LED_PIN, HIGH); // Wyłączona na starcie (Active LOW)

    // ESP32 Core 3.x API: timerBegin(częstotliwość) -> 1MHz = 1 tick / us
    timer = timerBegin(1000000); 
    timerAttachInterrupt(timer, &onTimer);
    timerAlarm(timer, 1000, true, 0);
    timerStart(timer);
    
    lastCRSFTime = millis();
    DEBUG_PRINTLN("[CoProcessor] Uruchomiono. Oczekiwanie na ramki CRSF...");
}

// ============================================================================
// Główna pętla
// ============================================================================
void loop() {
    parseCRSF();
    
    // Watchdog: Brak ramek > 500 ms -> Failsafe
    if (millis() - lastCRSFTime > 500) {
        if (!isFailsafeActive) {
            isFailsafeActive = true;
            DEBUG_PRINTLN("[WARN] Failsafe aktywne! Brak ramek z RPi. Wyłączam sygnał PPM.");
            
            portENTER_CRITICAL(&timerMux);
            timerStop(timer);
            digitalWrite(OUTPUT_PIN, HIGH); // Puszczamy linię luzem (Hi-Z)
            portEXIT_CRITICAL(&timerMux);
        }
    } else {
        if (isFailsafeActive) {
            isFailsafeActive = false;
            DEBUG_PRINTLN("[INFO] Odzyskano połączenie. Aktywuję sygnał PPM.");
            
            portENTER_CRITICAL(&timerMux);
            currentChannel = 0;
            currentFrameSum = 0;
            ppmState = PPM_PULSE;
            
            for (uint8_t i = 0; i < PPM_CHANNELS; i++) {
                working_channels[i] = channels[i];
            }

            timerWrite(timer, 0);
            timerAlarm(timer, 1, true, 0);
            timerStart(timer);
            portEXIT_CRITICAL(&timerMux);
        }
    }
    
    // Diagnostyka co 1 sek (Wyciszona dla ESP32-CAM, by nie przerywać CRSF!)
    static uint32_t lastLog = 0;
    if (millis() - lastLog > 1000) {
        DEBUG_PRINT("[STATUS] OK | ISR: ");
        DEBUG_PRINT(isrCount);
        DEBUG_PRINT(" | CH1: ");
        DEBUG_PRINT(channels[0]);
        DEBUG_PRINT(" | CH3 (Thr): ");
        DEBUG_PRINT(channels[2]);
        DEBUG_PRINT(" | FS: ");
        DEBUG_PRINTLN(isFailsafeActive ? "ACTIVE" : "OFF");
        lastLog = millis();
    }

    // Obsługa diody statusowej (GPIO 33, Active LOW)
    static uint32_t lastBlink = 0;
    static bool ledState = false;
    uint32_t blinkInterval = isFailsafeActive ? 100 : 1000; // Szybkie = Failsafe, Wolne = OK

    if (millis() - lastBlink > blinkInterval) {
        ledState = !ledState;
        digitalWrite(LED_PIN, ledState ? LOW : HIGH);
        lastBlink = millis();
    }
}