#include <Arduino.h>

uint16_t rc_channels[16]; // Tablica na odebrane kanały (1000-2000 us)
uint8_t buffer[35];       // Bufor na ramkę danych

void readSerialRC() {
    if (Serial.available() >= 35) {
        // Szukamy bajtów synchronizacyjnych
        if (Serial.peek() == 0xAA) {
            Serial.readBytes(buffer, 35);
            
            if (buffer[0] == 0xAA && buffer[1] == 0x55) {
                // Weryfikacja sumy kontrolnej XOR
                uint8_t calculated_xor = 0;
                for (int i = 2; i < 34; i++) {
                    calculated_xor ^= buffer[i];
                }
                
                if (calculated_xor == buffer[34]) {
                    // Kopiowanie danych bezpośrednio do tablicy kanałów
                    memcpy(rc_channels, &buffer[2], 32);
                    
                    // W tym miejscu rc_channels zawiera aktualne wartości 1000-2000 us
                }
            }
        } else {
            Serial.read(); // Odrzucenie błędnego bajtu, aby wyrównać strumień
        }
    }
}