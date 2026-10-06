"""
Jarvis — Postfach aufraeumen (von Hand)
Zeigt zuerst, was weg soll, und verschiebt erst nach deinem "j" alles in den Papierkorb.
Mails mit Faehnchen bleiben immer liegen.
"""

import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from mail_tools import DEFAULT_HOST, MailCleaner, describe_clean, describe_scan  # noqa: E402

CONFIG_PATH = os.path.join(os.path.dirname(__file__), "..", "config.json")


def main():
    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        config = json.load(f)
    cleaner = MailCleaner(config.get("mail_address", ""), config.get("mail_app_password", ""),
                          config.get("mail_imap_host", DEFAULT_HOST), config.get("mail_newsletter_days", 30))
    if not cleaner.enabled:
        sys.exit("Postfach nicht eingerichtet. Zuerst: python scripts/mail-setup.py")

    scan = cleaner.scan_sync()
    print(describe_scan(scan))
    if not scan["spam"] and not scan["newsletters"]:
        print("\nNichts zu tun, das Postfach ist sauber.")
        return
    if input("\nJetzt in den Papierkorb verschieben? [j/N] ").strip().lower() not in ("j", "ja", "y", "yes"):
        print("Abgebrochen, nichts veraendert.")
        return
    print(describe_clean(cleaner.clean_sync()))


if __name__ == "__main__":
    main()
