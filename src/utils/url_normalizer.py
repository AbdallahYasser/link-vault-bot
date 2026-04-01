import re
from urllib.parse import urlparse, parse_qs, urlencode, urlunparse

STRIP_PARAMS = {
    "utm_source", "utm_medium", "utm_campaign", "utm_term", "utm_content",
    "fbclid", "gclid", "ref", "igshid", "s", "si", "feature", "app"
}


def normalize(url: str) -> str:
    url = url.strip()

    # YouTube short links: youtu.be/ID -> youtube.com/watch?v=ID
    yt_short = re.match(r'https?://youtu\.be/([a-zA-Z0-9_-]+)', url)
    if yt_short:
        return f"https://www.youtube.com/watch?v={yt_short.group(1)}"

    parsed = urlparse(url)
    scheme = parsed.scheme.lower() or "https"
    netloc = parsed.netloc.lower()
    if netloc.startswith("www."):
        netloc = netloc[4:]

    # YouTube watch: keep only v= param
    if "youtube.com" in netloc and parsed.path == "/watch":
        params = parse_qs(parsed.query)
        v = params.get("v", [""])[0]
        return f"https://www.youtube.com/watch?v={v}"

    # Strip tracking params
    if parsed.query:
        params = parse_qs(parsed.query, keep_blank_values=True)
        clean = {k: v for k, v in params.items() if k not in STRIP_PARAMS}
        query = urlencode(clean, doseq=True)
    else:
        query = ""

    path = parsed.path.rstrip("/") or "/"
    return urlunparse((scheme, netloc, path, "", query, ""))
