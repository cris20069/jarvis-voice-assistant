"""
Jarvis — E-Mail-Postfach verbinden (zum Aufraeumen)
1. Yahoo: Kontoinfo -> Kontosicherheit -> "App-Passwort erstellen" (Name z.B. "Jarvis")
2. python scripts/mail-setup.py ausfuehren, Adresse und App-Passwort eingeben
Das Skript testet die Verbindung, zeigt was aufgeraeumt werden koennte und speichert
alles in config.json (wird nicht auf GitHub hochgeladen). Es wird nichts geloescht.
"""

import getpass
import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from mail_tools import DEFAULT_HOST, MailCleaner, describe_scan  # noqa: E402

CONFIG_PATH = os.path.join(os.path.dirname(__file__), "..", "config.json")


def main():
    if not os.path.exists(CONFIG_PATH):
        sys.exit("config.json fehlt. Bitte zuerst Jarvis einrichten.")
    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        config = json.load(f)

    address = input(f"E-Mail-Adresse [{config.get('mail_address', '')}]: ").strip() or config.get("mail_address", "")
    password = getpass.getpass("App-Passwort (Eingabe bleibt unsichtbar): ").strip()
    host = input(f"IMAP-Server [{config.get('mail_imap_host', DEFAULT_HOST)}]: ").strip() or config.get("mail_imap_host", DEFAULT_HOST)
    days_in = input(f"Newsletter aufraeumen, die aelter sind als ... Tage (0 = nie) [{config.get('mail_newsletter_days', 30)}]: ").strip()
    days = int(days_in) if days_in.isdigit() else int(config.get("mail_newsletter_days", 30))

    cleaner = MailCleaner(address, password, host, days)
    print("\nVerbinde ...")
    try:
        scan = cleaner.scan_sync()
    except Exception as e:
        sys.exit(f"Verbindung fehlgeschlagen: {e}\nPruefe Adresse und App-Passwort (nicht dein normales Passwort).")
    print("Verbindung klappt.\n")
    print(describe_scan(scan))

    config.update({"mail_address": address, "mail_app_password": password,
                   "mail_imap_host": host, "mail_newsletter_days": days})
    with open(CONFIG_PATH, "w", encoding="utf-8") as f:
        json.dump(config, f, ensure_ascii=False, indent=2)
    print("\nGespeichert in config.json. Starte server.py neu.")
    print('Dann: "Jarvis, raeum mein Postfach auf" oder python scripts/mail-cleanup.py')


if __name__ == "__main__":
    main()
