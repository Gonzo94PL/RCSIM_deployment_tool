#!/bin/bash
# ==============================================================================
# Skrypt uruchamiania systemu USB-to-RC w trybie developerskim / debugowania.
# ==============================================================================

# Wyczyszczenie konsoli
clear

echo -e "\e[1;34m======================================================================\e[0m"
echo -e "\e[1;36m           USB-to-RC CONVERTER - SYSTEM DIAGNOSTYCZNY (RPi 5)         \e[0m"
echo -e "\e[1;34m======================================================================\e[0m"

# Sprawdzenie uprawnień superużytkownika (evdev i magistrala I2C wymagają praw root)
if [ "$EUID" -ne 0 ]; then
  echo -e "\e[1;31m[Ostrzeżenie] Skrypt pownien być uruchomiony przez sudo w celu dostępu do USB HID i I2C!\e[0m"
  echo "Próba ponownego uruchomienia przez sudo..."
  sudo "$0" "$@"
  exit $?
fi

# Sprawdzanie obecności środowiska wirtualnego
if [ -d "venv" ]; then
  echo -e "\e[1;32m[SYSTEM] Wykryto lokalne środowisko wirtualne venv.\e[0m"
  source venv/bin/activate
else
  echo -e "\e[1;33m[SYSTEM] Brak lokalnego venv. Uruchamianie z globalnego parsera Python3.\e[0m"
fi

# Ustawienie zmiennej środowiskowej dla logowania w pełnym formacie DEBUG
export LOG_LEVEL=DEBUG

echo -e "\e[1;32m[SYSTEM] Start głównego wątku zasilania, portów i mikserów w konsoli...\e[0m"
python3 src/main.py
