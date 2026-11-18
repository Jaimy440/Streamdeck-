"""Tasten-Layout: Seiten mit frei belegbaren Tasten.

Das Layout wird in config.json unter "pages" gespeichert und kann komplett
vom iPhone aus bearbeitet werden (Bearbeiten-Modus).
"""
from __future__ import annotations

import re
import secrets

# Aktionen, die eine Taste auslösen kann
ACTION_TYPES = {
    "volume_up", "volume_down", "toggle_mute", "mic_mute",       # System
    "discord_mute", "discord_deafen", "full_mute",               # Discord
    "media",            # Medientaste: {"key": "play/pause media" | "next track" | "previous track"}
    "spotify",          # {"op": play_pause|next|previous|shuffle|repeat|vol_up|vol_down}
    "spotify_playlist", # {"uri", "name"}
    "chrome_url",       # {"url"}  -> neuer Tab in Chrome
    "chrome_video",     # {"op": toggle|back|fwd|next|mute|speed|vol_up|vol_down}
    "url_prompt",       # Eingabefeld für eine Adresse (nur iPhone)
    "hotkey",           # {"keys": "ctrl+shift+m"}
    "launch",           # {"target": Programm / Datei / Link}
    "command",          # {"target": Konsolenbefehl} – nur in config.json änderbar!
    "page",             # {"page": Seiten-ID} – Seite wechseln (nur iPhone)
    "none",
}
WIDGETS = {"volume", "spotify_now", "chrome_video", "playlists"}
SPOTIFY_OPS = {"play_pause", "next", "previous", "shuffle", "repeat", "vol_up", "vol_down"}
VIDEO_OPS = {"toggle", "back", "fwd", "next", "mute", "speed", "vol_up", "vol_down"}
MEDIA_KEYS = {"play/pause media", "next track", "previous track", "stop media", "volume mute"}
COLOR_RE = re.compile(r"^#[0-9a-fA-F]{6}$")
ICON_RE = re.compile(r"^[a-z0-9_-]{1,20}$")
MAX_PAGES, MAX_KEYS = 12, 64

C = {"cyan": "#22d3ee", "green": "#22e07a", "spotify": "#1ed760", "blue": "#3b82f6", "blurple": "#6d78ff",
     "red": "#ff453a", "orange": "#ff9f0a", "purple": "#bf5af2", "white": "#e5e5ea"}


def new_id(prefix: str = "k") -> str:
    return prefix + secrets.token_hex(4)


def k(action: dict | None = None, label: str = "", icon: str = "", color: str = C["cyan"],
      emoji: str = "", widget: str = "") -> dict:
    d = {"id": new_id(), "label": label, "icon": icon, "emoji": emoji, "color": color}
    if widget:
        d["widget"] = widget
    else:
        d["action"] = action or {"type": "none"}
    return d


def default_pages(old_buttons: list | None = None, favorites: list | None = None) -> list:
    """Standard-Layout. Alte Buttons/Favoriten aus früheren Versionen werden übernommen."""
    if old_buttons is None:
        custom = [
            k({"type": "media", "key": "play/pause media"}, "Play/Pause", "playc", C["purple"]),
            k({"type": "media", "key": "next track"}, "Weiter", "next", C["purple"]),
            k({"type": "media", "key": "previous track"}, "Zurück", "prev", C["purple"]),
            k({"type": "launch", "target": "discord://"}, "Discord", "chat", C["blurple"]),
            k({"type": "hotkey", "keys": "windows+shift+s"}, "Screenshot", "camera", C["orange"]),
            k({"type": "hotkey", "keys": "ctrl+shift+esc"}, "Tasks", "monitor", C["blue"]),
            k({"type": "command", "target": "rundll32.exe user32.dll,LockWorkStation"}, "Sperren", "lock", C["red"]),
        ]
    else:
        cycle = [C["cyan"], C["green"], C["purple"], C["orange"], C["blue"], C["blurple"]]
        custom = []
        for i, b in enumerate(old_buttons):
            a = b.get("action")
            if a == "hotkey":
                act = {"type": "hotkey", "keys": b.get("keys", "")}
            elif a in ("launch", "url"):
                act = {"type": "launch", "target": b.get("target", "")}
            elif a == "command":
                act = {"type": "command", "target": b.get("target", "")}
            else:
                continue
            if act["type"] == "hotkey" and act["keys"] in MEDIA_KEYS:
                act = {"type": "media", "key": act["keys"]}
            custom.append(k(act, b.get("label", ""), "", cycle[i % len(cycle)], emoji=b.get("icon", "")))

    favs = favorites if favorites is not None else [
        {"label": "YouTube", "url": "https://www.youtube.com", "color": "#ff0033"},
        {"label": "Twitch", "url": "https://www.twitch.tv", "color": "#9146ff"},
        {"label": "Netflix", "url": "https://www.netflix.com", "color": "#e50914"},
        {"label": "Google", "url": "https://www.google.com", "color": "#4285f4"},
    ]
    return [
        {"id": "control", "name": "Steuerung", "icon": "sliders", "keys": [
            k(widget="volume", label="PC-Lautstärke", color=C["cyan"]),
            k({"type": "volume_down"}, "Leiser", "voldown", C["cyan"]),
            k({"type": "volume_up"}, "Lauter", "volup", C["cyan"]),
            k({"type": "toggle_mute"}, "PC stumm", "volumex", C["orange"]),
            k({"type": "discord_mute"}, "DC-Mikro", "micoff", C["blurple"]),
            k({"type": "discord_deafen"}, "DC-Taub", "headphones", C["blurple"]),
            k({"type": "full_mute"}, "Full Mute", "ban", C["red"]),
            k({"type": "mic_mute"}, "Win-Mikro", "mic", C["green"]),
            *custom,
        ]},
        {"id": "spotify", "name": "Spotify", "icon": "music", "keys": [
            k(widget="spotify_now", label="Läuft gerade", color=C["spotify"]),
            k({"type": "spotify", "op": "previous"}, "Zurück", "prev", C["spotify"]),
            k({"type": "spotify", "op": "play_pause"}, "Play", "playc", C["spotify"]),
            k({"type": "spotify", "op": "next"}, "Weiter", "next", C["spotify"]),
            k({"type": "spotify", "op": "shuffle"}, "Zufall", "shuffle", C["spotify"]),
            k({"type": "spotify", "op": "repeat"}, "Schleife", "repeat", C["spotify"]),
            k({"type": "spotify", "op": "vol_down"}, "Leiser", "voldown", C["spotify"]),
            k({"type": "spotify", "op": "vol_up"}, "Lauter", "volup", C["spotify"]),
            k(widget="playlists", label="Alle Playlists", color=C["spotify"]),
        ]},
        {"id": "chrome", "name": "Chrome", "icon": "globe", "keys": [
            k(widget="chrome_video", label="Video", color=C["blue"]),
            k({"type": "url_prompt"}, "Öffnen", "search", C["blue"]),
            k({"type": "chrome_video", "op": "back"}, "−10 s", "back10", C["blue"]),
            k({"type": "chrome_video", "op": "toggle"}, "Play", "playc", C["blue"]),
            k({"type": "chrome_video", "op": "fwd"}, "+10 s", "fwd10", C["blue"]),
            k({"type": "chrome_video", "op": "next"}, "Nächstes", "next", C["blue"]),
            k({"type": "chrome_video", "op": "mute"}, "Ton", "volume", C["blue"]),
            k({"type": "chrome_video", "op": "speed"}, "Tempo", "gauge", C["blue"]),
            k({"type": "chrome_video", "op": "vol_down"}, "Leiser", "voldown", C["blue"]),
            k({"type": "chrome_video", "op": "vol_up"}, "Lauter", "volup", C["blue"]),
            *[k({"type": "chrome_url", "url": f.get("url", "")}, f.get("label", ""), "",
                f.get("color") if COLOR_RE.match(f.get("color") or "") else C["blue"]) for f in favs],
        ]},
    ]


