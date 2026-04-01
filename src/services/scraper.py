import httpx
import re
from html.parser import HTMLParser


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


async def fetch_metadata(url: str) -> dict:
    """Fetch title and description from a URL. Returns dict with title, description."""
    try:
        async with httpx.AsyncClient(
            follow_redirects=True,
            timeout=15,
            headers={"User-Agent": "Mozilla/5.0 (compatible; LinkVaultBot/1.0)"}
        ) as client:
            resp = await client.get(url)
            if resp.status_code != 200:
                return {"title": "", "description": ""}

            html = resp.text[:50000]  # only parse first 50KB

        parser = _MetaParser()
        parser.feed(html)
        return {
            "title": _clean(parser.title),
            "description": _clean(parser.description),
        }
    except Exception:
        return {"title": "", "description": ""}


def _clean(text: str) -> str:
    if not text:
        return ""
    text = re.sub(r'\s+', ' ', text).strip()
    return text[:500]
