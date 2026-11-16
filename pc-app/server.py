"""PC-Deck Server - verbindet dein iPhone mit dem PC.

Start:  python server.py
Dann den angezeigten QR-Code mit der iPhone-Kamera scannen.
"""
from __future__ import annotations

import asyncio
import copy
import json
import os
import secrets
import socket
import sys
import threading

from aiohttp import WSMsgType, web

import controls
import voicefilter

BASE = os.path.dirname(os.path.abspath(__file__))
CONFIG_PATH = os.path.join(BASE, "config.json")
WEB_DIR = os.path.join(BASE, "web")

DEFAULT_CONFIG = {
    "port": 8765,
    "token": "",
    "volume_step": 5,
    "discord": {
        # Diese Tastenkürzel musst du in Discord unter
        # Einstellungen > Tastenbelegung genauso eintragen!
        "mute_hotkey": "ctrl+shift+alt+m",
        "deafen_hotkey": "ctrl+shift+alt+d",
    },
    "voice_filter": {
        "input_device": None,           # None = Windows-Standardmikrofon
        "output_device": "CABLE Input",  # VB-Audio Virtual Cable
        "threshold": 0.72,
        "margin": 0.05,
        "noise_gate_db": -45,
        "lookahead_ms": 200,
        "hold_ms": 400,
        "autostart": False,
    },
    "buttons": [
        {"label": "Play / Pause", "icon": "⏯️", "action": "hotkey", "keys": "play/pause media"},
        {"label": "Weiter", "icon": "⏭️", "action": "hotkey", "keys": "next track"},
        {"label": "Zurück", "icon": "⏮️", "action": "hotkey", "keys": "previous track"},
        {"label": "Discord", "icon": "💬", "action": "url", "target": "discord://"},
        {"label": "Spotify", "icon": "🎵", "action": "launch", "target": "spotify:"},
        {"label": "Screenshot", "icon": "📸", "action": "hotkey", "keys": "windows+shift+s"},
        {"label": "Task-Manager", "icon": "📊", "action": "hotkey", "keys": "ctrl+shift+esc"},
        {"label": "Sperren", "icon": "🔒", "action": "command", "target": "rundll32.exe user32.dll,LockWorkStation"},
    ],
}


