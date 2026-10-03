"""
Jarvis — Telegram einrichten
1. In Telegram @BotFather oeffnen, /newbot senden, Namen vergeben -> Token kopieren
2. python scripts/telegram-setup.py ausfuehren und Token einfuegen
3. Dem eigenen Bot in Telegram eine Nachricht schicken (z.B. /start)
Das Skript findet deine Chat-ID, traegt beides in config.json ein und schickt eine Testnachricht.
"""

import json
import os
import sys
import time

import httpx

CONFIG_PATH = os.path.join(os.path.dirname(__file__), "..", "config.json")


def api(token: str, method: str, **params):
    resp = httpx.post(f"https://api.telegram.org/bot{token}/{method}", json=params, timeout=40)
    data = resp.json()
    if not data.get("ok"):
        raise RuntimeError(data.get("description", "Unbekannter Fehler"))
    return data["result"]


def main():
    if not os.path.exists(CONFIG_PATH):
        sys.exit("config.json fehlt. Bitte zuerst Jarvis einrichten.")
    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        config = json.load(f)

    token = input("Bot-Token von @BotFather: ").strip()
    try:
        bot = api(token, "getMe")
    except Exception as e:
        sys.exit(f"Token ungueltig: {e}")
    print(f"\nBot gefunden: @{bot['username']}")
    print(f"Oeffne jetzt https://t.me/{bot['username']} und schicke dem Bot eine Nachricht (z.B. /start).")
    print("Warte auf deine Nachricht ...")

    chat_id = None
    offset = None
    deadline = time.time() + 300
    while time.time() < deadline and chat_id is None:
        params = {"timeout": 25}
        if offset is not None:
            params["offset"] = offset
        for update in api(token, "getUpdates", **params):
            offset = update["update_id"] + 1
            msg = update.get("message") or {}
            if msg.get("chat", {}).get("type") == "private":
                chat_id = msg["chat"]["id"]
                print(f"Nachricht von {msg['chat'].get('first_name', '?')} empfangen.")
                break
    if chat_id is None:
        sys.exit("Keine Nachricht erhalten (5 Minuten gewartet). Bitte erneut versuchen.")

    config["telegram_bot_token"] = token
    config["telegram_chat_id"] = str(chat_id)
    config.setdefault("telegram_briefing_time", "07:30")
    config.setdefault("telegram_deadline_time", "18:00")
    config.setdefault("telegram_voice", True)
    with open(CONFIG_PATH, "w", encoding="utf-8") as f:
        json.dump(config, f, ensure_ascii=False, indent=2)

    address = config.get("user_address", "Sir")
    api(token, "sendMessage", chat_id=chat_id,
        text=f"Verbindung hergestellt, {address}. Ab sofort erreiche ich Sie auch unterwegs.")
    print("\nFertig! Testnachricht gesendet und config.json aktualisiert.")
    print("Starte server.py neu, damit Jarvis die Telegram-Einstellungen uebernimmt.")


if __name__ == "__main__":
    main()
