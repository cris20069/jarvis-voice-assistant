# Jarvis Setup Guide

Dein persoenlicher KI-Assistent — inspiriert von Iron Mans Jarvis.

**Was du bekommst:**
- Zweimal klatschen → dein komplettes Arbeits-Setup startet
- Jarvis begruesst dich mit Wetter und deinen Aufgaben
- Du sprichst frei mit Jarvis — er antwortet per Stimme
- Jarvis kann deinen Browser steuern (suchen, Seiten oeffnen)
- Jarvis kann deinen Bildschirm sehen und beschreiben

---

## Voraussetzungen

- **Windows 10/11**
- **Google Chrome** (fuer Spracheingabe + Jarvis UI)
- **Claude Code** installiert

Python, alle Dependencies und Browser-Treiber werden automatisch von Claude Code installiert — du musst nichts manuell einrichten.

---

## Setup starten

Oeffne diesen Ordner in VS Code, starte Claude Code, und sag:

> Richte Jarvis fuer mich ein.

Claude Code fragt dich dann nach:

1. **Dein Name** und wie du angesprochen werden willst (z.B. "Sir")
2. **Anthropic API Key** — von https://console.anthropic.com (fuer Claude Haiku, das Gehirn)
3. **ElevenLabs API Key** — von https://elevenlabs.io (fuer die Stimme)
4. **Spotify-Song** — Link zum Song der beim Start spielen soll
5. **Programme** — welche Apps sollen beim Doppelklatschen starten?
6. **Website** — welche Seite soll im Browser aufgehen?
7. **Stadt fuers Wetter** — z.B. Hamburg
8. **Obsidian Vault** — optional, welcher Ordner soll Jarvis kennen?

---

## Was Claude Code fuer dich einrichtet

### 1. Voraussetzungen installieren
Claude Code prueft und installiert automatisch:
- **Python 3.10+** (falls nicht vorhanden, via `winget install Python.Python.3.12`)
- **Alle Python-Pakete** (`pip install -r requirements.txt`)
- **Playwright Chromium** (`playwright install chromium`)

### 2. config.json erstellen
Claude Code erstellt `config.json` aus `config.example.json` mit deinen echten Daten:
```json
{
  "anthropic_api_key": "sk-ant-...",
  "elevenlabs_api_key": "sk_...",
  "elevenlabs_voice_id": "VOICE_ID",
  "user_name": "Dein Name",
  "user_address": "Sir",
  "city": "Hamburg",
  "workspace_path": "C:\\pfad\\zum\\jarvis_template",
  "spotify_track": "spotify:track:DEIN_TRACK_ID",
  "browser_url": "https://deine-website.com",
  "obsidian_inbox_path": "C:\\pfad\\zum\\obsidian\\inbox",
  "apps": ["obsidian://open"]
}
```

### 3. ElevenLabs Stimme
Eine deutsche Stimme auswaehlen und die Voice ID in die Config eintragen. Empfehlung: **Felix Serenitas** (Starter Plan noetig) oder eine der Standard-Stimmen (Free Plan).

### 4. Systemprompt
Der Systemprompt wird in `server.py` automatisch aus der Config generiert. Er enthaelt:
- Jarvis-Persoenlichkeit (trocken, sarkastisch, britisch-hoeflich)
- Siezen mit gewaehlter Anrede
- Wetter- und Aufgaben-Integration
- Browser-Steuerung via Action-Tags
- Screen-Capture-Faehigkeit

---

## Architektur

```
Mikrofon (Chrome) → Web Speech API → WebSocket → FastAPI Server
                                                      ↓
                                                Claude Haiku (denkt)
                                                      ↓
                                    ┌─────────────────┼──────────────────┐
                                    ↓                 ↓                  ↓
                            ElevenLabs TTS     Playwright Browser   Screen Capture
                            (spricht)          (sucht/oeffnet)     (sieht Bildschirm)
                                    ↓
                            Audio → Browser Speaker
```

---

## Starten

### Jarvis manuell starten
```
python server.py
```
Dann http://localhost:8340 in Chrome oeffnen.

### Alles per Doppelklatschen starten
```
python scripts\clap-trigger.py
```
Zweimal klatschen → Spotify, VS Code, Obsidian, Chrome mit Jarvis starten automatisch.

### Clap Trigger beim Windows-Start
1. `Win + R` → `taskschd.msc`
2. Aufgabe erstellen → Trigger: "Bei Anmeldung"
3. Aktion: `powershell` mit Argument:
   `-ExecutionPolicy Bypass -WindowStyle Hidden -Command "python C:\DEIN\PFAD\scripts\clap-trigger.py"`

---

## Dashboard und mehrere Monitore

`http://localhost:8340/dashboard` zeigt alles Wichtige auf einen Blick: Uhr, Wetter, CPU/RAM/Festplatte, Projekte mit Fortschritt und Fristen, Obsidian-Aufgaben, das Jarvis-Log und ein Laufband mit Meldungen. Mit **F** schaltest du den Vollbildmodus um.

