# PC-Deck – dein iPhone als Streamdeck

Steuere deinen Windows-PC vom iPhone aus:

- 🔊 **Lautstärke** lauter / leiser / Schieberegler / PC stumm
- 💬 **Discord**: Mikro stumm, Taub (Deafen), **Full Mute** (Discord taub + Windows-Mikro aus)
- 🎤 **Windows-Mikrofon** stumm schalten (wirkt auf alle Programme)
- 🧠 **Stimmfilter**: Nur **deine** Stimme geht ins Mikro, dein Bruder wird rausgefiltert
- ⚡ **Eigene Buttons**: Media-Tasten, Programme starten, Tastenkürzel, Webseiten … (frei in `config.json`)

Die iPhone-App ist eine Web-App, die der PC ausliefert. Du legst sie über Safari auf den
Home-Bildschirm, dann startet sie wie eine normale App im Vollbild.
**Du brauchst keinen Mac, kein Xcode und keinen App Store.**

```
 iPhone (PC-Deck-App) ──WLAN / WebSocket──▶ PC (server.py)
                                             ├─ Windows-Lautstärke (pycaw)
                                             ├─ Discord-Tastenkürzel (keyboard)
                                             └─ Stimmfilter: Mikro ─▶ Filter ─▶ VB-Cable ─▶ Discord
```

---

## 1. Installation am PC (einmalig)

1. **Python 3.11 oder 3.12** installieren: <https://www.python.org/downloads/>
   → beim Installieren **„Add python.exe to PATH“** anhaken.
2. Dieses Repo herunterladen (grüner Button „Code“ → „Download ZIP“) und entpacken.
3. Im Ordner `pc-app` doppelt auf **`start.bat`** klicken.
   Beim ersten Start werden alle Pakete installiert, das dauert etwa 1 Minute.
4. Fragt die Windows-Firewall nach, wähle **„Zulassen“** und hake **private Netzwerke** an.

Im Fenster erscheinen dann ein **QR-Code** und eine Adresse wie `http://192.168.1.20:8765/?token=…`.

## 2. App aufs iPhone holen

1. iPhone und PC müssen im **gleichen WLAN** sein.
2. QR-Code mit der **iPhone-Kamera** scannen → öffnet sich in Safari.
3. In Safari: **Teilen-Symbol** → **„Zum Home-Bildschirm“** → Hinzufügen.
4. Fertig: Ab jetzt einfach das **PC-Deck**-Symbol antippen.

> Der Token in der Adresse ist dein Passwort. Ohne ihn kann niemand im WLAN deinen PC steuern.
> Wenn du ihn ändern willst, lösche den Eintrag `"token"` in `config.json` und starte neu.

## 3. Discord einrichten (wichtig!)

PC-Deck steuert Discord über Tastenkürzel. Trag sie in Discord einmal ein:

Discord → ⚙️ Einstellungen → **Tastenbelegung** → „Tastenbelegung hinzufügen“

| Aktion in Discord          | Tastenkürzel           |
|----------------------------|------------------------|
| Stummschalten umschalten   | `Strg + Umschalt + Alt + M` |
| Ein-/Ausgabe deaktivieren umschalten (Taub) | `Strg + Umschalt + Alt + D` |

Andere Kürzel kannst du in `pc-app/config.json` unter `"discord"` einstellen.

> Discord meldet nicht zurück, ob du gerade stumm bist. Die App merkt sich den Zustand selbst.
> Falls die Anzeige mal falsch ist (z. B. weil du am PC geklickt hast), tippe in der App auf **„↺ Sync“**.
>
> Läuft Discord **als Administrator**, muss auch `start.bat` als Administrator laufen,
> sonst kommen die Tastendrücke nicht an.

---

## 4. Stimmfilter: Bruder rausfiltern 🧠

### So funktioniert's

Der Filter lernt deinen **Stimmabdruck**. Live prüft er alle 100 ms, ob gerade **du**
sprichst. Nur dann wird dein Mikro an Discord durchgelassen. Spricht dein Bruder (oder
ist es nur Hintergrundlärm), bleibt das Mikro zu. Weil das Mikro als virtuelles Gerät
umgeleitet wird, funktioniert der Filter in **jedem** Programm (Discord, TeamSpeak, Spiele …).

### Einrichtung

1. Im Ordner `pc-app` doppelt auf **`install_filter.bat`** klicken
   (lädt PyTorch, etwa 1 GB, dauert ein paar Minuten).
2. **VB-Audio Virtual Cable** installieren (kostenlos): <https://vb-audio.com/Cable/>
   → ZIP entpacken → `VBCABLE_Setup_x64.exe` **als Administrator** ausführen → PC neu starten.
3. `start.bat` neu starten.
4. In der App unter **Stimmfilter** auf **„🙋 Meine Stimme einlernen“** tippen und
   20 Sekunden ganz normal sprechen (z. B. etwas vorlesen). Dein Bruder ist dabei leise.
