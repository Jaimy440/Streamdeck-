"""Archiv alter Berichtshefte + Ähnlichkeitssuche (läuft komplett offline)."""
from __future__ import annotations

import json
import math
import os
import re
import threading
import time
import uuid
from collections import Counter

BASE = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE, "data")
ARCHIV_PATH = os.path.join(DATA_DIR, "berichte.json")

TAGE = ["Montag", "Dienstag", "Mittwoch", "Donnerstag", "Freitag"]

STOPWORDS = set("""
aber alle allem allen aller alles als also am an ander andere anderem anderen anderer anderes
auch auf aus bei beim bin bis bist da damit dann das dass dein dem den der des dessen die dies
diese diesem diesen dieser dieses doch dort du durch ein eine einem einen einer eines er es
etwas für gegen hab habe haben hat hatte hatten hier hin ich ihm ihn ihr im in ins ist ja jede
jedem jeden jeder jedes kann kein keine können man mein mich mir mit muss nach nicht noch nun
nur ob oder ohne sehr sein seine sich sie sind so solche soll sollte sondern um und uns unter
viel vom von vor war waren was weil welche wenn werden wie wieder wir wird wo wurde wurden zu
zum zur über heute tag tages woche wochen sowie bzw usw ca etc
""".split())

_lock = threading.Lock()


# ---------------------------------------------------------------- Speicher
def laden() -> list[dict]:
    if not os.path.exists(ARCHIV_PATH):
        return []
    with open(ARCHIV_PATH, encoding="utf-8") as f:
        return json.load(f)


def speichern(berichte: list[dict]) -> None:
    os.makedirs(DATA_DIR, exist_ok=True)
    tmp = ARCHIV_PATH + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(berichte, f, ensure_ascii=False, indent=1)
    os.replace(tmp, ARCHIV_PATH)


def hinzufuegen(eintraege: list[dict]) -> list[dict]:
    with _lock:
        berichte = laden()
        neu = []
        for e in eintraege:
            e = normalisieren(e)
            berichte.append(e)
            neu.append(e)
        speichern(berichte)
    return neu


def aktualisieren(bericht: dict) -> dict:
    with _lock:
        berichte = laden()
        b = normalisieren(bericht)
        for i, alt in enumerate(berichte):
            if alt["id"] == b["id"]:
                berichte[i] = b
                break
        else:
            berichte.append(b)
        speichern(berichte)
    return b


def loeschen(bid: str) -> None:
    with _lock:
        speichern([b for b in laden() if b["id"] != bid])


def normalisieren(e: dict) -> dict:
    tage = e.get("tage") or {}
    return {
        "id": e.get("id") or uuid.uuid4().hex[:12],
        "jahr": int(e["jahr"]) if str(e.get("jahr") or "").isdigit() else None,
        "kw": int(e["kw"]) if str(e.get("kw") or "").isdigit() else None,
        "abteilung": (e.get("abteilung") or "").strip(),
        "titel": (e.get("titel") or "").strip(),
        "text": (e.get("text") or "").strip(),
        "tage": {t: (tage.get(t) or "").strip() for t in TAGE if (tage.get(t) or "").strip()},
        "erstellt": e.get("erstellt") or time.strftime("%Y-%m-%d"),
    }


# ---------------------------------------------------------------- Import
_KW_RE = re.compile(r"^\s*(?:KW|Kalenderwoche|Woche)\s*[:.]?\s*(\d{1,2})(?:\s*[/.\-]\s*(\d{2,4}))?", re.I | re.M)
_TAG_RE = re.compile(r"^\s*(Montag|Dienstag|Mittwoch|Donnerstag|Freitag|Mo|Di|Mi|Do|Fr)\b\.?\s*:?\s*", re.I)
_KURZ = {"mo": "Montag", "di": "Dienstag", "mi": "Mittwoch", "do": "Donnerstag", "fr": "Freitag"}