def _merge(default: dict, user: dict) -> dict:
    out = dict(default)
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
    def __init__(self) -> None:
        self.cfg = load_config()
        self.audio = controls.Audio()
        self.clients: set[web.WebSocketResponse] = set()
        self.loop: asyncio.AbstractEventLoop | None = None
        self.discord = {"muted": False, "deafened": False}
        self.filter = voicefilter.VoiceFilter(self.cfg["voice_filter"], BASE, self.notify_threadsafe)
        self._last_sys = None

    # ---------------------------------------------------------------- State
    def state(self) -> dict:
        try:
            vol, muted, mic = self.audio.get_volume(), self.audio.is_muted(), self.audio.mic_muted()
        except Exception as e:
            vol, muted, mic = 0, False, False
            print(f"[Audio] Fehler: {e}")
        return {
            "type": "state",
            "volume": vol,
            "muted": muted,
            "mic_muted": mic,
            "discord": self.discord,
            "filter": self.filter.state(),
            "buttons": [{"label": b.get("label", "?"), "icon": b.get("icon", "")} for b in self.cfg["buttons"]],
            "audio_available": self.audio.available,
        }

    async def broadcast(self, extra: dict | None = None) -> None:
        msg = json.dumps(extra or self.state())
        for ws in list(self.clients):
            try:
                await ws.send_str(msg)
            except Exception:
                self.clients.discard(ws)

    def notify_threadsafe(self) -> None:
        if self.loop and self.clients:
            self.loop.call_soon_threadsafe(lambda: asyncio.ensure_future(self.broadcast()))

    async def poll_system(self) -> None:
        """Erkennt Änderungen, die direkt am PC gemacht wurden (z.B. Lautstärketasten)."""
        while True:
            await asyncio.sleep(1)
            if not self.clients:
                continue
            try:
                cur = (self.audio.get_volume(), self.audio.is_muted(), self.audio.mic_muted())
            except Exception:
                continue
            if cur != self._last_sys:
                self._last_sys = cur
                await self.broadcast()

    # ---------------------------------------------------------------- Befehle
    async def handle(self, msg: dict) -> None:
        cmd = msg.get("cmd")
        step = self.cfg.get("volume_step", 5)
        d = self.cfg["discord"]
        vf = self.filter
        loop = asyncio.get_running_loop()

        if cmd == "volume_up":
            self.audio.change_volume(step)
        elif cmd == "volume_down":
            self.audio.change_volume(-step)
        elif cmd == "volume_set":
            self.audio.set_volume(msg.get("value", 50))
        elif cmd == "toggle_mute":
            self.audio.toggle_mute()
        elif cmd == "mic_mute":
            self.audio.toggle_mic_mute()
        elif cmd == "discord_mute":
            await loop.run_in_executor(None, controls.send_hotkey, d["mute_hotkey"])
            if self.discord["deafened"]:      # Discord: Mute-Taste hebt Taubschaltung auf
                self.discord = {"muted": False, "deafened": False}
            else:
                self.discord["muted"] = not self.discord["muted"]
        elif cmd == "discord_deafen":
            await loop.run_in_executor(None, controls.send_hotkey, d["deafen_hotkey"])
            self.discord["deafened"] = not self.discord["deafened"]
        elif cmd == "full_mute":
            # Alles aus: Discord taub + Windows-Mikro stumm (bzw. alles wieder an)
            target = not (self.discord["deafened"] and self.audio.mic_muted())
            if self.discord["deafened"] != target:
                await loop.run_in_executor(None, controls.send_hotkey, d["deafen_hotkey"])
                self.discord["deafened"] = target
            if self.audio.mic_muted() != target:
                self.audio.toggle_mic_mute()
        elif cmd == "discord_reset":
            self.discord = {"muted": False, "deafened": False}
        elif cmd == "button":
            controls.run_action(self.cfg["buttons"][int(msg["index"])])
        elif cmd == "filter_toggle":
            await loop.run_in_executor(None, vf.stop if vf.running else vf.start)
        elif cmd == "filter_enroll":
            who = "other" if msg.get("who") == "other" else "me"
            secs = float(msg.get("seconds", 20))
            threading.Thread(target=self._enroll, args=(who, secs), daemon=True).start()
        elif cmd == "filter_delete":
            vf.delete_profile("other" if msg.get("who") == "other" else "me")
        elif cmd == "filter_threshold":
            self.cfg["voice_filter"]["threshold"] = round(float(msg["value"]), 2)
            save_config(self.cfg)
        elif cmd == "ping":
            return
        else:
            raise ValueError(f"Unbekannter Befehl: {cmd}")
        await self.broadcast()

    def _enroll(self, who: str, secs: float) -> None:
        try:
            self.filter.enroll(who, secs)
            self._toast(f"Stimme {'deines Bruders' if who == 'other' else 'von dir'} gespeichert ✅")
        except Exception as e:
            self._toast(f"Einlernen fehlgeschlagen: {e}", error=True)

    def _toast(self, text: str, error: bool = False) -> None:
        if self.loop:
            msg = {"type": "toast", "text": text, "error": error}
            self.loop.call_soon_threadsafe(lambda: asyncio.ensure_future(self.broadcast(msg)))

    # ---------------------------------------------------------------- HTTP
    async def ws_handler(self, request: web.Request) -> web.WebSocketResponse:
        if not secrets.compare_digest(request.query.get("token", ""), self.cfg["token"]):
            raise web.HTTPForbidden(text="Falscher Token")
        ws = web.WebSocketResponse(heartbeat=15)
        await ws.prepare(request)
        self.clients.add(ws)
        print(f"[+] Verbunden: {request.remote}")
        await ws.send_str(json.dumps(self.state()))
        try:
            async for m in ws:
                if m.type != WSMsgType.TEXT:
                    continue
                try:
                    await self.handle(json.loads(m.data))
                except Exception as e:
                    print(f"[!] {e}")
                    await ws.send_str(json.dumps({"type": "toast", "text": str(e), "error": True}))
        finally:
            self.clients.discard(ws)
            print(f"[-] Getrennt: {request.remote}")
        return ws

    async def index(self, request: web.Request) -> web.FileResponse:
        return web.FileResponse(os.path.join(WEB_DIR, "index.html"))

    async def on_startup(self, app: web.Application) -> None:
        self.loop = asyncio.get_running_loop()
        asyncio.ensure_future(self.poll_system())
        if self.cfg["voice_filter"].get("autostart") and self.filter.profiles["me"] is not None:
            try:
                await self.loop.run_in_executor(None, self.filter.start)
                print("[Filter] automatisch gestartet")
            except Exception as e:
                print(f"[Filter] Autostart fehlgeschlagen: {e}")

    def run(self) -> None:
        app = web.Application()
        app.router.add_get("/", self.index)
        app.router.add_get("/ws", self.ws_handler)
        app.router.add_static("/", WEB_DIR)
        app.on_startup.append(self.on_startup)

        port = int(self.cfg["port"])
        url = f"http://{local_ip()}:{port}/?token={self.cfg['token']}"
        print("=" * 60)
        print("  PC-Deck läuft!")
        print(f"  Öffne auf dem iPhone (gleiches WLAN):\n  {url}")
        print("=" * 60)
        try:
            import qrcode  # type: ignore

            qr = qrcode.QRCode(border=1)
            qr.add_data(url)
            qr.print_ascii(invert=True)
        except Exception:
            pass
        print("Dann in Safari: Teilen  ->  'Zum Home-Bildschirm'")
        web.run_app(app, host="0.0.0.0", port=port, print=None)


if __name__ == "__main__":
    if sys.platform == "win32":
        # Unicode-Ausgabe (QR-Code, Umlaute) in der Windows-Konsole
        try:
            sys.stdout.reconfigure(encoding="utf-8")  # type: ignore[attr-defined]
        except Exception:
            pass
    App().run()
