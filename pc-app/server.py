"""PC-Deck Server - verbindet dein iPhone mit dem PC.

Start:  python server.py   (oder start.bat)
Dann den angezeigten QR-Code mit der iPhone-Kamera scannen.
"""
from __future__ import annotations

import asyncio
import copy
import html
import json
import os
import secrets
import socket
import sys
import webbrowser

from aiohttp import WSMsgType, web

import chrome
import controls
import spotify

BASE = os.path.dirname(os.path.abspath(__file__))
CONFIG_PATH = os.path.join(BASE, "config.json")
WEB_DIR = os.path.join(BASE, "web")
COOKIE = "pcdeck"
COOKIE_AGE = 10 * 365 * 24 * 3600   # 10 Jahre = dauerhaft angemeldet

DEFAULT_CONFIG = {
    "port": 8765,
    "token": "",
    # Name im WLAN: die App ist unter http://pc-deck.local:8765 erreichbar,
    # auch wenn sich die IP-Adresse des PCs ändert.
    "hostname": "pc-deck",
    "volume_step": 5,
    "discord": {
        # Diese Tastenkürzel musst du in Discord unter
        # Einstellungen > Tastenbelegung genauso eintragen!
        "mute_hotkey": "ctrl+shift+alt+m",
        "deafen_hotkey": "ctrl+shift+alt+d",
    },
    "spotify": {
        # Client-ID deiner Spotify-App (developer.spotify.com, siehe README)
        "client_id": "",
    },
    "chrome": {
        "path": "",   # leer = automatisch suchen
        "favorites": [
            {"label": "YouTube", "url": "https://www.youtube.com", "color": "#ff0033"},
            {"label": "Twitch", "url": "https://www.twitch.tv", "color": "#9146ff"},
            {"label": "Netflix", "url": "https://www.netflix.com", "color": "#e50914"},
            {"label": "Google", "url": "https://www.google.com", "color": "#4285f4"},
            {"label": "Gmail", "url": "https://mail.google.com", "color": "#ea4335"},
            {"label": "ChatGPT", "url": "https://chatgpt.com", "color": "#10a37f"},
        ],
    },
    "buttons": [
        {"label": "Play / Pause", "icon": "⏯️", "action": "hotkey", "keys": "play/pause media"},
        {"label": "Weiter", "icon": "⏭️", "action": "hotkey", "keys": "next track"},
        {"label": "Zurück", "icon": "⏮️", "action": "hotkey", "keys": "previous track"},
        {"label": "Discord", "icon": "💬", "action": "url", "target": "discord://"},
        {"label": "Screenshot", "icon": "📸", "action": "hotkey", "keys": "windows+shift+s"},
        {"label": "Task-Manager", "icon": "📊", "action": "hotkey", "keys": "ctrl+shift+esc"},
        {"label": "Sperren", "icon": "🔒", "action": "command", "target": "rundll32.exe user32.dll,LockWorkStation"},
    ],
}


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
    cfg.pop("voice_filter", None)   # Altlast aus früherer Version
    if not cfg.get("token"):
        cfg["token"] = secrets.token_urlsafe(16)
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


def register_mdns(name: str, ip: str, port: int):
    """Macht den PC als <name>.local im WLAN bekannt (Bonjour) – das iPhone findet ihn so immer."""
    try:
        from zeroconf import ServiceInfo, Zeroconf  # type: ignore

        zc = Zeroconf()
        info = ServiceInfo("_http._tcp.local.", f"PC-Deck ({name})._http._tcp.local.",
                           addresses=[socket.inet_aton(ip)], port=port, server=f"{name}.local.")
        zc.register_service(info)
        return zc
    except Exception as e:
        print(f"[mDNS] nicht verfügbar ({e}) – nutze die IP-Adresse")
        return None


def toast(text: str, error: bool = False) -> dict:
    return {"type": "toast", "text": text, "error": error}


