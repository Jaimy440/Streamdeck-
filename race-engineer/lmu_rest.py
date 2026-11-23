"""Optionale Zusatzdaten aus der lokalen REST-API von Le Mans Ultimate (Port 6397).

Aktuell: Virtuelle Energie (Hypercar/LMDh/GT3 mit Energielimit), die nicht im
rF2-Shared-Memory steht. Läuft im Hintergrund; fehlt die API, passiert einfach nichts.
Die Felder werden robust gesucht, da sich die API zwischen LMU-Versionen ändern kann.
"""
from __future__ import annotations

import json
import threading
import time
import urllib.request

BASE = "http://localhost:6397"
ENDPOINTS = ["/rest/garage/UIScreen/RepairAndRefuel"]


def _find(obj, names):
    """Sucht rekursiv den ersten Wert zu einem der Schlüssel."""
    if isinstance(obj, dict):
        for k, v in obj.items():
            if k in names and isinstance(v, (int, float)):
                return float(v)
        for v in obj.values():
            r = _find(v, names)
            if r is not None:
                return r
    elif isinstance(obj, list):
        for v in obj:
            r = _find(v, names)
            if r is not None:
                return r
    return None


class LMURest:
    def __init__(self):
        self.virtual_energy: float | None = None   # 0..1
        self.updated = 0.0
        self.ok = False
        threading.Thread(target=self._loop, daemon=True, name="lmu-rest").start()

    def _get(self, path):
        with urllib.request.urlopen(BASE + path, timeout=0.6) as r:
            return json.loads(r.read().decode("utf-8", errors="replace"))

    def _loop(self):
        while True:
            delay = 1.0
            try:
                ve = None
                for ep in ENDPOINTS:
                    data = self._get(ep)
                    cur = _find(data, {"currentVirtualEnergy", "virtualEnergy", "currentEnergy"})
                    mx = _find(data, {"maxVirtualEnergy", "maxEnergy"})
                    if cur is not None and mx:
                        ve = max(0.0, min(1.0, cur / mx))
                        break
                self.virtual_energy = ve
                self.ok = True
                self.updated = time.monotonic()
            except Exception:
                self.ok = False
                self.virtual_energy = None
                delay = 10.0
            time.sleep(delay)

    def get_energy(self):
        if self.virtual_energy is None or time.monotonic() - self.updated > 5:
            return None
        return self.virtual_energy
