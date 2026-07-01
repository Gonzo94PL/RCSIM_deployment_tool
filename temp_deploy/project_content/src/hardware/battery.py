"""
src/hardware/battery.py
Moduł monitorowania baterii przez I2C.
Obsługuje układ INA219 (typowy dla nakładek UPS Waveshare RPi).
Adresy I2C: 0x40 (domyślny INA219) lub 0x42 (Waveshare UPS Hat).
Pakiet 2S LiPo: 100% = 8.4V, 0% = 6.4V.
"""
import logging

logger = logging.getLogger(__name__)

# Rejestry INA219
_REG_CONFIGURATION = 0x00
_REG_SHUNT_VOLTAGE  = 0x01
_REG_BUS_VOLTAGE    = 0x02
_REG_POWER          = 0x03
_REG_CURRENT        = 0x04
_REG_CALIBRATION    = 0x05

# Wartości demonstracyjne gdy brak sprzętu I2C
_DEMO_VOLTAGE = 7.80


class BatteryMonitor:
    """
    Monitor baterii oparty na INA219 przez magistralę I2C.
    Przy braku dostępnego I2C przechodzi w tryb bezpieczny (demo),
    co zapobiega awarii aplikacji na maszynach deweloperskich.
    """

    def __init__(self, bus_id: int = 1, address: int = 0x42) -> None:
        self.bus_id = bus_id
        self.address = address
        self._bus = None
        self.enabled = False
        
        # Parametry kalibracji INA219 (zgodne z ups.py)
        self.shunt_ohms = 0.1
        self.max_expected_amps = 2.0
        self._current_lsb = 0.0
        self._power_lsb = 0.0
        
        self._try_init()

    def update_config(self, address_hex: str) -> None:
        """Dynamiczna aktualizacja adresu I2C urządzenia."""
        try:
            addr = int(address_hex, 16)
            if addr != self.address:
                logger.info("BatteryMonitor: Zmiana adresu I2C z 0x%02X na 0x%02X", self.address, addr)
                self.address = addr
                self.enabled = False
                if self._bus is not None:
                    try:
                        self._bus.close()
                    except Exception:
                        pass
                    self._bus = None
                self._try_init()
        except Exception as exc:
            logger.error("BatteryMonitor: Błąd aktualizacji konfiguracji adresu I2C: %s", exc)

    def _write_register(self, register: int, value: int) -> None:
        """Zapisuje 16-bitową wartość do rejestru INA219 (Big-Endian)."""
        if self._bus is None:
            return
        try:
            data = [(value >> 8) & 0xFF, value & 0xFF]
            self._bus.write_i2c_block_data(self.address, register, data)
        except Exception as exc:
            logger.debug("BatteryMonitor: Błąd zapisu do rejestru 0x%02X: %s", register, exc)

    def _read_register(self, register: int) -> int:
        """Odczytuje 16-bitową wartość z rejestru INA219 (Big-Endian)."""
        if self._bus is None:
            return 0
        try:
            data = self._bus.read_i2c_block_data(self.address, register, 2)
            if len(data) >= 2:
                return (data[0] << 8) | data[1]
            return 0
        except Exception as exc:
            logger.debug("BatteryMonitor: Błąd odczytu z rejestru 0x%02X: %s", register, exc)
            return 0

    def _calibrate(self) -> None:
        """Konfiguruje i kalibruje INA219."""
        if self._bus is None:
            return

        self._current_lsb = self.max_expected_amps / 32768.0
        cal_value = int(0.04096 / (self._current_lsb * self.shunt_ohms))
        self._write_register(_REG_CALIBRATION, cal_value)

        self._power_lsb = self._current_lsb * 20.0

        # Reset & Config (takie same bity konfiguracyjne jak w ups.py)
        config = 0b0000_0001_1001_1111
        config &= ~0x2000
        config &= ~0x1800
        config |= 0b10 << 11
        config |= 0b0110 << 7
        config |= 0b0110 << 3
        config |= 0b111

        self._write_register(_REG_CONFIGURATION, config)
        logger.debug(
            "BatteryMonitor: INA219 skalibrowany. Kalibracja: %d, config: %s",
            cal_value, bin(config)
        )

    def _try_init(self) -> None:
        """Próba otwarcia magistrali I2C. Przy braku sprzętu przełącza w tryb demo."""
        try:
            import smbus2  # type: ignore
            self._bus = smbus2.SMBus(self.bus_id)
            # Próba kalibracji i sprawdzenie komunikacji
            self._calibrate()
            # Odczyt próbny rejestru konfiguracji w celu potwierdzenia obecności układu
            cfg = self._read_register(_REG_CONFIGURATION)
            if cfg != 0:
                self.enabled = True
                logger.info(
                    "BatteryMonitor: INA219 wykryty i skalibrowany na szynie I2C-%d, adres 0x%02X",
                    self.bus_id, self.address
                )
            else:
                raise OSError("INA219 zwrócił pusty rejestr konfiguracji")
        except ImportError:
            logger.warning("BatteryMonitor: biblioteka smbus2 niedostępna — tryb demo.")
        except Exception as exc:
            logger.warning(
                "BatteryMonitor: Brak dostępu do I2C (bus=%d, addr=0x%02X): %s — tryb demo.",
                self.bus_id, self.address, exc
            )
        finally:
            if not self.enabled and self._bus is not None:
                try:
                    self._bus.close()
                except Exception:
                    pass
                self._bus = None

    def read_voltage(self) -> float:
        """Zwraca napięcie w woltach [V]. W trybie demo zwraca _DEMO_VOLTAGE."""
        if not self.enabled or self._bus is None:
            return _DEMO_VOLTAGE

        try:
            raw = self._read_register(_REG_BUS_VOLTAGE)
            voltage = (raw >> 3) * 0.004  # LSB = 4 mV
            return round(voltage, 3)
        except Exception as exc:
            logger.error("BatteryMonitor: błąd odczytu napięcia: %s", exc)
            return _DEMO_VOLTAGE

    def read_current(self) -> float:
        """Zwraca prąd w miliamperach [mA]. W trybie demo zwraca 0.0."""
        if not self.enabled or self._bus is None:
            return 0.0

        try:
            raw = self._read_register(_REG_CURRENT)
            if raw > 32767:
                raw -= 65536
            current = raw * self._current_lsb * 1000.0
            return round(current, 2)
        except Exception as exc:
            logger.error("BatteryMonitor: błąd odczytu prądu: %s", exc)
            return 0.0

    def read_power(self) -> float:
        """Zwraca moc w watach [W]. W trybie demo zwraca 0.0."""
        if not self.enabled or self._bus is None:
            return 0.0

        try:
            raw = self._read_register(_REG_POWER)
            power = raw * self._power_lsb
            return round(power, 3)
        except Exception as exc:
            logger.error("BatteryMonitor: błąd odczytu mocy: %s", exc)
            return 0.0

    def get_percentage(self, voltage: float) -> int:
        """Przelicza napięcie na procent naładowania z automatyczną detekcją ogniw LiPo (2S-6S)."""
        # Automatyczne wykrywanie liczby ogniw LiPo
        if voltage > 18.0:
            cells = 6
        elif voltage > 13.0:
            cells = 4
        elif voltage > 9.0:
            cells = 3
        else:
            cells = 2

        v_max = cells * 4.2
        v_min = cells * 3.2

        if voltage >= v_max:
            return 100
        if voltage <= v_min:
            return 0
        pct = (voltage - v_min) / (v_max - v_min) * 100.0
        return max(0, min(100, int(pct)))

    def get_status(self) -> dict:
        """
        Zwraca słownik statusu baterii gotowy do serializacji JSON.
        Klucze: voltage [V], percentage [%], current [mA], power [W], i2c_active [bool], demo_mode [bool].
        """
        voltage = self.read_voltage()
        percentage = self.get_percentage(voltage)
        current = self.read_current()
        power = self.read_power()
        return {
            "voltage": voltage,
            "percentage": percentage,
            "current": current,
            "power": power,
            "i2c_active": self.enabled,
            "demo_mode": not self.enabled,
        }

    def close(self) -> None:
        """Bezpieczne zamknięcie magistrali I2C."""
        if self._bus is not None:
            try:
                self._bus.close()
                logger.info("BatteryMonitor: magistrala I2C zamknięta.")
            except Exception as exc:
                logger.warning("BatteryMonitor: błąd zamykania I2C: %s", exc)
            finally:
                self._bus = None
                self.enabled = False