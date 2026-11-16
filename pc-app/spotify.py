"""Spotify-Anbindung über die offizielle Web-API (OAuth mit PKCE, ohne Client-Secret).

- Login einmalig im Browser am PC, danach bleibt der Login dauerhaft gespeichert
  (spotify_token.json, wird automatisch erneuert).
- Playlists lesen und "Läuft gerade" funktioniert mit jedem Konto.
- Steuern (Playlist starten, Pause, Weiter, Lautstärke) verlangt bei Spotify Premium.
  Ohne Premium wird die Playlist in der Spotify-App geöffnet und Play/Pause/Weiter
  laufen über die Medientasten.
"""
from __future__ import annotations

import asyncio
import base64
import hashlib
import json
import os
import secrets
import time
import urllib.parse

import aiohttp

import controls

API = "https://api.spotify.com/v1"
AUTH = "https://accounts.spotify.com/authorize"
TOKEN = "https://accounts.spotify.com/api/token"
SCOPES = " ".join([
    "user-read-private", "playlist-read-private", "playlist-read-collaborative", "user-library-read",
    "user-read-playback-state", "user-modify-playback-state", "user-read-currently-playing",
])


class SpotifyError(Exception):
    def __init__(self, status: int, reason: str, message: str = ""):
        super().__init__(message or reason or f"HTTP {status}")
        self.status, self.reason = status, reason

    @property
    def premium(self) -> bool:
        return self.status == 403 and (self.reason == "PREMIUM_REQUIRED" or "premium" in str(self).lower())