Beim Doppelklatschen laeuft das so ab (Monitore von links nach rechts gezaehlt, 0 = ganz links):

1. VS Code, Obsidian, Chrome (Jarvis) und Spotify erscheinen als Viertel auf dem **mittleren** Monitor.
2. Jarvis begruesst dich.
3. Sobald er fertig gesprochen hat, **wandern die 4 Fenster auf den linken Monitor**.
4. In der Mitte oeffnet sich das **Dashboard** als Vollbild-Fenster.

| Einstellung in `config.json` | Bedeutung | Standard |
|---|---|---|
| `monitor_dashboard` | Monitor, auf dem alles startet und das Dashboard bleibt | `1` (Mitte) |
| `monitor_apps` | Monitor, auf den die 4 Fenster nach der Begruessung wandern | `0` (links) |

Mit zwei Monitoren landet das Dashboard rechts. Mit nur einem Monitor bleibt alles wie vorher und das Dashboard wird nicht gestartet. Falls die Reihenfolge nicht stimmt (Windows nummeriert nach der Anordnung in den Anzeigeeinstellungen), tausche die Zahlen.

Technisch: Der Browser meldet das Ende der Begruessung an `/api/greeting-done`, das Startskript wartet darauf (hoechstens 60 Sekunden) und schiebt dann die Fenster.

Fuer die Systemwerte wird `psutil` gebraucht: `pip install -r requirements.txt`.

---

## Finanz-Cockpit

`http://localhost:8340/finanzen` zeigt Einnahmen, Ausgaben, Saldo und Sparquote pro Monat, den Verlauf der letzten 6 Monate, Ausgaben nach Kategorie, offene und ueberfaellige Rechnungen, Abos mit Fixkosten und ein Sparziel.

- **+ Buchung**, **+ Rechnung**, **+ Abo**: Eintraege anlegen. Betraege im deutschen Format, z.B. `1.234,56`.
- **Bezahlt** bei einer Rechnung bucht die Einnahme automatisch.
- Pfeiltasten wechseln den Monat, `N` legt eine Buchung an.
- Die Daten liegen in `finance.json` auf deinem PC und sind per `.gitignore` aus dem Repo ausgeschlossen.
- Ohne Daten kannst du mit **Beispieldaten laden** das Cockpit ausprobieren. Beispiele sind markiert und lassen sich mit einem Klick entfernen.

---

## Nachrichten aufs Handy (Telegram, kostenlos)

Jarvis kann dir per Telegram schreiben — als Text und als Sprachnachricht mit seiner Stimme.

1. Telegram installieren, **@BotFather** suchen, `/newbot` senden, Namen vergeben → Token kopieren
2. `python scripts\telegram-setup.py` ausfuehren, Token einfuegen
3. Dem eigenen Bot in Telegram `/start` schicken → das Skript traegt alles in `config.json` ein
4. `server.py` neu starten

| Einstellung in `config.json` | Bedeutung |
|---|---|
| `telegram_briefing_time` | Uhrzeit fuers Morgen-Briefing (z.B. `"07:30"`, `""` = aus) |
| `telegram_deadline_time` | Uhrzeit fuer den Deadline-Alarm (Projekte heute/morgen faellig oder ueberfaellig) |
| `telegram_voice` | `true` = zusaetzlich Sprachnachricht (verbraucht ElevenLabs-Zeichen) |

Testen ohne zu warten (Server muss laufen):
```
curl -X POST "http://localhost:8340/api/telegram/test?kind=briefing"
```
`kind` = `hallo`, `briefing` oder `deadlines`.

Geplante Nachrichten kommen nur, wenn der Server laeuft — bis zu 60 Minuten nach der eingestellten Uhrzeit wird nachgeholt, hoechstens einmal pro Tag.

---

## Postfach aufraeumen (Spam und alte Newsletter)

Jarvis kann deinen Spam-Ordner leeren und alte Newsletter aus dem Posteingang raeumen. Alles landet im **Papierkorb** (nichts wird endgueltig geloescht), Mails mit **Faehnchen** bleiben immer liegen, und Jarvis fragt vorher nach.

1. Yahoo: Kontoinfo → **Kontosicherheit** → **App-Passwort erstellen** (Name z.B. "Jarvis"). Dein normales Passwort funktioniert hier nicht.
2. `python scripts\mail-setup.py` ausfuehren, Adresse und App-Passwort eingeben. Das Skript testet die Verbindung und zeigt, was aufgeraeumt werden koennte.
3. `server.py` neu starten.

Dann: **"Jarvis, raeum mein Postfach auf"** → Jarvis sagt, wie viel Spam und Newsletter er gefunden hat → **"Ja, mach"** → alles im Papierkorb.
Ohne Sprache: `python scripts\mail-cleanup.py` (zeigt erst alles an, verschiebt erst nach `j`).