class App:
    def __init__(self) -> None:
        self.cfg = load_config()
        self.port = int(self.cfg["port"])
        self.audio = controls.Audio()
        self.spotify = spotify.Spotify(self.cfg["spotify"], BASE, self.port)
        self.clients: set[web.WebSocketResponse] = set()
        self.ext: web.WebSocketResponse | None = None   # Chrome-Erweiterung
        self.chrome_media: dict | None = None
        self.discord = {"muted": False, "deafened": False}
        self._last_sys = None
        self._last_player = None

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
            "buttons": [{"label": b.get("label", "?"), "icon": b.get("icon", "")} for b in self.cfg["buttons"]],
            "favorites": self.cfg["chrome"]["favorites"],
            "chrome_ext": self.ext is not None,
            "spotify": self.spotify.status(),
            "audio_available": self.audio.available,
        }

    async def broadcast(self, msg: dict | None = None) -> None:
        data = json.dumps(msg or self.state())
        for ws in list(self.clients):
            try:
                await ws.send_str(data)
            except Exception:
                self.clients.discard(ws)

    @staticmethod
    async def send(ws, msg: dict) -> None:
        try:
            await ws.send_str(json.dumps(msg))
        except Exception:
            pass

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

    async def poll_spotify(self) -> None:
        while True:
            await asyncio.sleep(2)
            if self.clients and self.spotify.logged_in:
                await self.push_player()

    async def push_player(self) -> None:
        try:
            p = await self.spotify.player()
        except Exception as e:
            print(f"[Spotify] {e}")
            return
        if p != self._last_player:
            self._last_player = p
            await self.broadcast({"type": "spotify_player", "data": p})

    # ---------------------------------------------------------------- Befehle
    async def handle(self, msg: dict, ws: web.WebSocketResponse) -> None:
        cmd = msg.get("cmd", "")
        if cmd.startswith("spotify_"):
            return await self.handle_spotify(cmd, msg, ws)
        if cmd.startswith("chrome_"):
            return await self.handle_chrome(cmd, msg, ws)

        loop = asyncio.get_running_loop()
        step = self.cfg.get("volume_step", 5)
        d = self.cfg["discord"]
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
        elif cmd == "ping":
            return
        else:
            raise ValueError(f"Unbekannter Befehl: {cmd}")
        await self.broadcast()

    async def handle_spotify(self, cmd: str, msg: dict, ws) -> None:
        sp = self.spotify
        if cmd == "spotify_login":
            if not sp.configured:
                raise RuntimeError("Trage zuerst die Spotify Client-ID in config.json ein (siehe README)")
            webbrowser.open(sp.login_url())
            await self.send(ws, toast("Spotify-Login wurde im Browser am PC geöffnet"))
            return
        if cmd == "spotify_logout":
            sp.logout()
            self._last_player = None
            await self.broadcast()
            return
        if cmd == "spotify_playlists":
            await self.send(ws, {"type": "spotify_playlists", "data": await sp.playlists(bool(msg.get("force")))})
            await self.broadcast()   # Premium-Status ist jetzt bekannt
            return
        if cmd == "spotify_play":
            if await sp.play_context(msg["uri"]) == "opened":
                await self.send(ws, toast("Ohne Premium: Playlist wurde in Spotify geöffnet"))
        elif cmd == "spotify_control":
            await sp.control(msg["action"], msg.get("value"))
        else:
            raise ValueError(f"Unbekannter Befehl: {cmd}")
        await asyncio.sleep(0.35)   # Spotify braucht kurz, bis der neue Zustand abrufbar ist
        await self.push_player()

    async def handle_chrome(self, cmd: str, msg: dict, ws) -> None:
        if cmd == "chrome_open":
            url = chrome.normalize_url(msg.get("url", ""))
            if self.ext is not None:
                await self.ext.send_str(json.dumps({"cmd": "open_url", "url": url}))
            else:
                chrome.open_with_exe(url, self.cfg["chrome"].get("path"))
            await self.send(ws, toast("Neuer Tab: " + url.split("//", 1)[-1][:60]))
        elif cmd == "chrome_media":
            if self.ext is None:
                raise RuntimeError("Chrome-Erweiterung ist nicht verbunden (siehe README)")
            await self.ext.send_str(json.dumps({"cmd": "media", "action": msg["action"], "value": msg.get("value")}))
        else:
            raise ValueError(f"Unbekannter Befehl: {cmd}")

    # ---------------------------------------------------------------- Auth
    def authorized(self, request: web.Request) -> bool:
        tok = request.query.get("token") or request.cookies.get(COOKIE, "")
        return secrets.compare_digest(tok, self.cfg["token"])

    # ---------------------------------------------------------------- HTTP / WebSocket
    async def ws_handler(self, request: web.Request) -> web.WebSocketResponse:
        if not self.authorized(request):
            raise web.HTTPForbidden(text="Falscher Token")
        ws = web.WebSocketResponse(heartbeat=15)
        await ws.prepare(request)
        self.clients.add(ws)
        print(f"[+] iPhone verbunden: {request.remote}")
        await ws.send_str(json.dumps(self.state()))
        await self.send(ws, {"type": "chrome_media", "data": self.chrome_media})
        if self._last_player is not None:
            await self.send(ws, {"type": "spotify_player", "data": self._last_player})
        try:
            async for m in ws:
                if m.type != WSMsgType.TEXT:
                    continue
                try:
                    await self.handle(json.loads(m.data), ws)
                except Exception as e:
                    print(f"[!] {e}")
                    await self.send(ws, toast(str(e), error=True))
        finally:
            self.clients.discard(ws)
            print(f"[-] iPhone getrennt: {request.remote}")
        return ws

    async def ext_handler(self, request: web.Request) -> web.WebSocketResponse:
        """Verbindung der Chrome-Erweiterung – nur vom eigenen PC und nur von einer Erweiterung."""
        origin = request.headers.get("Origin", "")
        if request.remote not in ("127.0.0.1", "::1") or not origin.startswith("chrome-extension://"):
            raise web.HTTPForbidden()
        ws = web.WebSocketResponse(heartbeat=20)
        await ws.prepare(request)
        if self.ext is not None:
            await self.ext.close()
        self.ext = ws
        print("[Chrome] Erweiterung verbunden")
        await self.broadcast()
        try:
            async for m in ws:
                if m.type != WSMsgType.TEXT:
                    continue
                data = json.loads(m.data)
                if data.get("type") == "media":
                    self.chrome_media = data.get("data")
                    await self.broadcast({"type": "chrome_media", "data": self.chrome_media})
                elif data.get("type") == "error":
                    await self.broadcast(toast(data.get("text", "Chrome-Fehler"), error=True))
        finally:
            if self.ext is ws:
                self.ext = None
                self.chrome_media = None
                print("[Chrome] Erweiterung getrennt")
                await self.broadcast()
                await self.broadcast({"type": "chrome_media", "data": None})
        return ws

    async def spotify_callback(self, request: web.Request) -> web.Response:
        q = request.query
        try:
            if "error" in q:
                raise RuntimeError(q["error"])
            await self.spotify.finish_login(q.get("code", ""), q.get("state", ""))
            await self.spotify.user_id()
            text, ok = "Spotify ist verbunden! Du kannst dieses Fenster schließen.", True
            await self.broadcast()
            await self.broadcast(toast("Spotify verbunden ✅"))
        except Exception as e:
            text, ok = f"Fehler: {e}", False
        color = "#23a55a" if ok else "#f23f43"
        page = ("<!doctype html><meta charset=utf-8><title>PC-Deck</title>"
                "<body style='background:#313338;color:#f2f3f5;font:18px system-ui;display:grid;"
                f"place-items:center;height:90vh'><div><h2 style='color:{color}'>PC-Deck</h2>"
                f"<p>{html.escape(text)}</p></div>")
        return web.Response(text=page, content_type="text/html")

    async def index(self, request: web.Request) -> web.StreamResponse:
        resp = web.FileResponse(os.path.join(WEB_DIR, "index.html"), headers={"Cache-Control": "no-cache"})
        if request.query.get("token") and self.authorized(request):
            # Login merken -> dauerhaft angemeldet, auch ohne Token in der Adresse
            resp.set_cookie(COOKIE, self.cfg["token"], max_age=COOKIE_AGE, httponly=True, samesite="Lax")
        return resp

    async def on_startup(self, app: web.Application) -> None:
        asyncio.ensure_future(self.poll_system())
        asyncio.ensure_future(self.poll_spotify())

    async def on_cleanup(self, app: web.Application) -> None:
        await self.spotify.close()

    def run(self) -> None:
        app = web.Application()
        app.router.add_get("/", self.index)
        app.router.add_get("/ws", self.ws_handler)
        app.router.add_get("/ext", self.ext_handler)
        app.router.add_get("/spotify/callback", self.spotify_callback)
        app.router.add_static("/", WEB_DIR)
        app.on_startup.append(self.on_startup)
        app.on_cleanup.append(self.on_cleanup)

        ip = local_ip()
        host = self.cfg.get("hostname") or "pc-deck"
        zc = register_mdns(host, ip, self.port)
        q = f"/?token={self.cfg['token']}"
        url_ip = f"http://{ip}:{self.port}{q}"
        main_url = f"http://{host}.local:{self.port}{q}" if zc else url_ip

        print("=" * 64)
        print("  PC-Deck läuft!  Scanne den QR-Code mit der iPhone-Kamera.")
        print(f"  {main_url}")
        if zc:
            print(f"  Falls das nicht lädt:  {url_ip}")
        print("=" * 64)
        try:
            import qrcode  # type: ignore

            qr = qrcode.QRCode(border=1)
            qr.add_data(main_url)
            qr.print_ascii(invert=True)
        except Exception:
            pass
        print("Dann in Safari: Teilen  ->  'Zum Home-Bildschirm'")
        if self.spotify.configured and not self.spotify.logged_in:
            print("[Spotify] Noch nicht verbunden – in der App unter Spotify auf 'Verbinden' tippen.")
        try:
            web.run_app(app, host="0.0.0.0", port=self.port, print=None)
        finally:
            if zc:
                zc.close()


if __name__ == "__main__":
    if sys.platform == "win32":
        # Unicode-Ausgabe (QR-Code, Umlaute) in der Windows-Konsole
        try:
            sys.stdout.reconfigure(encoding="utf-8")  # type: ignore[attr-defined]
        except Exception:
            pass
    App().run()
