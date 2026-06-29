from pathlib import Path
from typing import Optional

from anthropic import AsyncAnthropic

from catalog import get_catalog_text
from config import (
    ANTHROPIC_API_KEY,
    CLAUDE_MAX_TOKENS,
    CLAUDE_MODEL,
    CLAUDE_TEMPERATURE,
    MAX_HISTORY,
)
from logger import logger

_client = AsyncAnthropic(api_key=ANTHROPIC_API_KEY)

_SYSTEM_PROMPT_PATH = Path(__file__).parent.parent / "01_AI_SELLER" / "SYSTEM_PROMPT.md"

_cached_system_prompt: Optional[str] = None


def _extract_base_prompt() -> str:
    text = _SYSTEM_PROMPT_PATH.read_text(encoding="utf-8")
    start_tag, end_tag = "<system_prompt>", "</system_prompt>"
    start = text.find(start_tag)
    end = text.find(end_tag)
    if start == -1 or end == -1:
        raise RuntimeError("SYSTEM_PROMPT.md: <system_prompt> block not found")
    return text[start + len(start_tag):end].strip()


def _build_system_prompt() -> str:
    global _cached_system_prompt
    if _cached_system_prompt is None:
        catalog = get_catalog_text()
        _cached_system_prompt = (
            _extract_base_prompt()
            + f"\n\n<catalog>\n{catalog}\n</catalog>"
        )
        logger.info("System prompt cached: %d chars", len(_cached_system_prompt))
    return _cached_system_prompt


async def get_ai_response(
    history: list[dict],
    user_message: str,
) -> tuple[str, list[dict]]:
    """
    Returns (ai_text, updated_history).
    history — сообщения ДО текущего запроса пользователя.
    """
    messages = list(history) + [{"role": "user", "content": user_message}]

    try:
        response = await _client.messages.create(
            model=CLAUDE_MODEL,
            max_tokens=CLAUDE_MAX_TOKENS,
            temperature=CLAUDE_TEMPERATURE,
            system=_build_system_prompt(),
            messages=messages[-MAX_HISTORY:],
        )
        ai_text = response.content[0].text
        logger.info(
            "Claude OK: in=%d out=%d tokens",
            response.usage.input_tokens,
            response.usage.output_tokens,
        )
    except Exception as exc:
        logger.error("Claude API error: %s", exc)
        return (
            "Извините, у меня технические неполадки. Попробуйте написать снова через минуту.",
            list(history),
        )

    return ai_text, messages + [{"role": "assistant", "content": ai_text}]
