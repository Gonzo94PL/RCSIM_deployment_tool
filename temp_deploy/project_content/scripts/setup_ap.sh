#!/bin/bash
# ==============================================================================
# Skrypt konfiguracji lokalnego punktu dostępowego Wi-Fi (AP) dla Raspberry Pi 5.
# Umożliwia jednoczesne połączenie z domową siecią Wi-Fi (skonfigurowaną w Imagerze)
# oraz rozgłaszanie własnego, otwartego hotspotu AP o nazwie "RCSIM_MCS" (bez hasła).
# ==============================================================================

# Kolory dla konsoli
YELLOW='\033[1;33m'
GREEN='\033[1;32m'
RED='\033[1;31m'
NC='\033[0m' # No Color

echo -e "${YELLOW}=== Konfiguracja Wi-Fi Access Point (Hotspot) RCSIM_MCS na RPi 5 ===${NC}"

# Weryfikacja konta root
if [ "$EUID" -ne 0 ]; then
  echo -e "${RED}[Error] Wykonaj ten skrypt z uprawnieniami sudo!${NC}"
  exit 1
fi

# Na nowym systemie Raspberry Pi OS (Bookworm) standardem jest NetworkManager
if command -v nmcli &> /dev/null; then
  echo -e "${GREEN}[SYSTEM] Wykryto NetworkManager. Konfiguracja jednoczesnego AP + STA (Multi-AP)...${NC}"
  
  # Usunięcie starej konfiguracji hotspotu jeśli istnieje
  nmcli connection delete RCSIM_MCS_AP &> /dev/null
  nmcli connection delete Hotspot &> /dev/null
  
  # RPi 5 / Bookworm wymaga współdzielenia tego samego kanału radiowego co sieć domowa (STA)
  # Pobieramy aktualny kanał, na którym wlan0 połączyło się z domowym Wi-Fi
  CURR_CHAN=$(iw dev wlan0 info 2>/dev/null | grep channel | awk '{print $2}')
  if [ -z "$CURR_CHAN" ]; then
    CURR_CHAN="1" # Fallback na kanał 1 jeśli brak połączenia
  fi
  echo "[SYSTEM] Domowe Wi-Fi działa na kanale: $CURR_CHAN. Ustawiam ten sam kanał dla AP..."

  # RPi 5 i NetworkManager w Bookworm najlepiej radzą sobie ze współdzieleniem,
  # jeśli dodamy połączenie i powiążemy je z wirtualnym interfejsem wlan0-hotspot
  # który NM sam automatycznie tworzy, gdy ifname jest wlan0 i mode to ap.
  # Aby uniknąć rozłączania STA, kluczowe jest nieblokowanie pasma i zgodność kanałów.
  
  echo "[SYSTEM] Konfiguracja połączenia NM Hotspot z hasłem na wlan0 (zgodność kanałów)..."
  nmcli connection add type wifi ifname wlan0 con-name RCSIM_MCS_AP ssid RCSIM_MCS mode ap
  nmcli connection modify RCSIM_MCS_AP 802-11-wireless.mode ap 802-11-wireless.band bg 
  nmcli connection modify RCSIM_MCS_AP 802-11-wireless.channel "$CURR_CHAN"
  nmcli connection modify RCSIM_MCS_AP ipv4.method shared
  nmcli connection modify RCSIM_MCS_AP 802-11-wireless-security.key-mgmt wpa-psk
  nmcli connection modify RCSIM_MCS_AP 802-11-wireless-security.psk "RCSIM_GORIDE"
  
  # Zapewnienie, że połączenie nie rozłączy połączenia STA
  nmcli connection modify RCSIM_MCS_AP connection.autoconnect yes
  
  # Uruchomienie hotspotu
  if nmcli connection up RCSIM_MCS_AP; then
    echo -e "${GREEN}[SUKCES] Hotspot został pomyślnie uruchomiony!${NC}"
    echo -e "${YELLOW}SSID: RCSIM_MCS${NC}"
    echo -e "${YELLOW}Hasło: RCSIM_GORIDE${NC}"
    echo -e "${YELLOW}RPi jednocześnie utrzymuje połączenie klienckie Wi-Fi (STA).${NC}"
    echo -e "${YELLOW}Adres IP bramy RPi (AP): 10.42.0.1 (Wejdź na http://10.42.0.1:8080)${NC}"
  else
    echo -e "${RED}[BŁĄD] Nie udało się podnieść hotspotu na wlan0 przy jednoczesnym STA.${NC}"
    echo -e "${YELLOW}[PRÓBA RATUNKOWA] Rozłączanie z Wi-Fi domowym w celu podniesienia samego AP...${NC}"
    nmcli device disconnect wlan0 &>/dev/null || true
    sleep 1
    if nmcli connection up RCSIM_MCS_AP; then
      echo -e "${GREEN}[SUKCES] Uruchomiono AP w trybie autonomicznym (bez połączenia z siecią domową).${NC}"
    else
      echo -e "${RED}[BŁĄD KRYTYCZNY] Nie można uruchomić interfejsu bezprzewodowego.${NC}"
    fi
  fi
  
