# Jarvis — Nächste Schritte am PC

Diese Anleitung bringt alles auf deinen PC, was unterwegs gebaut wurde:
**Command Center** (neues Dashboard mit Globus und Fokus-Modus), **YouTube-Videos**, **Postfach aufräumen**, **TikTok-Statistiken** und die **Gym-App**.

Hak die Kästchen der Reihe nach ab. Pflicht sind nur die Schritte 1 bis 4, der Rest ist optional.

> **Für Claude Code in VS Code:** Diese Datei beschreibt den Stand vom 06.10.2026. Alles liegt auf dem Branch `feature/projekt-zentrale`. Wenn der Nutzer bei einem Schritt hängt, hilf ihm genau bei diesem Schritt. Schreib keine Schlüssel oder Passwörter in Dateien außer `config.json`.

---

## Schritt 1 — Neuen Stand holen (2 Minuten)

- [ ] VS Code öffnen, deinen Jarvis-Ordner öffnen.
- [ ] Im Claude-Chat in VS Code schreiben:
  > Hol den Branch `feature/projekt-zentrale` von GitHub und wechsle darauf.

  Oder selbst im Terminal (Menü **Terminal → Neues Terminal**):
  ```
  git fetch origin
  git checkout feature/projekt-zentrale
  git pull
  ```
- [ ] **Falls ein Konflikt in `server.py` gemeldet wird:** Das liegt meist daran, dass dort dein Name eingetragen ist. Schreib Claude:
  > Löse den Konflikt in server.py. Behalte alle neuen Funktionen und meinen Namen und meine Ansprache im Systemprompt.

**Fertig, wenn:** Im Ordner gibt es die Dateien `youtube_tools.py`, `mail_tools.py`, `tiktok_tools.py` und den Ordner `frontend/vendor`.

---

## Schritt 2 — Pakete prüfen (1 Minute)

- [ ] Im Terminal:
  ```
  pip install -r requirements.txt
  ```
  Es kommen keine neuen Pakete dazu, das ist nur zur Sicherheit.

---

## Schritt 3 — YouTube-Schlüssel anlegen (5 Minuten, kostenlos)

Ohne Schlüssel zoomt das Dashboard trotzdem, zeigt aber keine Videos.

- [ ] **console.cloud.google.com** öffnen und mit deinem Google-Konto anmelden.
- [ ] Oben auf die Projektauswahl → **Neues Projekt** → Name `Jarvis` → **Erstellen**.
- [ ] Links im Menü: **APIs & Dienste → Bibliothek** → nach **YouTube Data API v3** suchen → **Aktivieren**.
- [ ] **APIs & Dienste → Anmeldedaten** → **Anmeldedaten erstellen → API-Schlüssel** → Schlüssel kopieren.
- [ ] In `config.json` (im Jarvis-Ordner) diese Zeile ergänzen. Auf das Komma am Ende der Zeile davor achten:
  ```json
  "youtube_api_key": "HIER-DEIN-SCHLÜSSEL"
  ```
- [ ] Datei speichern.

**Kosten:** keine. Pro Tag sind etwa 100 Suchen frei. Darüber wird nichts berechnet, es kommen nur keine neuen Videos mehr.

---

## Schritt 4 — Starten und testen (5 Minuten)

- [ ] Jarvis wie immer starten (Doppelklatschen oder `python server.py`).
- [ ] Auf dem mittleren Monitor öffnet sich das **Command Center**. Mit **F** schaltest du auf Vollbild.
- [ ] **Test Dashboard:** Siehst du Globus, Systemstatus, Projekt-Reaktor, Projekte, Finanzen, Fristen und Kennzahlen?
- [ ] **Test Fokus-Modus:** Frag Jarvis:
  > Wie entstehen Polarlichter?

  Erwartet: Das Dashboard zoomt in den Globus nach Island und zeigt Frage, Antwort und 3 YouTube-Videos. Nach 45 Sekunden oder mit **Esc** geht es zurück.
- [ ] **Test ohne Sprechen** (im Terminal, Jarvis muss laufen):
  ```
  Invoke-RestMethod -Method Post "http://localhost:8340/api/focus/demo?topic=Polarlichter%20Island&place=Iceland"
  ```

**Fertig, wenn:** Der Zoom läuft und die Videos erscheinen. Wenn nicht, schau unten bei *Wenn etwas nicht klappt*.

