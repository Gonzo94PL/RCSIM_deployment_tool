"""
src/engine/curves.py
Kalkulator krzywych wykładniczych (Expo) i skalowania sygnałów dla konwertera RC.
"""

def apply_expo(val: float, expo_percent: float) -> float:
    """
    Nakłada krzywą wykładniczą na znormalizowaną pozycję drążka [-1.0 .. 1.0].
    Wzór: y = (1 - e) * val + e * (val ^ 3)
    Gdzie:
        'e' to współczynnik wykładniczy [0.0 .. 1.0] (odzwierciedlający expo_percent od 0 do 100)
    """
    if val < -1.0:
        val = -1.0
    elif val > 1.0:
        val = 1.0
        
    e = max(0.0, min(100.0, expo_percent)) / 100.0
    return (1.0 - e) * val + e * (val ** 3)


def map_value_with_limits(val: float, reverse: bool, sub_trim: int, min_limit: int, max_limit: int) -> int:
    """
    Przekształca znormalizowaną wartość drążka [-1.0 .. 1.0] po nałożeniu expo na czas impulsu w µs [1000 .. 2000].
    Zastosowuje parametry:
        reverse: zmienność kierunku (On/Off)
        sub_trim: mikro-centrowanie (np. przesunięcie w µs)
        min_limit, max_limit: EPA końcowych punktów ruchu [1000 .. 2000]
    """
    # 1. Odwrócenie kierunku
    if reverse:
        val = -val
        
    # 2. Skalowanie z zakresu [-1.0, 1.0] do standardowego pasma [1000, 2000] z punktem środkowym 1500
    us = 1500.0 + (val * 500.0)
    
    # 3. Zastosowanie punktu Sub-Trim
    us += sub_trim
    
    # 4. Ograniczenie dolne/górne zgodnie z EPA (End-Points Adjustment)
    us = max(float(min_limit), min(float(max_limit), us))
    
    return int(round(us))


def apply_deadband(val: float, deadband: float) -> float:
    """
    Stosuje strefę martwą (deadband) na znormalizowanej wartości [-1.0 .. 1.0] lub [0.0 .. 1.0].
    Dla wartości wewnątrz [-deadband, deadband] zwraca 0.0.
    Pozostały zakres jest liniowo skalowany, aby zachować ciągłość sterowania.
    """
    if deadband <= 0.0:
        return val
    if deadband >= 1.0:
        return 0.0
        
    abs_val = abs(val)
    if abs_val < deadband:
        return 0.0
        
    sign = 1.0 if val > 0 else -1.0
    return sign * (abs_val - deadband) / (1.0 - deadband)

