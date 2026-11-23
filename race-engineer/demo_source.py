"""Demo-Modus: simuliert ein Multiklassen-Rennen im LMU-Datenformat.

So kannst du Dashboard, Sprachausgabe und KI ausprobieren, ohne dass das Spiel läuft.
Erzeugt exakt dieselben Frames wie lmu_shm.SharedMemoryReader.read().
"""
from __future__ import annotations

import math
import random
import time

TRACK_LEN = 5400.0
N_PTS = 1080
RACE_SECONDS = 25 * 60

DRIVERS = [
    ("Hypercar", "Ferrari 499P", ["A. Rossi", "M. Laurent", "K. Tanaka", "J. Becker", "L. Novak", "P. Santos"]),
    ("LMGT3", "Porsche 911 GT3 R", ["Du", "T. Weber", "R. Moreau", "S. Kowalski", "D. Fischer", "E. Lindqvist",
                                    "N. Hoffmann", "C. Dubois"]),
]
PLAYER_NAME = "Du"


def _build_track():
    pts = []
    for i in range(N_PTS):
        th = 2 * math.pi * i / N_PTS
        r = 1.0 + 0.22 * math.sin(3 * th) + 0.10 * math.cos(5 * th + 0.6) + 0.05 * math.sin(8 * th)
        pts.append((r * math.cos(th), r * math.sin(th)))
    length = sum(math.dist(pts[i], pts[(i + 1) % N_PTS]) for i in range(N_PTS))
    k = TRACK_LEN / length
    pts = [(x * k, y * k) for x, y in pts]
    # gleichmäßig nach Streckenmeter auflösen
    seg = [math.dist(pts[i], pts[(i + 1) % N_PTS]) for i in range(N_PTS)]
    cum = [0.0]
    for d in seg:
        cum.append(cum[-1] + d)
    step = TRACK_LEN / N_PTS
    out, j = [], 0
    for i in range(N_PTS):
        s = i * step
        while cum[j + 1] < s:
            j += 1
        f = (s - cum[j]) / max(seg[j], 1e-6)
        a, b = pts[j], pts[(j + 1) % N_PTS]
        out.append((a[0] + (b[0] - a[0]) * f, a[1] + (b[1] - a[1]) * f))
    # Kurvenradius -> Grenzgeschwindigkeit (m/s) für ein GT3-Auto
    vlim = []
    for i in range(N_PTS):
        p0, p1, p2 = out[i - 3], out[i], out[(i + 3) % N_PTS]
        a, b, c = math.dist(p0, p1), math.dist(p1, p2), math.dist(p0, p2)
        area = abs((p1[0] - p0[0]) * (p2[1] - p0[1]) - (p2[0] - p0[0]) * (p1[1] - p0[1])) / 2
        radius = (a * b * c) / (4 * area) if area > 1e-6 else 1e9
        vlim.append(min(74.0, math.sqrt(8.0 * radius)))
    # Beschleunigen / Bremsen glätten
    v = vlim[:]
    for _ in range(2):
        for i in range(N_PTS):          # vorwärts: Beschleunigung
            prev = v[i - 1]
            v[i] = min(v[i], math.sqrt(prev * prev + 2 * 7.0 * step))
        for i in range(N_PTS - 1, -1, -1):   # rückwärts: Bremsen
            nxt = v[(i + 1) % N_PTS]
            v[i] = min(v[i], math.sqrt(nxt * nxt + 2 * 18.0 * step))
    return out, v


TRACK, SPEED = _build_track()
STEP = TRACK_LEN / N_PTS


def _corners():
    """Kurven (Scheitelpunkte), Krümmung und eine einfache Ideallinie für die Demo-Fahrer."""
    curv = []
    for i in range(N_PTS):
        p0, p1, p2 = TRACK[i - 3], TRACK[i], TRACK[(i + 3) % N_PTS]
        ax, ay, bx, by = p1[0] - p0[0], p1[1] - p0[1], p2[0] - p1[0], p2[1] - p1[1]
        curv.append((ax * by - ay * bx) / (math.hypot(ax, ay) * math.hypot(bx, by) * 6 * STEP + 1e-9))
    apexes = []
    for i in range(N_PTS):
        win = [SPEED[(i + k) % N_PTS] for k in range(-40, 41)]
        if SPEED[i] == min(win) and max(SPEED[(i - k) % N_PTS] for k in range(80)) - SPEED[i] > 6:
            if not apexes or i - apexes[-1] > 20:
                apexes.append(i)
    ideal = [0.0] * N_PTS
    owner = [None] * N_PTS
    for k, a in enumerate(apexes):
        sign = 1.0 if curv[a] > 0 else -1.0     # positiv = Linkskurve -> innen = links
        for j in range(-90, 60):
            i = (a + j) % N_PTS
            d = j * STEP
            w = math.exp(-(d / 70) ** 2)
            e = math.exp(-(d / 230) ** 2)
            ideal[i] += sign * (4.0 * w - 3.0 * e * (1 - w))
            if -60 <= j <= 30:
                owner[i] = k
    return curv, apexes, ideal, owner


