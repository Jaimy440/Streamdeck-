"""Sprachausgabe des Renningenieurs.

- PC: Windows-Sprachausgabe (SAPI, deutsche Stimme z. B. "Microsoft Hedda/Katja").
- Browser: zusätzlich/alternativ spricht das Dashboard selbst (z. B. auf Tablet/iPhone).

Prioritäten: 0 = Spotter (unterbricht alles), 1 = wichtig, 2 = normal, 3 = Info.
Veraltete Meldungen werden verworfen, damit nichts Sekunden zu spät kommt.
"""
from __future__ import annotations

import itertools
import queue
import sys
import threading
import time

TTL = {0: 1.5, 1: 12.0, 2: 18.0, 3: 25.0}


class Voice:
    def __init__(self, cfg: dict, on_say=None):
        self.cfg = cfg
        self.on_say = on_say            # Callback -> Browser & Log
        self.q: queue.PriorityQueue = queue.PriorityQueue()
        self.seq = itertools.count()
        self.urgent = threading.Event()
        self.pc_ok = False
        if sys.platform == "win32":
            threading.Thread(target=self._sapi_loop, daemon=True, name="voice").start()

    # ------------------------------------------------------------------
    def say(self, text: str, prio: int = 2, cat: str = "info"):
        if self.on_say:
            self.on_say(text, prio, cat)
        if self.cfg.get("stumm"):
            return
        if self.cfg.get("sprachausgabe", "pc") not in ("pc", "beide"):
            return
        self.q.put((prio, next(self.seq), time.monotonic(), text))
        if prio == 0:
            self.urgent.set()

    # ------------------------------------------------------------------
    def _pick_voice(self, sp):
        want = (self.cfg.get("stimme") or "").lower()
        tokens = sp.GetVoices()
        best = None
        for i in range(tokens.Count):
            tok = tokens.Item(i)
            desc = tok.GetDescription()
            d = desc.lower()
            if want and want in d:
                return tok, desc
            if best is None and ("german" in d or "deutsch" in d):
                best = (tok, desc)
        return best or (None, None)

    def _sapi_loop(self):
        try:
            import comtypes  # type: ignore
            import comtypes.client  # type: ignore

            comtypes.CoInitialize()
            sp = comtypes.client.CreateObject("SAPI.SpVoice")
            tok, desc = self._pick_voice(sp)
            if tok is not None:
                sp.Voice = tok
                print(f"[Stimme] {desc}")
            else:
                print("[Stimme] Keine deutsche Stimme gefunden - nutze Standardstimme. "
                      "(Windows-Einstellungen > Zeit & Sprache > Sprache: Deutsch mit Sprachausgabe installieren)")
            self.pc_ok = True
        except Exception as e:
            print(f"[Stimme] Windows-Sprachausgabe nicht verfügbar: {e}")
            return

        ASYNC, PURGE = 1, 2
        while True:
            prio, _, created, text = self.q.get()
            if time.monotonic() - created > TTL.get(prio, 15):
                continue
            if self.cfg.get("stumm"):
                continue
            try:
                sp.Rate = int(self.cfg.get("sprechtempo", 1))
                sp.Volume = int(self.cfg.get("lautstaerke", 100))
                self.urgent.clear()
                sp.Speak(text, ASYNC | (PURGE if prio == 0 else 0))
                # warten, bis fertig - aber Spotter-Meldungen dürfen unterbrechen
                while not sp.WaitUntilDone(40):
                    if self.urgent.is_set() and prio > 0:
                        break
            except Exception as e:
                print(f"[Stimme] Fehler: {e}")
                time.sleep(0.5)
