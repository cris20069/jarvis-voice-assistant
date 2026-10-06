"""
Jarvis — TikTok-Statistiken ueber die offizielle TikTok-API (Login Kit + Display API).
Liest Profilzahlen und die neuesten Videos und vergleicht sie mit der letzten Abfrage.
Die Zugangsdaten liegen in tiktok_token.json (gitignored), der Vergleichsstand in tiktok_state.json.
"""

import json
import os
import time
import urllib.parse

import httpx

BASE = os.path.dirname(os.path.abspath(__file__))
TOKEN_PATH = os.path.join(BASE, "tiktok_token.json")
STATE_PATH = os.path.join(BASE, "tiktok_state.json")

AUTH_URL = "https://www.tiktok.com/v2/auth/authorize/"
TOKEN_URL = "https://open.tiktokapis.com/v2/oauth/token/"
USER_URL = "https://open.tiktokapis.com/v2/user/info/"
VIDEO_URL = "https://open.tiktokapis.com/v2/video/list/"
SCOPES = "user.info.basic,user.info.profile,user.info.stats,video.list"
USER_FIELDS = "open_id,display_name,username,follower_count,following_count,likes_count,video_count"
VIDEO_FIELDS = "id,title,video_description,create_time,view_count,like_count,comment_count,share_count,share_url"


def _load(path: str, default):
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return default


def _save(path: str, data):
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    os.replace(tmp, path)