| Einstellung in `config.json` | Bedeutung |
|---|---|
| `mail_newsletter_days` | Newsletter (Mails mit Abmelde-Link) aelter als so viele Tage werden mit aufgeraeumt, `0` = nur Spam |
| `mail_imap_host` | `imap.mail.yahoo.com` (Gmail: `imap.gmail.com`, GMX: `imap.gmx.net`, web.de: `imap.web.de`) |

Das App-Passwort steht nur in `config.json` auf deinem PC (nicht auf GitHub) und laesst sich bei Yahoo jederzeit widerrufen.

---

## Was Jarvis kann

- **"Wie ist das Wetter?"** → kennt das aktuelle Wetter
- **"Such nach MiroFish"** → oeffnet Browser, sucht, liest Ergebnisse
- **"Oeffne skool.com"** → oeffnet die Seite im Browser
- **"Was siehst du auf meinem Bildschirm?"** → macht Screenshot, beschreibt was er sieht
- **"Schick mir das aufs Handy"** → Jarvis schreibt dir per Telegram
- **"Raeum mein Postfach auf"** → Jarvis prueft Spam und alte Newsletter und verschiebt sie nach deinem OK in den Papierkorb
- **Jede Frage** → antwortet im Jarvis-Stil mit Stimme

---

## Fehlerbehebung

| Problem | Loesung |
|---|---|
| Jarvis spricht nicht | Pruefen ob Server laeuft (`python server.py`) und Chrome offen ist |
| "Verbindung verloren" | Alter Server-Prozess laeuft noch → `taskkill /f /im python.exe` und neu starten |
| Klatschen wird nicht erkannt | Threshold in `clap-trigger.py` anpassen |
| Browser-Suche geht nicht | `playwright install chromium` ausfuehren |
| Kein Audio im Browser | Einmal auf die Seite klicken (Chrome Autoplay-Policy) |

---

## Fuer Claude Code: Setup-Anweisungen

Wenn ein Nutzer "Richte Jarvis ein" sagt, fuehre folgende Schritte aus:

**Schritt 0 — Voraussetzungen pruefen und installieren:**
- Pruefe ob Python 3.10+ installiert ist: `python --version`
- Falls nicht: `winget install Python.Python.3.12` — warte bis fertig, pruefe erneut
- Pruefe ob Google Chrome installiert ist. Falls nicht, weise den Nutzer an Chrome zu installieren
- Installiere Python-Pakete: `pip install -r requirements.txt`
- Installiere Playwright Browser: `playwright install chromium`

**Schritt 1 — Nutzerdaten abfragen:**
Frage nach:
- Name (z.B. "Julian")
- Taetigkeit/Rolle (z.B. "KI-Berater und Automatisierungsexperte") — wird in den Systemprompt eingebaut
- Gewuenschte Anrede (z.B. "Sir", "Chef", oder einfach Vorname)
- Anthropic API Key (von https://console.anthropic.com)
- ElevenLabs API Key (von https://elevenlabs.io)
- Spotify-Song (Link zum Song der beim Start spielen soll)
- Programme die beim Doppelklatschen starten sollen (z.B. Obsidian, Notion)
- Website die im Browser aufgehen soll
- Stadt fuers Wetter (z.B. Hamburg)
- Obsidian Vault Pfad (optional)

**Schritt 2 — Config erstellen:**
Erstelle `config.json` aus `config.example.json` mit den Nutzerdaten. Setze den `workspace_path` auf den aktuellen Ordnerpfad.

**Schritt 3 — ElevenLabs Stimme einrichten:**
- Liste verfuegbare Stimmen via ElevenLabs API
- Empfehle eine deutsche Stimme
- Trage die Voice ID in die Config ein

**Schritt 4 — Systemprompt anpassen:**
Oeffne `server.py` und finde die Funktion `build_system_prompt()`. Dort steht der komplette Systemprompt als f-String. Ersetze ALLE Vorkommen der folgenden Werte im gesamten Prompt-Text:
- Jedes "Julian" → Name des Nutzers (kommt mehrfach vor im Prompt!)
- "KI-Berater und Automatisierungsexperte" → Taetigkeit/Rolle des Nutzers
- Jedes "Sir" als Anrede → gewuenschte Anrede des Nutzers
- "Hamburg" → Stadt des Nutzers

Ausserdem oben in `server.py` bei den Config-Defaults:
- `USER_NAME = config.get("user_name", "Julian")` → Default-Name anpassen
- `CITY = config.get("city", "Hamburg")` → Default-Stadt anpassen

WICHTIG: Pruefe den Prompt sorgfaeltig — "Julian" und "Sir" kommen an mehreren Stellen vor. Alle muessen ersetzt werden.

**Schritt 5 — Testen:**
- Starte den Server: `python server.py`
- Oeffne http://localhost:8340 in Chrome
- Pruefe ob Jarvis spricht und antwortet

**Schritt 6 — Optional: Autostart einrichten (Task Scheduler)**

---

## Credits

Template von Julian — [Skool Community](https://skool.com/ki-automatisierung)
