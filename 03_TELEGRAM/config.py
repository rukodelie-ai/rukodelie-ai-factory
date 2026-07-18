import os
from pathlib import Path
from dotenv import load_dotenv

from logger import logger

load_dotenv()


def _require(name: str) -> str:
    value = os.environ.get(name, "").strip()
    if not value:
        raise RuntimeError(f"Required environment variable '{name}' is not set. Check your .env file.")
    return value


# --- Tokens (never logged, never printed) ---
TELEGRAM_BOT_TOKEN: str = _require("TELEGRAM_BOT_TOKEN")
ANTHROPIC_API_KEY: str = _require("ANTHROPIC_API_KEY")

# --- Optional ---
ADMIN_CHAT_ID = int(os.environ["ADMIN_CHAT_ID"]) if os.environ.get("ADMIN_CHAT_ID") else None
GOOGLE_SHEETS_ID: str = os.environ.get("GOOGLE_SHEETS_ID", "")

# Google Sheets — AI Product Knowledge (категория «Пряжа»), отдельная таблица от GOOGLE_SHEETS_ID (заказы)
GOOGLE_SHEETS_PRODUCT_KNOWLEDGE_ID: str = os.environ.get("GOOGLE_SHEETS_PRODUCT_KNOWLEDGE_ID", "")

# chat_id не секрет (в отличие от токенов) — логируем открыто для диагностики уведомлений.
logger.info("Config loaded: ADMIN_CHAT_ID=%s", ADMIN_CHAT_ID if ADMIN_CHAT_ID is not None else "NOT SET")

# --- Claude API parameters (frozen per PROJECT_MEMORY.md) ---
CLAUDE_MODEL = "claude-sonnet-4-6"
CLAUDE_MAX_TOKENS = 1024
CLAUDE_TEMPERATURE = 0.3

# --- Conversation history limit (per PROJECT_MEMORY.md) ---
MAX_HISTORY = 20  # last 10 exchanges

# --- Catalog path ---
CATALOG_PATH = Path(
    os.environ.get("CATALOG_PATH", "../02_PRODUCT_DATABASE/catalog_v1.csv")
)

# --- Order storage ---
_BASE_DIR = Path(__file__).resolve().parent

# Локальный журнал заказов (fallback, работает без внешней настройки).
# Содержит телефоны клиентов — файл в .gitignore, не коммитить.
ORDERS_LOG_PATH = Path(
    os.environ.get("ORDERS_LOG_PATH") or (_BASE_DIR / "data" / "orders_local.jsonl")
)

# Сервисный аккаунт Google — JSON-ключ. Пока не задан → используется локальный JSONL.
GOOGLE_CREDENTIALS_PATH = (
    Path(os.environ["GOOGLE_CREDENTIALS_PATH"])
    if os.environ.get("GOOGLE_CREDENTIALS_PATH")
    else None
)
