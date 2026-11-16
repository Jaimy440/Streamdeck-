"""PC-Steuerung: Lautstärke, Mikrofon, Tastenkürzel (Discord), Programme starten.

Auf Windows werden pycaw (Core Audio) und keyboard verwendet. Auf anderen
Systemen läuft ein Dummy-Modus, damit man die App trotzdem testen kann.
"""
from __future__ import annotations

import os
import subprocess
import sys
import threading
import time
import webbrowser

IS_WIN = sys.platform == "win32"

try:
    import keyboard  # type: ignore
except Exception:  # pragma: no cover - nicht installiert / kein Windows
    keyboard = None


# --------------------------------------------------------------------------
# Lautstärke (Windows Core Audio über pycaw)
# --------------------------------------------------------------------------
def _endpoint(mic: bool):
    """Liefert das IAudioEndpointVolume-Interface des Standardgeräts.

    Wird bei jedem Aufruf neu geholt, damit ein Wechsel des Standardgeräts
    (z.B. Headset eingesteckt) automatisch berücksichtigt wird.
    """
    from pycaw.pycaw import AudioUtilities, IAudioEndpointVolume  # type: ignore

    dev = AudioUtilities.GetMicrophone() if mic else AudioUtilities.GetSpeakers()
    if dev is None:
        raise RuntimeError("Kein Audiogerät gefunden")
    # Neuere pycaw-Versionen liefern ein Wrapper-Objekt mit .EndpointVolume
    ev = getattr(dev, "EndpointVolume", None)
    if ev is not None:
        return ev
    from ctypes import POINTER, cast

    from comtypes import CLSCTX_ALL  # type: ignore

    iface = dev.Activate(IAudioEndpointVolume._iid_, CLSCTX_ALL, None)
    return cast(iface, POINTER(IAudioEndpointVolume))


class Audio:
    def __init__(self) -> None:
        self.available = False
        self._dummy = {"vol": 0.5, "mute": False, "mic_mute": False}
        if IS_WIN:
            try:
                _endpoint(False).GetMasterVolumeLevelScalar()
                self.available = True
            except Exception as e:  # pragma: no cover
                print(f"[Audio] pycaw nicht verfügbar: {e}")

    # --- Lautsprecher ---
    def get_volume(self) -> int:
        if not self.available:
            return round(self._dummy["vol"] * 100)
        return round(_endpoint(False).GetMasterVolumeLevelScalar() * 100)

    def set_volume(self, percent: float) -> int:
        v = max(0.0, min(100.0, float(percent))) / 100.0
        if not self.available:
            self._dummy["vol"] = v
        else:
            ep = _endpoint(False)
            ep.SetMasterVolumeLevelScalar(v, None)
            if v > 0 and ep.GetMute():
                ep.SetMute(0, None)
        return self.get_volume()

    def change_volume(self, delta: float) -> int:
        return self.set_volume(self.get_volume() + delta)

    def is_muted(self) -> bool:
        if not self.available:
            return self._dummy["mute"]
        return bool(_endpoint(False).GetMute())

    def toggle_mute(self) -> bool:
        new = not self.is_muted()
        if not self.available:
            self._dummy["mute"] = new
        else:
            _endpoint(False).SetMute(int(new), None)
        return new

    # --- Mikrofon (Windows-Ebene, wirkt auf ALLE Programme) ---
    def mic_muted(self) -> bool:
        if not self.available:
            return self._dummy["mic_mute"]
        try:
            return bool(_endpoint(True).GetMute())
        except Exception:
            return False

    def toggle_mic_mute(self) -> bool:
        new = not self.mic_muted()
        if not self.available:
            self._dummy["mic_mute"] = new
        else:
            _endpoint(True).SetMute(int(new), None)
        return new


# --------------------------------------------------------------------------
# Tastenkürzel / Aktionen
# --------------------------------------------------------------------------
def send_hotkey(combo: str, hold: float = 0.06) -> None:
    """Drückt eine Tastenkombination (z.B. 'ctrl+shift+alt+m').

    Die Tasten werden kurz gehalten, weil Discord sehr kurze Tastendrücke
    manchmal nicht erkennt.
    """
    if not combo:
        return
    if keyboard is None:
        print(f"[Hotkey] (Dummy) {combo}")
        return
    keyboard.press(combo)
    time.sleep(hold)
    keyboard.release(combo)


def run_action(btn: dict) -> None:
    """Führt eine frei konfigurierbare Button-Aktion aus config.json aus."""
    action = btn.get("action")
    if action == "hotkey":
        threading.Thread(target=send_hotkey, args=(btn.get("keys", ""),), daemon=True).start()
    elif action == "launch":
        target = btn.get("target", "")
        if IS_WIN:
            os.startfile(target)  # type: ignore[attr-defined]  # Programme, Dateien, spotify: usw.
        else:
            subprocess.Popen(["xdg-open", target])
    elif action == "url":
        webbrowser.open(btn.get("target", ""))
    elif action == "command":
        subprocess.Popen(btn.get("target", ""), shell=True)
    else:
        raise ValueError(f"Unbekannte Aktion: {action}")
