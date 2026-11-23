# 📒 Berichtsheft-Assistent

Schreibt dein Berichtsheft (Ausbildungsnachweis) in kurzen Stichpunkt-Sätzen – im Browser.

- **Stichworte rein, Bericht raus:** Pro Tag ein paar Stichworte tippen, z. B. `drucker repariert, tickets`
  → wird zu „Drucker repariert“, „Tickets bearbeitet“ …
- **Vergleich mit alten Berichtsheften:** Schon beim Tippen siehst du ähnliche Einträge aus früheren Wochen
  und kannst sie per Klick übernehmen. Nach dem Schreiben zeigt die App, mit welchen alten Wochen
  verglichen wurde.
- **Weißt du nicht mehr, was du gemacht hast?** Feld leer lassen oder `?` schreiben. Dann wird der Tag
  mit passenden Tätigkeiten aus alten Berichten ergänzt (gleiche Abteilung, ähnliche Kalenderwoche,
  Berufsschultage nur mit Schulthemen). Diese Punkte sind **orange markiert** – kurz prüfen!
- **Kopie-Warnung:** Stichpunkte, die fast wortgleich in alten Berichten stehen, werden gemeldet.
- `Urlaub`, `Krank`, `Feiertag` und das Häkchen **Berufsschule** werden erkannt.
- Ergebnis direkt bearbeiten, **als Text kopieren** (für Word/PDF-Vorlage oder Online-Berichtsheft)
  und **ins Archiv speichern** – so wird die App jede Woche besser.

## Start (Windows)

1. Python 3.11+ installieren (beim Installieren „Add python.exe to PATH“ anhaken).
2. Im Ordner `berichtsheft` doppelt auf **`start.bat`** klicken.
   Beim ersten Mal werden die Pakete installiert, danach öffnet sich <http://localhost:8090>.

Mac/Linux: `pip install -r requirements.txt` und dann `python3 server.py`.

Vom Handy im gleichen WLAN nutzen: `python server.py --lan` und dann `http://<PC-IP>:8090` öffnen.

## Alte Berichtshefte importieren

Reiter **Archiv** → Text einfügen oder `.txt`-Dateien wählen. Mehrere Wochen auf einmal gehen, wenn
jede Woche mit `KW 12` oder `KW 12/2025` beginnt:

```
KW 10/2025
Montag: Tickets im Helpdesk bearbeitet
- Drucker im Büro 2 repariert
Dienstag: Neue Laptops mit Windows 11 eingerichtet
Mittwoch: Berufsschule
- Netzwerktechnik: Subnetting
...
```

Aus Word/PDF einfach den Text markieren, kopieren und einfügen.

## Offline oder mit Claude

| Modus | Was passiert |
|-------|--------------|
| **Offline** (Standard) | Notizen werden in saubere Stichpunkte zerlegt, Lücken mit passenden Punkten aus dem Archiv gefüllt (Textähnlichkeit, läuft komplett lokal). |
| **Mit Claude** | Unter **Einstellungen** einen API-Key von <https://console.anthropic.com> eintragen. Claude formuliert die Sätze ordentlich um, schreibt Vorschläge aus alten Berichten **neu** statt sie zu kopieren und gibt Hinweise, was du prüfen solltest. Ist Claude nicht erreichbar, läuft automatisch der Offline-Modus. |

Alle Daten (Archiv, Einstellungen, API-Key) liegen nur lokal in `berichtsheft/data/`.
