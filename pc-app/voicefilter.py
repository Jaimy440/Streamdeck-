"""Stimmfilter: lässt nur DEINE Stimme durch, andere Stimmen werden stummgeschaltet.

Funktionsweise
--------------
1. Einlernen: Du sprichst ~20 s ins Mikro. Daraus wird ein "Stimmabdruck"
   (Speaker-Embedding, Resemblyzer) berechnet. Optional kann auch die Stimme
   deines Bruders eingelernt werden - dann wird die Erkennung deutlich sicherer.
2. Live: Das Mikrofon wird gelesen, alle 100 ms wird für die letzte Sekunde
   Audio geprüft, wessen Stimme das ist. Nur wenn es deine ist, geht das Signal
   auf das virtuelle Kabel (VB-Audio "CABLE Input"). In Discord wählst du
   "CABLE Output" als Mikrofon.
3. Ein kleiner Vorlauf (lookahead, Standard 200 ms) sorgt dafür, dass deine
   Wortanfänge nicht abgeschnitten werden.

Grenze: Reden du und dein Bruder GLEICHZEITIG, ist das Mikro offen (es ist
ja deine Stimme dabei) und er ist leise im Hintergrund hörbar. Eine echte
Trennung zweier gleichzeitiger Stimmen ist in Echtzeit kaum machbar.
"""
from __future__ import annotations

import collections
import os
import queue
import threading
import time
from typing import Callable, Optional

import numpy as np

try:
    import sounddevice as sd  # type: ignore
except Exception as e:  # pragma: no cover
    sd = None
    _SD_ERR = str(e)

SR = 48000            # Audio-Samplerate für Ein-/Ausgabe
EMB_SR = 16000        # Samplerate für das Stimmmodell
BLOCK = 960           # 20 ms Blöcke
WINDOW_S = 1.0        # Analysefenster
HOP_S = 0.1           # Analyse alle 100 ms


def _find_device(name: Optional[str], kind: str) -> Optional[int]:
    """Sucht ein Gerät per Namensteil. Bevorzugt MME (verträgt beliebige Sampleraten)."""
    if not name:
        return None
    key = "max_input_channels" if kind == "input" else "max_output_channels"
    hostapis = sd.query_hostapis()
    matches = []
    for idx, d in enumerate(sd.query_devices()):
        if d[key] > 0 and name.lower() in d["name"].lower():
            api = hostapis[d["hostapi"]]["name"]
            prio = {"MME": 0, "Windows DirectSound": 1}.get(api, 2)
            matches.append((prio, idx))
    if not matches:
        raise RuntimeError(f"Audiogerät '{name}' ({kind}) nicht gefunden")
    return sorted(matches)[0][1]


def list_devices() -> dict:
    if sd is None:
        return {"inputs": [], "outputs": []}
    hostapis = sd.query_hostapis()
    ins, outs = set(), set()
    for d in sd.query_devices():
        if hostapis[d["hostapi"]]["name"] not in ("MME", "Core Audio", "ALSA"):
            continue
        if d["max_input_channels"] > 0:
            ins.add(d["name"])
        if d["max_output_channels"] > 0:
            outs.add(d["name"])
    return {"inputs": sorted(ins), "outputs": sorted(outs)}


def _db(x: np.ndarray) -> float:
    return float(20 * np.log10(np.sqrt(np.mean(x * x)) + 1e-9))


