"""
Jarvis — passende YouTube-Videos zu einem Thema (offizielle YouTube Data API v3).
Kostenlos bis ca. 100 Suchen pro Tag. Ergebnisse werden 6 Stunden zwischengespeichert,
damit gleiche Fragen kein Kontingent verbrauchen.
"""

import html
import time

import httpx

SEARCH_URL = "https://www.googleapis.com/youtube/v3/search"
CACHE_SECONDS = 6 * 3600


class YouTubeSearch:
    def __init__(self, api_key: str, http: httpx.AsyncClient | None = None, region: str = "DE", language: str = "de"):
        self.api_key = (api_key or "").strip()
        self.http = http or httpx.AsyncClient(timeout=15)
        self.region = region
        self.language = language
        self._cache: dict[str, tuple[float, list[dict]]] = {}

    @property
    def enabled(self) -> bool:
        return bool(self.api_key)

    async def search(self, query: str, count: int = 3) -> list[dict]:
        key = query.strip().lower()
        hit = self._cache.get(key)
        if hit and time.time() - hit[0] < CACHE_SECONDS:
            return hit[1]
        resp = await self.http.get(SEARCH_URL, params={
            "part": "snippet", "type": "video", "maxResults": count, "q": query, "key": self.api_key,
            "regionCode": self.region, "relevanceLanguage": self.language, "safeSearch": "moderate",
        })
        data = resp.json()
        if "error" in data:
            raise RuntimeError(data["error"].get("message") or f"HTTP {resp.status_code}")
        videos = []
        for item in data.get("items", []):
            vid = (item.get("id") or {}).get("videoId")
            if not vid:
                continue
            sn = item.get("snippet") or {}
            thumbs = sn.get("thumbnails") or {}
            thumb = (thumbs.get("high") or thumbs.get("medium") or thumbs.get("default") or {}).get("url") \
                or f"https://i.ytimg.com/vi/{vid}/hqdefault.jpg"
            videos.append({
                "id": vid, "title": html.unescape(sn.get("title", "")), "channel": html.unescape(sn.get("channelTitle", "")),
                "thumb": thumb, "url": f"https://www.youtube.com/watch?v={vid}",
            })
        self._cache[key] = (time.time(), videos)
        return videos