def text_importieren(text: str, standard: dict | None = None) -> list[dict]:
    """Zerlegt eingefügten Text in einzelne Wochenberichte.

    Neue Woche beginnt bei Zeilen wie "KW 12", "KW 12/2025", "Woche 3".
    Ohne solche Überschriften wird der ganze Text ein Bericht.
    """
    standard = standard or {}
    text = text.replace("\r\n", "\n").strip()
    if not text:
        return []
    treffer = list(_KW_RE.finditer(text))
    bloecke = []
    if not treffer:
        bloecke.append((None, None, text))
    else:
        if treffer[0].start() > 0 and text[: treffer[0].start()].strip():
            bloecke.append((None, None, text[: treffer[0].start()]))
        for i, m in enumerate(treffer):
            ende = treffer[i + 1].start() if i + 1 < len(treffer) else len(text)
            jahr = m.group(2)
            if jahr and len(jahr) == 2:
                jahr = "20" + jahr
            bloecke.append((m.group(1), jahr, text[m.end():ende]))
    ergebnis = []
    for kw, jahr, block in bloecke:
        block = block.strip()
        if not block:
            continue
        ergebnis.append({
            "kw": kw or standard.get("kw"),
            "jahr": jahr or standard.get("jahr"),
            "abteilung": standard.get("abteilung", ""),
            "text": block,
            "tage": tage_erkennen(block),
        })
    return ergebnis


def tage_erkennen(text: str) -> dict:
    tage: dict[str, list[str]] = {}
    aktuell = None
    for zeile in text.split("\n"):
        m = _TAG_RE.match(zeile)
        if m:
            name = m.group(1).lower()
            aktuell = _KURZ.get(name[:2], name.capitalize())
            rest = zeile[m.end():].strip()
            tage.setdefault(aktuell, [])
            if rest:
                tage[aktuell].append(rest)
        elif aktuell and zeile.strip():
            tage[aktuell].append(zeile.strip())
    return {t: "\n".join(z) for t, z in tage.items()}


# ---------------------------------------------------------------- Ähnlichkeit
def tokens(text: str) -> list[str]:
    woerter = re.findall(r"[a-zA-ZäöüÄÖÜß0-9][\wäöüÄÖÜß\-]+", text.lower())
    return [stamm(w) for w in woerter if w not in STOPWORDS and len(w) > 2]


def stamm(w: str) -> str:
    for endung in ("ungen", "ung", "en", "er", "es", "e", "s", "n"):
        if len(w) > len(endung) + 3 and w.endswith(endung):
            return w[: -len(endung)]
    return w


def stichpunkte(text: str) -> list[str]:
    """Zerlegt Berichtstext in einzelne Stichpunkte."""
    punkte = []
    for zeile in text.replace("\r", "").split("\n"):
        zeile = _TAG_RE.sub("", zeile)
        zeile = re.sub(r"^\s*[-•*–·>]+\s*|^\s*\d+[.)]\s+", "", zeile).strip()
        if not zeile:
            continue
        teile = re.split(r"(?<=[.!;])\s+", zeile) if len(zeile) > 120 else [zeile]
        punkte.extend(t.strip(" .;") for t in teile if len(t.strip()) > 3)
    return punkte


