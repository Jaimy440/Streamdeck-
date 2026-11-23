"""Erzeugt die Stichpunkte einer Woche - mit Claude (wenn API-Key da) oder offline."""
from __future__ import annotations

import json
import re

import archiv

MODEL = "claude-opus-5-5"

UNBEKANNT = {"", "?", "??", "???", "weiß nicht", "weiss nicht", "keine ahnung", "k.a.", "ka", "unbekannt", "-"}

SYSTEM = """Du schreibst Ausbildungsnachweise (Berichtshefte) für deutsche Azubis.

Stil:
- Kurze, stichpunktartige Sätze, sachlich, ohne "ich".
  Beispiel: "Netzwerkkabel im Büro verlegt und Anschlüsse getestet."
- Pro Arbeitstag 2-5 Stichpunkte, jeder höchstens ca. 12 Wörter.
- Fachbegriffe passend zum Beruf/zur Abteilung verwenden, nichts Erfundenes übertreiben.
- Berufsschultage: Unterrichtsfächer/Themen als Stichpunkte.
- Urlaub/Krank/Feiertag: genau ein Stichpunkt mit diesem Wort.

Quellen:
- Notizen des Azubis sind die wichtigste Quelle: umformulieren, nichts weglassen.
- Fehlt eine Notiz oder steht dort "?"/"weiß nicht", schlage plausible Tätigkeiten vor,
  die sich an den alten Berichten (gleiche Abteilung, ähnliche Zeit) orientieren.
  Markiere diese Punkte mit quelle="vorschlag".
- Übernimm alte Stichpunkte nicht wortgleich, sondern formuliere sie neu,
  damit sich die Wochen nicht wie Kopien lesen.
- Ergänze bei knappen Notizen höchstens einen passenden Punkt aus dem Archiv (quelle="ergaenzt")."""

SCHEMA = {
    "type": "object",
    "properties": {
        "tage": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "tag": {"type": "string", "enum": archiv.TAGE},
                    "punkte": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "text": {"type": "string"},
                                "quelle": {"type": "string", "enum": ["notiz", "ergaenzt", "vorschlag"]},
                            },
                            "required": ["text", "quelle"],
                            "additionalProperties": False,
                        },
                    },
                },
                "required": ["tag", "punkte"],
                "additionalProperties": False,
            },
        },
        "hinweise": {"type": "array", "items": {"type": "string"}},
    },
    "required": ["tage", "hinweise"],
    "additionalProperties": False,
}


def ist_unbekannt(notiz: str) -> bool:
    return notiz.strip().lower() in UNBEKANNT


def sonderfall(notiz: str) -> str | None:
    n = notiz.strip().lower()
    for wort, text in (("urlaub", "Urlaub"), ("krank", "Krank (Arbeitsunfähigkeit)"), ("feiertag", "Gesetzlicher Feiertag")):
        if n.startswith(wort):
            return text
    return None


# ---------------------------------------------------------------- offline
def _ueberlappung(a: str, b: str) -> float:
    ta, tb = set(archiv.tokens(a)), set(archiv.tokens(b))
    return len(ta & tb) / max(1, min(len(ta), len(tb)))


def satz(fragment: str) -> str:
    s = re.sub(r"\s+", " ", fragment).strip(" -•*.;,")
    s = re.sub(r"^(ich|wir)\s+(habe|haben|hab)\s+", "", s, flags=re.I)
    if not s:
        return ""
    return s[0].upper() + s[1:]


def offline(woche: dict, index: archiv.Index) -> dict:
    tage_out, hinweise = [], []
    benutzt: set[str] = set()   # gleiche Vorschläge nicht an mehreren Tagen
    kontext = {"abteilung": woche.get("abteilung"), "kw": woche.get("kw")}
    for tag in archiv.TAGE:
        info = woche["tage"].get(tag, {})
        notiz = (info.get("notiz") or "").strip()
        schule = info.get("schule")
        punkte = []
        sf = sonderfall(notiz)
        if sf:
            punkte.append({"text": sf, "quelle": "notiz"})
        elif notiz and not ist_unbekannt(notiz):
            for frag in re.split(r"[\n,;]+", notiz):
                if satz(frag):
                    punkte.append({"text": satz(frag), "quelle": "notiz"})
            if len(punkte) < 3:
                # verwandten, aber nicht gleichen Punkt aus dem Archiv ergänzen
                for t in index.suche(notiz, limit=8, kontext=dict(kontext, tag=tag), schule=bool(schule)):
                    if t["punkt"].lower() not in benutzt and all(_ueberlappung(t["punkt"], p["text"]) < 0.5 for p in punkte):
                        punkte.append({"text": t["punkt"], "quelle": "ergaenzt", "aus": t["bericht"]["label"]})
                        benutzt.add(t["punkt"].lower())
                        break
        else:
            vorschlaege = [t for t in index.suche("", limit=15, kontext=dict(kontext, tag=tag), schule=bool(schule))
                           if t["punkt"].lower() not in benutzt][:3]
            benutzt.update(t["punkt"].lower() for t in vorschlaege)
            for t in vorschlaege:
                punkte.append({"text": t["punkt"], "quelle": "vorschlag", "aus": t["bericht"]["label"]})
            if not vorschlaege:
                hinweise.append(f"{tag}: keine Notiz und nichts Passendes im Archiv gefunden.")
        if schule and not any("schule" in p["text"].lower() for p in punkte):
            punkte.insert(0, {"text": "Berufsschule", "quelle": "notiz"})
        tage_out.append({"tag": tag, "punkte": punkte})
    if not index.eintraege:
        hinweise.append("Das Archiv ist leer - importiere alte Berichtshefte, damit Lücken ergänzt werden können.")
    hinweise.append("Offline-Modus: Für schönere Formulierungen in den Einstellungen einen Claude-API-Key eintragen.")
    return {"tage": tage_out, "hinweise": hinweise, "modus": "offline"}


