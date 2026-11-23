"""Spotter: "Auto links / rechts / drei breit / frei" und Radar-Daten fürs Dashboard.

Rechnet die Weltpositionen der anderen Autos in Fahrzeugkoordinaten des Spielers um.
rF2/LMU-Konvention: lokales -z = vorne, lokales +x = links. Sollten links/rechts
vertauscht sein, in config.json "spotter_seiten_tauschen": true setzen.
"""
from __future__ import annotations

import time

clock = time.monotonic   # austauschbar (Tests / Zeitraffer)

CAR_LEN = 4.9      # Meter, Überlappung nach vorne/hinten
CAR_WIDTH = 2.0
SIDE_MAX = 5.5     # bis zu diesem seitlichen Abstand zählt ein Auto als "neben dir"


class Spotter:
    def __init__(self, cfg: dict, say):
        self.cfg = cfg
        self.say = say
        self.state = "frei"           # frei | links | rechts | beide
        self.since = 0.0
        self.pending = None
        self.radar: list[dict] = []

    def update(self, frame: dict | None) -> dict:
        self.radar = []
        if not frame or not frame.get("player"):
            return {"state": "frei", "radar": []}
        t = frame["player"]
        me = next((c for c in frame["cars"] if c["is_player"]), None)
        if me is None:
            return {"state": "frei", "radar": []}
        fx, fy, fz = (-v for v in t["ori_z"])        # vorne in Weltkoordinaten
        lx, ly, lz = t["ori_x"]                         # links in Weltkoordinaten
        if self.cfg.get("spotter_seiten_tauschen"):
            lx, ly, lz = -lx, -ly, -lz
        px, py, pz = t["pos"]
        left = right = False
        for c in frame["cars"]:
            if c["is_player"] or c["in_pits"]:
                continue
            dx, dy, dz = c["pos"][0] - px, c["pos"][1] - py, c["pos"][2] - pz
            if abs(dx) > 40 or abs(dz) > 40:
                continue
            lon = dx * fx + dy * fy + dz * fz
            lat = dx * lx + dy * ly + dz * lz
            if abs(lon) < 30 and abs(lat) < 12:
                self.radar.append({"lon": round(lon, 2), "lat": round(lat, 2), "cls": c["cls"]})
            if abs(lon) < CAR_LEN and CAR_WIDTH * 0.5 < abs(lat) < SIDE_MAX:
                if lat > 0:
                    left = True
                else:
                    right = True

        active = (self.cfg.get("ansagen", {}).get("spotter", True) and t["speed"] > 40
                  and not me["in_pits"] and frame["session"]["phase"] in (3, 5, 6))
        new = "beide" if left and right else "links" if left else "rechts" if right else "frei"
        if not active:
            self.state, self.pending = new, None
            return {"state": new if t["speed"] > 40 else "frei", "radar": self.radar}

        now = clock()
        if new != self.state:
            # kurz bestätigen, damit es bei Wacklern nicht flattert ("frei" etwas länger)
            if self.pending is None or self.pending[0] != new:
                self.pending = (new, now)
            elif now - self.pending[1] > (0.35 if new == "frei" else 0.12):
                old, self.state = self.state, new
                self.pending = None
                self._announce(old, new)
        else:
            self.pending = None
        return {"state": self.state, "radar": self.radar}

    def _announce(self, old, new):
        if new == "beide":
            self.say("Drei breit!", 0, "spotter")
        elif new == "links":
            self.say("Rechts frei" if old == "beide" else "Auto links", 0, "spotter")
        elif new == "rechts":
            self.say("Links frei" if old == "beide" else "Auto rechts", 0, "spotter")
        else:
            self.say("Frei", 0, "spotter")
