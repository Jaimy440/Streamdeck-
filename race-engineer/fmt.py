"""Zahlen & Zeiten für Anzeige und Sprachausgabe (deutsch)."""
from __future__ import annotations

import math

TYRE_NAMES = ["vorne links", "vorne rechts", "hinten links", "hinten rechts"]
TYRE_SHORT = ["VL", "VR", "HL", "HR"]


def num(x: float, digits: int = 1) -> str:
    """1.25 -> '1,3' (deutsches Komma)."""
    s = f"{x:.{digits}f}"
    return s.replace(".", ",")


def laptime(t: float | None) -> str:
    """Anzeige: 92.345 -> '1:32.345'."""
    if t is None or t <= 0 or math.isnan(t):
        return "-:--.---"
    m = int(t // 60)
    return f"{m}:{t - m * 60:06.3f}"


def laptime_speech(t: float | None) -> str:
    """Sprache: 92.345 -> '1 Minute 32,3'."""
    if t is None or t <= 0:
        return "keine Zeit"
    m = int(t // 60)
    s = t - m * 60
    if m == 0:
        return f"{num(s)} Sekunden"
    return f"{m} {'Minute' if m == 1 else 'Minuten'} {num(s)}"


def gap_speech(sec: float) -> str:
    sec = abs(sec)
    if sec < 1.0:
        z = max(1, round(sec * 10))
        return f"{z} {'Zehntel' if z != 1 else 'Zehntel'}"
    if sec >= 60:
        return laptime_speech(sec)
    return f"{num(sec)} Sekunden"


def delta_speech(d: float) -> str:
    """Differenz zur Bestzeit, z. B. '3 Zehntel langsamer'."""
    word = "langsamer" if d > 0 else "schneller"
    return f"{gap_speech(d)} {word}"


def minutes_speech(sec: float) -> str:
    m = int(round(sec / 60))
    if m <= 1:
        return "eine Minute"
    return f"{m} Minuten"


def laps_speech(n: float) -> str:
    if n < 1:
        return "weniger als eine Runde"
    if n < 2:
        return "eine Runde"
    return f"{int(n)} Runden"


def liters(x: float) -> str:
    return f"{num(x)} Liter" if x < 10 else f"{round(x)} Liter"