class Index:
    """Einfacher TF-IDF-Index über alle Stichpunkte im Archiv."""

    def __init__(self, berichte: list[dict]):
        self.eintraege = []   # (bericht, tag, punkt, vektor, schultag)
        df: Counter = Counter()
        roh = []
        for b in berichte:
            quellen = b["tage"].items() if b.get("tage") else [(None, b.get("text", ""))]
            for tag, txt in quellen:
                schultag = bool(tag) and "schule" in txt.lower()
                for p in stichpunkte(txt):
                    tf = Counter(tokens(p))
                    if tf and p.lower().strip() not in ("berufsschule", "schule"):
                        roh.append((b, tag, p, tf, schultag))
                        df.update(tf.keys())
        n = max(len(roh), 1)
        self.idf = {w: math.log((n + 1) / (c + 0.5)) for w, c in df.items()}
        for b, tag, p, tf, schultag in roh:
            self.eintraege.append((b, tag, p, self._vektor(tf), schultag))

    def _vektor(self, tf: Counter) -> dict:
        v = {w: (1 + math.log(c)) * self.idf.get(w, 1.0) for w, c in tf.items()}
        norm = math.sqrt(sum(x * x for x in v.values())) or 1.0
        return {w: x / norm for w, x in v.items()}

    @staticmethod
    def _cos(a: dict, b: dict) -> float:
        if len(a) > len(b):
            a, b = b, a
        return sum(x * b.get(w, 0.0) for w, x in a.items())

    def suche(self, text: str, limit: int = 8, kontext: dict | None = None,
              schule: bool | None = None) -> list[dict]:
        """Ähnlichste Stichpunkte. kontext (abteilung, kw, tag) gibt leichten Bonus.
        schule=True/False filtert auf Berufsschul- bzw. Betriebstage."""
        kontext = kontext or {}
        q = self._vektor(Counter(tokens(text))) if text.strip() else {}
        ergebnis = []
        for b, tag, p, v, schultag in self.eintraege:
            if schule is not None and schultag != schule:
                continue
            score = self._cos(q, v) if q else 0.0
            if kontext.get("abteilung") and b.get("abteilung", "").lower() == kontext["abteilung"].lower():
                score += 0.15
            if kontext.get("tag") and tag == kontext["tag"]:
                score += 0.05
            if kontext.get("kw") and b.get("kw"):
                abstand = abs(int(kontext["kw"]) - b["kw"])
                abstand = min(abstand, 52 - abstand)
                score += 0.1 * max(0, 1 - abstand / 6)
            if score > 0.05:
                ergebnis.append({"punkt": p, "score": round(score, 3), "tag": tag, "bericht": kurzinfo(b)})
        ergebnis.sort(key=lambda x: -x["score"])
        gesehen, eindeutig = set(), []
        for e in ergebnis:
            k = e["punkt"].lower()
            if k not in gesehen:
                gesehen.add(k)
                eindeutig.append(e)
            if len(eindeutig) >= limit:
                break
        return eindeutig

    def aehnliche_berichte(self, text: str, berichte: list[dict], limit: int = 4, kontext: dict | None = None) -> list[dict]:
        """Ganze Berichte nach Ähnlichkeit sortiert (für Vergleich und KI-Kontext)."""
        kontext = kontext or {}
        q = self._vektor(Counter(tokens(text))) if text.strip() else {}
        bewertet = []
        for b in berichte:
            v = self._vektor(Counter(tokens(bericht_text(b))))
            score = self._cos(q, v) if q else 0.0
            if kontext.get("abteilung") and b.get("abteilung", "").lower() == kontext["abteilung"].lower():
                score += 0.2
            if kontext.get("kw") and b.get("kw"):
                abstand = abs(int(kontext["kw"]) - b["kw"])
                abstand = min(abstand, 52 - abstand)
                score += 0.1 * max(0, 1 - abstand / 6)
            bewertet.append((score, b))
        bewertet.sort(key=lambda x: -x[0])
        return [dict(kurzinfo(b), score=round(s, 3), text=bericht_text(b)) for s, b in bewertet[:limit] if s > 0.02]


def bericht_text(b: dict) -> str:
    if b.get("tage"):
        return "\n".join(f"{t}:\n{b['tage'][t]}" for t in TAGE if t in b["tage"])
    return b.get("text", "")


def kurzinfo(b: dict) -> dict:
    label = b.get("titel") or (f"KW {b['kw']}" + (f"/{b['jahr']}" if b.get("jahr") else "") if b.get("kw") else "ohne KW")
    if b.get("abteilung"):
        label += f" · {b['abteilung']}"
    return {"id": b["id"], "label": label}


def doppelte(punkte: list[str], index: Index, schwelle: float = 0.85) -> list[dict]:
    """Findet neue Stichpunkte, die fast wortgleich schon im Archiv stehen."""
    warn = []
    for p in punkte:
        top = index.suche(p, limit=1)
        if top and top[0]["score"] >= schwelle:
            warn.append({"punkt": p, "alt": top[0]["punkt"], "bericht": top[0]["bericht"]["label"]})
    return warn
