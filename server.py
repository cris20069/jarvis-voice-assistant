"""
Jarvis V2 — Voice AI Server
FastAPI backend: receives speech text, thinks with Claude Haiku,
speaks with ElevenLabs, controls browser with Playwright.
"""

import asyncio
import base64
import json
import os
import re
import time
from datetime import date, datetime, timedelta

import anthropic
import httpx
from fastapi import FastAPI, HTTPException, Request, WebSocket, WebSocketDisconnect
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

# Load config
CONFIG_PATH = os.path.join(os.path.dirname(__file__), "config.json")
with open(CONFIG_PATH, "r") as f:
    config = json.load(f)

ANTHROPIC_API_KEY = config["anthropic_api_key"]
ELEVENLABS_API_KEY = config["elevenlabs_api_key"]
ELEVENLABS_VOICE_ID = config.get("elevenlabs_voice_id", "rDmv3mOhK6TnhYWckFaD")
USER_NAME = config.get("user_name", "Julian")
USER_ADDRESS = config.get("user_address", "Sir")
CITY = config.get("city", "Hamburg")
TASKS_FILE = config.get("obsidian_inbox_path", "")
TELEGRAM_BRIEFING_TIME = config.get("telegram_briefing_time", "07:30")
TELEGRAM_DEADLINE_TIME = config.get("telegram_deadline_time", "18:00")
TELEGRAM_VOICE = config.get("telegram_voice", True)

ai = anthropic.AsyncAnthropic(api_key=ANTHROPIC_API_KEY)
http = httpx.AsyncClient(timeout=30)

app = FastAPI()

import browser_tools
import screen_capture
from telegram_notify import TelegramNotifier

telegram = TelegramNotifier(config.get("telegram_bot_token", ""), config.get("telegram_chat_id", ""))


def get_weather_sync():
    """Fetch raw weather data at startup."""
    import urllib.request
    try:
        req = urllib.request.Request(f"https://wttr.in/{CITY}?format=j1", headers={"User-Agent": "curl"})
        resp = urllib.request.urlopen(req, timeout=5)
        data = json.loads(resp.read())
        c = data["current_condition"][0]
        return {
            "temp": c["temp_C"],
            "feels_like": c["FeelsLikeC"],
            "description": c["weatherDesc"][0]["value"],
            "humidity": c["humidity"],
            "wind_kmh": c["windspeedKmph"],
        }
    except:
        return None


def get_tasks_sync():
    """Read open tasks from Obsidian (sync)."""
    if not TASKS_FILE:
        return []
    try:
        tasks_path = os.path.join(TASKS_FILE, "Tasks.md")
        with open(tasks_path, "r", encoding="utf-8") as f:
            lines = f.readlines()
        return [l.strip().replace("- [ ]", "").strip() for l in lines if l.strip().startswith("- [ ]")]
    except:
        return []


def refresh_data():
    """Refresh weather and tasks."""
    global WEATHER_INFO, TASKS_INFO
    WEATHER_INFO = get_weather_sync()
    TASKS_INFO = get_tasks_sync()
    print(f"[jarvis] Wetter: {WEATHER_INFO}", flush=True)
    print(f"[jarvis] Tasks: {len(TASKS_INFO)} geladen", flush=True)

WEATHER_INFO = ""
TASKS_INFO = []
refresh_data()

# Projekt-Register (frontend/projects.html)
PROJECTS_PATH = os.path.join(os.path.dirname(__file__), "projects.json")
PROJECT_ID_PATTERN = re.compile(r'^[A-Za-z0-9_-]{1,64}$')
PROJECT_STATUS_LABELS = {"idee": "Idee", "geplant": "Geplant", "arbeit": "In Arbeit", "pausiert": "Pausiert", "fertig": "Fertig"}


