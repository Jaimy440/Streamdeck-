"""LMU Race Engineer – KI-Renningenieur für Le Mans Ultimate.

Start:  python main.py          (liest Le Mans Ultimate über das Shared-Memory-Plugin)
        python main.py --demo   (simuliertes Rennen zum Ausprobieren, ohne Spiel)

Dashboard: http://127.0.0.1:8770 (öffnet sich automatisch). Andere Geräte im WLAN
(Tablet, Handy als Zweitbildschirm) nutzen die im Fenster angezeigte Adresse.
"""
from __future__ import annotations

import argparse
import asyncio
import copy
import json
import os
import secrets
import socket
import sys
import webbrowser

from aiohttp import WSMsgType, web

import assistant as assistant_mod
import engineer as engineer_mod
import spotter as spotter_mod
import voice as voice_mod

BASE = os.path.dirname(os.path.abspath(__file__))
CONFIG_PATH = os.path.join(BASE, "config.json")
WEB_DIR = os.path.join(BASE, "web")
COOKIE = "lmu_re"

DEFAULT_CONFIG = {
    "port": 8770,
    "token": "",
    "quelle": "auto",                 # auto | lmu | demo
    "demo_zeitraffer": 1.0,
    "browser_oeffnen": True,
    # Sprachausgabe
    "sprachausgabe": "pc",            # pc | browser | beide | aus
    "stumm": False,
    "stimme": "",                     # Teil des Stimmennamens, z. B. "Hedda" (leer = erste deutsche)
    "sprechtempo": 1,                 # -10 .. 10
    "lautstaerke": 100,               # 0 .. 100
    # Welche Ansagen?
    "ansagen": {
        "spotter": True, "flaggen": True, "sprit": True, "strategie": True, "reifen": True,
        "rundenzeiten": True, "abstaende": True, "position": True, "schaden": True,
        "technik": True, "session": True, "wetter": True, "verkehr": True,
    },
    "rundenzeit_jede_runde": True,
    "abstand_alle_runden": 2,
    "sprit_reserve_runden": 0.5,
    "reifen_heiss": 105,
    "reifen_kalt": 60,
    "bremse_heiss": 850,
    "wasser_max": 110,
    "kontakt_schwelle": 1500,
    "spotter_seiten_tauschen": False,
    # KI (Claude) – optional
    "ki_modus": "auto",               # auto (eingebaut + KI) | immer (alles über KI) | aus
    "anthropic_api_key": "",          # oder Umgebungsvariable ANTHROPIC_API_KEY
    "ki_modell": "claude-opus-5-5",
    # Tastenkürzel (auch Lenkrad-Tasten über die Lenkrad-Software / JoyToKey belegbar)
    "hotkeys": {
        "status": "ctrl+shift+1",
        "sprit": "ctrl+shift+2",
        "reifen": "ctrl+shift+3",
        "abstaende": "ctrl+shift+4",
        "stumm": "ctrl+shift+0",
    },
}

# Diese Einstellungen dürfen über das Dashboard geändert werden
SETTABLE = {"sprachausgabe", "stumm", "sprechtempo", "lautstaerke", "rundenzeit_jede_runde", "abstand_alle_runden",
            "sprit_reserve_runden", "reifen_heiss", "reifen_kalt", "spotter_seiten_tauschen", "ki_modus", "quelle"}


def _merge(default: dict, user: dict) -> dict:
    out = copy.deepcopy(default)
    for k, v in user.items():
        out[k] = _merge(default[k], v) if isinstance(v, dict) and isinstance(default.get(k), dict) else v
    return out


def load_config() -> dict:
    cfg = copy.deepcopy(DEFAULT_CONFIG)
    if os.path.exists(CONFIG_PATH):
        with open(CONFIG_PATH, encoding="utf-8") as f:
            cfg = _merge(DEFAULT_CONFIG, json.load(f))
    if not cfg.get("token"):
        cfg["token"] = secrets.token_urlsafe(12)
    save_config(cfg)
    return cfg


def save_config(cfg: dict) -> None:
    with open(CONFIG_PATH, "w", encoding="utf-8") as f:
        json.dump(cfg, f, indent=2, ensure_ascii=False)


def local_ip() -> str:
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(("10.255.255.255", 1))
        return s.getsockname()[0]
    except Exception:
        return "127.0.0.1"
    finally:
        s.close()


