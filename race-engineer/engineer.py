"""Der Renningenieur: wertet die Telemetrie aus und erzeugt Ansagen.

update(frame) wird ~20x pro Sekunde aufgerufen und liefert die aufbereitete Analyse
für das Dashboard. Ansagen gehen über die say()-Funktion an die Sprachausgabe.
"""
from __future__ import annotations

import bisect
import math
import time

clock = time.monotonic   # austauschbar (Tests / Zeitraffer)
from collections import deque

import fmt

MAP_BIN = 12.0            # Meter pro Punkt der Streckenkarte


def _mean(xs):
    return sum(xs) / len(xs) if xs else None


class Engineer:
    def __init__(self, cfg: dict, say):
        self.cfg = cfg
        self._say = say
        self.reset()

    # ------------------------------------------------------------------ Zustand
    def reset(self):
        self.session_key = None
        self.last_laps = None
        self.pending_lap_at = None
        self.lap_fuel_start = None
        self.lap_energy_start = None
        self.lap_pitted = False
        self.lap_yellow = False
        self.laps: list[dict] = []          # abgeschlossene Runden des Spielers
        self.fuel_hist: deque = deque(maxlen=6)
        self.energy_hist: deque = deque(maxlen=6)
        self.best_trace = None              # ([Meter], [Zeit]) der Bestrunde
        self.cur_trace: tuple[list, list] = ([], [])
        self.finished_trace: tuple[list, list] = ([], [])
        self._ld_last = None
        self._ld_et = 0.0
        self.best_lap = None
        self.gap_hist: list[dict] = []
        self.map_pts: dict[int, tuple] = {}
        self.map_ready = False
        self.map_version = 0
        self.cool: dict[str, float] = {}
        self.prev = {}
        self.class_pos = None
        self.pos_candidate = None
        self.yellow_prev = [0, 0, 0]
        self.wear_warned = set()
        self.time_called = set()
        self.hot_since = {}
        self.last_fuel = None
        self.window_called = False
        self.boxbox_called = False
        self.finish_called = False
        self.last_lap_called = False
        self.analysis = {}

    def say(self, text: str, prio: int = 2, cat: str = "info", key: str | None = None, cooldown: float = 0.0):
        if not self.cfg.get("ansagen", {}).get(cat, True):
            return
        now = clock()
        k = key or cat + ":" + text
        if cooldown and now - self.cool.get(k, -1e9) < cooldown:
            return
        self.cool[k] = now
        self._say(text, prio, cat)

    # ------------------------------------------------------------------ Hilfen
    @staticmethod
    def _player(frame):
        for c in frame["cars"]:
            if c["is_player"]:
                return c
        return None

    def _class_info(self, cars, me):
        """Klassenposition und Klassengeschwindigkeit (für Multiklassen-Rennen)."""
        classes = {}
        for c in cars:
            classes.setdefault(c["cls"], []).append(c)
        same = sorted(classes.get(me["cls"], []), key=lambda c: c["place"])
        pace = {}
        for cls, lst in classes.items():
            bests = sorted(c["best"] for c in lst if c["best"])
            pace[cls] = _mean(bests[: max(1, len(bests) // 2)]) if bests else None
        return same, pace, len(classes) > 1

    @staticmethod
    def _gap_between(a, b):
        """Zeitabstand b hinter a (beide aus der Gesamtwertung)."""
        laps = b["laps_behind_leader"] - a["laps_behind_leader"]
        t = b["time_behind_leader"] - a["time_behind_leader"]
        return t, laps

    def _ref_lap(self, me):
        valid = [l["time"] for l in self.laps[-5:] if l["valid"]]
        return _mean(valid) or me.get("best") or me.get("last") or me.get("est_lap") or 120.0

    # ------------------------------------------------------------------ Haupt
    def update(self, frame: dict | None) -> dict:
        if frame is None:
            self.analysis = {"connected": False}
            return self.analysis
        s = frame["session"]
        me = self._player(frame)
        t = frame.get("player")
        if me is None or t is None:
            self.analysis = {"connected": True, "waiting": True, "session": s}
            return self.analysis

        key = (frame["source"], s["id"], s["track"])
        if key != self.session_key or (self.prev.get("elapsed", 0) - s["elapsed"] > 30):
            self.reset()
            self.session_key = key
            self.last_laps = me["laps"]
            self.lap_fuel_start = t["fuel"]
            self.lap_energy_start = self._energy(t)
        now_et = t["elapsed"] or s["elapsed"]

        same, class_pace, multi = self._class_info(frame["cars"], me)
        class_pos = next((i for i, c in enumerate(same, 1) if c["is_player"]), me["place"])

        # --- Runde abgeschlossen? (kurz warten, bis die Rundenzeit aktualisiert ist)
        if me["laps"] > (self.last_laps or 0):
            if self.pending_lap_at is None:
                self.pending_lap_at = clock()
                self._finish_trace(me)
            if clock() - self.pending_lap_at > 0.6:
                self._on_lap(frame, me, t, same, class_pos, multi)
                self.last_laps = me["laps"]
                self.pending_lap_at = None
        if me["in_pits"] or t.get("in_pitlane"):
            self.lap_pitted = True
        if s["phase"] == 6 or any(f == 1 for f in s["sector_flags"]):
            self.lap_yellow = True

        # Tanken erkannt -> Verbrauchsmessung dieser Runde ungültig
        if self.last_fuel is not None and t["fuel"] > self.last_fuel + 0.5:
            self.lap_pitted = True
        self.last_fuel = t["fuel"]

        # --- Delta zur Bestrunde
        time_into = max(0.0, now_et - me["lap_start_et"]) if me["lap_start_et"] else me.get("time_into_lap", 0)
        # LMU aktualisiert die Streckenposition nur ~5x/s -> mit der Geschwindigkeit hochrechnen
        if me["lap_dist"] != self._ld_last:
            self._ld_last, self._ld_et = me["lap_dist"], now_et
        dist = me["lap_dist"] + t["speed"] / 3.6 * max(0.0, min(0.4, now_et - self._ld_et))
        ds, ts = self.cur_trace
        if self.pending_lap_at is None and (not ds or dist > ds[-1] + 1.0) and dist < s["track_length"]:
            ds.append(dist)
            ts.append(time_into)
        delta = None
        if self.best_trace and time_into > 3:
            ref = self._trace_time(self.best_trace, dist)
            if ref is not None:
                delta = time_into - ref

        # --- Streckenkarte aus der eigenen Fahrlinie
        if not self.map_ready and not me["in_pits"] and t["speed"] > 30:
            mb = int(me["lap_dist"] // MAP_BIN)
            if mb not in self.map_pts:
                self.map_pts[mb] = (round(t["pos"][0], 1), round(t["pos"][2], 1))
                n_bins = max(1, int(s["track_length"] // MAP_BIN))
                if len(self.map_pts) >= n_bins * 0.97:
                    self.map_ready = True
                    self.map_version += 1
                elif len(self.map_pts) % 40 == 0:
                    self.map_version += 1

        # --- Kennzahlen
        fuel = self._fuel_calc(frame, me, t, time_into)
        energy = self._energy_calc(frame, me, t, time_into)
        gaps = self._gaps(frame, me, same)
        relative = self._relative(frame, me, class_pace)

        self._checks(frame, me, t, s, class_pos, same, multi, class_pace, fuel, energy, relative)

        self.prev.update({"elapsed": s["elapsed"], "phase": s["phase"], "in_pits": me["in_pits"],
                          "penalties": me["penalties"], "dents": list(t["dents"]),
                          "impact_et": t["last_impact_et"], "raining": s["raining"],
                          "wetness": s["wetness"], "finish": me["finish_status"]})

        tyres = []
        for i, ty in enumerate(t["tyres"]):
            tyres.append({**ty, "name": fmt.TYRE_SHORT[i], "avg": round(sum(ty["temps"]) / 3, 1)})

        self.analysis = {
            "connected": True,
            "source": frame["source"],
            "session": {**s, "laps_remaining": fuel.get("race_laps_left"), "finished": me["finish_status"] == 1},
            "car": {
                "vehicle": t["vehicle"], "cls": me["cls"], "speed": round(t["speed"]), "gear": t["gear"],
                "rpm": round(t["rpm"]), "max_rpm": t["max_rpm"], "throttle": round(t["throttle"], 3),
                "brake": round(t["brake"], 3), "steering": round(t["steering"], 3),
                "limiter": t["limiter"], "in_pits": me["in_pits"], "water": round(t["water_temp"], 1),
                "oil": round(t["oil_temp"], 1), "overheating": t["overheating"], "battery": t.get("battery"),
                "brake_bias": round((1 - t["rear_brake_bias"]) * 100, 1) if t.get("rear_brake_bias") else None,
                "compound": t.get("compound_front"),
            },
            "position": {"overall": me["place"], "cls": class_pos, "cls_count": len(same),
                         "total": len(frame["cars"]), "multi": multi, "pitstops": me["pitstops"],
                         "penalties": me["penalties"], "flag": me["flag"]},
            "timing": {
                "lap": me["laps"] + 1, "current": round(time_into, 3), "last": me["last"], "best": self.best_lap or me["best"],
                "delta": round(delta, 3) if delta is not None else None,
                "s1": me["cur_s1"], "s2": me["cur_s2"], "last_s1": me["last_s1"], "last_s2": me["last_s2"],
                "last_s3": (me["last"] - me["last_s1"] - me["last_s2"]) if me["last"] and me["last_s1"] and me["last_s2"] else None,
                "best_s1": me["best_s1"], "best_s2": me["best_s2"],
                "sector": me["sector"],
                "laps": self.laps[-12:],
            },
            "fuel": fuel,
            "energy": energy,
            "tyres": tyres,
            "damage": {"dents": t["dents"], "detached": t["detached"],
                       "level": max(t["dents"]) if t["dents"] else 0},
            "gaps": gaps,
            "relative": relative,
            "standings": self._standings(frame, me, multi),
            "map_version": self.map_version,
            "cars_pos": [{"id": c["id"], "x": round(c["pos"][0], 1), "z": round(c["pos"][2], 1),
                          "cls": c["cls"], "me": c["is_player"], "p": c["place"],
                          "pit": c["in_pits"]} for c in frame["cars"]],
        }
        return self.analysis

    def track_map(self):
        if not self.map_pts:
            return []
        return [self.map_pts[k] for k in sorted(self.map_pts)]

    # ------------------------------------------------------------------ Runden
    def _finish_trace(self, me):
        self.finished_trace = self.cur_trace
        self.cur_trace = ([], [])

    def _on_lap(self, frame, me, t, same, class_pos, multi):
        s = frame["session"]
        lap_no = me["laps"]
        lap_time = me["last"]
        fuel_used = (self.lap_fuel_start - t["fuel"]) if self.lap_fuel_start is not None else None
        e_now = self._energy(t)
        e_used = (self.lap_energy_start - e_now) if (self.lap_energy_start is not None and e_now is not None) else None
        valid = bool(lap_time) and not self.lap_pitted
        entry = {"lap": lap_no, "time": lap_time, "valid": valid, "pit": self.lap_pitted,
                 "yellow": self.lap_yellow, "fuel": round(fuel_used, 2) if fuel_used else None,
                 "s1": me["last_s1"], "s2": me["last_s2"], "pos": class_pos}
        self.laps.append(entry)
        if fuel_used and valid and 0.05 < fuel_used < 40:
            self.fuel_hist.append(fuel_used)
        if e_used and valid and 0.001 < e_used < 0.6:
            self.energy_hist.append(e_used)

        # Bestzeit & Delta-Kurve
        new_pb = False
        if valid and lap_time and (self.best_lap is None or lap_time < self.best_lap):
            had = self.best_lap is not None
            self.best_lap = lap_time
            ds, ts = self.finished_trace
            if len(ds) > 50 and ds[0] < 0.1 * s["track_length"] and ds[-1] > 0.9 * s["track_length"]:
                self.best_trace = (ds + [s["track_length"]], ts + [lap_time])
            new_pb = had

        # Abstände merken (für Trend: holst du auf / verlierst du?)
        g = self._gaps(frame, me, same)
        self.gap_hist.append({"lap": lap_no, "ahead": g.get("ahead"), "behind": g.get("behind")})

        # ---------- Ansagen zur Runde
        race = s["kind"] == "race"
        parts = []
        if lap_time and self.cfg.get("rundenzeit_jede_runde", True):
            parts.append(f"{fmt.laptime_speech(lap_time)}.")
            if new_pb:
                parts.append("Neue persönliche Bestzeit!")
            elif self.best_lap and lap_time > self.best_lap and valid:
                parts.append(f"{fmt.delta_speech(lap_time - self.best_lap)} als deine Bestzeit.")
        if parts:
            self.say(" ".join(parts), 3, "rundenzeiten")
        elif new_pb:
            self.say(f"Neue Bestzeit, {fmt.laptime_speech(lap_time)}!", 2, "rundenzeiten")

        self._fuel_lap_calls(frame, me, t, race)
        if race and lap_no >= 2:
            every = max(1, int(self.cfg.get("abstand_alle_runden", 2)))
            if lap_no % every == 0:
                self._gap_call(frame, me)
        # Reifenverschleiß
        wear_min = min(ty["wear"] for ty in t["tyres"])
        worst = min(range(4), key=lambda i: t["tyres"][i]["wear"])
        for th in (0.5, 0.3, 0.15):
            if wear_min < th and th not in self.wear_warned:
                self.wear_warned.add(th)
                self.say(f"Reifen {fmt.TYRE_NAMES[worst]} nur noch {round(wear_min * 100)} Prozent.",
                         1 if th < 0.2 else 2, "reifen")
                break
        if wear_min > 0.95:
            self.wear_warned.clear()
        # letzte Runde
        if race and not self.last_lap_called:
            ll = self._race_laps_left(frame, me, 0.0)
            if ll is not None and ll <= 1.05:
                self.last_lap_called = True
                self.say("Letzte Runde! Bring es nach Hause.", 1, "session")

        self.lap_fuel_start = t["fuel"]
        self.lap_energy_start = self._energy(t)
        self.lap_pitted = bool(me["in_pits"])
        self.lap_yellow = False

    @staticmethod
    def _trace_time(trace, dist):
        """Zeit der Referenzrunde an Streckenmeter dist (linear interpoliert)."""
        ds, ts = trace
        i = bisect.bisect_left(ds, dist)
        if i <= 0 or i >= len(ds):
            return None
        d0, d1 = ds[i - 1], ds[i]
        f = (dist - d0) / (d1 - d0) if d1 > d0 else 0.0
        return ts[i - 1] + (ts[i] - ts[i - 1]) * f

    # ------------------------------------------------------------------ Sprit
    def _race_laps_left(self, frame, me, frac):
        """Wie viele Runden (Distanz) du bis zur Zielflagge noch fährst."""
        s = frame["session"]
        if s["kind"] != "race":
            return None
        if me["finish_status"]:
            return 0.0
        if s["max_laps"]:
            return max(0.0, s["max_laps"] - me["laps"] - frac)
        if s["time_left"] is None:
            return None
        # Zeitrennen: nach Ablauf der Uhr wird die angefangene Runde zu Ende gefahren
        L = self._ref_lap(me)
        remaining = s["time_left"] - (1 - frac) * L
        if remaining <= 0:
            return 1 - frac
        return (1 - frac) + math.ceil(remaining / L)

    def _fuel_calc(self, frame, me, t, time_into):
        s = frame["session"]
        per_lap = _mean(list(self.fuel_hist)[-5:])
        frac = min(0.999, me["lap_dist"] / s["track_length"]) if s["track_length"] else 0.0
        out = {"fuel": round(t["fuel"], 2), "capacity": t["fuel_capacity"], "per_lap": None, "max_lap": None,
               "laps_left": None, "race_laps_left": None, "need_finish": None, "to_add": None, "stops": None,
               "window_open": None, "last_lap_used": self.laps[-1]["fuel"] if self.laps else None}
        race_left = self._race_laps_left(frame, me, frac)
        out["race_laps_left"] = round(race_left, 2) if race_left is not None else None
        if not per_lap:
            return out
        reserve = float(self.cfg.get("sprit_reserve_runden", 0.5))
        out["per_lap"] = round(per_lap, 2)
        out["max_lap"] = round(max(self.fuel_hist), 2)
        out["laps_left"] = round(t["fuel"] / per_lap, 1)
        if race_left is not None:
            need = (race_left + reserve) * per_lap
            out["need_finish"] = round(need, 1)
            add = max(0.0, need - t["fuel"])
            out["to_add"] = round(add, 1)
            cap = t["fuel_capacity"] or 0
            if add > 0 and cap > 0:
                out["stops"] = math.ceil(add / cap)
                # Boxenfenster: offen, sobald ein voller Tank ab jetzt bis ins Ziel reicht
                out["window_open"] = need <= cap
                out["window_in_laps"] = 0 if need <= cap else math.ceil((need - cap) / per_lap)
            else:
                out["stops"] = 0
        return out

    @staticmethod
    def _energy(t):
        ve = t.get("virtual_energy")
        return ve if isinstance(ve, (int, float)) else None

    def _energy_calc(self, frame, me, t, time_into):
        e = self._energy(t)
        if e is None:
            return None
        per = _mean(list(self.energy_hist)[-5:])
        out = {"level": round(e * 100, 1), "per_lap": round(per * 100, 2) if per else None,
               "laps_left": round(e / per, 1) if per else None}
        s = frame["session"]
        frac = min(0.999, me["lap_dist"] / s["track_length"]) if s["track_length"] else 0.0
        race_left = self._race_laps_left(frame, me, frac)
        if per and race_left is not None:
            need = (race_left + float(self.cfg.get("sprit_reserve_runden", 0.5))) * per
            out["need_finish"] = round(need * 100, 1)
            out["to_add"] = round(max(0.0, need - e) * 100, 1)
        return out

    def _fuel_lap_calls(self, frame, me, t, race):
        f = self._fuel_calc(frame, me, t, 0)
        e = self._energy_calc(frame, me, t, 0)
        if not f.get("per_lap"):
            return
        laps_left = f["laps_left"]
        limit_name, limit_laps = "Sprit", laps_left
        if e and e.get("laps_left") is not None and e["laps_left"] < laps_left:
            limit_name, limit_laps = "Energie", e["laps_left"]
        n_valid = len(self.fuel_hist)
        reaches = race and f.get("to_add") == 0
        # kritisch
        if limit_laps < 1.6 and not reaches:
            self.boxbox_called = True
            self.say(f"Box, Box! {limit_name} reicht nur noch für diese Runde. Komm diese Runde rein.", 1, "sprit")
            return
        if limit_laps < 3.2 and not reaches:
            self.say(f"{limit_name} für noch {fmt.laps_speech(limit_laps)}.", 1, "sprit")
            return
        if n_valid == 2 or (n_valid > 2 and len(self.laps) % 4 == 0):
            txt = f"Verbrauch {fmt.num(f['per_lap'])} Liter pro Runde, Sprit für {fmt.laps_speech(laps_left)}."
            if e and e.get("per_lap"):
                txt += f" Energie {fmt.num(e['per_lap'])} Prozent pro Runde, reicht für {fmt.laps_speech(e['laps_left'])}."
            if race and f.get("to_add") is not None:
                if f["to_add"] == 0:
                    txt += f" Das reicht bis ins Ziel."
                else:
                    txt += f" Bis ins Ziel fehlen dir {fmt.liters(f['to_add'])}."
            self.say(txt, 2, "sprit")
        if race and f.get("window_open") and not self.window_called and f.get("stops") == 1 and laps_left <= 5:
            self.window_called = True
            self.say(f"Boxenfenster ist offen, der Sprit reicht noch für {fmt.laps_speech(laps_left)}. "
                     f"{fmt.liters(f['to_add'])} nachtanken, dann reicht es bis ins Ziel.", 2, "strategie")

    # ------------------------------------------------------------------ Abstände
    def _gaps(self, frame, me, same):
        out = {}
        idx = next((i for i, c in enumerate(same) if c["is_player"]), None)
        if idx is None:
            return out
        if idx > 0:
            a = same[idx - 1]
            t, laps = self._gap_between(a, me)
            out.update({"ahead": round(t, 2), "ahead_laps": laps, "ahead_name": a["driver"], "ahead_last": a["last"]})
        if idx + 1 < len(same):
            b = same[idx + 1]
            t, laps = self._gap_between(me, b)
            out.update({"behind": round(t, 2), "behind_laps": laps, "behind_name": b["driver"], "behind_last": b["last"]})
        # Trend der letzten Runden
        for side in ("ahead", "behind"):
            vals = [h[side] for h in self.gap_hist[-4:] if h.get(side) is not None]
            if len(vals) >= 2:
                out[side + "_trend"] = round((vals[-1] - vals[0]) / (len(vals) - 1), 2)
        return out

    def _gap_call(self, frame, me):
        g = self._gaps(frame, me, self._class_info(frame["cars"], me)[0])
        parts = []
        if g.get("ahead") is not None and g.get("ahead_laps", 0) == 0:
            txt = f"Nach vorne zu {g['ahead_name']}: {fmt.gap_speech(g['ahead'])}"
            tr = g.get("ahead_trend")
            if tr is not None and abs(tr) >= 0.1:
                txt += f", du {'holst' if tr < 0 else 'verlierst'} {fmt.gap_speech(tr)} pro Runde"
            parts.append(txt + ".")
        if g.get("behind") is not None and g.get("behind_laps", 0) == 0:
            txt = f"Hinter dir {g['behind_name']} mit {fmt.gap_speech(g['behind'])}"
            tr = g.get("behind_trend")
            if tr is not None and abs(tr) >= 0.1:
                txt += f", er {'kommt' if tr < 0 else 'verliert'} {fmt.gap_speech(tr)} pro Runde"
            parts.append(txt + ".")
        if parts:
            self.say(" ".join(parts), 3, "abstaende")

    def _relative(self, frame, me, class_pace):
        """Autos auf der Strecke um dich herum (Zeitabstand, unabhängig von der Wertung)."""
        L = frame["session"]["track_length"] or 1.0
        ref = self._ref_lap(me)
        rows = []
        for c in frame["cars"]:
            if c["in_pits"] and not c["is_player"]:
                continue
            d = c["lap_dist"] - me["lap_dist"]
            if d > L / 2:
                d -= L
            elif d < -L / 2:
                d += L
            rel = d / L * ref
            lap_diff = (c["laps"] + c["lap_dist"] / L) - (me["laps"] + me["lap_dist"] / L) - d / L
            rows.append({"id": c["id"], "driver": c["driver"], "cls": c["cls"], "place": c["place"],
                         "rel": round(rel, 2), "lapped": round(lap_diff), "me": c["is_player"],
                         "faster_cls": bool(class_pace.get(c["cls"]) and class_pace.get(me["cls"])
                                            and class_pace[c["cls"]] < class_pace[me["cls"]] * 0.98)})
        rows.sort(key=lambda r: -r["rel"])
        i = next(i for i, r in enumerate(rows) if r["me"])
        return rows[max(0, i - 4): i + 5]

    def _standings(self, frame, me, multi):
        cars = sorted(frame["cars"], key=lambda c: c["place"])
        cls_count = {}
        out = []
        for c in cars:
            cls_count[c["cls"]] = cls_count.get(c["cls"], 0) + 1
            gap, laps = self._gap_between(me, c)
            out.append({"place": c["place"], "cls_place": cls_count[c["cls"]], "driver": c["driver"],
                        "vehicle": c["vehicle"], "cls": c["cls"], "best": c["best"], "last": c["last"],
                        "laps": c["laps"], "gap_leader": round(c["time_behind_leader"], 1),
                        "laps_leader": c["laps_behind_leader"], "gap_me": round(gap, 1), "laps_me": laps,
                        "pit": c["in_pits"], "stops": c["pitstops"], "me": c["is_player"]})
        return out

    # ------------------------------------------------------------------ Laufende Checks
    def _checks(self, frame, me, t, s, class_pos, same, multi, class_pace, fuel, energy, relative):
        race = s["kind"] == "race"
        prev = self.prev
        phase_prev = prev.get("phase")

        # Start / Gelbphasen
        if phase_prev is not None and phase_prev != s["phase"]:
            if s["phase"] == 5 and phase_prev in (3, 4) and race:
                self.say("Grün, grün, grün! Viel Erfolg.", 1, "flaggen")
            elif s["phase"] == 5 and phase_prev == 6:
                self.say("Grüne Flagge, das Rennen ist wieder freigegeben!", 1, "flaggen")
            elif s["phase"] == 6:
                self.say("Full Course Yellow! Tempo runter, nicht überholen.", 1, "flaggen")
            elif s["phase"] == 3 and race:
                self.say("Formationsrunde. Reifen und Bremsen auf Temperatur bringen.", 2, "flaggen")

        # Lokale Gelbe Flaggen
        flags = s["sector_flags"]
        for i in range(3):
            if flags[i] == 1 and self.yellow_prev[i] != 1:
                ahead = (i + 1) in (me["sector"], me["sector"] % 3 + 1)
                txt = f"Gelb in Sektor {i + 1}" + (", direkt vor dir. Vorsicht!" if ahead else ".")
                self.say(txt, 1 if ahead else 2, "flaggen", key=f"yellow{i}", cooldown=15)
        if any(self.yellow_prev[i] == 1 for i in range(3)) and not any(f == 1 for f in flags) and s["phase"] == 5:
            self.say("Strecke frei, wieder grün.", 2, "flaggen", key="green", cooldown=10)
        self.yellow_prev = list(flags)

        # Blaue Flagge
        if me["flag"] == 6:
            self.say("Blaue Flagge, lass das schnellere Auto vorbei.", 1, "flaggen", key="blue", cooldown=30)

        # Zielflagge
        if me["finish_status"] == 1 and not self.finish_called:
            self.finish_called = True
            pos = f"P{class_pos}" + (" in deiner Klasse" if multi else "")
            best = f" Deine schnellste Runde: {fmt.laptime_speech(self.best_lap)}." if self.best_lap else ""
            self.say(f"Zielflagge! Du beendest das Rennen auf {pos}.{best} Gute Arbeit!", 1, "session")

        # Position
        if race and s["phase"] == 5 and not me["in_pits"]:
            if self.class_pos is None:
                self.class_pos = class_pos
            elif class_pos != self.class_pos:
                if self.pos_candidate is None or self.pos_candidate[0] != class_pos:
                    self.pos_candidate = (class_pos, clock())
                elif clock() - self.pos_candidate[1] > 2.5:
                    old, self.class_pos = self.class_pos, class_pos
                    self.pos_candidate = None
                    if class_pos < old:
                        self.say(f"P{class_pos}! " + ("Du führst!" if class_pos == 1 else "Stark gemacht."), 2, "position",
                                 key="pos", cooldown=5)
                    else:
                        self.say(f"Position verloren, jetzt P{class_pos}.", 2, "position", key="pos", cooldown=5)
            else:
                self.pos_candidate = None

        # Box rein / raus
        if prev.get("in_pits") is not None and prev["in_pits"] != me["in_pits"]:
            if me["in_pits"]:
                if race and fuel.get("to_add"):
                    self.say(f"In der Box: {fmt.liters(fuel['to_add'])} tanken bringt dich ins Ziel.", 2, "strategie",
                             key="pitin", cooldown=20)
                self.boxbox_called = False
                self.window_called = False
            else:
                self.say(f"Raus aus der Box, {fmt.liters(t['fuel'])} an Bord. Pitlimiter aus nicht vergessen.", 2,
                         "strategie", key="pitout", cooldown=20)
        if (me["in_pits"] or t.get("in_pitlane")) and t["speed"] > 20 and not t["limiter"]:
            self.hot_since.setdefault("limiter", clock())
            if clock() - self.hot_since["limiter"] > 1.5:
                self.say("Pitlimiter!", 0, "strategie", key="limiter", cooldown=12)
        else:
            self.hot_since.pop("limiter", None)

        # Strafen
        pen_prev = prev.get("penalties")
        if pen_prev is not None and me["penalties"] != pen_prev:
            if me["penalties"] > pen_prev:
                self.say("Achtung, du hast eine Strafe bekommen. Schau ins Pit-Menü.", 1, "flaggen")
            else:
                self.say("Strafe abgesessen.", 2, "flaggen")

        # Schaden
        dents_prev = prev.get("dents")
        if dents_prev and any(a > b for a, b in zip(t["dents"], dents_prev)):
            lvl = max(t["dents"])
            self.say("Schaden am Auto! " + ("Sieht übel aus, überleg dir einen Boxenstopp." if lvl >= 2
                                              else "Leichter Schaden, fahr erstmal weiter."), 1, "schaden",
                     key="dmg", cooldown=8)
        elif prev.get("impact_et") is not None and t["last_impact_et"] > prev["impact_et"] + 0.01 \
                and t["last_impact_mag"] > float(self.cfg.get("kontakt_schwelle", 1500)):
            self.say("Kontakt! Alles ok?", 1, "schaden", key="impact", cooldown=10)
        if t["detached"]:
            self.say("Du hast Teile verloren!", 1, "schaden", key="detached", cooldown=120)
        for i, ty in enumerate(t["tyres"]):
            if ty["flat"]:
                self.say(f"Reifenschaden {fmt.TYRE_NAMES[i]}! Ab in die Box.", 0, "schaden", key=f"flat{i}", cooldown=60)

        # Motor
        if t["overheating"] or t["water_temp"] > float(self.cfg.get("wasser_max", 110)):
            self.say("Motor wird zu heiß! Mehr Windschatten meiden, Kühlung beachten.", 1, "technik",
                     key="water", cooldown=60)

        # Reifen-/Bremstemperaturen (mit Verzögerung, damit kurze Spitzen nicht nerven)
        hot = float(self.cfg.get("reifen_heiss", 105))
        cold = float(self.cfg.get("reifen_kalt", 60))
        now = clock()
        if t["speed"] > 60 and not me["in_pits"]:
            for i, ty in enumerate(t["tyres"]):
                avg = sum(ty["temps"]) / 3
                k = f"hot{i}"
                if avg > hot:
                    self.hot_since.setdefault(k, now)
                    if now - self.hot_since[k] > 8:
                        self.say(f"Reifen {fmt.TYRE_NAMES[i]} überhitzt, {round(avg)} Grad. Etwas schonen.", 2, "reifen",
                                 key=k, cooldown=90)
                else:
                    self.hot_since.pop(k, None)
            avg_all = sum(sum(ty["temps"]) / 3 for ty in t["tyres"]) / 4
            if avg_all < cold and me["laps"] >= 1 and self.lap_fuel_start is not None:
                self.hot_since.setdefault("cold", now)
                if now - self.hot_since["cold"] > 25:
                    self.say("Reifen sind noch kalt, vorsichtig in den Kurven.", 2, "reifen", key="cold", cooldown=180)
            else:
                self.hot_since.pop("cold", None)
            bmax = max(ty["brake_temp"] for ty in t["tyres"])
            if bmax > float(self.cfg.get("bremse_heiss", 850)):
                self.say("Bremsen sind sehr heiß!", 2, "technik", key="brakes", cooldown=120)

        # Restzeit
        if race and s["time_left"] is not None and s["phase"] == 5:
            for mins in (30, 15, 10, 5, 2, 1):
                if s["time_left"] <= mins * 60 and s["time_left"] > mins * 60 - 20 and mins not in self.time_called:
                    self.time_called.add(mins)
                    if s["elapsed"] > 60:
                        self.say(f"Noch {fmt.minutes_speech(mins * 60)} im Rennen.", 2, "session")

        # Wetter
        r_prev, w_prev = prev.get("raining"), prev.get("wetness")
        if r_prev is not None:
            if s["raining"] >= 0.1 > r_prev:
                self.say("Es fängt an zu regnen.", 2, "wetter", key="rain", cooldown=120)
            elif s["raining"] < 0.03 <= r_prev:
                self.say("Der Regen hat aufgehört.", 2, "wetter", key="rainstop", cooldown=120)
            if s["wetness"] >= 0.3 > (w_prev or 0):
                self.say("Die Strecke wird richtig nass. Denk über Regenreifen nach.", 2, "wetter", key="wet", cooldown=300)

        # Schnellere Klasse von hinten / langsamere Autos voraus (Multiklasse)
        if multi and race and not me["in_pits"]:
            for r in relative:
                if r["me"]:
                    continue
                if r["faster_cls"] and -2.6 < r["rel"] < -0.6:
                    self.say(f"{r['cls']} kommt von hinten, {fmt.gap_speech(r['rel'])}.", 2, "verkehr",
                             key=f"faster{r['id']}", cooldown=45)
                elif not r["faster_cls"] and r["cls"] != me["cls"] and 1.0 < r["rel"] < 3.5 \
                        and class_pace.get(r["cls"]) and class_pace.get(me["cls"]) \
                        and class_pace[r["cls"]] > class_pace[me["cls"]] * 1.02:
                    self.say(f"Langsamerer {r['cls']} voraus.", 3, "verkehr", key=f"slower{r['id']}", cooldown=60)

    # ------------------------------------------------------------------ Berichte (für Hotkeys & Fragen)
    def fuel_report(self) -> str:
        a = self.analysis
        f = a.get("fuel") or {}
        if not a.get("connected") or "fuel" not in a:
            return "Ich habe noch keine Daten vom Auto."
        if not f.get("per_lap"):
            return f"Du hast {fmt.liters(f['fuel'])} im Tank. Für den Verbrauch brauche ich noch eine volle Runde."
        txt = (f"{fmt.liters(f['fuel'])} im Tank, Verbrauch {fmt.num(f['per_lap'])} Liter pro Runde. "
               f"Das reicht für {fmt.laps_speech(f['laps_left'])}.")
        if f.get("to_add") is not None:
            txt += " Das reicht bis ins Ziel." if f["to_add"] == 0 else \
                f" Bis ins Ziel fehlen {fmt.liters(f['to_add'])}, also {f['stops']} Stopp{'s' if f['stops'] > 1 else ''}."
        e = a.get("energy")
        if e and e.get("per_lap"):
            txt += f" Virtuelle Energie {fmt.num(e['level'])} Prozent, reicht für {fmt.laps_speech(e['laps_left'])}."
        return txt

    def tyre_report(self) -> str:
        ty = self.analysis.get("tyres")
        if not ty:
            return "Ich habe noch keine Reifendaten."
        parts = []
        for i, t in enumerate(ty):
            parts.append(f"{fmt.TYRE_NAMES[i]} {round(t['avg'])} Grad, {round(t['wear'] * 100)} Prozent")
        hot = max(ty, key=lambda t: t["avg"])
        return "Reifen: " + "; ".join(parts) + f". Drücke zwischen {round(min(t['pressure'] for t in ty))} und " \
               f"{round(max(t['pressure'] for t in ty))} kPa."

    def gap_report(self) -> str:
        g = self.analysis.get("gaps")
        if g is None:
            return "Ich habe noch keine Abstände."
        parts = []
        if g.get("ahead") is not None:
            parts.append(f"Vor dir {g['ahead_name']}, " + (f"{g['ahead_laps']} Runden" if g.get("ahead_laps") else fmt.gap_speech(g["ahead"])))
        else:
            parts.append("Vor dir ist niemand aus deiner Klasse, du führst")
        if g.get("behind") is not None:
            parts.append(f"hinter dir {g['behind_name']}, " + (f"{g['behind_laps']} Runden" if g.get("behind_laps") else fmt.gap_speech(g["behind"])))
        return ", ".join(parts) + "."

    def position_report(self) -> str:
        p = self.analysis.get("position")
        if not p:
            return "Ich habe noch keine Positionsdaten."
        if p["multi"]:
            return f"Du bist P{p['cls']} von {p['cls_count']} in deiner Klasse, gesamt P{p['overall']}."
        return f"Du bist P{p['overall']} von {p['total']}."

    def pace_report(self) -> str:
        tm = self.analysis.get("timing")
        if not tm:
            return "Ich habe noch keine Rundenzeiten."
        txt = f"Letzte Runde {fmt.laptime_speech(tm['last'])}, Bestzeit {fmt.laptime_speech(tm['best'])}."
        valid = [l["time"] for l in tm["laps"] if l["valid"]][-5:]
        if len(valid) >= 3:
            txt += f" Schnitt der letzten {len(valid)} Runden: {fmt.laptime_speech(sum(valid) / len(valid))}."
        return txt

    def session_report(self) -> str:
        s = self.analysis.get("session")
        if not s:
            return "Keine Session aktiv."
        txt = f"{s['name']} auf {s['track']}."
        if s.get("time_left") is not None:
            txt += f" Noch {fmt.minutes_speech(s['time_left'])}."
        if s.get("laps_remaining") is not None:
            txt += f" Etwa {fmt.laps_speech(s['laps_remaining'])} zu fahren."
        return txt

    def weather_report(self) -> str:
        s = self.analysis.get("session")
        if not s:
            return "Keine Wetterdaten."
        rain = "kein Regen" if s["raining"] < 0.05 else ("leichter Regen" if s["raining"] < 0.3 else "starker Regen")
        return (f"Luft {round(s['air_temp'])} Grad, Strecke {round(s['track_temp'])} Grad, {rain}, "
                f"Strecke {round(s['wetness'] * 100)} Prozent nass.")

    def damage_report(self) -> str:
        d = self.analysis.get("damage")
        if not d:
            return "Keine Daten."
        if d["level"] == 0 and not d["detached"]:
            return "Kein Schaden erkannt, das Auto ist heil."
        return ("Schwerer" if d["level"] >= 2 else "Leichter") + " Schaden am Auto" + \
            (", es fehlen Teile." if d["detached"] else ".")

    def status_report(self) -> str:
        if not self.analysis.get("connected") or "timing" not in self.analysis:
            return "Ich warte noch auf Daten aus Le Mans Ultimate."
        return " ".join([self.position_report(), self.gap_report(), self.fuel_report()])
