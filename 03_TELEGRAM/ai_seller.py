from pathlib import Path
from typing import Awaitable, Callable, Optional

from anthropic import AsyncAnthropic

from catalog import get_product_knowledge_text
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

# Максимум циклов tool-use в одном ответе — защита от зацикливания.
_MAX_TOOL_LOOPS = 5

# Колбэк оформления заказа. AI Seller НЕ знает, где хранится заказ —
# реализацию инжектирует роутер (Dependency Inversion). Принимает распарсенный
# ввод инструмента, возвращает текст-результат для Claude (например, "Заказ ... сохранён").
CreateOrderHandler = Callable[[dict], Awaitable[str]]

# Колбэк отправки фото товара. AI Seller НЕ знает про Telegram Bot API —
# реализацию инжектирует роутер. Принимает точные данные варианта из tool input.
ShowPhotoHandler = Callable[[dict], Awaitable[str]]

# Инструмент оформления заказа (Claude tool-use).
CREATE_ORDER_TOOL = {
    "name": "create_order",
    "description": (
        "Оформить заказ. Вызывай ТОЛЬКО когда клиент согласился оформить заказ и ты "
        "собрал: товар(ы) с количеством, имя и телефон клиента. Розничная цена берётся "
        "из каталога; для канала kaspi наценка +15% применяется автоматически. "
        "Не запрашивай реквизиты оплаты — оплату оформляет менеджер."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "client_name": {"type": "string", "description": "Имя клиента"},
            "phone": {"type": "string", "description": "Телефон клиента для связи"},
            "channel": {
                "type": "string",
                "enum": ["site", "store", "kaspi"],
                "description": "Канал продажи. По умолчанию site (розничная цена).",
            },
            "comment": {"type": "string", "description": "Комментарий/пожелания (необязательно)"},
            "items": {
                "type": "array",
                "description": "Позиции заказа",
                "items": {
                    "type": "object",
                    "properties": {
                        "product": {"type": "string", "description": "Название товара из каталога"},
                        "qty": {"type": "integer", "description": "Количество"},
                        "color": {"type": "string", "description": "Цвет/вариант, если применимо"},
                        "retail_price_kzt": {
                            "type": "number",
                            "description": "Розничная цена за единицу из каталога, ₸",
                        },
                    },
                    "required": ["product", "qty"],
                },
            },
        },
        "required": ["client_name", "phone", "items"],
    },
}

_ORDER_TOOL_HINT = (
    "\n\n<order_tool>\n"
    "Когда клиент согласился оформить заказ и собраны товар(ы) с количеством, имя и "
    "телефон — вызови инструмент create_order. Розничная цена — из каталога; для Kaspi "
    "наценка +15% применяется автоматически. Реквизиты оплаты не называй — это менеджер.\n"
    "</order_tool>"
)

# Инструмент отправки фото товара (Claude tool-use).
SHOW_PHOTO_TOOL = {
    "name": "show_product_photo",
    "description": (
        "Отправить клиенту фото ОДНОГО конкретного цветового варианта товара из каталога. "
        "Поля product, color_code и color_name ДОЛЖНЫ быть точно скопированы из одного "
        "варианта блока <catalog>. Никогда не подставляй другой товар или другой цвет."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "product": {"type": "string", "description": "Точное название товара из каталога"},
            "color_code": {"type": "string", "description": "Точный код выбранного цвета из каталога"},
            "color_name": {"type": "string", "description": "Точное название выбранного цвета из каталога"},
            "characteristic_key": {
                "type": "string",
                "description": "characteristic_key выбранного варианта, только если он доступен в контексте",
            },
        },
        "required": ["product", "color_code", "color_name"],
    },
}

_PHOTO_TOOL_HINT = (
    "\n\n<photo_tool>\n"
    "Правила вызова show_product_photo — строго соблюдай:\n"
    "1. Вызывай ТОЛЬКО когда однозначно понятны товар и ОДИН конкретный цвет. "
    "product, color_code и color_name дословно копируй из одной строки варианта <catalog>.\n"
    "2. Если клиент назвал товар, которого нет в каталоге (например, \"Jeans\", \"Dolce\") — "
    "НЕ вызывай инструмент вообще и НЕ подставляй вместо него другой товар, включая "
    "товар, который ты уже показывал раньше в этом диалоге. Прямо скажи клиенту, что "
    "этого товара нет, и при желании предложи то, что реально есть в каталоге.\n"
    "3. Никогда не заменяй выбранный цвет ближайшим, похожим или первым доступным цветом. "
    "Если точный цвет не определён — сначала задай уточняющий вопрос.\n"
    "4. Если запрос расплывчатый (\"пряжа для сумки\", \"что-то для вязания шапки\") и "
    "подходит несколько товаров или цветов ИЛИ ты не уверен, какой именно нужен — НЕ вызывай "
    "инструмент. Сначала перечисли текстом подходящие варианты из каталога (сколько "
    "реально есть, до 5) и спроси, какой интересует. Вызывай show_product_photo только "
    "после того, как клиент выбрал конкретный товар.\n"
    "5. Лучше уточнить у клиента, чем показать фото товара, в котором не уверен.\n"
    "6. Если клиент явно просит фото (например, «покажи фото», «покажи фотографию», "
    "«как выглядит», «покажи его», «а второй?») и товар с конкретным цветом уже "
    "однозначно определён в контексте диалога — ОБЯЗАТЕЛЬНО вызови show_product_photo. "
    "Не отвечай «Фото сейчас уточняется» и не обещай показать фото позже, если все "
    "обязательные поля инструмента уже известны.\n"
    "7. Если клиент просит «покажи оба», «покажи оба мотка» или аналогично просит "
    "несколько уже однозначно выбранных вариантов — вызови show_product_photo отдельно "
    "для КАЖДОГО варианта, передавая точные product, color_code и color_name каждого.\n"
    "</photo_tool>"
)


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
        catalog = get_product_knowledge_text()
        _cached_system_prompt = (
            _extract_base_prompt()
            + f"\n\n<catalog>\n{catalog}\n</catalog>"
            + _ORDER_TOOL_HINT
            + _PHOTO_TOOL_HINT
        )
        logger.info("System prompt cached: %d chars", len(_cached_system_prompt))
    return _cached_system_prompt