CURV, APEXES, IDEAL, OWNER = _corners()


def _track_at(s: float):
    s %= TRACK_LEN
    f = s / TRACK_LEN * N_PTS
    i = int(f) % N_PTS
    t = f - int(f)
    a, b = TRACK[i], TRACK[(i + 1) % N_PTS]
    x, y = a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t
    v = SPEED[i] + (SPEED[(i + 1) % N_PTS] - SPEED[i]) * t
    dx, dy = b[0] - a[0], b[1] - a[1]
    n = math.hypot(dx, dy) or 1.0
    return x, y, v, dx / n, dy / n


class _Car:
    def __init__(self, cid, driver, vehicle, cls, pace, start_s):
        self.id = cid
        self.driver = driver
        self.vehicle = vehicle
        self.cls = cls
        self.base_pace = pace
        self.pace = pace
        self.s = start_s           # Streckenmeter (kann am Start negativ sein)
        self.laps = 0
        self.lap_start = 0.0
        self.best = None
        self.last = None
        self.s1 = self.s2 = None
        self.last_s1 = self.last_s2 = None
        self.best_s1 = self.best_s2 = None
        self.cur_s1 = self.cur_s2 = None
        self.lateral = random.uniform(-2.5, 2.5)
        self.lat_target = self.lateral
        self.in_pits = False
        self.pit_timer = 0.0
        self.pitstops = 0
        self.speed = 0.0
        self.is_player = driver == PLAYER_NAME