# ---------------------------------------------------------------- Claude
def mit_claude(woche: dict, index: archiv.Index, berichte: list[dict], api_key: str | None) -> dict:
    import anthropic

    client = anthropic.Anthropic(api_key=api_key) if api_key else anthropic.Anthropic()
    alle_notizen = " ".join((woche["tage"].get(t, {}).get("notiz") or "") for t in archiv.TAGE)
    kontext = {"abteilung": woche.get("abteilung"), "kw": woche.get("kw")}
    vergleich = index.aehnliche_berichte(alle_notizen, berichte, limit=5, kontext=kontext)

    alt = "\n\n".join(f"--- {b['label']} ---\n{b['text']}" for b in vergleich) or "(keine alten Berichte vorhanden)"
    zeilen = []
    for t in archiv.TAGE:
        info = woche["tage"].get(t, {})
        notiz = (info.get("notiz") or "").strip() or "?"
        zeilen.append(f"{t}{' (Berufsschule)' if info.get('schule') else ''}: {notiz}")
    anfrage = (
        f"Beruf: {woche.get('beruf') or 'nicht angegeben'}\n"
        f"Abteilung: {woche.get('abteilung') or 'nicht angegeben'}\n"
        f"KW {woche.get('kw') or '?'} / {woche.get('jahr') or '?'}\n\n"
        f"<alte_berichte>\n{alt}\n</alte_berichte>\n\n"
        f"<notizen_diese_woche>\n" + "\n".join(zeilen) + "\n</notizen_diese_woche>\n\n"
        "Schreibe die Stichpunkte für alle fünf Tage. "
        "Unter 'hinweise' kurz notieren, welche Tage geraten wurden und was der Azubi prüfen sollte."
    )

    antwort = client.beta.messages.create(
        model=MODEL,
        max_tokens=16000,
        betas=["server-side-fallback-2026-07-01"],
        fallbacks="default",
        output_config={"effort": "low", "format": {"type": "json_schema", "schema": SCHEMA}},
        system=SYSTEM,
        messages=[{"role": "user", "content": anfrage}],
    )
    if antwort.stop_reason == "refusal":
        raise RuntimeError("Claude hat die Anfrage abgelehnt.")
    if antwort.stop_reason == "max_tokens":
        raise RuntimeError("Antwort wurde abgeschnitten.")
    text = next((b.text for b in antwort.content if b.type == "text"), "")
    daten = json.loads(text)
    daten["modus"] = "claude"
    daten["vergleich"] = [{"id": b["id"], "label": b["label"], "score": b["score"]} for b in vergleich]
    return daten


def erzeugen(woche: dict, api_key: str | None) -> dict:
    berichte = archiv.laden()
    index = archiv.Index(berichte)
    fehler = None
    ergebnis = None
    if api_key or _env_key():
        try:
            ergebnis = mit_claude(woche, index, berichte, api_key)
        except ImportError:
            fehler = "Paket 'anthropic' fehlt - nutze Offline-Modus."
        except Exception as e:  # Netzwerk, Key ungültig, ... -> offline weiter
            fehler = f"Claude nicht erreichbar ({type(e).__name__}: {e}) - nutze Offline-Modus."
    if ergebnis is None:
        ergebnis = offline(woche, index)
        alle = " ".join((woche["tage"].get(t, {}).get("notiz") or "") for t in archiv.TAGE)
        vergleich = index.aehnliche_berichte(alle, berichte, limit=5,
                                             kontext={"abteilung": woche.get("abteilung"), "kw": woche.get("kw")})
        ergebnis["vergleich"] = [{"id": b["id"], "label": b["label"], "score": b["score"]} for b in vergleich]
    if fehler:
        ergebnis["hinweise"].insert(0, fehler)
    # Punkte, die offline bewusst aus dem Archiv kommen ("aus ..."), sind sichtbar markiert
    alle_punkte = [p["text"] for t in ergebnis["tage"] for p in t["punkte"]
                   if not p.get("aus") and len(archiv.tokens(p["text"])) >= 3]
    ergebnis["doppelt"] = archiv.doppelte(alle_punkte, index)
    return ergebnis


def _env_key() -> bool:
    import os
    return bool(os.environ.get("ANTHROPIC_API_KEY") or os.environ.get("ANTHROPIC_AUTH_TOKEN"))
