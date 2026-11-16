# PC-Deck – dein iPhone als Streamdeck

Steuere deinen Windows-PC vom iPhone aus – im Look eines Hardware-Streamdecks: dunkle Tasten mit
leuchtenden Farbakzenten, gemacht fürs **Querformat** (iPhone quer z. B. auf einem Ständer neben der Tastatur).
Hochformat geht auch. Zwischen den Seiten wechselst du unten oder per Wischen; Playlists erscheinen als Tasten mit Cover.

| Bereich | Was geht |
|---------|----------|
| **Steuerung** | Lautstärke (Regler, lauter/leiser, PC stumm) · Discord Mikro stumm / Taub / **Full Mute** · Windows-Mikro · eigene Aktions-Buttons |
| **Spotify** | Deine Playlists & Lieblingssongs auswählen und abspielen · Play/Pause, Weiter, Zurück, Zufall, Wiederholen · Spotify-Lautstärke · Zeitleiste |
| **Chrome** | Webseiten öffnen (immer als **neuer Tab** im offenen Chrome-Fenster) · Favoriten · laufendes **Video steuern**: Play/Pause, ±10 s, Zeitleiste, Lautstärke, Tempo, nächstes Video |

Die iPhone-App ist eine Web-App, die der PC ausliefert. Du legst sie über Safari auf den
Home-Bildschirm, dann startet sie wie eine normale App im Vollbild.
**Du brauchst keinen Mac, kein Xcode und keinen App Store.**

```
 iPhone (PC-Deck) ──WLAN──▶ PC (server.py) ──┬─ Windows-Lautstärke / Mikro
                                              ├─ Discord (Tastenkürzel)
                                              ├─ Spotify (offizielle Web-API)
                                              └─ Chrome-Erweiterung ──▶ Tabs & Videos
```

---

## 1. Installation am PC (einmalig)

1. **Python 3.11 oder 3.12** installieren: <https://www.python.org/downloads/>
   → beim Installieren **„Add python.exe to PATH“** anhaken.
2. Dieses Repo herunterladen (grüner Button „Code“ → „Download ZIP“) und entpacken.
3. Im Ordner `pc-app` doppelt auf **`start.bat`** klicken.
   Beim ersten Start werden alle Pakete installiert, das dauert etwa 1 Minute.
4. Fragt die Windows-Firewall nach, wähle **„Zulassen“** und hake **private Netzwerke** an.

> **Update von einer älteren Version?** Lösche einmal den Ordner `pc-app\.venv` und starte
> `start.bat` neu, damit die neuen Pakete installiert werden.

## 2. App aufs iPhone holen

1. iPhone und PC müssen im **gleichen WLAN** sein.
2. Den **QR-Code** im PC-Deck-Fenster mit der **iPhone-Kamera** scannen → öffnet sich in Safari.
3. In Safari: **Teilen-Symbol** → **„Zum Home-Bildschirm“** → Hinzufügen.
4. Fertig: Ab jetzt einfach das **PC-Deck**-Symbol antippen und das iPhone quer halten.

### Dauerhaft angemeldet

- Du musst dich **nur einmal** per QR-Code verbinden. Danach bleibt das iPhone dauerhaft angemeldet,
  auch nach Neustarts von PC oder iPhone.
- Die App nutzt die Adresse **`pc-deck.local`** statt der IP-Adresse. Sie funktioniert also weiter,
  auch wenn dein Router dem PC eine neue IP gibt.
  (Falls der QR-Code nicht lädt, steht im Fenster eine Ersatz-Adresse mit IP.)
- Der Token in der Adresse ist dein Passwort. Ohne ihn kann niemand im WLAN deinen PC steuern.
  Willst du alle Geräte abmelden, lösche den Eintrag `"token"` in `config.json` und starte neu.

## 3. Discord einrichten

PC-Deck steuert Discord über Tastenkürzel. Trag sie in Discord einmal ein:

Discord → ⚙️ Einstellungen → **Tastenbelegung** → „Tastenbelegung hinzufügen“

| Aktion in Discord          | Tastenkürzel           |
|----------------------------|------------------------|
| Stummschalten umschalten   | `Strg + Umschalt + Alt + M` |
| Ein-/Ausgabe deaktivieren umschalten (Taub) | `Strg + Umschalt + Alt + D` |

Andere Kürzel kannst du in `pc-app/config.json` unter `"discord"` einstellen.

> Discord meldet nicht zurück, ob du gerade stumm bist. Die App merkt sich den Zustand selbst.
> Falls die Anzeige mal falsch ist, tippe in der App auf **„Sync“**.
> Läuft Discord **als Administrator**, muss auch `start.bat` als Administrator laufen.

## 4. Spotify einrichten (einmalig, ca. 3 Minuten)

Spotify erlaubt Fernsteuerung nur über eine eigene, kostenlose „Spotify-App“:

1. Am PC <https://developer.spotify.com/dashboard> öffnen und mit deinem Spotify-Konto anmelden.
2. **Create app** →
   - App name / Description: z. B. `PC-Deck`
   - **Redirect URI:** `http://127.0.0.1:8765/spotify/callback` (genau so!) → **Add**
   - Bei **„Which API/SDKs are you planning to use?“**: **Web API** anhaken
   - Nutzungsbedingungen akzeptieren → **Save**