# ---------------------------------------------------------------------- Prüfen
def _s(v, n: int) -> str:
    return str(v or "")[:n]


def _old_keys(pages: list) -> dict:
    return {key.get("id"): key for p in pages or [] for key in p.get("keys", [])}


def clean_action(a, old_key: dict | None) -> dict:
    if not isinstance(a, dict) or a.get("type") not in ACTION_TYPES:
        return {"type": "none"}
    t = a["type"]
    if t == "media":
        return {"type": t, "key": a.get("key") if a.get("key") in MEDIA_KEYS else "play/pause media"}
    if t == "spotify":
        return {"type": t, "op": a.get("op") if a.get("op") in SPOTIFY_OPS else "play_pause"}
    if t == "chrome_video":
        return {"type": t, "op": a.get("op") if a.get("op") in VIDEO_OPS else "toggle"}
    if t == "spotify_playlist":
        uri = _s(a.get("uri"), 120)
        if not uri.startswith("spotify:"):
            return {"type": "none"}
        return {"type": t, "uri": uri, "name": _s(a.get("name"), 80)}
    if t == "chrome_url":
        return {"type": t, "url": _s(a.get("url"), 1000)}
    if t == "hotkey":
        return {"type": t, "keys": _s(a.get("keys"), 60).lower()}
    if t == "launch":
        return {"type": t, "target": _s(a.get("target"), 500)}
    if t == "page":
        return {"type": t, "page": _s(a.get("page"), 40)}
    if t == "command":
        # Sicherheit: Konsolenbefehle dürfen nicht vom iPhone aus angelegt/geändert werden
        old = (old_key or {}).get("action") or {}
        if old.get("type") == "command" and old.get("target") == a.get("target"):
            return {"type": t, "target": old["target"]}
        raise ValueError("Konsolenbefehle kannst du nur in config.json am PC eintragen")
    return {"type": t}


def clean_pages(pages, old_pages: list) -> list:
    if not isinstance(pages, list) or not pages:
        raise ValueError("Mindestens eine Seite wird gebraucht")
    old = _old_keys(old_pages)
    out, seen = [], set()
    for p in pages[:MAX_PAGES]:
        pid = _s(p.get("id"), 40) or new_id("p")
        while pid in seen:
            pid = new_id("p")
        seen.add(pid)
        keys = []
        for key in (p.get("keys") or [])[:MAX_KEYS]:
            kid = _s(key.get("id"), 40) or new_id()
            while kid in seen:
                kid = new_id()
            seen.add(kid)
            icon = _s(key.get("icon"), 20)
            color = key.get("color") if COLOR_RE.match(str(key.get("color") or "")) else C["cyan"]
            item = {"id": kid, "label": _s(key.get("label"), 40), "icon": icon if ICON_RE.match(icon) else "",
                    "emoji": _s(key.get("emoji"), 8), "color": color}
            if key.get("widget") in WIDGETS:
                item["widget"] = key["widget"]
            else:
                item["action"] = clean_action(key.get("action"), old.get(kid))
            keys.append(item)
        icon = _s(p.get("icon"), 20)
        out.append({"id": pid, "name": _s(p.get("name"), 30) or "Seite",
                    "icon": icon if ICON_RE.match(icon) else "grid", "keys": keys})
    return out


def find_key(pages: list, key_id: str) -> dict | None:
    for p in pages:
        for key in p.get("keys", []):
            if key.get("id") == key_id:
                return key
    return None
