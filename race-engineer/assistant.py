"""KI-Assistent: beantwortet Fragen des Fahrers ("Wie viel Sprit brauche ich?").

1. Schnelle, eingebaute Antworten für die typischen Fragen (offline, sofort).
2. Alles andere (und auf Wunsch alles) beantwortet Claude mit den aktuellen
   Telemetriedaten als Kontext – dafür wird ein Anthropic-API-Schlüssel benötigt.
"""
from __future__ import annotations

import json
import os
import re

import fmt

SYSTEM_PROMPT = """Du bist ein erfahrener Renningenieur am Funk und betreust einen Sim-Racer in Le Mans Ultimate.
Deine Antworten werden laut vorgelesen, während der Fahrer fährt. Deshalb:
- Antworte auf Deutsch, in ein bis drei kurzen Sätzen, ohne Aufzählungszeichen, Markdown oder Emojis.
- Nenne konkrete Zahlen aus den Telemetriedaten, gerundet und gut sprechbar (z. B. "1,2 Sekunden", "14 Liter").
- Nutze ausschließlich die mitgeschickten Daten. Wenn etwas fehlt, sag ehrlich, dass du es nicht weißt.
- Sei ruhig, präzise und motivierend wie ein echter Ingenieur.
Zeitangaben in den Daten sind Sekunden, Temperaturen Grad Celsius, Drücke kPa, Sprit Liter,
Reifenverschleiß "wear" ist der verbleibende Anteil (1.0 = neu). "gap" positiv = Rückstand.
"fahrlinie" vergleicht die letzte Runde Kurve für Kurve mit der Bestrunde: loss = Zeitverlust in Sekunden,
brake_diff = Bremspunkt in Metern (negativ = früher), minv_diff = Kurvenspeed-Differenz in km/h,
thr_diff = Gaspunkt in Metern (positiv = später), apex_off/exit_off = Linie in Metern (positiv = weiter innen)."""

DEBRIEF_PROMPT = """Du bist Renningenieur und machst nach der Session eine Analyse für einen Sim-Racer (Le Mans Ultimate).
Schreibe auf Deutsch eine kompakte Auswertung mit kurzen Absätzen: Pace und Konstanz, Sprit/Strategie,
Reifen, auffällige Runden, und zwei bis drei konkrete Tipps fürs nächste Mal. Nutze nur die mitgeschickten Daten."""

# Schlüsselwörter -> eingebauter Bericht
INTENTS = [
    (r"linie|kurve|bremspunkt|scheitel|wo verliere|zeit liegen|einlenk|apex|verbesser|schneller werden|theoretisch",
     "line_report"),
    (r"sprit|benzin|tank|fuel|verbrauch|liter|energie|energy", "fuel_report"),
    (r"wetter|regen|nass|weather|rain|luft|temperatur der strecke|streckentemp", "weather_report"),
    (r"reifen|tyre|tire|pneu|grip|druck|bremse", "tyre_report"),
    (r"abstand|gap|vor mir|hinter mir|vorne|hinten|wer ist", "gap_report"),
    (r"position|platz|stand|welcher", "position_report"),
    (r"rundenzeit|bestzeit|pace|schnell|zeit der letzten|letzte runde", "pace_report"),
    (r"schaden|kaputt|damage", "damage_report"),
    (r"wie lange|restzeit|übrig|verbleib|noch zu fahren|runden noch|wie viele runden", "session_report"),
    (r"status|bericht|lage|update", "status_report"),
]


def compact_context(analysis: dict, engineer=None) -> dict:
    """Die wichtigsten Daten kompakt für die KI (spart Tokens)."""
    a = analysis
    if not a.get("connected") or "timing" not in a:
        return {"status": "keine Live-Daten"}
    tm = a["timing"]
    rel = [{"fahrer": r["driver"], "klasse": r["cls"], "abstand_s": r["rel"], "runden_diff": r["lapped"]}
           for r in a.get("relative", []) if not r["me"]]
    my_cls = a["car"]["cls"]
    coach = engineer.coach.summary() if engineer is not None else None
    standings = [{"p": s["cls_place"], "fahrer": s["driver"], "best": s["best"], "gap_zu_mir": s["gap_me"],
                  "runden_zu_mir": s["laps_me"], "stopps": s["stops"]}
                 for s in a.get("standings", []) if s["cls"] == my_cls][:12]
    return {
        "session": {k: a["session"].get(k) for k in ("name", "kind", "track", "time_left", "laps_remaining",
                                                      "raining", "wetness", "air_temp", "track_temp")},
        "auto": a["car"],
        "position": a["position"],
        "zeiten": {"runde": tm["lap"], "letzte": tm["last"], "beste": tm["best"], "delta_live": tm["delta"],
                   "runden": [{"nr": l["lap"], "zeit": l["time"], "sprit": l["fuel"], "box": l["pit"]}
                              for l in tm["laps"][-8:]]},
        "sprit": a["fuel"],
        "virtuelle_energie": a.get("energy"),
        "reifen": [{"pos": t["name"], "temp": t["avg"], "druck": t["pressure"], "wear": round(t["wear"], 3),
                    "bremse": t["brake_temp"]} for t in a["tyres"]],
        "schaden": a["damage"],
        "abstaende_klasse": a["gaps"],
        "um_mich_herum": rel,
        "klassenwertung": standings,
        "fahrlinie": coach,
    }


