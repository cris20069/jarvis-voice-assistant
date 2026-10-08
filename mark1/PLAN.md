# Mark I — Schreibtisch-Bot fuer Jarvis

Projektplan und Kontext fuer Claude Code. Visueller Bauplan (Teile-Links, Vorschau):
https://claude.ai/artifact/PJHko8SHLPQfUVcX3Bo9k5

## Worum es geht

Ein kleiner Iron-Man-Roboter auf Christians Schreibtisch. **Jarvis ist das Gehirn**
(`server.py` auf dem Windows-11-PC: Claude + ElevenLabs), der Bot ist der **Koerper**:

- Rundes Farb-Display als Arc-Reactor-Auge, darum ein LED-Ring als Glow
- Kopf auf Pan-Tilt-Halterung mit 2 Servos (drehen + nicken)
- Verbindung per WLAN zum Jarvis-Server
- Stimme kommt vorerst weiter aus den PC-Lautsprechern

## Entscheidungen des Nutzers

| Thema | Entscheidung |
|---|---|
| Look | Cool, Iron-Man-Stil: Rot-Gold, blau leuchtendes Auge |
| 3D-Drucker | Nein — Gehaeuse aus EVA-Schaum (5 mm), Plasti Dip, Spruehlack |
| Budget | Nur das Noetigste, Grundbau ca. 35–45 EUR |
| Standort | Schreibtisch, Strom per USB (kein Akku) |
| Loeten | Nicht im Grundbau — alles auf Breadboard gesteckt |
| Erfahrung | Einsteiger. Schritt fuer Schritt und auf Deutsch erklaeren |
| Name | "Mark I" ist ein Platzhalter, Nutzer darf umbenennen |

## Hardware (Grundbau)

| Teil | Typ |
|---|---|
| Mikrocontroller | ESP32 Dev Kit C V4 (ESP32-WROOM-32), USB-C |
| Auge | GC9A01 1,28" rundes TFT, 240x240, SPI |
| Glow | WS2812B LED-Ring, 12 LEDs |
| Hals | Pan-Tilt-Halterung + 2x SG90 Servo |
| Sonstiges | Breadboard 830, Jumper-Kabel (m-m, m-f), Elko 470 uF / 16 V, USB-Datenkabel |

### Pinbelegung

| Teil | Anschluss | ESP32 |
|---|---|---|
| Display | VCC / GND | 3V3 / GND |
| Display | SCL (CLK) | GPIO 18 |
| Display | SDA (MOSI) | GPIO 23 |
| Display | CS | GPIO 5 |
| Display | DC | GPIO 16 |
| Display | RST | GPIO 17 |
| LED-Ring | 5V / GND | VIN / GND |
| LED-Ring | DIN | GPIO 13 |
| Servo Pan (drehen) | Signal | GPIO 25 |
| Servo Tilt (nicken) | Signal | GPIO 26 |
| Servos | + / − | VIN / GND (ueber Breadboard) |
| Elko 470 uF | + / − | VIN / GND, nah an den Servos |

Hinweis: Display-Beschriftungen variieren je nach Haendler — vor dem Verkabeln mit
den echten Teilen (Foto) abgleichen.

## Software-Architektur

```
Chrome (frontend/main.js)  --ws /ws-->  server.py  --ws /ws/bot-->  ESP32 (mark1/firmware)
        setOrbState(...)                 broadcastet Zustand          Auge + LEDs + Servos
```

- **Firmware**: Arduino-Framework (Arduino IDE 2), Ordner `mark1/firmware/`.
  Bibliotheken: TFT_eSPI oder Arduino_GFX (GC9A01), Adafruit NeoPixel, ESP32Servo,
  WebSockets (Links2004/arduinoWebSockets), ArduinoJson.
- **WLAN-Daten und PC-IP** in `mark1/firmware/secrets.h` (gitignored), Vorlage
  `secrets.example.h`.
- **Server**: neuer WebSocket-Endpoint `/ws/bot` in `server.py`. Der Bot verbindet sich
  als Client; der Server schickt ihm Zustaende als JSON:
  `{"type": "state", "state": "idle|listening|thinking|speaking|sarcasm|hello|yes|no"}`
- **Zustandsquelle**: `frontend/main.js` kennt die Orb-Zustaende schon
  (`setOrbState('idle' | 'listening' | 'thinking' | 'speaking')`). Diese an den Server
  melden (z. B. `{"type": "orb", "state": ...}` ueber `/ws`), Server leitet an alle Bots weiter.
- **Stimmung/Gesten**: spaeter optional ueber ein Tag wie `[MOOD:sarcasm]` im
  Systemprompt — still ausgefuehrt, nicht vorgelesen (wie die bestehenden `[ACTION:...]`).

### Zustaende -> Verhalten

| Zustand | Auge / LED-Ring | Kopf |
|---|---|---|
| idle | Blau, ruhig pulsierend | Schaut ab und zu herum |
| listening | Blau, heller | Schaut nach vorne |
| thinking | Weiss, ein Licht kreist | Leicht geneigt |
| speaking | Hellblau, flackert im Takt | Kleine Bewegungen |
| sarcasm | Rot | Kopf zur Seite geneigt |
| hello | Gold | Richtet sich auf |
| yes / no | Gruen / Rot kurz | Nicken / Kopfschuetteln |

## Bau-Stufen

1. **Das Auge erwacht** — Display + LED-Ring, Animation laeuft standalone (kein WLAN).
2. **Verbindung zu Jarvis** — WLAN, `/ws/bot`, Zustaende aus dem Frontend.
3. **Der Kopf lebt** — Servos, Gesten (nicken, schuetteln, umschauen).
4. **Die Ruestung** — Gehaeuse aus EVA-Schaum, Masse passend zur Halterung.

Aktueller Stand: Stufe 0 — Teile werden bestellt. Noch kein Firmware-Code.

## Upgrades (spaeter)

Lautsprecher (MAX98357A), Mikrofon (INMP441), Gesichtsverfolgung per PC-Webcam,
Touch-Sensor (TTP223), Abstandssensor (VL53L0X), Arc Reactor im Sockel (2. LED-Ring),
Status-OLED, Fahrgestell.