def load_projects() -> list:
    try:
        with open(PROJECTS_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data if isinstance(data, list) else []
    except (FileNotFoundError, json.JSONDecodeError):
        return []


def save_projects(projects: list):
    tmp = PROJECTS_PATH + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(projects, f, ensure_ascii=False, indent=2)
    os.replace(tmp, PROJECTS_PATH)


def project_progress(p: dict) -> int:
    if p.get("status") == "fertig":
        return 100
    tasks = p.get("tasks") or []
    if tasks:
        return round(sum(1 for t in tasks if t.get("done")) / len(tasks) * 100)
    return int(p.get("progress") or 0)


def project_days_left(p: dict):
    try:
        return (date.fromisoformat(p.get("deadline") or "") - date.today()).days
    except ValueError:
        return None


# Action parsing
ACTION_PATTERN = re.compile(r'\[ACTION:(\w+)\]\s*(.*?)$', re.DOTALL | re.MULTILINE)

conversations: dict[str, list] = {}

def build_system_prompt():
    weather_block = ""
    if WEATHER_INFO:
        w = WEATHER_INFO
        weather_block = f"\nWetter {CITY}: {w['temp']}°C, gefuehlt {w['feels_like']}°C, {w['description']}"

    task_block = ""
    if TASKS_INFO:
        task_block = f"\nOffene Aufgaben ({len(TASKS_INFO)}): " + ", ".join(TASKS_INFO[:5])

    project_block = ""
    open_projects = [p for p in load_projects() if p.get("status") != "fertig"]
    if open_projects:
        prio_rank = {"kritisch": 0, "hoch": 1, "mittel": 2, "niedrig": 3}
        open_projects.sort(key=lambda p: prio_rank.get(p.get("priority"), 2))
        parts = []
        for p in open_projects[:8]:
            info = f"{PROJECT_STATUS_LABELS.get(p.get('status'), p.get('status'))}, {project_progress(p)}%"
            if p.get("deadline"):
                info += f", Deadline {p['deadline']}"
            parts.append(f"{p.get('name', '?')} ({info})")
        project_block = f"\nOffene Projekte ({len(open_projects)}): " + "; ".join(parts)

    return f"""Du bist Jarvis, der KI-Assistent von Tony Stark aus Iron Man. Dein Dienstherr ist Julian, ein KI-Berater und Automatisierungsexperte. Du sprichst ausschliesslich Deutsch. Julian moechte mit "Sir" angesprochen und gesiezt werden. Nutze "Sie" als Pronomen — FALSCH: "Sir planen", RICHTIG: "Sie planen, Sir". Dein Ton ist trocken, sarkastisch und britisch-hoeflich - wie ein Butler der alles gesehen hat und trotzdem loyal bleibt. Du machst subtile, trockene Bemerkungen, bist aber niemals respektlos. Wenn Sir eine offensichtliche Frage stellt, darfst du mit elegantem Sarkasmus antworten. Du bist hochintelligent, effizient und immer einen Schritt voraus. Halte deine Antworten kurz - maximal 3 Saetze. Du kommentierst fragwuerdige Entscheidungen hoeflich aber spitz.

WICHTIG: Schreibe NIEMALS Regieanweisungen, Emotionen oder Tags in eckigen Klammern wie [sarcastic] [formal] [amused] [dry] oder aehnliches. Dein Sarkasmus muss REIN durch die Wortwahl kommen. Alles was du schreibst wird laut vorgelesen.

Du hast die volle Kontrolle ueber den Browser von Julian. Du kannst im Internet suchen, Webseiten oeffnen und den Bildschirm sehen. Wenn Sir dich bittet etwas nachzuschauen, zu recherchieren, zu googeln, eine Seite zu oeffnen, oder irgendetwas im Internet zu tun — nutze IMMER eine Aktion. Frag nicht ob du es tun sollst, tu es einfach.

AKTIONEN - Schreibe die passende Aktion ans ENDE deiner Antwort. Der Text VOR der Aktion wird vorgelesen, die Aktion selbst wird still ausgefuehrt.
[ACTION:SEARCH] suchbegriff - Internet durchsuchen und Ergebnisse zusammenfassen
[ACTION:OPEN] url - URL im Browser oeffnen
[ACTION:SCREEN] - Bildschirm ansehen und beschreiben. WICHTIG: Bei SCREEN schreibe NUR die Aktion, KEINEN Text davor. Also NUR "[ACTION:SCREEN]" und sonst nichts.
[ACTION:TELEGRAM] nachricht - Schickt Julian eine Nachricht aufs Handy (Telegram). Nutze das, wenn er sagt "schick mir das", "erinnere mich per Nachricht" oder aehnliches. Die Nachricht steht nach dem Tag, vollstaendig und verstaendlich ohne Kontext.
[ACTION:NEWS] - Aktuelle Weltnachrichten abrufen. Nutze diese Aktion wenn nach News, Nachrichten, was in der Welt passiert, aktuelle Lage oder Weltgeschehen gefragt wird. Schreibe einen kurzen Satz davor wie "Ich schaue nach den aktuellen Nachrichten."

WENN Julian "Jarvis activate" sagt:
- Begruesse ihn passend zur Tageszeit (aktuelle Zeit: {{time}}).
- Gebe eine kurze Info ueber das Wetter — Temperatur und ob Sonne/klar/bewoelkt/Regen, und wie es sich anfuehlt. Keine Luftfeuchtigkeit.
- Fasse die Aufgaben kurz als Ueberblick in einem Satz zusammen, ohne dabei jede einzelne Aufgabe einfach vorzulesen. Gebe gerne einen humorvollen Kommentar am Ende an.
- Sei kreativ bei der Begruessung.

Julian pflegt seine Projekte in der Projekt-Zentrale unter http://localhost:8340/projects. Wenn er nach seinen Projekten, Plaenen oder dem Stand der Dinge fragt, nutze die Projektdaten unten.

=== AKTUELLE DATEN ==={weather_block}{task_block}{project_block}
==="""


def get_system_prompt():
    return build_system_prompt().replace("{time}", time.strftime("%H:%M"))


def extract_action(text: str):
    match = ACTION_PATTERN.search(text)
    if match:
        clean = text[:match.start()].strip()
        return clean, {"type": match.group(1), "payload": match.group(2).strip()}
    return text, None


async def synthesize_speech(text: str) -> bytes:
    if not text.strip():
        return b""

    # Split long text into chunks at sentence boundaries to avoid ElevenLabs cutoff
    chunks = []
    if len(text) > 250:
        sentences = re.split(r'(?<=[.!?])\s+', text)
        current = ""
        for s in sentences:
            if len(current) + len(s) > 250 and current:
                chunks.append(current.strip())
                current = s
            else:
                current = (current + " " + s).strip()
        if current:
            chunks.append(current.strip())
    else:
        chunks = [text]

    audio_parts = []
    for chunk in chunks:
        url = f"https://api.elevenlabs.io/v1/text-to-speech/{ELEVENLABS_VOICE_ID}"
        try:
            resp = await http.post(url, headers={
                "xi-api-key": ELEVENLABS_API_KEY,
                "Content-Type": "application/json",
                "Accept": "audio/mpeg",
            }, json={
                "text": chunk,
                "model_id": "eleven_turbo_v2_5",
                "voice_settings": {"stability": 0.5, "similarity_boost": 0.85},
            })
            print(f"  TTS chunk status: {resp.status_code}, size: {len(resp.content)}", flush=True)
            if resp.status_code == 200:
                audio_parts.append(resp.content)
            else:
                print(f"  TTS error body: {resp.text[:200]}", flush=True)
        except Exception as e:
            print(f"  TTS EXCEPTION: {e}", flush=True)

    return b"".join(audio_parts)


async def execute_action(action: dict) -> str:
    t = action["type"]
    p = action["payload"]

    if t == "SEARCH":
        result = await browser_tools.search_and_read(p)
        if "error" not in result:
            return f"Seite: {result.get('title', '')}\nURL: {result.get('url', '')}\n\n{result.get('content', '')[:2000]}"
        return f"Suche fehlgeschlagen: {result.get('error', '')}"

    elif t == "BROWSE":
        result = await browser_tools.visit(p)
        if "error" not in result:
            return f"Seite: {result.get('title', '')}\n\n{result.get('content', '')[:2000]}"
        return f"Seite nicht erreichbar: {result.get('error', '')}"

    elif t == "OPEN":
        await browser_tools.open_url(p)
        return f"Geoeffnet: {p}"

    elif t == "SCREEN":
        return await screen_capture.describe_screen(ai)

    elif t == "NEWS":
        result = await browser_tools.fetch_news()
        return result

    elif t == "TELEGRAM":
        if not telegram.enabled:
            return "Telegram ist nicht eingerichtet."
        ok = await send_jarvis_message(p, voice=False)
        return "Nachricht gesendet." if ok else "Telegram-Versand fehlgeschlagen."

    return ""


async def process_message(session_id: str, user_text: str, ws: WebSocket):
    """Process message and send responses via WebSocket."""
    if session_id not in conversations:
        conversations[session_id] = []

    # Refresh weather + tasks on activate
    if "activate" in user_text.lower():
        refresh_data()

    conversations[session_id].append({"role": "user", "content": user_text})
    history = conversations[session_id][-16:]

    # LLM call
    response = await ai.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=400,
        system=get_system_prompt(),
        messages=history,
    )
    reply = response.content[0].text
    print(f"  LLM raw: {reply[:200]}", flush=True)
    spoken_text, action = extract_action(reply)

    # Speak the main response immediately
    if spoken_text:
        audio = await synthesize_speech(spoken_text)
        print(f"  Jarvis: {spoken_text[:80]}", flush=True)
        print(f"  Audio bytes: {len(audio)}", flush=True)
        conversations[session_id].append({"role": "assistant", "content": spoken_text})
        await ws.send_json({
            "type": "response",
            "text": spoken_text,
            "audio": base64.b64encode(audio).decode("utf-8") if audio else "",
        })

    # Execute action if any
    if action:
        print(f"  Action: {action['type']} -> {action['payload'][:100]}", flush=True)

        # Quick voice feedback for SCREEN so user knows Jarvis is working
        if action["type"] == "SCREEN":
            hint = "Lassen Sie mich einen Blick auf Ihren Bildschirm werfen."
            hint_audio = await synthesize_speech(hint)
            await ws.send_json({
                "type": "response",
                "text": hint,
                "audio": base64.b64encode(hint_audio).decode("utf-8") if hint_audio else "",
            })

        try:
            action_result = await execute_action(action)
            print(f"  Result: {action_result}", flush=True)
        except Exception as e:
            print(f"  Action error: {e}", flush=True)
            action_result = f"Fehler: {e}"

        if action["type"] == "OPEN":
            # Just opened browser, nothing to summarize
            return

        if action["type"] == "TELEGRAM":
            # Jarvis hat die Nachricht schon angekuendigt, nur bei Fehlern etwas sagen
            if action_result != "Nachricht gesendet.":
                msg = f"Die Nachricht ist leider nicht angekommen, {USER_ADDRESS}. {action_result}"
                audio_err = await synthesize_speech(msg)
                await ws.send_json({
                    "type": "response",
                    "text": msg,
                    "audio": base64.b64encode(audio_err).decode("utf-8") if audio_err else "",
                })
            return

        # SEARCH, BROWSE, SCREEN — summarize results
        if action_result and "fehlgeschlagen" not in action_result:
            summary_resp = await ai.messages.create(
                model="claude-haiku-4-5-20251001",
                max_tokens=250,
                system=f"Du bist Jarvis. Fasse die folgenden Informationen KURZ auf Deutsch zusammen, maximal 3 Saetze, im Jarvis-Stil. Sprich den Nutzer als {USER_ADDRESS} an. KEINE Tags in eckigen Klammern. KEINE ACTION-Tags.",
                messages=[{"role": "user", "content": f"Fasse zusammen:\n\n{action_result}"}],
            )
            summary = summary_resp.content[0].text
            summary, _ = extract_action(summary)
        else:
            summary = f"Das hat leider nicht funktioniert, {USER_ADDRESS}."

        audio2 = await synthesize_speech(summary)
        conversations[session_id].append({"role": "assistant", "content": summary})
        await ws.send_json({
            "type": "response",
            "text": summary,
            "audio": base64.b64encode(audio2).decode("utf-8") if audio2 else "",
        })


