"""Berichtsheft-Assistent - Webserver.

Start:  python server.py   (oder start.bat)
Danach öffnet sich http://localhost:8090 im Browser.
"""
from __future__ import annotations

import asyncio
import json
import os
import sys
import webbrowser

from aiohttp import web

import archiv
import generator

BASE = os.path.dirname(os.path.abspath(__file__))
WEB_DIR = os.path.join(BASE, "web")
CONFIG_PATH = os.path.join(archiv.DATA_DIR, "config.json")
PORT = int(os.environ.get("BERICHTSHEFT_PORT", "8090"))


def config_laden() -> dict:
    try:
        with open(CONFIG_PATH, encoding="utf-8") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {}


def config_speichern(cfg: dict) -> None:
    os.makedirs(archiv.DATA_DIR, exist_ok=True)
    with open(CONFIG_PATH, "w", encoding="utf-8") as f:
        json.dump(cfg, f, ensure_ascii=False, indent=1)


# ---------------------------------------------------------------- API
async def index(_):
    return web.FileResponse(os.path.join(WEB_DIR, "index.html"))


async def get_config(_):
    cfg = config_laden()
    return web.json_response({
        "beruf": cfg.get("beruf", ""),
        "abteilung": cfg.get("abteilung", ""),
        "key_gesetzt": bool(cfg.get("api_key")),
        "env_key": generator._env_key(),
    })


async def post_config(req):
    daten = await req.json()
    cfg = config_laden()
    for k in ("beruf", "abteilung"):
        if k in daten:
            cfg[k] = daten[k].strip()
    if "api_key" in daten:
        if daten["api_key"].strip():
            cfg["api_key"] = daten["api_key"].strip()
        else:
            cfg.pop("api_key", None)
    config_speichern(cfg)
    return await get_config(req)


async def get_berichte(_):
    berichte = archiv.laden()
    berichte.sort(key=lambda b: (b.get("jahr") or 0, b.get("kw") or 0), reverse=True)
    return web.json_response(berichte)


async def post_import(req):
    daten = await req.json()
    standard = {k: daten.get(k) for k in ("kw", "jahr", "abteilung")}
    eintraege = archiv.text_importieren(daten.get("text", ""), standard)
    if not eintraege:
        return web.json_response({"fehler": "Kein Text gefunden."}, status=400)
    neu = archiv.hinzufuegen(eintraege)
    return web.json_response({"importiert": len(neu)})


async def put_bericht(req):
    return web.json_response(archiv.aktualisieren(await req.json()))


async def delete_bericht(req):
    archiv.loeschen(req.match_info["id"])
    return web.json_response({"ok": True})


async def post_generieren(req):
    woche = await req.json()
    woche.setdefault("tage", {})
    api_key = config_laden().get("api_key")
    ergebnis = await asyncio.to_thread(generator.erzeugen, woche, api_key)
    return web.json_response(ergebnis)


async def post_vorschlag(req):
    """Ähnliche Stichpunkte aus dem Archiv für einen Suchtext (Live-Vergleich)."""
    daten = await req.json()
    idx = archiv.Index(archiv.laden())
    treffer = idx.suche(daten.get("text", ""), limit=6,
                        kontext={"abteilung": daten.get("abteilung"), "kw": daten.get("kw"), "tag": daten.get("tag")})
    return web.json_response(treffer)


def app() -> web.Application:
    a = web.Application(client_max_size=20 * 1024 * 1024)
    a.add_routes([
        web.get("/", index),
        web.get("/api/config", get_config),
        web.post("/api/config", post_config),
        web.get("/api/berichte", get_berichte),
        web.post("/api/import", post_import),
        web.put("/api/berichte", put_bericht),
        web.delete("/api/berichte/{id}", delete_bericht),
        web.post("/api/generieren", post_generieren),
        web.post("/api/vorschlag", post_vorschlag),
        web.static("/static", WEB_DIR),
    ])
    return a


if __name__ == "__main__":
    host = "0.0.0.0" if "--lan" in sys.argv else "127.0.0.1"
    url = f"http://localhost:{PORT}"
    print(f"Berichtsheft-Assistent läuft: {url}   (Beenden mit Strg+C)")
    if "--no-browser" not in sys.argv:
        webbrowser.open(url)
    web.run_app(app(), host=host, port=PORT, print=None)
