from urllib.parse import urlparse

PLATFORM_MAP = {
    "youtube.com": "youtube",
    "youtu.be": "youtube",
    "instagram.com": "instagram",
    "tiktok.com": "tiktok",
    "twitter.com": "twitter",
    "x.com": "twitter",
    "reddit.com": "reddit",
    "redd.it": "reddit",
    "linkedin.com": "linkedin",
    "facebook.com": "facebook",
    "fb.com": "facebook",
    "medium.com": "medium",
    "substack.com": "substack",
    "github.com": "github",
}


def detect(url: str) -> str:
    try:
        host = urlparse(url).netloc.lower().lstrip("www.")
        for domain, platform in PLATFORM_MAP.items():
            if host == domain or host.endswith("." + domain):
                return platform
    except Exception:
        pass
    return "article"
