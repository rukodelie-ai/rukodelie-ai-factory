import asyncio
import re

from aiogram import F, Router
from aiogram.filters import CommandStart
from aiogram.types import BufferedInputFile, Message

from ai_seller import get_ai_response
from catalog import get_product_photo
from config import ADMIN_CHAT_ID
from dialog_memory import memory
from event_logger import log_event
from logger import logger
from orders import Order, OrderItem, SalesChannel, save_order
from orders.draft import SaleState, reset_state, set_state

router = Router()

_WORD_RE = re.compile(r"[а-яёa-z0-9]+", re.IGNORECASE)


def _mentions_product(user_text: str, product_name: str, history: list[dict]) -> bool:
    """Проверяет, что товар есть в текущем или недавнем контексте диалога.

    Последние сообщения нужны для follow-up фраз вроде «покажи оба» или «а второй?»,
    где клиент не повторяет название. Ограниченное окно сохраняет защиту от
    подстановки постороннего товара из старой части переписки.
    """
    def tokens(s: str) -> set[str]:
        return {w for w in _WORD_RE.findall(s.lower()) if len(w) >= 3}

    product_tokens = tokens(product_name)
    if tokens(user_text) & product_tokens:
        return True

    recent_context = " ".join(
        str(item.get("content", ""))
        for item in history[-6:]
        if isinstance(item.get("content"), str)
    )
    normalized_product = " ".join(product_name.casefold().split())
    normalized_context = " ".join(recent_context.casefold().split())
    return normalized_product in normalized_context

WELCOME_MESSAGE = """
Привет!
Я Алина, AI-консультант Рукоделие.kz.

Помогу подобрать товары, проверить наличие и оформить заказ.

Что ищете?
"""


@router.message(CommandStart())
async def cmd_start(message: Message) -> None:
    user_id = message.from_user.id
    chat_id = message.chat.id
    memory.reset(user_id)
    reset_state(user_id)
    logger.info(
        "New session: user_id=%d chat_id=%d ADMIN_CHAT_ID=%s",
        user_id, chat_id, ADMIN_CHAT_ID,
    )
    await message.answer(WELCOME_MESSAGE)


def _build_order(user_id: int, data: dict) -> Order:
    items = [
        OrderItem(
            product=item["product"],
            qty=int(item["qty"]),
            color=item.get("color", ""),
            retail_price_kzt=float(item.get("retail_price_kzt") or 0),
        )
        for item in data.get("items", [])
    ]
    return Order(
        client_name=data["client_name"],
        phone=data["phone"],
        items=items,
        channel=SalesChannel(data.get("channel", "site")),
        comment=data.get("comment", ""),
        tg_chat_id=user_id,
    )


async def _notify_manager(message: Message, order: Order) -> None:
    user_id = message.from_user.id
    chat_id = message.chat.id
    logger.info(
        "Notify manager attempt: order_id=%s user_id=%d chat_id=%d ADMIN_CHAT_ID=%s",
        order.order_id, user_id, chat_id, ADMIN_CHAT_ID,
    )
    if not ADMIN_CHAT_ID:
        logger.warning(
            "ADMIN_CHAT_ID not set — manager not notified for %s (order remains saved)",
            order.order_id,
        )
        return
    lines = [
        f"🛒 Новый заказ {order.order_id}",
        f"Клиент: {order.client_name}",
        f"Телефон: {order.phone}",
        f"Канал: {order.channel.value}",
        "",
    ]
    for item in order.items:
        color = f" ({item.color})" if item.color else ""
        lines.append(f"• {item.product} × {item.qty}{color} — {item.line_total_kzt:.0f}₸")
    lines.append("")
    lines.append(f"Итого: {order.total_kzt:.0f}₸")
    if order.comment:
        lines.append(f"Комментарий: {order.comment}")
    lines.append(f"TG chat_id: {order.tg_chat_id}")
    try:
        await message.bot.send_message(ADMIN_CHAT_ID, "\n".join(lines))
    except Exception as exc:  # noqa: BLE001
        logger.error(
            "Manager notify failed: order_id=%s ADMIN_CHAT_ID=%s error=%s (order remains saved)",
            order.order_id, ADMIN_CHAT_ID, exc,
        )


