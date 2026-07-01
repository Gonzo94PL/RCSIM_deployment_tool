"""
src/input/evdev_reader.py
Wątek przetwarzający zdarzenia wejściowe (Linux evdev) z joysticków USB HID.
"""
import logging
import os
import threading
import time
from typing import Any

from src.engine.curves import apply_expo, map_value_with_limits, apply_deadband
from src.engine.state import RCState

logger = logging.getLogger(__name__)

# Przekładnik kodów osi evdev na czytelny format np. ABS_X -> "Oś X"
EV_ABS_MAP = {
    0: "ABS_X",        # Zazwyczaj lewy drążek poziomo
    1: "ABS_Y",        # Zazwyczaj lewy drążek pionowo
    2: "ABS_Z",        # Często pedał sprzęgła / oś pomocnicza
    3: "ABS_RX",       # Prawy drążek poziomo
    4: "ABS_RY",       # Prawy drążek pionowo
    5: "ABS_RZ",       # Często oś pomocnicza / prawy trigger na niektórych padach
    6: "ABS_THROTTLE", # Przepustnica
    7: "ABS_RUDDER",   # Rudder
    8: "ABS_WHEEL",    # Koło kierownicy
    9: "ABS_GAS",      # Gaz (standardowy prawy trigger RT w evdev)
    10: "ABS_BRAKE",   # Hamulec (standardowy lewy trigger LT w evdev)
    16: "ABS_HAT0X",   # D-Pad X
    17: "ABS_HAT0Y",   # D-Pad Y
    18: "ABS_HAT1X",   # Hat 1 X
    19: "ABS_HAT1Y",   # Hat 1 Y
    20: "ABS_HAT2X",   # Hat 2 X
    21: "ABS_HAT2Y",   # Hat 2 Y
    22: "ABS_HAT3X",   # Hat 3 X
    23: "ABS_HAT3Y",   # Hat 3 Y
    40: "ABS_MISC",    # Różne
}

try:
    import evdev  # type: ignore
    for code, name in evdev.ecodes.ABS.items():
        if code not in EV_ABS_MAP:
            EV_ABS_MAP[code] = name
except ImportError:
    pass


