import os
from dotenv import load_dotenv

load_dotenv()

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")

GROQ_KEYS = [
    v for k, v in sorted(os.environ.items())
    if k.startswith("GROQ_API_KEY_") and v.strip()
]

OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY", "")
FACEBOOK_COOKIES_B64 = os.getenv("FACEBOOK_COOKIES_B64", "")

DATA_DIR = os.getenv("DATA_DIR", "./data")
DB_PATH = os.getenv("DB_PATH", f"{DATA_DIR}/links.db")
COOKIES_PATH = os.path.join(DATA_DIR, "fb_cookies.txt")

os.makedirs(DATA_DIR, exist_ok=True)

# Write Facebook cookies file on startup if configured
if FACEBOOK_COOKIES_B64:
    import base64
    with open(COOKIES_PATH, "wb") as _f:
        _f.write(base64.b64decode(FACEBOOK_COOKIES_B64))
