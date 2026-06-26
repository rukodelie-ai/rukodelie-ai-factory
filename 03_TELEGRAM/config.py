import os
from pathlib import Path
from dotenv import load_dotenv

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