# ---------- Telegram: Nachrichten von Jarvis ----------
NOTIFY_STATE_PATH = os.path.join(os.path.dirname(__file__), "notify_state.json")


def load_notify_state() -> dict:
    try:
        with open(NOTIFY_STATE_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {}


def save_notify_state(state: dict):
    with open(NOTIFY_STATE_PATH, "w", encoding="utf-8") as f:
        json.dump(state, f)


async def send_jarvis_message(text: str, voice: bool = TELEGRAM_VOICE) -> bool:
    """Text an Telegram schicken, optional zusaetzlich als Sprachnachricht mit Jarvis-Stimme."""
    ok = await telegram.send_text(text)
    if ok and voice:
        audio = await synthesize_speech(text)
        if audio:
            await telegram.send_voice(audio)
    return ok


def deadline_lines() -> list[str]:
    lines = []
    for p in load_projects():
        if p.get("status") == "fertig":
            continue
        d = project_days_left(p)
        if d is None or d > 1:
            continue
        when = "ist heute faellig" if d == 0 else "ist morgen faellig" if d == 1 else f"ist seit {-d} Tagen ueberfaellig"
        lines.append(f"{p.get('name', '?')} {when} (Fortschritt {project_progress(p)}%)")
    return lines


async def jarvis_write(instruction: str) -> str:
    resp = await ai.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=400,
        system=get_system_prompt() + "\n\nDu schreibst jetzt eine Nachricht, die per Telegram aufs Handy geschickt und vorgelesen wird. KEINE Aktionen, KEINE Tags in eckigen Klammern, kein Markdown.",
        messages=[{"role": "user", "content": instruction}],
    )
    text, _ = extract_action(resp.content[0].text)
    return text.strip()