class Spotify:
    def __init__(self, cfg: dict, data_dir: str, port: int):
        self.cfg = cfg
        self.token_path = os.path.join(data_dir, "spotify_token.json")
        self.redirect_uri = f"http://127.0.0.1:{port}/spotify/callback"
        self._tok: dict | None = None
        self._pkce: dict = {}
        self._http: aiohttp.ClientSession | None = None
        self._playlists: tuple[float, list] | None = None
        self._user_id: str | None = None
        self.premium: bool | None = None
        try:
            with open(self.token_path, encoding="utf-8") as f:
                self._tok = json.load(f)
        except Exception:
            pass

    # ---------------------------------------------------------------- Status
    @property
    def configured(self) -> bool:
        return bool(self.cfg.get("client_id"))

    @property
    def logged_in(self) -> bool:
        return bool(self._tok and self._tok.get("refresh_token"))

    def status(self) -> dict:
        return {"configured": self.configured, "logged_in": self.logged_in,
                "premium": self.premium, "redirect_uri": self.redirect_uri}

    async def http(self) -> aiohttp.ClientSession:
        if self._http is None or self._http.closed:
            self._http = aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=10))
        return self._http

    # ---------------------------------------------------------------- Login
    def login_url(self) -> str:
        verifier = secrets.token_urlsafe(64)
        challenge = base64.urlsafe_b64encode(hashlib.sha256(verifier.encode()).digest()).rstrip(b"=").decode()
        state = secrets.token_urlsafe(16)
        self._pkce = {"verifier": verifier, "state": state}
        return AUTH + "?" + urllib.parse.urlencode({
            "client_id": self.cfg["client_id"], "response_type": "code",
            "redirect_uri": self.redirect_uri, "scope": SCOPES, "state": state,
            "code_challenge_method": "S256", "code_challenge": challenge,
        })

    async def finish_login(self, code: str, state: str) -> None:
        if not self._pkce or state != self._pkce.get("state"):
            raise RuntimeError("Login abgelaufen – bitte in der App erneut auf 'Verbinden' tippen")
        await self._token_request({
            "grant_type": "authorization_code", "code": code, "redirect_uri": self.redirect_uri,
            "client_id": self.cfg["client_id"], "code_verifier": self._pkce["verifier"],
        })
        self._pkce = {}
        self._playlists = None

    def logout(self) -> None:
        self._tok = None
        self._playlists = None
        try:
            os.remove(self.token_path)
        except FileNotFoundError:
            pass

    async def _token_request(self, data: dict) -> None:
        s = await self.http()
        async with s.post(TOKEN, data=data) as r:
            body = await r.json(content_type=None)
            if r.status != 200:
                if body.get("error") == "invalid_grant":   # Zugriff widerrufen
                    self.logout()
                raise RuntimeError(f"Spotify-Login fehlgeschlagen: {body.get('error_description') or body}")
        tok = dict(self._tok or {})
        tok.update(body)
        tok["expires_at"] = time.time() + body.get("expires_in", 3600) - 60
        self._tok = tok
        with open(self.token_path, "w", encoding="utf-8") as f:
            json.dump(tok, f)

    async def _access_token(self) -> str:
        if not self.logged_in:
            raise RuntimeError("Nicht mit Spotify verbunden")
        if time.time() >= self._tok.get("expires_at", 0):
            await self._token_request({"grant_type": "refresh_token", "client_id": self.cfg["client_id"],
                                       "refresh_token": self._tok["refresh_token"]})
        return self._tok["access_token"]

    # ---------------------------------------------------------------- API
    async def api(self, method: str, path: str, **kw):
        s = await self.http()
        headers = {"Authorization": f"Bearer {await self._access_token()}"}
        async with s.request(method, API + path, headers=headers, **kw) as r:
            if r.status == 204 or r.content_length == 0:
                return None
            body = await r.json(content_type=None) if r.content_length != 0 else None
            if r.status >= 400:
                err = (body or {}).get("error", {}) if isinstance(body, dict) else {}
                raise SpotifyError(r.status, err.get("reason", ""), err.get("message", ""))
            return body

    async def user_id(self) -> str:
        if not self._user_id:
            me = await self.api("GET", "/me")
            self._user_id = me["id"]
            self.premium = me.get("product") == "premium" if "product" in me else self.premium
        return self._user_id

    async def playlists(self, force: bool = False) -> list:
        if self._playlists and not force and time.time() - self._playlists[0] < 120:
            return self._playlists[1]
        uid = await self.user_id()
        items, url = [], "/me/playlists?limit=50"
        while url and len(items) < 300:
            page = await self.api("GET", url)
            items += [p for p in page.get("items", []) if p]
            nxt = page.get("next")
            url = nxt[len(API):] if nxt else None
        out = [{"name": "Lieblingssongs", "uri": f"spotify:user:{uid}:collection",
                "image": None, "owner": "Du", "liked": True}]
        for p in items:
            imgs = p.get("images") or []
            out.append({
                "name": p.get("name") or "Ohne Namen",
                "uri": p["uri"],
                "image": imgs[-2]["url"] if len(imgs) > 1 else (imgs[0]["url"] if imgs else None),
                "owner": (p.get("owner") or {}).get("display_name") or "",
                "tracks": (p.get("tracks") or p.get("items") or {}).get("total"),
            })
        self._playlists = (time.time(), out)
        return out

    async def player(self) -> dict | None:
        p = await self.api("GET", "/me/player?additional_types=episode")
        if not p:
            return None
        item = p.get("item") or {}
        imgs = (item.get("album") or item.get("show") or {}).get("images") or item.get("images") or []
        dev = p.get("device") or {}
        return {
            "playing": p.get("is_playing", False),
            "title": item.get("name", ""),
            "artist": ", ".join(a["name"] for a in item.get("artists", [])) or (item.get("show") or {}).get("name", ""),
            "image": imgs[0]["url"] if imgs else None,
            "progress": p.get("progress_ms") or 0,
            "duration": item.get("duration_ms") or 0,
            "shuffle": p.get("shuffle_state", False),
            "repeat": p.get("repeat_state", "off"),
            "volume": dev.get("volume_percent"),
            "device": dev.get("name", ""),
            "context": (p.get("context") or {}).get("uri"),
        }

    # ---------------------------------------------------------------- Steuerung
    async def _device_id(self) -> str | None:
        """Aktives Gerät -> None (Spotify nimmt das aktive). Sonst PC-Gerät suchen / Spotify starten."""
        for attempt in range(12):
            devs = (await self.api("GET", "/me/player/devices") or {}).get("devices", [])
            if any(d.get("is_active") for d in devs):
                return None
            if devs:
                pc = [d for d in devs if d.get("type") == "Computer"] or devs
                return pc[0]["id"]
            if attempt == 0:
                controls.open_target("spotify:")   # Spotify-App starten
            await asyncio.sleep(1)
        raise RuntimeError("Kein Spotify-Gerät gefunden – bitte Spotify am PC öffnen")

    async def play_context(self, uri: str) -> str:
        try:
            dev = await self._device_id()
            await self.api("PUT", "/me/player/play", params={"device_id": dev} if dev else None,
                           json={"context_uri": uri})
            self.premium = True
            return "playing"
        except SpotifyError as e:
            if not e.premium:
                raise
            self.premium = False
            controls.open_target(uri if ":collection" not in uri else "spotify:collection:tracks")
            return "opened"

    async def control(self, action: str, value=None) -> None:
        paths = {
            "play": ("PUT", "/me/player/play", None),
            "pause": ("PUT", "/me/player/pause", None),
            "next": ("POST", "/me/player/next", None),
            "previous": ("POST", "/me/player/previous", None),
            "shuffle": ("PUT", "/me/player/shuffle", {"state": "true" if value else "false"}),
            "repeat": ("PUT", "/me/player/repeat", {"state": value or "off"}),
            "volume": ("PUT", "/me/player/volume", {"volume_percent": int(value or 0)}),
            "seek": ("PUT", "/me/player/seek", {"position_ms": int(value or 0)}),
        }
        method, path, params = paths[action]
        try:
            await self.api(method, path, params=params)
            self.premium = True
        except SpotifyError as e:
            # Ohne Premium (oder ohne aktives Gerät): Medientasten als Ersatz
            keys = {"play": "play/pause media", "pause": "play/pause media",
                    "next": "next track", "previous": "previous track"}.get(action)
            if (e.premium or e.status == 404) and keys:
                if e.premium:
                    self.premium = False
                await asyncio.get_running_loop().run_in_executor(None, controls.send_hotkey, keys)
            elif e.premium:
                self.premium = False
                raise RuntimeError("Dafür braucht Spotify ein Premium-Konto") from None
            else:
                raise

    async def close(self) -> None:
        if self._http:
            await self._http.close()
