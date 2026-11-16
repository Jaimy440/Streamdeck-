"""Chrome-Anbindung.

Mit Erweiterung (Ordner chrome-extension/):
  - Webseiten öffnen sich als NEUER TAB im zuletzt benutzten Chrome-Fenster
  - Videos (YouTube, Twitch, Netflix, ... jedes <video>) steuern
Ohne Erweiterung:
  - Webseiten werden über chrome.exe geöffnet (Chrome macht dann ebenfalls einen Tab auf,
    wenn es schon läuft) – Video-Steuerung geht dann nicht.
"""
from __future__ import annotations

import os
import re
import subprocess
import sys
import urllib.parse

IS_WIN = sys.platform == "win32"


def normalize_url(text: str) -> str:
    """'youtube.com' -> https://youtube.com, 'katzen videos' -> Google-Suche."""
    t = (text or "").strip()
    if not t:
        raise ValueError("Keine Adresse angegeben")
    if re.match(r"^[a-z][a-z0-9+.-]*://", t, re.I):
        scheme = t.split(":", 1)[0].lower()
        if scheme not in ("http", "https"):
            raise ValueError("Nur http/https-Adressen erlaubt")
        return t
    if " " not in t and re.match(r"^[\w.-]+\.[a-z]{2,}(:\d+)?(/.*)?$", t, re.I):
        return "https://" + t
    return "https://www.google.com/search?q=" + urllib.parse.quote_plus(t)


def find_chrome(custom: str | None = None) -> str | None:
    if custom and os.path.exists(custom):
        return custom
    if not IS_WIN:
        for c in ("google-chrome", "chromium", "chromium-browser"):
            from shutil import which
            if which(c):
                return which(c)
        return None
    try:
        import winreg

        for root in (winreg.HKEY_CURRENT_USER, winreg.HKEY_LOCAL_MACHINE):
            try:
                with winreg.OpenKey(root, r"SOFTWARE\Microsoft\Windows\CurrentVersion\App Paths\chrome.exe") as k:
                    path = winreg.QueryValue(k, None)
                    if path and os.path.exists(path):
                        return path
            except OSError:
                pass
    except ImportError:
        pass
    for base in (os.environ.get("PROGRAMFILES"), os.environ.get("PROGRAMFILES(X86)"), os.environ.get("LOCALAPPDATA")):
        if base:
            p = os.path.join(base, "Google", "Chrome", "Application", "chrome.exe")
            if os.path.exists(p):
                return p
    return None


def open_with_exe(url: str, custom_path: str | None = None) -> None:
    """Fallback ohne Erweiterung. Läuft Chrome schon, öffnet chrome.exe <url> einen neuen Tab."""
    exe = find_chrome(custom_path)
    if not exe:
        raise RuntimeError("Google Chrome nicht gefunden")
    subprocess.Popen([exe, url])