async def send_morning_briefing() -> bool:
    await asyncio.to_thread(refresh_data)
    deadlines = deadline_lines()
    extra = (" Weise besonders auf diese Deadlines hin: " + "; ".join(deadlines) + ".") if deadlines else ""
    text = await jarvis_write(
        "Schreibe das Morgen-Briefing: Begruessung passend zur Uhrzeit, Wetter in einem Satz, "
        "ein kurzer Ueberblick ueber Aufgaben und offene Projekte, und ein trockener Kommentar zum Abschluss. "
        "Maximal 5 Saetze." + extra
    )
    return await send_jarvis_message(text)


async def send_deadline_alert() -> bool:
    deadlines = deadline_lines()
    if not deadlines:
        return True  # nichts zu melden, gilt fuer heute als erledigt
    text = await jarvis_write(
        "Warne kurz und hoeflich-spitz vor diesen Projekt-Deadlines, maximal 3 Saetze: " + "; ".join(deadlines)
    )
    return await send_jarvis_message(text)


SCHEDULED_MESSAGES = [
    ("briefing", TELEGRAM_BRIEFING_TIME, send_morning_briefing),
    ("deadlines", TELEGRAM_DEADLINE_TIME, send_deadline_alert),
]


async def telegram_scheduler():
    """Prueft jede halbe Minute, ob eine geplante Nachricht faellig ist (max. 1x pro Tag, bis 60 Min. nach Termin)."""
    while True:
        try:
            now = datetime.now()
            state = load_notify_state()
            for name, at, job in SCHEDULED_MESSAGES:
                if not at or state.get(name) == now.date().isoformat():
                    continue
                hour, minute = (int(x) for x in at.split(":"))
                due = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
                if not (due <= now < due + timedelta(minutes=60)):
                    continue
                print(f"[jarvis] Telegram: sende {name}", flush=True)
                if await job():
                    state[name] = now.date().isoformat()
                    save_notify_state(state)
        except Exception as e:
            print(f"[jarvis] Telegram-Zeitplan Fehler: {e}", flush=True)
        await asyncio.sleep(30)


