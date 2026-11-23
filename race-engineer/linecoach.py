"""Fahrlinien- und Kurvenanalyse ("Coach").

Zeichnet jede Runde auf (Position, Speed, Gas, Bremse, Lenkung über die Streckenmeter),
erkennt aus der Bestrunde automatisch die Kurven und vergleicht jede weitere Runde damit:
  - Zeitgewinn/-verlust pro Kurvenabschnitt (die Summe ergibt genau das Runden-Delta)
  - Bremspunkt, minimaler Kurvenspeed, Gaspunkt, Speed am Ausgang
  - Linie: wie weit innen/außen du am Scheitelpunkt und am Ausgang warst
  - Theoretische Bestzeit (beste Abschnitte aus allen Runden)
"""
from __future__ import annotations

import bisect
import math
import statistics

import fmt

GRID = 5.0                 # Meter pro Stützstelle
MIN_LOSS_CALL = 0.10       # ab so viel Zeitverlust gibt es einen Funk-Tipp


def _interp(xs, ys, x):
    i = bisect.bisect_left(xs, x)
    if i <= 0:
        return ys[0]
    if i >= len(xs):
        return ys[-1]
    x0, x1 = xs[i - 1], xs[i]
    f = (x - x0) / (x1 - x0) if x1 > x0 else 0.0
    return ys[i - 1] + (ys[i] - ys[i - 1]) * f


