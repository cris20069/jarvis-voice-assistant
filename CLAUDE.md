# CLAUDE.md

Dieses Workspace ist **Jarvis** — ein persoenlicher KI-Assistent mit Sprachsteuerung, Browser-Kontrolle und Doppelklatschen-Trigger.

---

## Fuer Claude Code: Setup-Modus

Wenn der Nutzer nach dem Setup fragt oder "Richte Jarvis ein" sagt, folge den Anweisungen in `SETUP.md`. Frage den Nutzer nach seinem Namen, seiner Taetigkeit, und wie er angesprochen werden moechte — diese Infos muessen in den Systemprompt in `server.py` eingetragen werden (ersetze die aktuellen Platzhalter "Julian", "KI-Berater und Automatisierungsexperte", "Sir").

**WICHTIG — Pruefe und installiere zuerst alle Voraussetzungen:**

1. **Python**: Pruefe ob Python 3.10+ installiert ist (`python --version`). Falls nicht, installiere es:
   - Windows: `winget install Python.Python.3.12`
   - Warte bis die Installation abgeschlossen ist und pruefe erneut

2. **Google Chrome**: Pruefe ob Chrome installiert ist. Falls nicht, weise den Nutzer an Chrome von https://google.com/chrome zu installieren.

3. **pip Dependencies**: `pip install -r requirements.txt`

4. **Playwright Browser**: `playwright install chromium`

Erst NACHDEM alle Voraussetzungen installiert sind, fahre mit dem Setup in `SETUP.md` fort (API Keys abfragen, config.json erstellen, etc.).

---

## Aktuelles Projekt: Mark I (Schreibtisch-Bot)

Der Nutzer (Christian) baut einen kleinen Iron-Man-Roboter als Koerper fuer Jarvis:
ESP32 + rundes Display als Auge + LED-Ring + 2 Servos, per WLAN mit `server.py` verbunden.
**Lies zuerst `mark1/PLAN.md`** — dort stehen Teile, Pinbelegung, Architektur,
Bau-Stufen, aktueller Stand und die Entscheidungen des Nutzers.

Christian ist Einsteiger: erklaere Schritt fuer Schritt, auf Deutsch, und baue in
Stufen, die jeweils fuer sich funktionieren. Aktualisiere den Abschnitt
"Aktueller Stand" in `mark1/PLAN.md`, wenn eine Stufe fertig ist.

---

## Workspace Structure

```
.
├── CLAUDE.md              # This file
├── SETUP.md               # Setup-Anleitung fuer Claude Code
├── config.json            # Persoenliche Config (gitignored)
├── config.example.json    # Template mit Platzhaltern
├── requirements.txt       # Python Dependencies
├── server.py              # FastAPI Backend (Claude Haiku + ElevenLabs TTS)
├── browser_tools.py       # Playwright Browser-Steuerung
├── screen_capture.py      # Screenshot + Claude Vision
├── frontend/
│   ├── index.html         # Jarvis Web-UI
│   ├── main.js            # Speech Recognition + WebSocket + Audio
│   └── style.css          # Dark Theme mit Orb-Animation
├── scripts/
│   ├── clap-trigger.py    # Doppelklatschen-Erkennung
│   └── launch-session.ps1 # Startet alle Apps + Jarvis
└── mark1/
    └── PLAN.md            # Schreibtisch-Bot: Plan, Teile, Pins, Stand
```