@app.on_event("startup")
async def start_telegram_scheduler():
    if telegram.enabled:
        asyncio.create_task(telegram_scheduler())
        print(f"[jarvis] Telegram aktiv (Briefing {TELEGRAM_BRIEFING_TIME or 'aus'}, Deadlines {TELEGRAM_DEADLINE_TIME or 'aus'})", flush=True)
    else:
        print("[jarvis] Telegram nicht eingerichtet (python scripts/telegram-setup.py)", flush=True)


@app.post("/api/telegram/test")
async def telegram_test(kind: str = "hallo"):
    """Testnachricht ausloesen: kind = hallo | briefing | deadlines"""
    if not telegram.enabled:
        raise HTTPException(status_code=400, detail="Telegram ist nicht eingerichtet")
    if kind == "briefing":
        ok = await send_morning_briefing()
    elif kind == "deadlines":
        ok = await send_jarvis_message("\n".join(deadline_lines()) or f"Keine Deadlines in Sicht, {USER_ADDRESS}.", voice=False)
    else:
        ok = await send_jarvis_message(f"Systeme online, {USER_ADDRESS}. Ab sofort erreiche ich Sie auch unterwegs.")
    return {"sent": ok}


@app.websocket("/ws")
async def websocket_endpoint(ws: WebSocket):
    await ws.accept()
    session_id = str(id(ws))
    print(f"[jarvis] Client connected", flush=True)

    try:
        while True:
            data = await ws.receive_json()
            user_text = data.get("text", "").strip()
            if not user_text:
                continue

            print(f"  You:    {user_text}", flush=True)
            await process_message(session_id, user_text, ws)

    except WebSocketDisconnect:
        conversations.pop(session_id, None)