3. Die **Client ID** kopieren und in `pc-app/config.json` eintragen:
   ```json
   "spotify": { "client_id": "hier-deine-client-id" }
   ```
4. PC-Deck neu starten → in der App auf die Seite **Spotify** → **„Mit Spotify verbinden“**.
   Am PC öffnet sich der Spotify-Login → **Zustimmen**. Fertig.

Der Spotify-Login bleibt **dauerhaft gespeichert** (`spotify_token.json`) und wird automatisch erneuert.

> **Premium oder Free?** Playlists anzeigen geht mit jedem Konto. Musik **direkt starten und steuern**
> erlaubt Spotify über die API nur mit **Premium**. Mit Spotify Free öffnet PC-Deck die gewählte
> Playlist in der Spotify-App am PC (dort dann Play drücken) und Play/Weiter/Zurück laufen über die Medientasten.
>
> Ist Spotify am PC zu, startet PC-Deck es automatisch, sobald du eine Playlist wählst.

## 5. Chrome-Erweiterung installieren (einmalig, 1 Minute)

Webseiten öffnen funktioniert auch ohne Erweiterung. Für die **Video-Steuerung** und das sichere
**„immer neuer Tab statt neues Fenster“** brauchst du die kleine Erweiterung aus diesem Repo:

1. In Chrome die Adresse `chrome://extensions` öffnen.
2. Oben rechts **Entwicklermodus** einschalten.
3. **„Entpackte Erweiterung laden“** → den Ordner **`chrome-extension`** aus diesem Repo auswählen.
4. Fertig. In der App auf der Seite **Chrome** steht jetzt „Verbunden“.

So funktioniert es:
- **Webseite öffnen:** Ist Chrome offen, kommt ein **neuer Tab** ins zuletzt benutzte Fenster.
  Nur wenn Chrome ganz zu ist, öffnet sich ein Fenster. Du kannst eine Adresse (`youtube.com`)
  oder einfach Suchbegriffe eintippen (dann wird gegoogelt).
- **Video steuern:** Gesteuert wird das Video, das gerade Ton macht (sonst das im aktiven Tab).
  Das klappt auf YouTube, Twitch, Netflix und fast jeder Seite mit Video.
  „Nächstes Video“ geht auf YouTube und bei Netflix-Serien.

Die Erweiterung verbindet sich nur mit PC-Deck auf deinem eigenen PC (`127.0.0.1`) und sendet nichts ins Internet.

Favoriten änderst du in `config.json` unter `"chrome"` → `"favorites"`:
```json
{ "label": "YouTube", "url": "https://www.youtube.com", "color": "#ff0033" }
```

---

## Eigene Aktions-Buttons (`config.json`)

```json
"buttons": [
  { "label": "Play / Pause", "icon": "⏯️", "action": "hotkey",  "keys": "play/pause media" },
  { "label": "OBS Szene 1",  "icon": "🎬", "action": "hotkey",  "keys": "ctrl+alt+f1" },
  { "label": "Steam",        "icon": "🎮", "action": "launch",  "target": "C:\\Program Files (x86)\\Steam\\steam.exe" },
  { "label": "Sperren",      "icon": "🔒", "action": "command", "target": "rundll32.exe user32.dll,LockWorkStation" }
]
```

`action`: `hotkey` (Tastenkürzel), `launch` (Programm/Datei/App-Link), `url` (Webseite), `command` (Konsolenbefehl).
Nach dem Ändern `start.bat` neu starten.

## Probleme?

| Problem | Lösung |
|---------|--------|
| iPhone verbindet nicht | Gleiches WLAN? Firewall-Abfrage zugelassen? Im Gast-WLAN geht es nicht. Sonst die Ersatz-Adresse mit IP aus dem Fenster nutzen. |
| Discord reagiert nicht | Tastenkürzel in Discord eingetragen? Discord als Admin → PC-Deck auch als Admin starten. |
| Spotify: „INVALID_CLIENT“ / Redirect-Fehler | Redirect URI im Spotify-Dashboard exakt `http://127.0.0.1:8765/spotify/callback`? |
| Spotify startet nichts | Ohne Premium öffnet sich die Playlist nur in der Spotify-App (siehe oben). |
| Chrome: „Erweiterung fehlt“ | Erweiterung geladen (Schritt 5)? PC-Deck läuft? Chrome einmal neu starten. |
| Kein Video erkannt | Video einmal am PC anklicken/starten, dann erscheint es in der App. |

## Dateien

```
pc-app/
  start.bat            Startet PC-Deck (installiert beim 1. Mal alles)
  server.py            Server, Login, Befehle
  controls.py          Lautstärke, Mikro, Tastenkürzel, Programme
  spotify.py           Spotify-Anbindung
  chrome.py            Chrome öffnen (ohne Erweiterung)
  web/                 Die iPhone-App (HTML/CSS/JS)
  config.json          Deine Einstellungen (wird beim 1. Start erstellt)
chrome-extension/      Chrome-Erweiterung für Tabs & Video-Steuerung
```