---

## Schritt 5 (optional) — Postfach aufräumen lassen (5 Minuten)

Jarvis verschiebt Spam und alte Newsletter in den Papierkorb. Er fragt vorher nach, löscht nie endgültig und lässt Mails mit Fähnchen in Ruhe.

- [ ] Yahoo im Browser → Profilbild → **Kontoinfo** → **Kontosicherheit** → **App-Passwort erstellen** → Name `Jarvis` → Passwort kopieren.
- [ ] Im Terminal:
  ```
  python scripts\mail-setup.py
  ```
  Adresse und App-Passwort eingeben (dein normales Yahoo-Passwort funktioniert hier nicht). Das Skript zeigt, was aufgeräumt werden könnte, und löscht dabei noch nichts.
- [ ] Jarvis neu starten und sagen:
  > Jarvis, räum mein Postfach auf.

  Er nennt die Zahlen und fragt nach. Mit „Ja“ wird aufgeräumt.

---

## Schritt 6 (optional) — TikTok verbinden (15 Minuten)

- [ ] **developers.tiktok.com** → mit TikTok anmelden → **Manage apps** → neue App `Jarvis`.
- [ ] Produkt **Login Kit** hinzufügen, Berechtigungen aktivieren: `user.info.basic`, `user.info.profile`, `user.info.stats`, `video.list`.
- [ ] Als **Redirect URI** eintragen: `https://cris20069.github.io/Jarvis-gym/`
- [ ] **Sandbox** anlegen und dein TikTok-Konto als **Target User** hinzufügen.
- [ ] **Client Key** und **Client Secret** kopieren.
- [ ] Im Terminal:
  ```
  python scripts\tiktok-setup.py
  ```
  Key und Secret eingeben. Im Browser bei TikTok **Erlauben** tippen, dann die komplette Adresse aus der Adresszeile ins Terminal einfügen.
- [ ] Jarvis neu starten und sagen:
  > Was gibt es Neues auf TikTok?

Die Menünamen bei TikTok können leicht anders heißen. Bei Problemen einen Screenshot an Claude schicken.

---

## Schritt 7 — Gym-App (nichts zu tun)

Sie liegt auf deinem Handy und aktualisiert sich selbst. Adresse, falls du sie neu installieren musst:
**https://cris20069.github.io/Jarvis-gym/** → in Safari öffnen → Teilen → **Zum Home-Bildschirm**.

---

## Wenn etwas nicht klappt

| Problem | Lösung |
|---|---|
| `git pull` meldet einen Konflikt | Siehe Schritt 1: Claude den Konflikt lösen lassen, Namen behalten |
| Dashboard sieht noch alt aus | Im Dashboard-Fenster **Strg + F5** drücken (Neu laden ohne Cache) |
| Zoom klappt, aber keine Videos | Steht `youtube_api_key` in `config.json`? Server danach neu gestartet? Im Dashboard unter *Systemstatus → YouTube* muss **ON** stehen |
| Im Fokus steht „YouTube nicht erreichbar“ | Schlüssel falsch kopiert oder die YouTube Data API v3 ist im Google-Projekt nicht aktiviert |
| Jarvis antwortet, aber das Dashboard zoomt nicht | Das passiert nur bei Wissensfragen, nicht bei Smalltalk oder Befehlen. Mit dem Test-Befehl aus Schritt 4 prüfen, ob das Dashboard reagiert |
| `config.json` lässt sich nicht laden | Meist fehlt ein Komma oder steht eins zu viel. Datei Claude zeigen: „Prüf meine config.json auf Fehler“ (vorher Schlüssel schwärzen) |

---

## Offene Ideen für später

- **Kino-Modus:** Wenn Projektor (Epson EH-TW7100) und Leinwand (Elite Screens SK100XHW-E12) da sind, schaltet „Jarvis, Kino-Modus“ den Projektor ein, fährt die Leinwand runter und legt das Dashboard auf die Wand.
- **Ohne YouTube-Schlüssel:** ein Button „Auf YouTube ansehen“ statt der Vorschaubilder.
- **Pull Request nach `main`:** alles von heute sauber in den Hauptstand übernehmen.
- **TikTok-Videos hochladen:** erst nach Prüfung der TikTok-App durch TikTok möglich.