5. **Sehr empfohlen:** Auf **„👦 Bruder einlernen“** tippen. Jetzt spricht 20 Sekunden lang
   nur dein Bruder. Danach vergleicht der Filter beide Stimmen und wird **viel genauer**.
6. Schalter **Stimmfilter** einschalten.
7. In **Discord** → Einstellungen → Sprache & Video → **Eingabegerät: `CABLE Output (VB-Audio Virtual Cable)`**.
   In Discord außerdem **Rauschunterdrückung (Krisp) ausschalten** und
   **„Eingabeempfindlichkeit automatisch bestimmen“** ausschalten bzw. ganz niedrig stellen.

### Feineinstellung in der App

- **Ähnlichkeit zu dir**: blauer Balken. Er sollte beim Sprechen **rechts** von der weißen Markierung (Schwelle) liegen.
- **Ähnlichkeit Bruder**: gelber Balken.
- **Empfindlichkeit (Schwelle)**:
  - Du wirst abgeschnitten → Schwelle **runter** (z. B. 0.65)
  - Dein Bruder kommt durch → Schwelle **hoch** (z. B. 0.80) oder Bruder einlernen

Weitere Werte in `config.json` unter `"voice_filter"`:

| Wert | Bedeutung |
|------|-----------|
| `input_device` | Dein echtes Mikro (Namensteil, z. B. `"Yeti"`). `null` = Windows-Standard |
| `lookahead_ms` | Vorlauf, damit Wortanfänge nicht fehlen (mehr = sicherer, aber mehr Verzögerung) |
| `hold_ms` | Wie lange das Mikro nach deiner Stimme offen bleibt (Sprechpausen) |
| `noise_gate_db` | Alles leiser als das gilt als Stille |
| `margin` | Wie deutlich du „mehr du“ als „Bruder“ sein musst |
| `autostart` | `true` = Filter startet automatisch mit dem Programm |

### Ehrliche Grenzen

- Reden du und dein Bruder **gleichzeitig**, ist das Mikro offen (deine Stimme ist ja dabei)
  und er ist leise im Hintergrund zu hören. Zwei gleichzeitige Stimmen in Echtzeit sauber
  zu trennen schafft kein Heim-PC-Tool zuverlässig.
- Es gibt etwa 0,2 s Verzögerung (der Vorlauf). In Discord merkt das praktisch niemand.
- **Tipp dazu:** Ein **dynamisches Nieren-Mikro** (z. B. Shure SM58 oder Samson Q2U) oder ein
  Headset-Mikro nah am Mund nimmt deinen Bruder schon von sich aus viel leiser auf.
  Zusammen mit dem Filter ist das die beste Lösung.

---

## Eigene Buttons (`config.json`)

```json
"buttons": [
  { "label": "Play / Pause", "icon": "⏯️", "action": "hotkey",  "keys": "play/pause media" },
  { "label": "OBS Szene 1",  "icon": "🎬", "action": "hotkey",  "keys": "ctrl+alt+f1" },
  { "label": "Spotify",      "icon": "🎵", "action": "launch",  "target": "spotify:" },
  { "label": "Steam",        "icon": "🎮", "action": "launch",  "target": "C:\\Program Files (x86)\\Steam\\steam.exe" },
  { "label": "YouTube",      "icon": "📺", "action": "url",     "target": "https://youtube.com" },
  { "label": "Sperren",      "icon": "🔒", "action": "command", "target": "rundll32.exe user32.dll,LockWorkStation" }
]
```

`action`: `hotkey` (Tastenkürzel), `launch` (Programm/Datei/App-Link), `url` (Webseite), `command` (Konsolenbefehl).
Nach dem Ändern `start.bat` neu starten.

## Probleme?

| Problem | Lösung |
|---------|--------|
| iPhone verbindet nicht | Gleiches WLAN? Firewall-Abfrage zugelassen? Bei „Gast-WLAN“ geht es nicht. |
| Discord reagiert nicht | Tastenkürzel in Discord eingetragen? Discord als Admin → PC-Deck auch als Admin starten. |
| Filter: „Audiogerät 'CABLE Input' nicht gefunden“ | VB-Cable installieren und PC neu starten. |
| Filter schneidet dich ab | Schwelle runter, eigene Stimme in ruhiger Umgebung neu einlernen. |
| PC-IP hat sich geändert | Neuen QR-Code scannen und App neu zum Home-Bildschirm hinzufügen (oder im Router feste IP vergeben). |

## Dateien

```
pc-app/
  start.bat            Startet PC-Deck (installiert beim 1. Mal alles)
  install_filter.bat   Installiert den Stimmfilter
  server.py            Server + Befehle
  controls.py          Lautstärke, Mikro, Tastenkürzel, Programme
  voicefilter.py       Stimmerkennung & Mikrofon-Filter
  web/                 Die iPhone-App (HTML/CSS/JS)
  config.json          Deine Einstellungen (wird beim 1. Start erstellt)
```
