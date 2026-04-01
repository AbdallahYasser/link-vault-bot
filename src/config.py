import os
from dotenv import load_dotenv

load_dotenv()

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")

GROQ_KEYS = [
    v for k, v in sorted(os.environ.items())
    if k.startswith("GROQ_API_KEY_") and v.strip()
]

OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY", "")

DATA_DIR = os.getenv("DATA_DIR", "./data")
DB_PATH = os.getenv("DB_PATH", f"{DATA_DIR}/links.db")

os.makedirs(DATA_DIR, exist_ok=True)
