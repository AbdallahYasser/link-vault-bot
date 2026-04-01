import asyncio
import httpx
import re
from html.parser import HTMLParser

# Platforms where yt-dlp handles metadata better than HTML scraping
YTDLP_PLATFORMS = {"facebook", "instagram", "tiktok", "twitter", "youtube"}


async def fetch_metadata(url: str) -> dict:
    """Fetch title and description from a URL.
    Uses yt-dlp for social platforms, httpx for articles/blogs."""
    from src.utils.platform import detect
    platform = detect(url)

    if platform in YTDLP_PLATFORMS:
        result = await _ytdlp_metadata(url)
        if result["title"]:
            return result

    # Fallback: plain HTTP + HTML parsing
    return await _http_metadata(url)


async def _ytdlp_metadata(url: str) -> dict:
    """Use yt-dlp to extract title and description without downloading."""
    try:
        import yt_dlp
        from src.config import COOKIES_PATH, FACEBOOK_COOKIES_B64
        import os

        opts = {
            "quiet": True,
            "no_warnings": True,
            "skip_download": True,
            "extract_flat": False,
            "ignore_no_formats_error": True,
            "logger": _SilentLogger(),
        }

        # Use Facebook cookies if available and URL is Facebook
        if FACEBOOK_COOKIES_B64 and "facebook.com" in url and os.path.exists(COOKIES_PATH):
            opts["cookiefile"] = COOKIES_PATH

        loop = asyncio.get_event_loop()

        def _extract():
            with yt_dlp.YoutubeDL(opts) as ydl:
                info = ydl.extract_info(url, download=False)
                if not info:
                    return {"title": "", "description": ""}
                return {
                    "title": _clean(info.get("title", "")),
                    "description": _clean(info.get("description", "")),
                }

        return await loop.run_in_executor(None, _extract)
    except Exception:
        return {"title": "", "description": ""}


class _SilentLogger:
    def debug(self, msg): pass
    def info(self, msg): pass
    def warning(self, msg): pass
    def error(self, msg): pass


def _load_fb_cookies() -> dict:
    """Parse Netscape cookies file into a dict for httpx."""
    try:
        from src.config import COOKIES_PATH, FACEBOOK_COOKIES_B64
        import os
        if not FACEBOOK_COOKIES_B64 or not os.path.exists(COOKIES_PATH):
            return {}
        cookies = {}
        with open(COOKIES_PATH) as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                parts = line.split("\t")
                if len(parts) >= 7:
                    cookies[parts[5]] = parts[6]
        return cookies
    except Exception:
        return {}


async def _http_metadata(url: str) -> dict:
    """Fetch og:title / og:description via plain HTTP.
    Uses Facebook cookies for facebook.com URLs."""
    try:
        cookies = {}
        if "facebook.com" in url:
            cookies = _load_fb_cookies()

        async with httpx.AsyncClient(
            follow_redirects=True,
            timeout=15,
            headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                "Accept-Language": "en-US,en;q=0.9",
            },
            cookies=cookies,
        ) as client:
            resp = await client.get(url)
            if resp.status_code != 200:
                return {"title": "", "description": ""}
            html = resp.text[:50000]

        parser = _MetaParser()
        parser.feed(html)

        # Ignore generic Facebook login-wall titles
        title = _clean(parser.title)
        if title.lower() in ("facebook", "log in or sign up to view", ""):
            title = ""

        return {
            "title": title,
            "description": _clean(parser.description),
        }
    except Exception:
        return {"title": "", "description": ""}


class _MetaParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.title = ""
        self.description = ""
        self._in_title = False

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == "title":
            self._in_title = True
        if tag == "meta":
            name = attrs.get("name", attrs.get("property", "")).lower()
            content = attrs.get("content", "")
            if not self.title and name in ("og:title", "twitter:title"):
                self.title = content
            if not self.description and name in ("og:description", "twitter:description", "description"):
                self.description = content

    def handle_data(self, data):
        if self._in_title and not self.title:
            self.title = data.strip()
            self._in_title = False

    def handle_endtag(self, tag):
        if tag == "title":
            self._in_title = False


def _clean(text: str) -> str:
    if not text:
        return ""
    text = re.sub(r'\s+', ' ', text).strip()
    return text[:500]