def _ago(seconds: float) -> str:
    h = int(seconds // 3600)
    if h < 1:
        return "vor weniger als einer Stunde"
    if h < 48:
        return f"vor {h} Stunden"
    return f"vor {h // 24} Tagen"


class TikTokClient:
    def __init__(self, client_key: str, client_secret: str, redirect_uri: str, http: httpx.AsyncClient | None = None):
        self.client_key = (client_key or "").strip()
        self.client_secret = (client_secret or "").strip()
        self.redirect_uri = (redirect_uri or "").strip()
        self.http = http or httpx.AsyncClient(timeout=30)

    @property
    def enabled(self) -> bool:
        return bool(self.client_key and self.client_secret and os.path.exists(TOKEN_PATH))

    def auth_url(self, state: str) -> str:
        return AUTH_URL + "?" + urllib.parse.urlencode({
            "client_key": self.client_key, "scope": SCOPES, "response_type": "code",
            "redirect_uri": self.redirect_uri, "state": state,
        })

    async def _post_token(self, data: dict) -> dict:
        resp = await self.http.post(TOKEN_URL, data={"client_key": self.client_key, "client_secret": self.client_secret, **data},
                                    headers={"Content-Type": "application/x-www-form-urlencoded", "Cache-Control": "no-cache"})
        j = resp.json()
        if "access_token" not in j:
            raise RuntimeError(j.get("error_description") or j.get("error") or f"HTTP {resp.status_code}")
        now = time.time()
        tok = {
            "access_token": j["access_token"], "refresh_token": j.get("refresh_token", ""),
            "expires_at": now + int(j.get("expires_in", 0)), "refresh_expires_at": now + int(j.get("refresh_expires_in", 0)),
            "open_id": j.get("open_id", ""), "scope": j.get("scope", ""),
        }
        _save(TOKEN_PATH, tok)
        return tok

    async def exchange_code(self, code: str) -> dict:
        return await self._post_token({"code": code, "grant_type": "authorization_code", "redirect_uri": self.redirect_uri})

    async def _access_token(self) -> str:
        tok = _load(TOKEN_PATH, None)
        if not tok:
            raise RuntimeError("TikTok ist nicht verbunden (python scripts/tiktok-setup.py)")
        if tok["expires_at"] - 300 < time.time():
            if tok.get("refresh_expires_at", 0) < time.time():
                raise RuntimeError("Die TikTok-Anmeldung ist abgelaufen, bitte scripts/tiktok-setup.py erneut ausfuehren")
            tok = await self._post_token({"grant_type": "refresh_token", "refresh_token": tok["refresh_token"]})
        return tok["access_token"]

    async def _api(self, method: str, url: str, **kw) -> dict:
        token = await self._access_token()
        resp = await self.http.request(method, url, headers={"Authorization": f"Bearer {token}"}, **kw)
        j = resp.json()
        err = j.get("error") or {}
        if err.get("code") not in (None, "", "ok"):
            raise RuntimeError(err.get("message") or err.get("code"))
        return j.get("data") or {}

    async def user(self) -> dict:
        return (await self._api("GET", USER_URL, params={"fields": USER_FIELDS})).get("user", {})

    async def videos(self, count: int = 6) -> list[dict]:
        data = await self._api("POST", VIDEO_URL, params={"fields": VIDEO_FIELDS}, json={"max_count": count})
        return data.get("videos", [])

    async def report(self) -> dict:
        user = await self.user()
        videos = await self.videos()
        prev = _load(STATE_PATH, {})
        now = time.time()
        latest = videos[0] if videos else None
        others = [v.get("view_count", 0) for v in videos[1:6]]
        r = {
            "username": user.get("username") or user.get("display_name", ""),
            "followers": user.get("follower_count", 0), "likes": user.get("likes_count", 0),
            "videos": user.get("video_count", 0),
            "since": prev.get("checked_at"),
            "follower_delta": user.get("follower_count", 0) - prev["followers"] if "followers" in prev else None,
            "likes_delta": user.get("likes_count", 0) - prev["likes"] if "likes" in prev else None,
            "latest": None,
        }
        if latest:
            views = latest.get("view_count", 0)
            prev_views = prev.get("video_views", {}).get(latest.get("id"))
            r["latest"] = {
                "title": (latest.get("title") or latest.get("video_description") or "ohne Titel").strip()[:90],
                "posted": latest.get("create_time", 0), "views": views,
                "likes": latest.get("like_count", 0), "comments": latest.get("comment_count", 0),
                "shares": latest.get("share_count", 0), "url": latest.get("share_url", ""),
                "views_delta": views - prev_views if prev_views is not None else None,
                "avg_views_before": round(sum(others) / len(others)) if others else None,
            }
        _save(STATE_PATH, {"checked_at": now, "followers": r["followers"], "likes": r["likes"],
                           "video_views": {v.get("id"): v.get("view_count", 0) for v in videos}})
        return r


def describe(r: dict) -> str:
    sign = lambda n: f"+{n}" if n > 0 else str(n)
    lines = [f"TikTok @{r['username']}: {r['followers']} Follower, {r['likes']} Likes insgesamt, {r['videos']} Videos."]
    if r.get("since"):
        when = _ago(time.time() - r["since"])
        lines.append(f"Seit der letzten Abfrage ({when}): Follower {sign(r['follower_delta'])}, Likes {sign(r['likes_delta'])}.")
    else:
        lines.append("Erste Abfrage, ab jetzt vergleicht Jarvis mit diesem Stand.")
    v = r.get("latest")
    if v:
        posted = _ago(time.time() - v["posted"]) if v["posted"] else "unbekannt"
        lines.append(f"Neuestes Video \"{v['title']}\" (gepostet {posted}): {v['views']} Aufrufe, {v['likes']} Likes, "
                     f"{v['comments']} Kommentare, {v['shares']} Shares.")
        if v["views_delta"] is not None:
            lines.append(f"Seit der letzten Abfrage {sign(v['views_delta'])} Aufrufe.")
        if v["avg_views_before"]:
            ratio = v["views"] / v["avg_views_before"]
            verdict = "deutlich besser als" if ratio >= 1.3 else "schwaecher als" if ratio < 0.7 else "etwa wie"
            lines.append(f"Damit laeuft es {verdict} die vorherigen Videos (Schnitt {v['avg_views_before']} Aufrufe).")
    else:
        lines.append("Noch keine Videos gefunden.")
    return "\n".join(lines)


def parse_redirect(url_or_code: str) -> tuple[str, str]:
    text = url_or_code.strip()
    if "code=" not in text:
        return text, ""
    q = urllib.parse.parse_qs(urllib.parse.urlparse(text).query)
    return (q.get("code") or [""])[0], (q.get("state") or [""])[0]
