"""
Jarvis — Telegram-Benachrichtigungen
Schickt Text- und Sprachnachrichten ueber einen eigenen Telegram-Bot (kostenlos).
Einrichtung: python scripts/telegram-setup.py
"""

import httpx

API = "https://api.telegram.org/bot{token}/{method}"


class TelegramNotifier:
    def __init__(self, token: str, chat_id: str):
        self.token = (token or "").strip()
        self.chat_id = str(chat_id or "").strip()
        self.http = httpx.AsyncClient(timeout=30)

    @property
    def enabled(self) -> bool:
        return bool(self.token and self.chat_id)

    def _url(self, method: str) -> str:
        return API.format(token=self.token, method=method)

    async def send_text(self, text: str) -> bool:
        if not self.enabled or not text.strip():
            return False
        try:
            resp = await self.http.post(self._url("sendMessage"), json={
                "chat_id": self.chat_id,
                "text": text[:4000],
            })
            if resp.status_code != 200:
                print(f"  Telegram error: {resp.status_code} {resp.text[:200]}", flush=True)
            return resp.status_code == 200
        except Exception as e:
            print(f"  Telegram EXCEPTION: {e}", flush=True)
            return False

    async def send_voice(self, audio_mp3: bytes, caption: str = "") -> bool:
        """Sprachnachricht senden. Faellt auf eine Audiodatei zurueck, falls Telegram die Sprachblase ablehnt."""
        if not self.enabled or not audio_mp3:
            return False
        data = {"chat_id": self.chat_id}
        if caption:
            data["caption"] = caption[:1000]
        for method, field in (("sendVoice", "voice"), ("sendAudio", "audio")):
            try:
                resp = await self.http.post(
                    self._url(method),
                    data=data,
                    files={field: ("jarvis.mp3", audio_mp3, "audio/mpeg")},
                )
                if resp.status_code == 200:
                    return True
                print(f"  Telegram {method} error: {resp.status_code} {resp.text[:200]}", flush=True)
            except Exception as e:
                print(f"  Telegram {method} EXCEPTION: {e}", flush=True)
        return False
