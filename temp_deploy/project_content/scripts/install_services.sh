#!/bin/bash

# Uruchamiać jako root/sudo
if [ "$EUID" -ne 0 ]; then
  echo "Uruchom ten skrypt z uprawnieniami root (sudo)!"
  exit 1
fi

echo "[Install] Tworzenie katalogu docelowego w /opt/..."
mkdir -p /opt/usb_rc_converter
cp -r . /opt/usb_rc_converter
cd /opt/usb_rc_converter

echo "[Install] Tworzenie środowiska wirtualnego venv..."
python3 -m venv venv
./venv/bin/pip install --upgrade pip
./venv/bin/pip install -r requirements.txt

echo "[Install] Dodawanie użytkownika 'root' do grup wejściowych (I2C/Input)..."
usermod -aG input root
usermod -aG i2c root

echo "[Install] Rejestracja usługi w systemd..."
cp systemd/usb_rc.service /etc/systemd/system/
systemctl daemon-reload
systemctl enable usb_rc.service

echo "[Install] Uruchamianie usługi..."
systemctl restart usb_rc.service

echo "[Install] Sukces! Status usługi:"
systemctl status usb_rc.service --no-pager