class App:
    def __init__(self, cfg: dict, force_demo: bool):
        self.cfg = cfg
        self.clients: set[web.WebSocketResponse] = set()
        self.loop: asyncio.AbstractEventLoop | None = None
        self.log: list[dict] = []
        self.voice = voice_mod.Voice(cfg, on_say=self._on_say)
        self.eng = engineer_mod.Engineer(cfg, self.voice.say)
        self.spot = spotter_mod.Spotter(cfg, self.voice.say)
        self.ai = assistant_mod.Assistant(cfg, self.eng)
        self.force_demo = force_demo
        self.source = None
        self.source_name = None
        self.rest = None
        self.sent_map_version = -1
        self._select_source()

    # ------------------------------------------------------------------ Datenquelle
    def _select_source(self):
        want = "demo" if self.force_demo else self.cfg.get("quelle", "auto")
        if want == "auto":
            want = "lmu" if sys.platform == "win32" else "demo"
        if want == self.source_name:
            return
        if self.source is not None and hasattr(self.source, "close"):
            self.source.close()
        if want == "lmu":
            import lmu_rest
            import lmu_shm
            self.source = lmu_shm.SharedMemoryReader()
            if self.rest is None:
                self.rest = lmu_rest.LMURest()
        else:
            import demo_source
            self.source = demo_source.DemoSource(speedup=float(self.cfg.get("demo_zeitraffer", 1.0)))
        self.source_name = want
        self.eng.reset()
        self.sent_map_version = -1
        print(f"[Quelle] {'Le Mans Ultimate (Shared Memory)' if want == 'lmu' else 'Demo-Rennen'}")

    # ------------------------------------------------------------------ Ausgabe
    def _on_say(self, text, prio, cat):
        """Wird aus beliebigen Threads aufgerufen."""
        entry = {"type": "say", "text": text, "prio": prio, "cat": cat,
                 "browser": (not self.cfg.get("stumm")) and self.cfg.get("sprachausgabe") in ("browser", "beide")}
        print(f"[Ingenieur] {text}")
        if self.loop:
            self.loop.call_soon_threadsafe(self._push_log, entry)

    def _push_log(self, entry):
        self.log.append(entry)
        self.log = self.log[-60:]
        self.broadcast(entry)

    def broadcast(self, msg: dict):
        data = json.dumps(msg, ensure_ascii=False, default=lambda o: None)
        for ws in list(self.clients):
            if not ws.closed:
                asyncio.ensure_future(self._send(ws, data))

    @staticmethod
    async def _send(ws, data):
        try:
            await ws.send_str(data)
        except Exception:
            pass

    def public_config(self):
        c = {k: self.cfg.get(k) for k in SETTABLE}
        c["ansagen"] = self.cfg["ansagen"]
        c["ki_verfuegbar"] = self.ai.claude_available()
        c["quelle_aktiv"] = self.source_name
        return c

    # ------------------------------------------------------------------ Hauptschleife
    async def run_loop(self):
        tick = 0
        while True:
            try:
                frame = self.source.read()
                if frame and self.rest and frame.get("player"):
                    frame["player"]["virtual_energy"] = self.rest.get_energy()
                analysis = self.eng.update(frame)
                spot = self.spot.update(frame)
                if tick % 2 == 0 and self.clients:
                    if self.eng.map_version != self.sent_map_version:
                        self.sent_map_version = self.eng.map_version
                        self.broadcast({"type": "map", "pts": self.eng.track_map()})
                    self.broadcast({"type": "state", "data": analysis, "spotter": spot,
                                    "source": self.source_name})
            except Exception as e:      # eine kaputte Runde darf das Programm nicht beenden
                import traceback
                traceback.print_exc()
                print(f"[Fehler] {e}")
                await asyncio.sleep(1)
            tick += 1
            await asyncio.sleep(0.05)

    # ------------------------------------------------------------------ Aktionen
    REPORTS = {"status": "status_report", "sprit": "fuel_report", "reifen": "tyre_report",
               "abstaende": "gap_report", "position": "position_report", "pace": "pace_report",
               "wetter": "weather_report", "schaden": "damage_report", "session": "session_report"}

    def report(self, which: str):
        if which == "stumm":
            self.cfg["stumm"] = not self.cfg.get("stumm")
            save_config(self.cfg)
            self.broadcast({"type": "config", "config": self.public_config()})
            if not self.cfg["stumm"]:
                self.voice.say("Funk ist wieder an.", 1, "system")
            return
        m = self.REPORTS.get(which)
        if m:
            self.voice.say(getattr(self.eng, m)(), 1, "antwort")

    async def handle_ask(self, q: str):
        self.broadcast({"type": "thinking", "q": q})
        text, src = await self.ai.ask(q)
        self.broadcast({"type": "answer", "q": q, "text": text, "src": src})
        self.voice.say(text, 1, "antwort")

    async def handle_debrief(self):
        self.broadcast({"type": "thinking", "q": "Rennanalyse"})
        text = await self.ai.debrief()
        self.broadcast({"type": "debrief", "text": text})

    def setup_hotkeys(self):
        try:
            import keyboard  # type: ignore
        except Exception as e:
            print(f"[Tasten] keine Tastenkürzel ({e})")
            return
        for action, combo in self.cfg.get("hotkeys", {}).items():
            if not combo:
                continue
            try:
                keyboard.add_hotkey(combo, lambda a=action: self.loop.call_soon_threadsafe(self.report, a))
                print(f"[Tasten] {combo:>14}  ->  {action}")
            except Exception as e:
                print(f"[Tasten] {combo} geht nicht: {e}")


