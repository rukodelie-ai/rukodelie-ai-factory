from aiogram import F, Router
from aiogram.filters import CommandStart
from aiogram.types import Message

from ai_seller import get_ai_response
from logger import logger

router = Router()

WELCOME_MESSAGE = """
Привет!
Я Алина, AI-консультант Рукоделие.kz.

Помогу подобрать товары, проверить наличие и оформить заказ.

Что ищете?
"""

# RAM: история диалогов {user_id: list[dict]}
_history: dict[int, list[dict]] = {}


@router.message(CommandStart())
async def cmd_start(message: Message) -> None:
    logger.info("CMD_START fired")
    user_id = message.from_user.id
    _history[user_id] = []
    logger.info("New session: user_id=%d", user_id)
    await message.answer(WELCOME_MESSAGE)


@router.message(F.text)
async def handle_text(message: Message) -> None:
    logger.info("HANDLE_TEXT fired")
    user_id = message.from_user.id
    logger.info("Text message: user_id=%d", user_id)
    history = _history.get(user_id, [])
    ai_text, updated_history = await get_ai_response(history, message.text)
    _history[user_id] = updated_history
    await message.answer(ai_text)
