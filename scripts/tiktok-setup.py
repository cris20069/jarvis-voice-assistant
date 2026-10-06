"""
Jarvis — TikTok verbinden
Vorher auf developers.tiktok.com eine App anlegen (siehe SETUP.md, Abschnitt TikTok).
Das Skript oeffnet die TikTok-Anmeldung. Nach dem Erlauben landest du auf deiner Redirect-Seite:
kopiere die komplette Adresse aus der Adresszeile und fuege sie hier ein.
"""

import asyncio
import getpass
import json
import os
import secrets
import sys
import webbrowser

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from tiktok_tools import TikTokClient, describe, parse_redirect  # noqa: E402

CONFIG_PATH = os.path.join(os.path.dirname(__file__), "..", "config.json")
DEFAULT_REDIRECT = "https://cris20069.github.io/Jarvis-gym/"


async def connect(client: TikTokClient, code: str):
    await client.exchange_code(code)
    return await client.report()


def main():
    if not os.path.exists(CONFIG_PATH):
        sys.exit("config.json fehlt. Bitte zuerst Jarvis einrichten.")
    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        config = json.load(f)

    key = input(f"Client Key [{config.get('tiktok_client_key', '')}]: ").strip() or config.get("tiktok_client_key", "")
    secret = getpass.getpass("Client Secret (Eingabe bleibt unsichtbar, Enter = gespeicherten nehmen): ").strip() or config.get("tiktok_client_secret", "")
    redirect = input(f"Redirect URI [{config.get('tiktok_redirect_uri', DEFAULT_REDIRECT)}]: ").strip() or config.get("tiktok_redirect_uri", DEFAULT_REDIRECT)
    if not key or not secret:
        sys.exit("Client Key und Client Secret werden gebraucht.")

    client = TikTokClient(key, secret, redirect)
    state = secrets.token_urlsafe(16)
    url = client.auth_url(state)
    print("\nOeffne die TikTok-Anmeldung im Browser ... falls nichts passiert, diese Adresse oeffnen:\n" + url)
    webbrowser.open(url)
    pasted = input("\nNach dem Erlauben: komplette Adresse aus der Adresszeile hier einfuegen:\n> ")
    code, got_state = parse_redirect(pasted)
    if not code:
        sys.exit("Kein Code in der Adresse gefunden.")
    if got_state and got_state != state:
        sys.exit("Sicherheitspruefung fehlgeschlagen (state passt nicht). Bitte erneut versuchen.")

    try:
        report = asyncio.run(connect(client, code))
    except Exception as e:
        sys.exit(f"Verbindung fehlgeschlagen: {e}")

    config.update({"tiktok_client_key": key, "tiktok_client_secret": secret, "tiktok_redirect_uri": redirect})
    if report.get("username"):
        config["tiktok_username"] = report["username"]
    with open(CONFIG_PATH, "w", encoding="utf-8") as f:
        json.dump(config, f, ensure_ascii=False, indent=2)
    print("\nVerbunden!\n" + describe(report))
    print('\nStarte server.py neu. Dann: "Jarvis, was gibt es Neues auf TikTok?"')


if __name__ == "__main__":
    main()