else
  # Starsze wersje / fallback do hostapd + dnsmasq
  echo -e "${YELLOW}[SYSTEM] Brak nmcli. Wykryto tradycyjne zarządzanie interfejsami (hostapd + dnsmasq)...${NC}"
  
  echo "Instalacja pakietów..."
  apt-get update && apt-get install -y hostapd dnsmasq iw
  
  # Tworzenie wirtualnego interfejsu uap0 do obsługi AP równolegle z wlan0
  echo "Konfiguracja wirtualnego interfejsu uap0..."
  iw dev wlan0 interface add uap0 type __ap 2>/dev/null || true
  
  systemctl stop hostapd
  systemctl stop dnsmasq
  
  # Konfiguracja dhcpcd.conf
  echo "Konfiguracja stałego IP na uap0 w /etc/dhcpcd.conf..."
  if ! grep -q "interface uap0" /etc/dhcpcd.conf; then
    echo -e "\ninterface uap0\nstatic ip_address=192.168.4.1/24\nnohook wpa_supplicant" >> /etc/dhcpcd.conf
  fi
  
  # Konfiguracja hostapd
  echo "Tworzenie pliku konfiguracyjnego /etc/hostapd/hostapd.conf dla uap0..."
  cat <<EOF > /etc/hostapd/hostapd.conf
interface=uap0
driver=nl80211
ssid=RCSIM_MCS
hw_mode=g
channel=7
wmm_enabled=0
macaddr_acl=0
auth_algs=1
ignore_broadcast_ssid=0
wpa=2
wpa_passphrase=RCSIM_GORIDE
wpa_key_mgmt=WPA-PSK
wpa_pairwise=TKIP
rsn_pairwise=CCMP
EOF

  # Podłączenie pliku konfiguracyjnego do daemona systemowego
  sed -i 's|#DAEMON_CONF=""|DAEMON_CONF="/etc/hostapd/hostapd.conf"|g' /etc/default/hostapd

  # Konfiguracja dnsmasq
  mv /etc/dnsmasq.conf /etc/dnsmasq.conf.bak &> /dev/null
  cat <<EOF > /etc/dnsmasq.conf
interface=uap0
dhcp-range=192.168.4.2,192.168.4.20,255.255.255.0,24h
EOF

  # Zapewnienie podnoszenia uap0 przy każdym starcie systemu przed hostapd
  if ! grep -q "iw dev wlan0 interface add uap0 type __ap" /etc/rc.local; then
    sed -i '/exit 0/i iw dev wlan0 interface add uap0 type __ap && ip link set uap0 up' /etc/rc.local
  fi

  # Uruchomienie i włączenie usług
  systemctl daemon-reload
  systemctl unmask hostapd
  systemctl enable hostapd
  systemctl enable dnsmasq
  
  systemctl start hostapd
  systemctl start dnsmasq
  
  echo -e "${GREEN}[SUKCES] Hotspot Wi-Fi hostapd na uap0 uruchomiony!${NC}"
  echo -e "${YELLOW}SSID: RCSIM_MCS (Otwarty)${NC}"
  echo -e "${YELLOW}Adres IP RPi dla uap0: 192.168.4.1 (Wejdź na http://192.168.4.1:8080)${NC}"
fi