app.mount("/static", StaticFiles(directory=os.path.join(os.path.dirname(__file__), "frontend")), name="static")


@app.get("/")
async def serve_index():
    return FileResponse(os.path.join(os.path.dirname(__file__), "frontend", "index.html"))


@app.get("/projects")
async def serve_projects():
    return FileResponse(os.path.join(os.path.dirname(__file__), "frontend", "projects.html"))


@app.get("/api/projects")
async def list_projects():
    return load_projects()


@app.put("/api/projects/{project_id}")
async def upsert_project(project_id: str, request: Request):
    if not PROJECT_ID_PATTERN.match(project_id):
        raise HTTPException(status_code=400, detail="Ungueltige Projekt-ID")
    project = await request.json()
    if not isinstance(project, dict) or not str(project.get("name", "")).strip():
        raise HTTPException(status_code=400, detail="Projekt braucht einen Namen")
    project["id"] = project_id
    projects = [p for p in load_projects() if p.get("id") != project_id]
    projects.append(project)
    save_projects(projects)
    return project


@app.delete("/api/projects/{project_id}")
async def delete_project(project_id: str):
    projects = load_projects()
    remaining = [p for p in projects if p.get("id") != project_id]
    if len(remaining) == len(projects):
        raise HTTPException(status_code=404, detail="Projekt nicht gefunden")
    save_projects(remaining)
    return {"deleted": project_id}


if __name__ == "__main__":
    import uvicorn
    print("=" * 50, flush=True)
    print("  J.A.R.V.I.S. V2 Server", flush=True)
    print(f"  http://localhost:8340", flush=True)
    print(f"  Projekte: http://localhost:8340/projects", flush=True)
    print("=" * 50, flush=True)
    uvicorn.run(app, host="0.0.0.0", port=8340)