class Lap:
    """Eine aufgezeichnete Runde, auf ein festes 5-m-Raster umgerechnet."""

    FIELDS = ("t", "v", "thr", "brk", "steer", "x", "z")

    def __init__(self, samples: list[tuple], length: float, lap_time: float, number: int):
        self.number = number
        self.lap_time = lap_time
        self.length = length
        self.n = int(length // GRID) + 1
        ds = [s[0] for s in samples]
        cols = list(zip(*[s[1:] for s in samples]))
        # Anker: Zeit 0 am Start, Rundenzeit am Ziel
        ds_t = [0.0] + ds + [length]
        ts = [0.0] + list(cols[0]) + [lap_time]
        grid = [min(i * GRID, length) for i in range(self.n)]
        self.d = grid
        self.t = [_interp(ds_t, ts, g) for g in grid]
        for name, col in zip(self.FIELDS[1:], cols[1:]):
            setattr(self, name, [_interp(ds, col, g) for g in grid])

    def time_at(self, d: float) -> float:
        return _interp(self.d, self.t, min(max(d, 0.0), self.length))


def coverage_ok(samples, length) -> bool:
    if len(samples) < 40:
        return False
    ds = [s[0] for s in samples]
    if ds[0] > 0.03 * length or ds[-1] < 0.97 * length:
        return False
    # keine großen Lücken (z. B. Pause, Teleport)
    return max(b - a for a, b in zip(ds, ds[1:])) < 60


class LineCoach:
    def __init__(self, cfg: dict, say):
        self.cfg = cfg
        self.say = say
        self.reset()

    def reset(self):
        self.samples: list[tuple] = []
        self.finished: list[tuple] = []
        self.ref: Lap | None = None
        self.laps: list[Lap] = []           # gültige, vollständige Runden
        self.corners: list[dict] = []
        self.bounds: list[float] = []       # Abschnittsgrenzen in Metern
        self.last_cmp: dict | None = None   # Vergleich der letzten Runde
        self.history: list[dict] = []       # Vergleiche der letzten Runden
        self.version = 0
        self._last_d = -1.0

    # ------------------------------------------------------------------ Aufzeichnen
    def sample(self, dist, time_into, t):
        if dist <= self._last_d + 1.0:
            if dist < self._last_d - 200:      # neue Runde ohne Rundenwechsel (Reset/Teleport)
                self.samples = []
                self._last_d = -1.0
            return
        self._last_d = dist
        self.samples.append((dist, time_into, t["speed"], t["throttle"], t["brake"], t["steering"],
                             t["pos"][0], t["pos"][2]))

    def lap_boundary(self):
        """Aufgerufen, sobald der Rundenwechsel erkannt wurde."""
        self.finished = self.samples
        self.samples = []
        self._last_d = -1.0

    def on_lap(self, number: int, lap_time: float | None, valid: bool, is_best: bool, length: float):
        samples = self.finished
        self.finished = []
        if not (valid and lap_time and length > 500 and coverage_ok(samples, length)):
            return
        lap = Lap(samples, length, lap_time, number)
        self.laps.append(lap)
        self.laps = self.laps[-40:]
        if is_best or self.ref is None or abs(self.ref.length - length) > 1:
            first = self.ref is None
            self.ref = lap
            self._detect_corners()
            self.version += 1
            if first and self.corners:
                self.say(f"Ich habe {len(self.corners)} Kurven erkannt. Ab jetzt vergleiche ich jede Runde "
                         f"mit deiner Bestrunde.", 3, "fahrlinie")
            # Vergleich der vorigen Runden mit der neuen Referenz aktualisieren
            self.history = [self._compare(l) for l in self.laps[-4:-1]]
            self.last_cmp = None
            return
        cmp = self._compare(lap)
        self.last_cmp = cmp
        self.history.append(cmp)
        self.history = self.history[-5:]
        self.version += 1
        self._lap_call(cmp)

    # ------------------------------------------------------------------ Kurven erkennen
    def _detect_corners(self):
        r = self.ref
        v, n = r.v, r.n
        apexes = []
        for i in range(3, n - 10):
            lo, hi = max(0, i - 30), min(n, i + 31)          # ±150 m
            if v[i] > min(v[lo:hi]) or v[i] > 280:
                continue
            before = v[max(0, i - 80):i + 1]                 # 400 m davor
            after = v[i:min(n, i + 60)]
            drop = max(before) - v[i]
            if drop < 10 and max(after) - v[i] < 10:
                continue
            if apexes and i - apexes[-1] < 20:               # Schikane: tiefsten Punkt behalten
                if v[i] < v[apexes[-1]]:
                    apexes[-1] = i
                continue
            apexes.append(i)

        corners = []
        for a in apexes:
            b, kind = None, "Bremsen"
            j = a
            while j > max(0, a - 120) and r.brk[j] < 0.15:
                j -= 1
            if r.brk[j] >= 0.15:
                # Anfang dieser Bremsphase (vom Scheitel aus rückwärts, ohne Lücke)
                while j > max(0, a - 120) and r.brk[j - 1] >= 0.15:
                    j -= 1
                k = 0
                while j > 0 and r.brk[j - 1] > 0.05 and k < 6:
                    j -= 1
                    k += 1
                b = j
            else:
                kind = "Lupfen"
                j = a
                while j > max(0, a - 80) and r.thr[j - 1] < 0.9:
                    j -= 1
                b = j
            g = a
            while g < n - 1 and r.thr[g] < 0.9:
                g += 1
            steer = sum(r.steer[max(0, a - 4):a + 5]) / len(r.steer[max(0, a - 4):a + 5])
            corners.append({"apex": a, "brake": b, "throttle": g, "kind": kind,
                            "dir": "links" if steer < 0 else "rechts",
                            "x": round(r.x[a], 1), "z": round(r.z[a], 1),
                            "ref_min_v": round(min(v[max(0, a - 12):a + 13]))})
        # Abschnittsgrenzen: 20 m vor dem Bremspunkt
        bounds, keep = [], []
        for c in corners:
            bd = max(GRID, (c["brake"] - 4) * GRID)
            if bounds and bd <= bounds[-1] + 30:
                continue
            bounds.append(bd)
            keep.append(c)
        for i, c in enumerate(keep, 1):
            c["n"] = i
            c["name"] = f"Kurve {i}"
            c["start"] = bounds[i - 1]
            c["end"] = bounds[i] if i < len(bounds) else r.length
        self.corners = keep
        self.bounds = bounds

    # ------------------------------------------------------------------ Vergleich
    def _segments(self, lap: Lap):
        pts = [0.0] + self.bounds + [lap.length]
        return [lap.time_at(b) - lap.time_at(a) for a, b in zip(pts, pts[1:])]

    def _inside_vec(self, i):
        """Richtung zum Kurveninneren an Index i (aus der Sehne der Referenzlinie)."""
        r = self.ref
        a, b = max(0, i - 8), min(r.n - 1, i + 8)
        mx, mz = (r.x[a] + r.x[b]) / 2 - r.x[i], (r.z[a] + r.z[b]) / 2 - r.z[i]
        ln = math.hypot(mx, mz)
        return (mx / ln, mz / ln) if ln > 0.05 else None

    def _normal_towards(self, i, inside):
        """Quer zur Fahrtrichtung an Index i, zur Kurveninnenseite zeigend."""
        if inside is None:
            return None
        r = self.ref
        a, b = max(0, i - 1), min(r.n - 1, i + 1)
        dx, dz = r.x[b] - r.x[a], r.z[b] - r.z[a]
        ln = math.hypot(dx, dz)
        if ln < 1e-6:
            return None
        nx, nz = -dz / ln, dx / ln
        return (nx, nz) if nx * inside[0] + nz * inside[1] >= 0 else (-nx, -nz)

    def _offset(self, lap: Lap, i, inside):
        if inside is None:
            return None
        return (lap.x[i] - self.ref.x[i]) * inside[0] + (lap.z[i] - self.ref.z[i]) * inside[1]

    def _brake_start(self, lap: Lap, ref_b, apex):
        """Beginn der Bremsphase vor diesem Scheitelpunkt (max. 120 m vor dem Referenz-Bremspunkt)."""
        j = apex
        while j > ref_b - 24 and j > 0 and lap.brk[j] < 0.15:
            j -= 1
        if lap.brk[j] < 0.15:
            return None
        while j > max(0, ref_b - 24) and lap.brk[j - 1] >= 0.15:
            j -= 1
        k = 0
        while j > 0 and lap.brk[j - 1] > 0.05 and k < 6:
            j -= 1
            k += 1
        return j

    def _compare(self, lap: Lap) -> dict:
        r = self.ref
        seg_l, seg_r = self._segments(lap), self._segments(r)
        out = []
        for c in self.corners:
            i = c["n"]
            a, b, g = c["apex"], c["brake"], c["throttle"]
            w0, w1 = max(0, a - 12), min(r.n, a + 13)
            minv_l, minv_r = min(lap.v[w0:w1]), min(r.v[w0:w1])
            res = {"n": i, "loss": round(seg_l[i] - seg_r[i], 3), "time": round(seg_l[i], 3),
                   "minv": round(minv_l), "minv_diff": round(minv_l - minv_r, 1)}
            if c["kind"] == "Bremsen":
                bl = self._brake_start(lap, b, a)
                diff = (bl - b) * GRID if bl is not None else None
                res["brake_diff"] = round(diff) if diff is not None and abs(diff) <= 100 else None
            else:
                res["brake_diff"] = None
            k = w0 + min(range(w1 - w0), key=lambda q: lap.v[w0 + q])
            while k < lap.n - 1 and lap.thr[k] < 0.9:
                k += 1
            res["thr_diff"] = round((k - g) * GRID)
            inside = self._inside_vec(a)
            off = self._offset(lap, a, inside)
            res["apex_off"] = round(off, 1) if off is not None else None
            e = min(r.n - 1, g + 6)
            off_e = self._offset(lap, e, self._normal_towards(e, inside))
            res["exit_off"] = round(off_e, 1) if off_e is not None else None
            ei = min(r.n - 1, int(c["end"] // GRID) - 2)
            res["exit_v_diff"] = round(lap.v[ei] - r.v[ei], 1)
            res["tip"] = self._tip(res)
            out.append(res)
        return {"lap": lap.number, "lap_time": lap.lap_time, "delta": round(lap.lap_time - r.lap_time, 3),
                "straight_loss": round(seg_l[0] - seg_r[0], 3), "corners": out}

    @staticmethod
    def _tip(res) -> str:
        if res["loss"] < 0.05:          # nur erklären, wo wirklich Zeit liegen bleibt
            return ""
        parts = []
        bd, mv, td, ao = res.get("brake_diff"), res["minv_diff"], res["thr_diff"], res.get("apex_off")
        if bd is not None and bd <= -10:
            parts.append(f"{abs(bd)} Meter zu früh gebremst")
        elif bd is not None and bd >= 10 and mv < -2:
            parts.append(f"{bd} Meter später gebremst und die Kurve überfahren")
        if mv <= -2.5:
            parts.append(f"{round(abs(mv))} km/h weniger Kurvenspeed")
        elif mv >= 3 and res["loss"] > 0.05:
            parts.append(f"{round(mv)} km/h mehr Kurvenspeed, aber schlechter raus")
        if ao is not None and ao <= -1.2:
            parts.append(f"am Scheitelpunkt {fmt.num(abs(ao))} Meter zu weit außen")
        elif ao is not None and ao >= 1.5 and mv < -1:
            parts.append(f"{fmt.num(ao)} Meter enger als sonst, zu früh eingelenkt")
        if td >= 12:
            parts.append(f"{td} Meter später voll am Gas")
        if not parts and res["exit_v_diff"] <= -2:
            parts.append(f"{round(abs(res['exit_v_diff']))} km/h langsamer am Kurvenausgang")
        return ", ".join(parts[:2])

    # ------------------------------------------------------------------ Ansagen & Berichte
    def _lap_call(self, cmp):
        if not self.cfg.get("fahrlinie_tipps", True):
            return
        worst = max(cmp["corners"], key=lambda c: c["loss"], default=None)
        if not worst or worst["loss"] < MIN_LOSS_CALL:
            return
        txt = f"Kurve {worst['n']}: {fmt.gap_speech(worst['loss'])} verloren"
        if worst["tip"]:
            txt += f", {worst['tip']}"
        self.say(txt + ".", 3, "fahrlinie")

    def theoretical_best(self):
        if not self.ref or not self.laps:
            return None
        segs = [self._segments(l) for l in self.laps if abs(l.length - self.ref.length) < 1]
        if not segs:
            return None
        return sum(min(col) for col in zip(*segs))

    def corner_stats(self):
        """Pro Kurve: Durchschnittsverlust der letzten Runden und Konstanz."""
        stats = {}
        for c in self.corners:
            losses = [h["corners"][c["n"] - 1]["loss"] for h in self.history
                      if len(h["corners"]) >= c["n"]]
            stats[c["n"]] = {"avg_loss": round(statistics.mean(losses), 3) if losses else None,
                             "spread": round(statistics.pstdev(losses), 3) if len(losses) >= 2 else None}
        return stats

    def report(self) -> str:
        if not self.ref:
            return "Für die Linienanalyse brauche ich erst eine saubere, vollständige Runde."
        if not self.history:
            return (f"Ich habe {len(self.corners)} Kurven erkannt und deine Bestrunde gespeichert. "
                    "Fahr noch eine Runde, dann sage ich dir, wo du Zeit liegen lässt.")
        st = self.corner_stats()
        ranked = sorted((c for c in self.corners if st[c["n"]]["avg_loss"] is not None),
                        key=lambda c: -st[c["n"]]["avg_loss"])
        last = self.history[-1]["corners"]
        parts = []
        for c in ranked[:2]:
            loss = st[c["n"]]["avg_loss"]
            if loss < 0.04:
                continue
            tip = last[c["n"] - 1]["tip"] if len(last) >= c["n"] else ""
            parts.append(f"In Kurve {c['n']} verlierst du im Schnitt {fmt.gap_speech(loss)}" + (f", {tip}" if tip else ""))
        tb = self.theoretical_best()
        txt = ". ".join(parts) + "." if parts else "Du fährst deine Kurven sehr konstant, kaum Zeitverlust zur Bestrunde."
        if tb and self.ref and self.ref.lap_time - tb > 0.05:
            txt += f" Theoretische Bestzeit {fmt.laptime_speech(tb)}, also {fmt.gap_speech(self.ref.lap_time - tb)} Potenzial."
        return txt

    def summary(self) -> dict | None:
        """Kompakte Daten für die KI."""
        if not self.ref:
            return None
        st = self.corner_stats()
        last = self.history[-1]["corners"] if self.history else []
        return {
            "referenz_runde": self.ref.lap_time,
            "theoretische_bestzeit": self.theoretical_best(),
            "kurven": [{**{k: c[k] for k in ("n", "dir", "kind", "ref_min_v")},
                        "bremspunkt_m": c["brake"] * GRID, "scheitel_m": c["apex"] * GRID,
                        "verlust_schnitt_s": st[c["n"]]["avg_loss"], "streuung_s": st[c["n"]]["spread"],
                        "letzte_runde": last[c["n"] - 1] if len(last) >= c["n"] else None}
                       for c in self.corners],
        }

    def dashboard(self) -> dict:
        """Daten für die Kurven-Ansicht im Dashboard (nur bei Änderungen gesendet)."""
        if not self.ref:
            return {"ready": False, "laps": len(self.laps)}
        r = self.ref
        last = self.laps[-1] if self.laps and self.laps[-1] is not r and self.last_cmp else None
        step = 2   # alle 10 m

        def pack(lap):
            if lap is None:
                return None
            return {"lap": lap.number, "time": lap.lap_time,
                    "x": [round(v, 1) for v in lap.x[::step]], "z": [round(v, 1) for v in lap.z[::step]],
                    "v": [round(v) for v in lap.v[::step]], "thr": [round(v, 2) for v in lap.thr[::step]],
                    "brk": [round(v, 2) for v in lap.brk[::step]]}

        st = self.corner_stats()
        cmp = {c["n"]: c for c in (self.last_cmp or {}).get("corners", [])}
        corners = []
        for c in self.corners:
            corners.append({**{k: c[k] for k in ("n", "name", "dir", "kind", "x", "z", "ref_min_v")},
                            "brake_d": c["brake"] * GRID, "apex_d": c["apex"] * GRID,
                            "thr_d": c["throttle"] * GRID, "start": c["start"], "end": c["end"],
                            "last": cmp.get(c["n"]), **st[c["n"]]})
        tb = self.theoretical_best()
        return {"ready": True, "step_m": GRID * step, "length": r.length, "ref": pack(r), "last": pack(last),
                "corners": corners, "theoretical_best": tb, "ref_time": r.lap_time,
                "laps": len(self.laps), "delta": (self.last_cmp or {}).get("delta")}