class DemoSource:
    """Simuliert ein 25-Minuten-Rennen auf einem fiktiven 5,4-km-Kurs."""

    def __init__(self, speedup: float = 1.0):
        random.seed()
        self.speedup = speedup
        self.t = 0.0
        self.wall = time.monotonic()
        self.cars: list[_Car] = []
        cid = 0
        grid = 0
        for cls, vehicle, names in DRIVERS:
            for name in names:
                pace = (1.11 if cls == "Hypercar" else 1.0) * random.uniform(0.985, 1.012)
                if name == PLAYER_NAME:
                    pace = 1.004
                self.cars.append(_Car(cid, name, vehicle, cls, pace, -grid * 14.0 - 5))
                cid += 1
                grid += 1
        self.player = next(c for c in self.cars if c.is_player)
        # Spieler-Zustand
        self.fuel = 31.0
        self.fuel_cap = 100.0
        self.wear = [1.0, 1.0, 1.0, 1.0]
        self.tyre_t = [[60.0] * 3 for _ in range(4)]
        self.brake_t = [150.0] * 4
        self.water = 80.0
        self.oil = 90.0
        self.rpm = 3000.0
        self.gear = 1
        self.last_impact_et = 0.0
        self.last_impact_mag = 0.0
        self.dents = [0] * 8
        self.penalties = 0
        self.prev_v = 0.0
        self.limiter = False
        self.pit_request = False
        self.corner_style = {}
        self._new_style()

    # ------------------------------------------------------------------
    def _weather(self):
        rain = 0.0
        if self.t > 14 * 60:
            rain = min(0.45, (self.t - 14 * 60) / 240 * 0.45)
        wet = min(0.6, max(0.0, (self.t - 15 * 60) / 400))
        return rain, wet

    def _update_car(self, c: _Car, dt: float, rain: float):
        x, y, vlim, _, _ = _track_at(max(c.s, 0.0))
        grip = 1.0 - 0.12 * rain
        idx = int((max(c.s, 0.0) % TRACK_LEN) / STEP) % N_PTS
        line_err = 0.0
        if c.is_player and OWNER[idx] is not None:
            # Fahrfehler des Demo-Fahrers: Bremspunkt, Kurvenspeed, Linie
            shift, apex_f, line_err = self.corner_style.get(OWNER[idx], (0.0, 1.0, 0.0))
            vlim = _track_at(max(c.s, 0.0) + shift)[2]
            near = abs(((idx - APEXES[OWNER[idx]] + N_PTS // 2) % N_PTS) - N_PTS // 2) * STEP < 90
            if near:
                vlim *= apex_f * (1 - 0.012 * abs(line_err))
        target = vlim * c.pace * grip
        if c.in_pits:
            target = 60 / 3.6
            c.pit_timer -= dt
            if c.pit_timer <= 0 and c.s % TRACK_LEN > 200:
                c.in_pits = False
            elif c.pit_timer > 0 and c.pit_timer < 25 and c.s % TRACK_LEN > 80:
                target = 0.0   # steht in der Box
        # sanft auf Zielgeschwindigkeit
        if target > c.speed:
            c.speed = min(target, c.speed + 7.0 * dt)
        else:
            c.speed = max(target, c.speed - 18.0 * dt)
        if self.t < 2.0:
            c.speed = min(c.speed, 25.0)
        c.s += c.speed * dt
        # Linie: Ideallinie + eigene Abweichung
        if random.random() < dt * 0.15:
            c.lat_target = 0.0 if c.is_player else random.uniform(-1.8, 1.8)
        c.lat_off = getattr(c, "lat_off", 0.0) + (c.lat_target - getattr(c, "lat_off", 0.0)) * min(1.0, dt * 0.8)
        apex_w = 0.0
        if OWNER[idx] is not None:
            dd = ((idx - APEXES[OWNER[idx]] + N_PTS // 2) % N_PTS - N_PTS // 2) * STEP
            apex_w = math.exp(-(dd / 70) ** 2) * (1.0 if CURV[APEXES[OWNER[idx]]] > 0 else -1.0)
        c.lateral = max(-5.5, min(5.5, IDEAL[idx] + c.lat_off - line_err * apex_w))   # Fehler = nach außen

        lap_time = self.t - c.lap_start
        frac = c.s / TRACK_LEN
        if c.cur_s1 is None and frac >= 1 / 3 and c.laps >= 0 and c.s < TRACK_LEN:
            c.cur_s1 = lap_time
        if c.cur_s2 is None and c.cur_s1 is not None and frac >= 2 / 3 and c.s < TRACK_LEN:
            c.cur_s2 = lap_time - c.cur_s1
        if c.s >= TRACK_LEN:
            c.s -= TRACK_LEN
            if c.lap_start > 0 or c.laps > 0:
                lt = lap_time
                c.last = lt
                if c.cur_s1 and c.cur_s2:
                    c.last_s1, c.last_s2 = c.cur_s1, c.cur_s2
                    if c.best_s1 is None or c.cur_s1 < c.best_s1:
                        c.best_s1 = c.cur_s1
                    if c.best_s2 is None or c.cur_s2 < c.best_s2:
                        c.best_s2 = c.cur_s2
                if not c.in_pits and (c.best is None or lt < c.best):
                    c.best = lt
            c.laps += 1
            c.lap_start = self.t
            c.cur_s1 = c.cur_s2 = None
            c.pace = c.base_pace * random.gauss(1.0, 0.004)
            if c.is_player:
                self._player_lap_done()
            elif not c.is_player and c.laps in (9, 10) and random.random() < 0.5 and c.pitstops == 0:
                c.in_pits = True
                c.pit_timer = 38
                c.pitstops += 1

    def _new_style(self):
        """Pro Runde und Kurve leicht andere Bremspunkte/Linie, ab und zu ein deutlicher Fehler."""
        style = {}
        for k in range(len(APEXES)):
            shift, apex_f, err = random.gauss(0, 5), random.gauss(1.0, 0.008), random.gauss(0, 0.5)
            r = random.random()
            if r < 0.07:
                shift += 25          # viel zu früh gebremst
            elif r < 0.12:
                err += 2.2           # Scheitelpunkt verpasst (zu weit außen)
            elif r < 0.16:
                apex_f -= 0.04       # zu langsam durch die Kurve
            style[k] = (shift, apex_f, err)
        self.corner_style = style

    def _player_lap_done(self):
        self._new_style()
        p = self.player
        if self.pit_request:
            self.pit_request = False
            p.in_pits = True
            p.pit_timer = 40
            p.pitstops += 1
            self.fuel = min(self.fuel_cap, self.fuel + 32.0)
            self.wear = [1.0] * 4

    def _progress(self, c):
        return c.laps + c.s / TRACK_LEN

    # ------------------------------------------------------------------
    def read(self) -> dict:
        now = time.monotonic()
        dt_total = min(0.5, now - self.wall) * self.speedup
        self.wall = now
        return self.step(dt_total)

    def step(self, dt_total: float) -> dict:
        steps = max(1, int(dt_total / 0.05))
        dt = dt_total / steps
        rain, wet = self._weather()
        for _ in range(steps):
            self.t += dt
            if self.t >= RACE_SECONDS + 400:
                break
            for c in self.cars:
                self._update_car(c, dt, rain)
            self._player_physics(dt, rain)
        return self._frame(rain, wet)

    def _player_physics(self, dt, rain):
        p = self.player
        v = p.speed
        acc = (v - self.prev_v) / dt if dt > 0 else 0.0
        self.prev_v = v
        self.throttle = max(0.0, min(1.0, 0.3 + acc / 7.0)) if v > 1 else 0.2
        self.brake = max(0.0, min(1.0, -acc / 18.0))
        kmh = v * 3.6
        gears = [0, 75, 115, 150, 185, 220, 999]
        self.gear = next(i for i, g in enumerate(gears) if kmh <= g) if kmh > 1 else 1
        lo = gears[self.gear - 1] if self.gear > 1 else 0
        hi = gears[self.gear] if self.gear < 6 else 290
        self.rpm = 4200 + (kmh - lo) / max(hi - lo, 1) * 5000
        self.limiter = p.in_pits
        # Sprit
        if not p.in_pits:
            self.fuel = max(0.0, self.fuel - (0.0009 + 0.0062 * self.throttle) * v * dt / 8.0)
        # Reifen
        lat = abs(math.sin(p.s / 140.0))
        for i in range(4):
            front = i < 2
            work = (0.6 * self.throttle * (0.6 if front else 1.0) + 0.9 * self.brake * (1.0 if front else 0.6)
                    + 0.8 * lat) * (v / 60)
            target = 60 + 32 * min(work, 1.6) - 25 * rain
            for j in range(3):
                bias = (4 if (j == 0 and i % 2 == 0) or (j == 2 and i % 2 == 1) else 0) + (2 if j == 1 else 0)
                self.tyre_t[i][j] += (target + bias - self.tyre_t[i][j]) * min(1.0, dt * 0.35)
            if not p.in_pits:
                self.wear[i] = max(0.0, self.wear[i] - dt * v * (0.0000042 if i == 0 else 0.0000033) * (1 + work))
            btarget = 120 + 650 * self.brake * (1.0 if front else 0.7)
            self.brake_t[i] += (btarget - self.brake_t[i]) * min(1.0, dt * (1.2 if self.brake > 0.1 else 0.25))
        # gelegentlich Boxenstopp anfordern (die Demo-KI macht das selbst)
        if not p.in_pits and self.fuel < 4.5 and p.laps > 0:
            self.pit_request = True
        # Feindkontakt bei Minute 9
        if 540 < self.t < 540 + dt * 1.5:
            self.last_impact_et = self.t
            self.last_impact_mag = 4200.0
            self.dents[1] = 1

    def _frame(self, rain, wet) -> dict:
        cars_sorted = sorted(self.cars, key=self._progress, reverse=True)
        leader = cars_sorted[0]
        lead_lap = leader.best or leader.last or (TRACK_LEN / 55.0)
        out_cars = []
        for place, c in enumerate(cars_sorted, 1):
            ahead = cars_sorted[place - 2] if place > 1 else None
            d_lead = self._progress(leader) - self._progress(c)
            d_next = (self._progress(ahead) - self._progress(c)) if ahead else 0.0
            x, y, _, dx, dy = _track_at(max(c.s, 0.0))
            nx, ny = -dy, dx          # links von der Fahrtrichtung
            wx, wz = x + nx * c.lateral, y + ny * c.lateral
            est = c.best or c.last or lead_lap
            out_cars.append({
                "id": c.id, "driver": c.driver, "vehicle": c.vehicle, "cls": c.cls,
                "place": place, "laps": c.laps, "lap_dist": c.s % TRACK_LEN,
                "path_lateral": c.lateral,
                "sector": 1 + min(2, int((c.s % TRACK_LEN) / TRACK_LEN * 3)),
                "best": c.best, "last": c.last,
                "best_s1": c.best_s1, "best_s2": c.best_s2,
                "last_s1": c.last_s1, "last_s2": c.last_s2,
                "cur_s1": c.cur_s1, "cur_s2": c.cur_s2,
                "pitstops": c.pitstops, "penalties": self.penalties if c.is_player else 0,
                "is_player": c.is_player, "in_pits": c.in_pits, "pit_state": 3 if c.in_pits else 0,
                "time_behind_next": d_next * lead_lap, "laps_behind_next": int(d_next),
                "time_behind_leader": d_lead * lead_lap, "laps_behind_leader": int(d_lead),
                "lap_start_et": c.lap_start, "time_into_lap": self.t - c.lap_start, "est_lap": est,
                "pos": (wx, 0.0, wz), "speed": c.speed * 3.6,
                "flag": 0, "finish_status": 1 if self.t > RACE_SECONDS and c.s < 100 and c.laps > 1 else 0,
                "under_yellow": False, "control": 0 if c.is_player else 1,
            })
        me = next(c for c in out_cars if c["is_player"])
        # Blaue Flagge: Hypercar mit einer Runde Vorsprung direkt hinter dir
        for c in out_cars:
            if c["cls"] != me["cls"] and self._progress(self.cars[c["id"]]) - self._progress(self.player) > 0.97:
                gap = (self.player.s - self.cars[c["id"]].s) % TRACK_LEN
                if gap < 120:
                    me["flag"] = 6
        p = self.player
        x, y, _, dx, dy = _track_at(max(p.s, 0.0))
        yellow = [0, 0, 0]
        if 360 < self.t < 400:
            yellow[1] = 1
        phase = 5
        if self.t >= RACE_SECONDS and leader.laps > 0:
            phase = 8 if all(c["finish_status"] for c in out_cars) else 5
        time_left = max(0.0, RACE_SECONDS - self.t)
        tyres = []
        for i in range(4):
            temps = [round(t, 1) for t in self.tyre_t[i]]
            avg = sum(temps) / 3
            tyres.append({
                "temps": temps, "inner": [round(t + 4, 1) for t in temps], "carcass": round(avg + 6, 1),
                "pressure": round(162 + (avg - 70) * 0.35, 1), "wear": self.wear[i],
                "flat": False, "detached": False, "brake_temp": round(self.brake_t[i]), "surface": 0,
            })
        return {
            "source": "demo",
            "session": {
                "id": 10, "name": "Rennen (Demo)", "kind": "race", "phase": phase,
                "elapsed": self.t, "time_left": time_left, "max_laps": None,
                "track": "Demo-Ring", "track_length": TRACK_LEN,
                "yellow_state": 0, "sector_flags": yellow, "start_lights": 0, "red_lights": 0,
                "in_realtime": True, "raining": rain, "dark_cloud": rain,
                "air_temp": 21.0 - 4 * rain, "track_temp": 31.0 - 10 * rain - 8 * self._weather()[1],
                "wetness": self._weather()[1], "num_cars": len(out_cars),
            },
            "cars": out_cars,
            "player": {
                "vehicle": p.vehicle, "speed": p.speed * 3.6, "gear": self.gear if p.speed > 0.5 else 0,
                "rpm": self.rpm, "max_rpm": 9400.0,
                "throttle": getattr(self, "throttle", 0.0), "brake": getattr(self, "brake", 0.0),
                "clutch": 0.0, "steering": max(-1.0, min(1.0, -CURV[int((max(p.s, 0.0) % TRACK_LEN) / STEP) % N_PTS] * 60)),
                "fuel": self.fuel, "fuel_capacity": self.fuel_cap,
                "lap_number": p.laps, "lap_start_et": p.lap_start, "elapsed": self.t,
                "water_temp": 82 + 6 * getattr(self, "throttle", 0), "oil_temp": 95.0,
                "overheating": False, "detached": False, "dents": self.dents,
                "last_impact_et": self.last_impact_et, "last_impact_mag": self.last_impact_mag,
                "limiter": self.limiter, "in_pitlane": p.in_pits, "headlights": False,
                "rear_brake_bias": 0.44, "battery": None, "boost_state": 0,
                "tyres": tyres, "compound_front": "Medium", "compound_rear": "Medium",
                "pos": (x + -dy * p.lateral, 0.0, y + dx * p.lateral),
                # lokales -z = vorne, lokales +x = links (rF2-Konvention)
                "ori_z": (-dx, 0.0, -dy), "ori_x": (-dy, 0.0, dx),
                "virtual_energy": None,
            },
        }