# ---------------------------------------------------------------------- Web
def make_web_app(app: App) -> web.Application:
    token = app.cfg["token"]

    def allowed(request: web.Request) -> bool:
        if request.remote in ("127.0.0.1", "::1"):
            return True
        return request.query.get("t") == token or request.cookies.get(COOKIE) == token

    async def index(request: web.Request):
        if not allowed(request):
            return web.Response(status=403, text="Zugriff verweigert - bitte die Adresse aus dem Programmfenster nutzen.")
        resp = web.FileResponse(os.path.join(WEB_DIR, "index.html"))
        if request.query.get("t") == token:
            resp.set_cookie(COOKIE, token, max_age=10 * 365 * 24 * 3600, httponly=True, samesite="Lax")
        resp.headers["Cache-Control"] = "no-cache"
        return resp

    async def ws_handler(request: web.Request):
        if not allowed(request):
            raise web.HTTPForbidden()
        ws = web.WebSocketResponse(heartbeat=20)
        await ws.prepare(request)
        app.clients.add(ws)
        await ws.send_str(json.dumps({"type": "config", "config": app.public_config()}))
        await ws.send_str(json.dumps({"type": "map", "pts": app.eng.track_map()}))
        await ws.send_str(json.dumps({"type": "log", "items": app.log[-30:]}, ensure_ascii=False))
        try:
            async for msg in ws:
                if msg.type != WSMsgType.TEXT:
                    continue
                try:
                    d = json.loads(msg.data)
                except ValueError:
                    continue
                t = d.get("type")
                if t == "ask" and isinstance(d.get("q"), str) and d["q"].strip():
                    asyncio.ensure_future(app.handle_ask(d["q"]))
                elif t == "report":
                    app.report(str(d.get("which")))
                elif t == "debrief":
                    asyncio.ensure_future(app.handle_debrief())
                elif t == "set":
                    key, val = d.get("key"), d.get("value")
                    if key in SETTABLE:
                        app.cfg[key] = val
                    elif isinstance(key, str) and key.startswith("ansagen.") and key[8:] in app.cfg["ansagen"]:
                        app.cfg["ansagen"][key[8:]] = bool(val)
                    else:
                        continue
                    save_config(app.cfg)
                    if key == "quelle":
                        app._select_source()
                    app.broadcast({"type": "config", "config": app.public_config()})
        finally:
            app.clients.discard(ws)
        return ws

    wa = web.Application()
    wa.router.add_get("/", index)
    wa.router.add_get("/ws", ws_handler)
    wa.router.add_static("/static/", WEB_DIR)
    return wa


async def main_async(force_demo: bool):
    cfg = load_config()
    app = App(cfg, force_demo)
    app.loop = asyncio.get_running_loop()
    app.setup_hotkeys()
    runner = web.AppRunner(make_web_app(app))
    await runner.setup()
    port = int(cfg["port"])
    await web.TCPSite(runner, "0.0.0.0", port).start()
    ip = local_ip()
    print("=" * 64)
    print("  LMU Race Engineer läuft")
    print(f"  Dashboard am PC:        http://127.0.0.1:{port}")
    print(f"  Tablet/Handy im WLAN:   http://{ip}:{port}/?t={cfg['token']}")
    print(f"  KI (Claude):            {'aktiv' if app.ai.claude_available() else 'aus (kein API-Schlüssel)'}")
    print("  Beenden: Fenster schließen oder Strg+C")
    print("=" * 64)
    if cfg.get("browser_oeffnen"):
        webbrowser.open(f"http://127.0.0.1:{port}")
    app.voice.say("Renningenieur ist bereit. Funkcheck, hörst du mich?", 2, "system")
    await app.run_loop()


def main():
    ap = argparse.ArgumentParser(description="KI-Renningenieur für Le Mans Ultimate")
    ap.add_argument("--demo", action="store_true", help="simuliertes Rennen statt LMU")
    args = ap.parse_args()
    try:
        asyncio.run(main_async(args.demo))
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