class Assistant:
    def __init__(self, cfg: dict, engineer):
        self.cfg = cfg
        self.eng = engineer
        self.history: list[dict] = []
        self._client = None

    # ------------------------------------------------------------------
    def claude_available(self) -> bool:
        if self.cfg.get("ki_modus", "auto") == "aus":
            return False
        try:
            import anthropic  # noqa: F401
        except ImportError:
            return False
        return bool(self.cfg.get("anthropic_api_key") or os.environ.get("ANTHROPIC_API_KEY")
                    or os.environ.get("ANTHROPIC_AUTH_TOKEN"))

    def _get_client(self):
        if self._client is None:
            import anthropic
            key = self.cfg.get("anthropic_api_key") or None
            self._client = anthropic.AsyncAnthropic(api_key=key) if key else anthropic.AsyncAnthropic()
        return self._client

    def builtin_answer(self, question: str) -> str | None:
        q = question.lower()
        for pattern, method in INTENTS:
            if re.search(pattern, q):
                return getattr(self.eng, method)()
        return None

    async def ask(self, question: str) -> tuple[str, str]:
        """Liefert (Antwort, Quelle) mit Quelle 'regel' oder 'ki'."""
        question = question.strip()[:500]
        mode = self.cfg.get("ki_modus", "auto")
        if mode != "immer" or not self.claude_available():
            ans = self.builtin_answer(question)
            if ans:
                return ans, "regel"
        if not self.claude_available():
            return ("Das kann ich ohne KI-Schlüssel nicht beantworten. Frag mich nach Sprit, Reifen, Abständen, "
                    "Position, Rundenzeiten, Wetter, Schaden oder Restzeit."), "regel"
        ctx = json.dumps(compact_context(self.eng.analysis, self.eng), ensure_ascii=False, default=lambda o: None)
        msgs = self.history[-8:] + [{"role": "user", "content": f"Aktuelle Telemetrie (JSON):\n{ctx}\n\nFahrer: {question}"}]
        text = await self._claude(SYSTEM_PROMPT, msgs, effort="low", max_tokens=1024)
        self.history += [{"role": "user", "content": question}, {"role": "assistant", "content": text}]
        self.history = self.history[-8:]
        return text, "ki"

    async def debrief(self) -> str:
        if not self.claude_available():
            return "Für die Rennanalyse brauchst du einen Anthropic-API-Schlüssel (siehe README)."
        a = self.eng.analysis
        data = {"kontext": compact_context(a, self.eng), "alle_runden": self.eng.laps,
                "verbrauch_je_runde": list(self.eng.fuel_hist)}
        msgs = [{"role": "user", "content": "Session-Daten (JSON):\n" + json.dumps(data, ensure_ascii=False, default=lambda o: None)}]
        return await self._claude(DEBRIEF_PROMPT, msgs, effort="medium", max_tokens=4000)

    async def _claude(self, system: str, messages: list, effort: str, max_tokens: int) -> str:
        import anthropic
        try:
            resp = await self._get_client().beta.messages.create(
                model=self.cfg.get("ki_modell", "claude-opus-5-5"),
                max_tokens=max_tokens,
                system=system,
                messages=messages,
                output_config={"effort": effort},
                betas=["server-side-fallback-2026-07-01"],
                fallbacks="default",
            )
        except anthropic.AuthenticationError:
            return "Der KI-Schlüssel ist ungültig. Bitte in der config.json prüfen."
        except anthropic.RateLimitError:
            return "Die KI ist gerade überlastet, frag mich gleich nochmal."
        except anthropic.APIStatusError as e:
            return f"Die KI hat einen Fehler gemeldet ({e.status_code})."
        except anthropic.APIConnectionError:
            return "Keine Verbindung zur KI. Ist der PC online?"
        if resp.stop_reason == "refusal":
            return "Dazu kann ich leider nichts sagen."
        text = " ".join(b.text for b in resp.content if b.type == "text").strip()
        return text or "Dazu habe ich gerade keine Antwort."