class VoiceFilter:
    def __init__(self, cfg: dict, data_dir: str, on_change: Callable[[], None]):
        self.cfg = cfg
        self.data_dir = data_dir
        self.on_change = on_change
        self.error: Optional[str] = None
        self.available = sd is not None
        self._encoder = None
        self._enc_lock = threading.Lock()
        self.profiles: dict[str, Optional[np.ndarray]] = {
            "me": self._load("me"), "other": self._load("other")}

        self.running = False
        self.enrolling: Optional[dict] = None  # {"who", "progress"}
        # Live-Werte für die Anzeige
        self.sim_me = 0.0
        self.sim_other = 0.0
        self.level_db = -90.0
        self.gate_open = False

        self._target = 0.0
        self._gain = 0.0
        self._ring = np.zeros(int(SR * WINDOW_S), dtype=np.float32)
        self._ring_lock = threading.Lock()
        self._delay: collections.deque = collections.deque()
        self._out_q: "queue.Queue[np.ndarray]" = queue.Queue(maxsize=50)
        self._streams: list = []
        self._stop = threading.Event()
        if sd is None:
            self.error = "sounddevice nicht installiert"

    # ------------------------------------------------------------------ Profile
    def _path(self, who: str) -> str:
        return os.path.join(self.data_dir, f"voice_{who}.npy")

    def _load(self, who: str) -> Optional[np.ndarray]:
        try:
            return np.load(self._path(who))
        except Exception:
            return None

    def delete_profile(self, who: str) -> None:
        self.profiles[who] = None
        try:
            os.remove(self._path(who))
        except FileNotFoundError:
            pass

    # ------------------------------------------------------------------ Modell
    def _get_encoder(self):
        if self._encoder is None:
            from resemblyzer import VoiceEncoder  # type: ignore  # lädt torch, dauert kurz
            self._encoder = VoiceEncoder("cpu", verbose=False)
        return self._encoder

    def _embed(self, wav48: np.ndarray) -> np.ndarray:
        """Embedding für ein Stück Audio @48 kHz (gleiche Vorverarbeitung wie live)."""
        from scipy.signal import resample_poly  # type: ignore

        wav = resample_poly(wav48, 1, 3).astype(np.float32)
        rms = np.sqrt(np.mean(wav * wav)) + 1e-9
        wav = np.clip(wav * (0.1 / rms), -1, 1)  # Lautstärke normalisieren (~ -20 dBFS)
        with self._enc_lock:
            emb = self._get_encoder().embed_utterance(wav)
        return emb / (np.linalg.norm(emb) + 1e-9)

    # ------------------------------------------------------------------ Einlernen
    def enroll(self, who: str, seconds: float = 20.0) -> None:
        """Nimmt `seconds` Sekunden auf und speichert den Stimmabdruck (blockierend)."""
        if sd is None:
            raise RuntimeError(self.error)
        was_running = self.running
        if was_running:
            self.stop()
        try:
            self.enrolling = {"who": who, "progress": 0.0}
            self.on_change()
            dev = _find_device(self.cfg.get("input_device"), "input")
            frames = int(seconds * SR)
            rec = sd.rec(frames, samplerate=SR, channels=1, dtype="float32", device=dev)
            t0 = time.time()
            while time.time() - t0 < seconds:
                time.sleep(0.25)
                self.enrolling["progress"] = min(0.99, (time.time() - t0) / seconds)
                self.on_change()
            sd.wait()
            self.enrolling["progress"] = 1.0
            self.on_change()
            wav = rec[:, 0]
            # Einzelne 1-s-Fenster einbetten (wie live) und mitteln
            win, hop = int(SR * WINDOW_S), int(SR * 0.5)
            gate = self.cfg.get("noise_gate_db", -45)
            embs = [self._embed(wav[i:i + win]) for i in range(0, len(wav) - win, hop)
                    if _db(wav[i:i + win]) > gate]
            if len(embs) < 5:
                raise RuntimeError("Zu wenig Sprache erkannt - bitte lauter/länger sprechen")
            prof = np.mean(embs, axis=0)
            prof /= np.linalg.norm(prof)
            np.save(self._path(who), prof)
            self.profiles[who] = prof
            sims = [float(e @ prof) for e in embs]
            print(f"[Filter] Profil '{who}' gespeichert ({len(embs)} Fenster, "
                  f"Ähnlichkeit min {min(sims):.2f} / Mittel {np.mean(sims):.2f})")
        finally:
            self.enrolling = None
            self.on_change()
            if was_running:
                self.start()

    # ------------------------------------------------------------------ Live
    def start(self) -> None:
        if self.running:
            return
        if sd is None:
            raise RuntimeError(self.error)
        if self.profiles["me"] is None:
            raise RuntimeError("Bitte zuerst deine Stimme einlernen")
        self._get_encoder()  # Modell vorab laden
        in_dev = _find_device(self.cfg.get("input_device"), "input")
        out_dev = _find_device(self.cfg.get("output_device") or "CABLE Input", "output")
        out_ch = min(2, sd.query_devices(out_dev)["max_output_channels"])

        self._delay.clear()
        while not self._out_q.empty():
            self._out_q.get_nowait()
        self._gain = self._target = 0.0
        self._stop.clear()

        lookahead = max(0, int(self.cfg.get("lookahead_ms", 200) / 20))
        attack = BLOCK / (SR * 0.010)    # 10 ms auf
        release = BLOCK / (SR * 0.080)   # 80 ms zu

        def in_cb(indata, frames, t, status):
            x = indata[:, 0].copy()
            with self._ring_lock:
                self._ring = np.concatenate([self._ring[len(x):], x])
            self._delay.append(x)
            if len(self._delay) <= lookahead:
                return
            blk = self._delay.popleft()
            g0 = self._gain
            d = self._target - g0
            g1 = g0 + (min(d, attack) if d > 0 else max(d, -release))
            self._gain = g1
            out = blk * np.linspace(g0, g1, len(blk), dtype=np.float32)
            try:
                self._out_q.put_nowait(out)
            except queue.Full:
                pass

        def out_cb(outdata, frames, t, status):
            try:
                blk = self._out_q.get_nowait()
            except queue.Empty:
                blk = np.zeros(frames, dtype=np.float32)
            if len(blk) != frames:
                blk = np.resize(blk, frames)
            outdata[:] = np.repeat(blk[:, None], outdata.shape[1], axis=1)

        try:
            self._streams = [
                sd.InputStream(SR, BLOCK, in_dev, 1, "float32", callback=in_cb),
                sd.OutputStream(SR, BLOCK, out_dev, out_ch, "float32", callback=out_cb),
            ]
            for s in self._streams:
                s.start()
        except Exception:
            self._close_streams()
            raise
        threading.Thread(target=self._analyze_loop, daemon=True).start()
        self.running = True
        self.error = None
        self.on_change()

    def _close_streams(self) -> None:
        for s in self._streams:
            try:
                s.stop()
                s.close()
            except Exception:
                pass
        self._streams = []

    def stop(self) -> None:
        self._stop.set()
        self._close_streams()
        self.running = False
        self.gate_open = False
        self.on_change()

    def _analyze_loop(self) -> None:
        hold_s = self.cfg.get("hold_ms", 400) / 1000
        last_me = 0.0
        last_push = 0.0
        while not self._stop.is_set():
            t0 = time.time()
            with self._ring_lock:
                wav = self._ring.copy()
            # Nur die letzten 250 ms für den Pegel -> reagiert schneller auf Stille
            self.level_db = _db(wav[-SR // 4:])
            thr = float(self.cfg.get("threshold", 0.72))
            margin = float(self.cfg.get("margin", 0.05))
            is_me = is_other = False
            if self.level_db > self.cfg.get("noise_gate_db", -45):
                try:
                    emb = self._embed(wav)
                    self.sim_me = float(emb @ self.profiles["me"])
                    other = self.profiles["other"]
                    self.sim_other = float(emb @ other) if other is not None else 0.0
                    is_me = self.sim_me >= thr and (
                        other is None or self.sim_me - self.sim_other >= margin)
                    is_other = other is not None and self.sim_other - self.sim_me >= margin
                except Exception as e:
                    self.error = f"Analyse-Fehler: {e}"
            else:
                self.sim_me = self.sim_other = 0.0
            now = time.time()
            if is_me:
                last_me = now
            # Kurz nach deiner Stimme offen lassen (Haltezeit), damit Sätze nicht zerhackt werden
            # (aber sofort zu, wenn klar die andere Stimme erkannt wird)
            self.gate_open = is_me or (now - last_me < hold_s and not is_other
                                       and self.level_db > self.cfg.get("noise_gate_db", -45))
            self._target = 1.0 if self.gate_open else 0.0
            if now - last_push > 0.2:
                last_push = now
                self.on_change()
            self._stop.wait(max(0.0, HOP_S - (time.time() - t0)))

    def state(self) -> dict:
        return {
            "available": self.available,
            "running": self.running,
            "enrolled_me": self.profiles["me"] is not None,
            "enrolled_other": self.profiles["other"] is not None,
            "enrolling": self.enrolling,
            "sim_me": round(self.sim_me, 3),
            "sim_other": round(self.sim_other, 3),
            "level_db": round(self.level_db, 1),
            "open": self.gate_open,
            "threshold": self.cfg.get("threshold", 0.72),
            "error": self.error,
        }