def _first_text(content) -> str:
    for block in content:
        if getattr(block, "type", None) == "text":
            return block.text
    return "Готово."


async def _handle_tool_use(
    content,
    on_create_order: Optional[CreateOrderHandler],
    on_show_photo: Optional[ShowPhotoHandler],
) -> list[dict]:
    """Выполняет вызванные инструменты, возвращает блоки tool_result для Claude."""
    results: list[dict] = []
    for block in content:
        if getattr(block, "type", None) != "tool_use":
            continue
        if block.name == "create_order" and on_create_order:
            try:
                result_text = await on_create_order(dict(block.input))
            except Exception as exc:  # noqa: BLE001
                logger.error("create_order handler failed: %s", exc)
                result_text = "Ошибка: заказ не сохранён. Извинись и предложи повторить."
            results.append({
                "type": "tool_result",
                "tool_use_id": block.id,
                "content": result_text,
            })
        elif block.name == "show_product_photo" and on_show_photo:
            try:
                result_text = await on_show_photo(dict(block.input))
            except Exception as exc:  # noqa: BLE001
                logger.error("show_product_photo handler failed: %s", exc)
                result_text = "Фото не отправлено. Продолжи словесным описанием товара."
            results.append({
                "type": "tool_result",
                "tool_use_id": block.id,
                "content": result_text,
            })
        else:
            results.append({
                "type": "tool_result",
                "tool_use_id": block.id,
                "content": "Неизвестный инструмент.",
                "is_error": True,
            })
    return results


async def get_ai_response(
    history: list[dict],
    user_message: str,
    on_create_order: Optional[CreateOrderHandler] = None,
    on_show_photo: Optional[ShowPhotoHandler] = None,
) -> tuple[str, list[dict]]:
    """
    Returns (ai_text, updated_history).
    history — сообщения ДО текущего запроса пользователя.
    on_create_order — колбэк оформления заказа (инжектируется роутером). Если None,
    инструмент create_order не предлагается Claude.
    on_show_photo — колбэк отправки фото товара (инжектируется роутером). Если None,
    инструмент show_product_photo не предлагается Claude.

    В возвращаемую историю попадают только текстовые ходы (user + финальный assistant);
    промежуточный обмен tool_use/tool_result не сохраняется — RAM-история остаётся
    из строк и не рвётся при обрезке до MAX_HISTORY.
    """
    tools = []
    if on_create_order:
        tools.append(CREATE_ORDER_TOOL)
    if on_show_photo:
        tools.append(SHOW_PHOTO_TOOL)
    working = list(history) + [{"role": "user", "content": user_message}]

    try:
        ai_text = "Готово."
        for _ in range(_MAX_TOOL_LOOPS):
            response = await _client.messages.create(
                model=CLAUDE_MODEL,
                max_tokens=CLAUDE_MAX_TOKENS,
                temperature=CLAUDE_TEMPERATURE,
                system=_build_system_prompt(),
                messages=working[-MAX_HISTORY:],
                tools=tools,
            )
            logger.info(
                "Claude OK: in=%d out=%d tokens stop=%s",
                response.usage.input_tokens,
                response.usage.output_tokens,
                response.stop_reason,
            )
            if response.stop_reason == "tool_use" and (on_create_order or on_show_photo):
                working.append({"role": "assistant", "content": response.content})
                results = await _handle_tool_use(response.content, on_create_order, on_show_photo)
                working.append({"role": "user", "content": results})
                continue
            ai_text = _first_text(response.content)
            break
    except Exception as exc:
        logger.error("Claude API error: %s", exc)
        return (
            "Извините, у меня технические неполадки. Попробуйте написать снова через минуту.",
            list(history),
        )

    updated_history = list(history) + [
        {"role": "user", "content": user_message},
        {"role": "assistant", "content": ai_text},
    ]
    return ai_text, updated_history