class EvdevReader(threading.Thread):
    def __init__(self, device_path: str, mappings: list[dict[str, Any]], rc_state: RCState, profile: dict[str, Any]) -> None:
        super().__init__(daemon=True, name=f"EvdevReader-{os.path.basename(device_path)}")
        self.device_path = device_path
        self.mappings = mappings
        self.rc_state = rc_state
        self.profile = profile
        self.running = False
        self._dev = None
        self._gas_val = 0.0
        self._brake_val = 0.0
        self._last_throttle_us = 1500
        
        # Sprawdzenie konfliktów przycisków w profilu
        buttons = {
            "cruise_btn": self.profile.get("cruise_btn", ""),
            "drive_mode_btn": self.profile.get("drive_mode_btn", ""),
            "arm_btn": self.profile.get("arm_btn", ""),
            "gear_up": self.profile.get("gearbox_config", {}).get("btn_up", ""),
            "gear_down": self.profile.get("gearbox_config", {}).get("btn_down", "")
        }
        active_buttons = {k: v for k, v in buttons.items() if v}
        seen = {}
        for key, btn in active_buttons.items():
            if btn in seen:
                logger.warning(
                    "KONFLIKT MAPOWANIA: Przycisk '%s' jest przypisany do wielu funkcji jednocześnie: '%s' oraz '%s'!",
                    btn, seen[btn], key
                )
            else:
                seen[btn] = key

    def apply_failsafe(self) -> None:
        """Stosuje ustawienia failsafe dla wszystkich zmapowanych kanałów wejściowych."""
        logger.info("EvdevReader: Zastosowanie procedury failsafe dla %s", self.device_path)
        for mapping in self.mappings:
            channel = int(mapping.get("channel", 1))
            failsafe_mode = mapping.get("failsafe_mode", "center")
            
            # Wartości sub_trim i limity
            sub_trim = int(mapping.get("sub_trim", 0))
            min_limit = int(mapping.get("min_limit", 1000))
            max_limit = int(mapping.get("max_limit", 2000))
            
            is_throttle = mapping.get("name", "").lower() == "throttle"
            if is_throttle and failsafe_mode == "hold":
                logger.warning("EvdevReader: Tryb failsafe 'hold' jest niedozwolony dla gazu (throttle). Wymuszam 'center' dla bezpieczeństwa.")
                failsafe_mode = "center"
            
            if failsafe_mode == "center":
                # Ustawiamy kanał w pozycji środkowej
                center_val = 1500 + sub_trim
                final_val = max(min_limit, min(max_limit, center_val))
                self.rc_state.set_channel(channel, final_val)
            elif failsafe_mode == "custom":
                # Ustawiamy kanał na zdefiniowaną wartość niestandardową
                failsafe_val = int(mapping.get("failsafe_value", 1500))
                final_val = max(min_limit, min(max_limit, failsafe_val))
                self.rc_state.set_channel(channel, final_val)
            elif failsafe_mode == "hold":
                # 'hold' -> pozostawiamy ostatnią przetworzoną wartość (nic nie robimy)
                pass

    def run(self) -> None:
        self.running = True
        logger.info("EvdevReader: Uruchomiono wątek dla %s", self.device_path)
        
        while self.running:
            try:
                import evdev # type: ignore
                self._dev = evdev.InputDevice(self.device_path)
                logger.info("EvdevReader: Otwarto urządzenie: %s (%s)", self._dev.name, self._dev.path)
                
                # Obsługa FFB Auto-Center i Kąta Skrętu
                ffb_val = 0
                steering_range = 900
                hardware_range = 900
                for input_cfg in self.profile.get("inputs", []):
                    cfg_dev_name = input_cfg.get("device_name", "")
                    if cfg_dev_name.lower() in self._dev.name.lower() or self._dev.name.lower() in cfg_dev_name.lower():
                        ffb_val = input_cfg.get("ffb_autocenter", 0)
                        steering_range = input_cfg.get("steering_range", 900)
                        hardware_range = input_cfg.get("hardware_range", 900)
                        break
                
                if ffb_val > 0:
                    ffb_write_val = int((ffb_val / 100.0) * 65535)
                    try:
                        self._dev.write(evdev.ecodes.EV_FF, evdev.ecodes.FF_AUTOCENTER, ffb_write_val)
                        logger.info("EvdevReader: Ustawiono auto-center FFB na %d%% (%d) dla %s", ffb_val, ffb_write_val, self._dev.name)
                    except Exception as e:
                        logger.warning("EvdevReader: Nie udało się ustawić FFB dla %s: %s", self._dev.name, e)

                if steering_range > 0:
                    try:
                        import glob
                        paths = (glob.glob("/sys/class/leds/*g29*/device/range") +
                                 glob.glob("/sys/class/leds/*g27*/device/range") +
                                 glob.glob("/sys/class/leds/*g920*/device/range") +
                                 glob.glob("/sys/bus/hid/drivers/logitech/*/range"))
                        for p in paths:
                            try:
                                with open(p, "w") as f:
                                    f.write(str(steering_range))
                                logger.info("EvdevReader: Ustawiono sprzętowy zakres skrętu na %d stopni w %s", steering_range, p)
                            except Exception as e:
                                logger.warning("EvdevReader: Błąd zapisu zakresu skrętu do %s: %s", p, e)
                    except Exception as e:
                        logger.warning("EvdevReader: Błąd przy wyszukiwaniu urządzeń kierownicy Logitech: %s", e)

                self._soft_lock_effect_id = -1
                if steering_range < hardware_range and steering_range > 0:
                    try:
                        # Obliczamy martwą strefę sprężyny (zakres skrętu jako ułamek zakresu sprzętowego)
                        deadband_val = int((steering_range / hardware_range) * 0xffff)
                        condition = evdev.ff.Condition(
                            right_coeff=0x7fff,      # Maksymalna sztywność po prawej
                            left_coeff=0x7fff,       # Maksymalna sztywność po lewej
                            right_saturation=0xffff, # Maksymalna siła po prawej
                            left_saturation=0xffff,  # Maksymalna siła po lewej
                            deadband=deadband_val,   # Swobodny ruch w zadanym zakresie skrętu
                            center=0
                        )
                        effect = evdev.ff.Effect(
                            evdev.ecodes.FF_SPRING,
                            -1,
                            0,
                            evdev.ff.Trigger(0, 0),
                            evdev.ff.Replay(0xffff, 0),
                            evdev.ff.EffectData(condition=[condition, condition])
                        )
                        self._soft_lock_effect_id = self._dev.upload_effect(effect)
                        self._dev.write(evdev.ecodes.EV_FF, self._soft_lock_effect_id, 1)
                        logger.info("EvdevReader: Załadowano sprzętowy soft-lock FFB dla %s (martwa strefa: %d)", self._dev.name, deadband_val)
                    except Exception as e:
                        logger.warning("EvdevReader: Urządzenie %s nie obsługuje efektu FF_SPRING (%s). Soft-lock będzie realizowany programowo.", self._dev.name, e)

                # Odczyt osi oraz ich limitów kalibracji
                abs_info = {}
                for code, info in self._dev.capabilities().get(evdev.ecodes.EV_ABS, []):
                    # info format: InputAbsInfo(value, min, max, fuzz, flat, resolution)
                    abs_info[code] = {
                        "min": info.min,
                        "max": info.max,
                        "range": info.max - info.min if info.max > info.min else 1
                    }
                    
                for event in self._dev.read_loop():
                    if not self.running:
                        break
                        
                    # Filtr zdarzeń joysticka: EV_ABS (ruch osi) lub EV_KEY (przyciski)
                    if event.type == evdev.ecodes.EV_ABS:
                        code = event.code
                        val = event.value
                        
                        # Pobranie specyfikacji osi i normalizacja do zakresu [-1.0 .. 1.0]
                        info = abs_info.get(code)
                        if info:
                            # Normalizuj z zakresu [min, max] pod [-1.0, 1.0]
                            normalized = 2.0 * (val - info["min"]) / info["range"] - 1.0
                        else:
                            # podstawowa normalizacja
                            normalized = val / 32768.0
                            
                        # Przypisanie do zmapowanych kanałów wyjściowych
                        axis_name = EV_ABS_MAP.get(code, f"ABS_{code}")
                        
                        for mapping in self.mappings:
                            # 1. Standardowe dopasowanie osi (lub Gaz dla Split Axis)
                            is_gas = mapping.get("axis") == axis_name
                            is_brake = mapping.get("axisBrake") == axis_name
                            is_split = mapping.get("type") == "split_axis"
                            is_throttle = mapping.get("name", "").lower() == "throttle"

                            if is_gas or (is_split and is_brake):
                                # Określamy czy używamy głównej osi czy hamulca osi dzielonej
                                if is_gas:
                                    raw_min = mapping.get("raw_min")
                                    raw_max = mapping.get("raw_max")
                                    raw_center = mapping.get("raw_center")
                                else:
                                    raw_min = mapping.get("raw_min_brake")
                                    raw_max = mapping.get("raw_max_brake")
                                    raw_center = None

                                # Bezpieczna konwersja na int
                                try:
                                    raw_min = int(raw_min) if raw_min is not None else None
                                    raw_max = int(raw_max) if raw_max is not None else None
                                    raw_center = int(raw_center) if raw_center is not None else None
                                except (ValueError, TypeError):
                                    raw_min = None
                                    raw_max = None
                                    raw_center = None

                                if raw_min is not None and raw_max is not None:
                                    val_range = float(raw_max - raw_min)
                                    if val_range == 0:
                                        val_range = 1.0
                                    t = (val - raw_min) / val_range
                                    t = max(0.0, min(1.0, t))
                                    if raw_center is not None:
                                        t_center = (raw_center - raw_min) / val_range
                                        if 0.0 < t_center < 1.0:
                                            if t < t_center:
                                                m_normalized = (t - t_center) / t_center
                                            else:
                                                m_normalized = (t - t_center) / (1.0 - t_center)
                                        else:
                                            m_normalized = 2.0 * t - 1.0
                                    else:
                                        m_normalized = 2.0 * t - 1.0
                                else:
                                    m_normalized = normalized

                                channel = int(mapping.get("channel", 1))
                                
                                # Zapisujemy stany stateful dla osi dzielonej z uwzględnieniem strefy martwej
                                if is_gas:
                                    gas_db = float(mapping.get("deadband", 0.02))
                                    self._gas_val = apply_deadband(max(0.0, m_normalized), gas_db)
                                if is_split and is_brake:
                                    brake_db = float(mapping.get("deadbandBrake", 0.02))
                                    self._brake_val = apply_deadband(max(0.0, m_normalized), brake_db)
                                    
                                # Jeśli to jest oś dzielona (Split Axis)
                                if is_split:
                                    # Failsafe dla tempomatu w osi dzielonej
                                    cruise_active, cruise_us = self.rc_state.get_cruise()
                                    if cruise_active:
                                        if self._brake_val > 0.05:
                                            self.rc_state.set_cruise(False)
                                            logger.info("Cruise Control: wyłączony przez wciśnięcie hamulca.")
                                            cruise_active = False

                                    if cruise_active:
                                        final_us = cruise_us
                                    else:
                                        gearbox = self.rc_state.gearbox
                                        gear = gearbox.current_gear
                                        gas_lim = gearbox.get_current_throttle_limit()
                                        
                                        # Stosujemy Expo
                                        expo_gas = float(mapping.get("expo", 0))
                                        expo_brake = float(mapping.get("expoBrake", 0))
                                        
                                        gas_val = apply_expo(self._gas_val, expo_gas)
                                        brake_val = apply_expo(self._brake_val, expo_brake)
                                        
                                        # Uwzględnienie trybów jazdy (Drive Modes)
                                        drive_mode = self.rc_state.get_drive_mode()
                                        
                                        eff_gas = gas_val * gas_lim
                                        if drive_mode == "eco":
                                            eff_gas *= 0.5
                                        elif drive_mode == "crawler":
                                            eff_gas *= 0.2
                                        elif drive_mode == "wet":
                                            eff_gas *= 0.65
                                            
                                        epa_min = int(mapping.get("min_limit", 1000))
                                        epa_max = int(mapping.get("max_limit", 2000))
                                        center = 1500 + int(mapping.get("sub_trim", 0))
                                        
                                        # Oblicz końcowy sygnał PWM na podstawie biegu
                                        if gear == 0:  # Neutral
                                            final_us = center
                                        elif gear == -1:  # Reverse
                                            if brake_val > 0.01:
                                                # Hamowanie podczas cofania -> ruch w przód (zwykły gaz)
                                                final_us = center + int(brake_val * (epa_max - center))
                                            elif eff_gas > 0.01:
                                                # Gaz podczas cofania -> ruch w tył
                                                final_us = center - int(eff_gas * (center - epa_min))
                                            else:
                                                final_us = center
                                        else:  # Bieg do przodu (1..N)
                                            if brake_val > 0.01:
                                                # Hamowanie podczas jazdy -> ruch w tył
                                                final_us = center - int(brake_val * (center - epa_min))
                                            elif eff_gas > 0.01:
                                                # Gaz podczas jazdy -> ruch w przód
                                                final_us = center + int(eff_gas * (epa_max - center))
                                            else:
                                                # Crawler Drag Brake
                                                if drive_mode == "crawler":
                                                    final_us = center - int(0.15 * (center - epa_min))
                                                else:
                                                    final_us = center
                                                    
                                        # Wet mode rate limiter (Slew rate filter)
                                        if drive_mode == "wet":
                                            max_step = 25
                                            diff = final_us - self._last_throttle_us
                                            if diff > max_step:
                                                final_us = self._last_throttle_us + max_step
                                            elif diff < -max_step:
                                                final_us = self._last_throttle_us - max_step
                                                
                                        self._last_throttle_us = final_us
                                        
                                    self.rc_state.set_channel(channel, final_us)
                                    
                                else:
                                    # Standardowa oś dwukierunkowa
                                    # Zastosuj software scaling dla skrętu (Aileron / Rudder), gdy zakres skrętu jest mniejszy od sprzętowego
                                    mapped_name = mapping.get("name", "").lower()
                                    if mapped_name in ("aileron", "rudder") and steering_range < hardware_range and steering_range > 0:
                                        scale = hardware_range / steering_range
                                        normalized_for_axis = max(-1.0, min(1.0, m_normalized * scale))
                                    else:
                                        normalized_for_axis = m_normalized

                                    # Zastosowanie strefy martwej (deadband)
                                    deadband = float(mapping.get("deadband", 0.02))
                                    normalized_for_axis = apply_deadband(normalized_for_axis, deadband)

                                    reverse = bool(mapping.get("reverse", False))
                                    sub_trim = int(mapping.get("sub_trim", 0))
                                    min_limit = int(mapping.get("min_limit", 1000))
                                    max_limit = int(mapping.get("max_limit", 2000))
                                    expo = float(mapping.get("expo", 0))
                                    
                                    # 1. Nałożenie expo
                                    expo_val = apply_expo(normalized_for_axis, expo)
                                    
                                    # 2. Skalowanie przez skrzynię biegów jeśli to Throttle
                                    if is_throttle:
                                        # Failsafe dla tempomatu
                                        cruise_active, cruise_us = self.rc_state.get_cruise()
                                        if cruise_active:
                                            if m_normalized < -0.05:
                                                self.rc_state.set_cruise(False)
                                                logger.info("Cruise Control: wyłączony przez ruch drążka wstecz.")
                                                cruise_active = False

                                        if cruise_active:
                                            us_val = cruise_us
                                        else:
                                            gearbox = self.rc_state.gearbox
                                            gear = gearbox.current_gear
                                            gas_lim = gearbox.get_current_throttle_limit()
                                            
                                            # Uwzględnienie trybów jazdy
                                            drive_mode = self.rc_state.get_drive_mode()
                                            
                                            if gear == 0:
                                                expo_val = 0.0
                                            elif gear == -1:
                                                if expo_val > 0.0:
                                                    expo_val = 0.0
                                                else:
                                                    if drive_mode == "eco":
                                                        expo_val *= 0.5
                                                    elif drive_mode == "crawler":
                                                        expo_val *= 0.2
                                                    elif drive_mode == "wet":
                                                        expo_val *= 0.65
                                                    expo_val *= gas_lim
                                            else:
                                                if expo_val > 0.0:
                                                    if drive_mode == "eco":
                                                        expo_val *= 0.5
                                                    elif drive_mode == "crawler":
                                                        expo_val *= 0.2
                                                    elif drive_mode == "wet":
                                                        expo_val *= 0.65
                                                    expo_val *= gas_lim
                                                    
                                            us_val = map_value_with_limits(expo_val, reverse, sub_trim, min_limit, max_limit)
                                            
                                            # Crawler drag brake (jeśli gaz jest w neutrum ok. 1500 us)
                                            if drive_mode == "crawler" and abs(expo_val) < 0.01:
                                                center = 1500 + sub_trim
                                                us_val = center - int(0.15 * (center - min_limit))
                                                
                                            # Slew rate limiter w trybie wet
                                            if drive_mode == "wet":
                                                max_step = 25
                                                diff = us_val - self._last_throttle_us
                                                if diff > max_step:
                                                    us_val = self._last_throttle_us + max_step
                                                elif diff < -max_step:
                                                    us_val = self._last_throttle_us - max_step
                                            self._last_throttle_us = us_val
                                    else:
                                        # Standardowa oś inna niż Throttle
                                        us_val = map_value_with_limits(expo_val, reverse, sub_trim, min_limit, max_limit)
                                        
                                    # 4. Zapis do głównego stanu
                                    self.rc_state.set_channel(channel, us_val)
                                
                    elif event.type == evdev.ecodes.EV_KEY:
                        # Wciśnięcia przycisków mapowane na skrajne pozycje pomocniczych kanałów (Aux)
                        code = event.code
                        val = event.value # 1 dla naciśnięcia, 0 dla zwolnienia
                        
                        btn_name = f"BTN_{code}"
                        
                        # Obsługa przycisków specjalnych (tylko rising edge, czyli val == 1)
                        if val == 1:
                            # 1. Skrzynia biegów
                            gearbox = self.rc_state.gearbox
                            if gearbox.config.get("mode", "none") == "sequential":
                                btn_up = gearbox.config.get("btn_up", "")
                                btn_down = gearbox.config.get("btn_down", "")
                                if btn_name == btn_up:
                                    gearbox.change_gear(1)
                                    self.rc_state.set_cruise(False)
                                    logger.info("Gearbox: Zmiana biegu w górę. Wyłączono Cruise Control.")
                                elif btn_name == btn_down:
                                    gearbox.change_gear(-1)
                                    self.rc_state.set_cruise(False)
                                    logger.info("Gearbox: Zmiana biegu w dół. Wyłączono Cruise Control.")
                                    
                            # 2. Tryb jazdy (Drive Mode)
                            mode_btn = self.profile.get("drive_mode_btn", "")
                            if btn_name == mode_btn:
                                current_mode = self.rc_state.get_drive_mode()
                                modes = ["sport", "eco", "crawler", "wet"]
                                next_index = (modes.index(current_mode) + 1) % len(modes)
                                self.rc_state.set_drive_mode(modes[next_index])
                                logger.info("Drive Mode: zmieniono tryb na %s przyciskiem.", modes[next_index])
                                
                            # 3. Tempomat (Cruise Control)
                            cruise_btn = self.profile.get("cruise_btn", "")
                            if btn_name == cruise_btn:
                                cruise_active, _ = self.rc_state.get_cruise()
                                if cruise_active:
                                    self.rc_state.set_cruise(False)
                                    logger.info("Cruise Control: wyłączony przyciskiem.")
                                else:
                                    # Pobierz obecny gaz i ustaw jako prędkość tempomatu (lub bezpieczne 1650 us)
                                    current_ch_val = self.rc_state.get_channel(3)
                                    if current_ch_val < 1520:
                                        current_ch_val = 1650
                                    self.rc_state.set_cruise(True, current_ch_val)
                                    logger.info("Cruise Control: włączony na wartość %d us przyciskiem.", current_ch_val)

                            # 4. Uzbrojenie (ARM / DISARM)
                            arm_btn = self.profile.get("arm_btn", "")
                            if btn_name == arm_btn:
                                current_paused = self.rc_state.is_paused()
                                self.rc_state.set_paused(not current_paused)
                                logger.info("Sygnał RC: %s przyciskiem kontrolera.", "DISARMED" if not current_paused else "ARMED")

                        
                        normalized = 1.0 if val else -1.0
                        
                        for mapping in self.mappings:
                            if mapping.get("axis") == btn_name:
                                channel = int(mapping.get("channel", 1))
                                reverse = bool(mapping.get("reverse", False))
                                sub_trim = int(mapping.get("sub_trim", 0))
                                min_limit = int(mapping.get("min_limit", 1000))
                                max_limit = int(mapping.get("max_limit", 2000))
                                
                                us_val = map_value_with_limits(normalized, reverse, sub_trim, min_limit, max_limit)
                                self.rc_state.set_channel(channel, us_val)
                                
            except ImportError:
                logger.error("EvdevReader: Biblioteka evdev niedostępna.")
                time.sleep(5)
            except Exception as e:
                logger.warning("EvdevReader: Błąd odczytu lub utrata połączenia dla %s: %s. Re-inicjalizacja za 2 s.", self.device_path, e)
                self.apply_failsafe()
                if self._dev:
                    if hasattr(self, "_soft_lock_effect_id") and self._soft_lock_effect_id != -1:
                        try:
                            self._dev.erase_effect(self._soft_lock_effect_id)
                        except Exception:
                            pass
                    try:
                        self._dev.close()
                    except Exception:
                        pass
                    self._dev = None
                time.sleep(2.0)
                 
        logger.info("EvdevReader: Zakończono dla %s", self.device_path)

    def stop(self) -> None:
        self.running = False
        self.apply_failsafe()
        if self._dev:
            if hasattr(self, "_soft_lock_effect_id") and self._soft_lock_effect_id != -1:
                try:
                    self._dev.erase_effect(self._soft_lock_effect_id)
                except Exception:
                    pass
            try:
                self._dev.close()
            except Exception:
                pass
            self._dev = None
