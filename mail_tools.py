"""
Jarvis — Postfach aufraeumen (IMAP).
Verschiebt Spam und alte Newsletter in den Papierkorb. Nichts wird endgueltig
geloescht, mit Faehnchen markierte Mails werden nie angefasst.
"""

import asyncio
import imaplib
import re
from collections import Counter
from datetime import date, timedelta
from email.header import decode_header, make_header
from email.utils import parseaddr

DEFAULT_HOST = "imap.mail.yahoo.com"
LIST_RE = re.compile(rb'\((?P<flags>[^)]*)\) (?:"[^"]*"|NIL) (?P<name>.+)$')
SPAM_NAMES = ("bulk", "spam", "junk", "bulk mail")
TRASH_NAMES = ("trash", "papierkorb", "deleted items", "deleted messages")
CHUNK = 200


def _quote(name: str) -> str:
    return '"' + name.replace("\\", "\\\\").replace('"', '\\"') + '"'


def _imap_date(d: date) -> str:
    return f"{d.day:02d}-{['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec'][d.month - 1]}-{d.year}"


def _sender(raw: bytes) -> str:
    text = raw.decode("utf-8", errors="replace")
    m = re.search(r"(?im)^from:\s*(.+(?:\r?\n[ \t].+)*)", text)
    if not m:
        return "?"
    try:
        value = str(make_header(decode_header(m.group(1))))
    except Exception:
        value = m.group(1)
    name, addr = parseaddr(value)
    return addr.lower() or name or "?"


class MailCleaner:
    def __init__(self, address: str, app_password: str, host: str = DEFAULT_HOST, newsletter_days: int = 30):
        self.address = (address or "").strip()
        self.app_password = (app_password or "").replace(" ", "").strip()
        self.host = (host or DEFAULT_HOST).strip()
        self.newsletter_days = max(0, int(newsletter_days or 0))

    @property
    def enabled(self) -> bool:
        return bool(self.address and self.app_password)

    def _connect(self):
        imap = imaplib.IMAP4_SSL(self.host, 993, timeout=30)
        imap.login(self.address, self.app_password)
        return imap

    def _folders(self, imap) -> tuple[str | None, str | None]:
        status, rows = imap.list()
        spam = trash = None
        for row in rows or []:
            m = LIST_RE.match(row or b"")
            if not m:
                continue
            flags = m.group("flags").lower()
            name = m.group("name").strip()
            if name.startswith(b'"') and name.endswith(b'"'):
                name = name[1:-1].replace(b'\\"', b'"').replace(b"\\\\", b"\\")
            name = name.decode("utf-8", errors="replace")
            low = name.lower()
            if b"\\junk" in flags or (spam is None and low in SPAM_NAMES):
                spam = name
            if b"\\trash" in flags or (trash is None and low in TRASH_NAMES):
                trash = name
        return spam, trash

    def _uids(self, imap, folder: str, *criteria: str) -> list[bytes]:
        status, _ = imap.select(_quote(folder))
        if status != "OK":
            raise RuntimeError(f"Ordner {folder} nicht lesbar")
        status, data = imap.uid("SEARCH", *criteria)
        if status != "OK":
            raise RuntimeError(f"Suche in {folder} fehlgeschlagen")
        return data[0].split() if data and data[0] else []

    def _newsletter_criteria(self) -> tuple[str, ...]:
        cutoff = date.today() - timedelta(days=self.newsletter_days)
        return ("UNFLAGGED", "BEFORE", _imap_date(cutoff), "HEADER", "List-Unsubscribe", '""')

    def _top_senders(self, imap, uids: list[bytes], n: int = 5) -> list[tuple[str, int]]:
        counts = Counter()
        for i in range(0, min(len(uids), 600), CHUNK):
            chunk = b",".join(uids[i:i + CHUNK]).decode()
            status, parts = imap.uid("FETCH", chunk, "(BODY.PEEK[HEADER.FIELDS (FROM)])")
            for p in parts or []:
                if isinstance(p, tuple):
                    counts[_sender(p[1])] += 1
        return counts.most_common(n)

    def _move(self, imap, uids: list[bytes], trash: str) -> int:
        caps = {c.upper() for c in getattr(imap, "capabilities", ())}
        moved = 0
        for i in range(0, len(uids), CHUNK):
            chunk = b",".join(uids[i:i + CHUNK]).decode()
            if "MOVE" in caps:
                status, _ = imap.uid("MOVE", chunk, _quote(trash))
            else:
                status, _ = imap.uid("COPY", chunk, _quote(trash))
                if status == "OK":
                    imap.uid("STORE", chunk, "+FLAGS.SILENT", r"(\Deleted)")
                    imap.expunge()
            if status != "OK":
                raise RuntimeError("Verschieben in den Papierkorb fehlgeschlagen")
            moved += len(uids[i:i + CHUNK])
        return moved

    def scan_sync(self) -> dict:
        imap = self._connect()
        try:
            spam, trash = self._folders(imap)
            spam_uids = self._uids(imap, spam, "UNFLAGGED") if spam else []
            news_uids, senders = [], []
            if self.newsletter_days:
                news_uids = self._uids(imap, "INBOX", *self._newsletter_criteria())
                senders = self._top_senders(imap, news_uids)
            return {"spam_folder": spam, "trash_folder": trash, "spam": len(spam_uids),
                    "newsletters": len(news_uids), "newsletter_days": self.newsletter_days, "top_senders": senders}
        finally:
            imap.logout()

    def clean_sync(self) -> dict:
        imap = self._connect()
        try:
            spam, trash = self._folders(imap)
            if not trash:
                raise RuntimeError("Papierkorb-Ordner nicht gefunden")
            moved_spam = moved_news = 0
            if spam:
                uids = self._uids(imap, spam, "UNFLAGGED")
                moved_spam = self._move(imap, uids, trash) if uids else 0
            if self.newsletter_days:
                uids = self._uids(imap, "INBOX", *self._newsletter_criteria())
                moved_news = self._move(imap, uids, trash) if uids else 0
            return {"spam": moved_spam, "newsletters": moved_news, "trash_folder": trash}
        finally:
            imap.logout()

    async def scan(self) -> dict:
        return await asyncio.to_thread(self.scan_sync)

    async def clean(self) -> dict:
        return await asyncio.to_thread(self.clean_sync)


def describe_scan(r: dict) -> str:
    lines = [f"Spam-Ordner ({r.get('spam_folder') or 'nicht gefunden'}): {r['spam']} Mails."]
    if r.get("newsletter_days"):
        lines.append(f"Newsletter im Posteingang, aelter als {r['newsletter_days']} Tage: {r['newsletters']} Mails.")
        if r.get("top_senders"):
            lines.append("Haeufigste Absender: " + ", ".join(f"{s} ({n})" for s, n in r["top_senders"]))
    lines.append("Alles wuerde in den Papierkorb verschoben, markierte Mails bleiben unberuehrt.")
    return "\n".join(lines)


def describe_clean(r: dict) -> str:
    return (f"{r['spam']} Spam-Mails und {r['newsletters']} alte Newsletter in den Papierkorb "
            f"({r['trash_folder']}) verschoben.")
