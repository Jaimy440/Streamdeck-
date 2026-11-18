"""Liste der installierten Programme (Startmenü-Verknüpfungen) für die Tasten-Auswahl."""
from __future__ import annotations

import glob
import os
import sys
import time

_cache: tuple[float, list] | None = None
SKIP = ("uninstall", "deinstall", "readme", "help", "hilfe", "documentation", "license", "lizenz", "website")


def list_apps() -> list[dict]:
    global _cache
    if _cache and time.time() - _cache[0] < 60:
        return _cache[1]
    found: dict[str, dict] = {}
    if sys.platform == "win32":
        roots = [os.path.join(os.environ.get(v, ""), r"Microsoft\Windows\Start Menu\Programs")
                 for v in ("PROGRAMDATA", "APPDATA") if os.environ.get(v)]
        for root in roots:
            for pattern in ("**/*.lnk", "**/*.url"):
                for path in glob.glob(os.path.join(root, pattern), recursive=True):
                    name = os.path.splitext(os.path.basename(path))[0]
                    if any(s in name.lower() for s in SKIP):
                        continue
                    found.setdefault(name.lower(), {"name": name, "target": path})
    else:  # Linux/macOS: nur zum Testen
        for path in glob.glob("/usr/share/applications/*.desktop"):
            name = os.path.splitext(os.path.basename(path))[0]
            found.setdefault(name.lower(), {"name": name, "target": path})
    apps = sorted(found.values(), key=lambda a: a["name"].lower())
    _cache = (time.time(), apps)
    return apps
