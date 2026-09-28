import os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "data"
KB_PATH = DATA_DIR / "knowledge.json"
DB_PATH = DATA_DIR / "assistant.sqlite3"

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "").strip()
CHAT_MODEL = os.getenv("OPENAI_CHAT_MODEL", "gpt-5-mini").strip()
EMBEDDING_MODEL = os.getenv("OPENAI_EMBEDDING_MODEL", "text-embedding-3-small").strip()
ALLOWED_ORIGINS = {x.strip().rstrip("/") for x in os.getenv("ALLOWED_ORIGINS", "https://aolukomorie56.ru,https://www.aolukomorie56.ru,https://bot.aolukomorie56.ru").split(",") if x.strip()}
CACHE_TTL = int(os.getenv("CACHE_TTL_SECONDS", "86400"))
TOP_K = int(os.getenv("TOP_K", "7"))
MIN_RELEVANCE = float(os.getenv("MIN_RELEVANCE", "0.18"))
RATE_LIMIT = int(os.getenv("RATE_LIMIT_PER_MINUTE", "20"))
PORT = int(os.getenv("PORT", "8080"))
HOST = os.getenv("HOST", "127.0.0.1").strip()

FALLBACK = "К сожалению, в моей базе нет точной информации по этому вопросу. Пожалуйста, уточните у администратора: 8 (35363) 4-33-56 или 8 (800) 500-28-40."