@router.message(F.text)
async def handle_text(message: Message) -> None:
    user_id = message.from_user.id
    chat_id = message.chat.id
    logger.info(
        "Message: user_id=%d chat_id=%d ADMIN_CHAT_ID=%s",
        user_id, chat_id, ADMIN_CHAT_ID,
    )
    history = memory.get_history(user_id)

    async def on_create_order(data: dict) -> str:
        order = _build_order(user_id, data)
        # Сохранение может блокировать (Sheets) — уводим в поток.
        order_id = await asyncio.to_thread(save_order, order)
        set_state(user_id, SaleState.ORDER_PLACED)
        log_event(
            "order_created",
            order_id=order_id,
            user_id=user_id,
            total_kzt=order.total_kzt,
            channel=order.channel.value,
        )
        await _notify_manager(message, order)
        return (
            f"Заказ {order_id} сохранён. Сумма к оплате: {order.total_kzt:.0f}₸. "
            f"Менеджер уведомлён и свяжется с клиентом. "
            f"Подтверди клиенту оформление и поблагодари."
        )

    async def on_show_photo(data: dict) -> str:
        product_name = str(data.get("product", "")).strip()
        color_code = str(data.get("color_code", "")).strip()
        color_name = str(data.get("color_name", "")).strip()
        characteristic_key = str(data.get("characteristic_key", "")).strip() or None

        if not _mentions_product(message.text, product_name, history):
            logger.warning(
                "Photo tool blocked: product=%r not mentioned in user text=%r (user_id=%d)",
                product_name, message.text, user_id,
            )
            return (
                f"СТОП: клиент в своём последнем сообщении не называл товар "
                f"«{product_name}» — это подстановка. НЕ отправляй его фото и не выдавай "
                f"его за ответ клиенту. Если не уверен, какой именно товар нужен — "
                f"задай клиенту уточняющий вопрос вместо показа фото наугад."
            )

        photo = await asyncio.to_thread(
            get_product_photo,
            product_name,
            color_code,
            characteristic_key,
        )
        if photo is None:
            return (
                f"Фото точного оттенка «{color_code} — {color_name}» временно недоступно. "
                f"НЕ отправляй фото другого цвета и нейтрально сообщи клиенту, что фото "
                f"этого оттенка сейчас недоступно."
            )
        if photo.color_code != color_code or photo.color_name.casefold() != color_name.casefold():
            logger.warning(
                "Photo color mismatch blocked: product=%r requested_code=%r resolved_code=%r",
                product_name,
                color_code,
                photo.color_code,
            )
            return (
                f"Фото точного оттенка «{color_code} — {color_name}» временно недоступно. "
                f"НЕ отправляй фото другого цвета."
            )

        caption = f"{product_name}, цвет {photo.color_code} — {photo.color_name}"
        try:
            image = BufferedInputFile(photo.data, filename=photo.filename)
            await message.answer_photo(image, caption=caption)
        except Exception as exc:  # noqa: BLE001
            logger.error(
                "Photo send failed: user_id=%d product=%s color_code=%s error=%s",
                user_id,
                product_name,
                color_code,
                type(exc).__name__,
            )
            return "Фото не отправилось. Продолжи словесным описанием товара, не упоминая ошибку."
        return f"Фото точного варианта {color_code} — {color_name} отправлено клиенту."

    ai_text, updated_history = await get_ai_response(
        history, message.text, on_create_order=on_create_order, on_show_photo=on_show_photo
    )
    memory.set_history(user_id, updated_history)
    await message.answer(ai_text)
