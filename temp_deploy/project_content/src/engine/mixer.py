"""
src/engine/mixer.py
Mikser kanałów oraz obsługa profili RC (np. skrzydła typu delta / elevons, V-tail).
"""

class ChannelMixer:
    """
    Obsługuje miksowanie sygnałów cyfrowych.
    """
    @staticmethod
    def mix_elevons(aileron: float, elevator: float) -> tuple[float, float]:
        """
        Klasyczny mikser dla latających skrzydeł (Elevon / Delta).
        Używa wejść lotek (Aileron) oraz wysokości (Elevator), mieszając je na lewe i prawe skrzydło:
        Left Elevon = Elevator + Aileron
        Right Elevon = Elevator - Aileron
        Wartości wejściowe i wyjściowe w znormalizowanym zakresie [-1.0 .. 1.0].
        """
        left = elevator + aileron
        right = elevator - aileron
        
        # Ograniczenia i normalizacja
        left = max(-1.0, min(1.0, left))
        right = max(-1.0, min(1.0, right))
        return left, right

    @staticmethod
    def mix_vtail(rudder: float, elevator: float) -> tuple[float, float]:
        """
        Mikser ogona typu V-tail (np. szybowce).
        Lewy ster = Elevator + Rudder
        Prawy ster = Elevator - Rudder
        """
        left = elevator + rudder
        right = elevator - rudder
        
        left = max(-1.0, min(1.0, left))
        right = max(-1.0, min(1.0, right))
        return left, right
