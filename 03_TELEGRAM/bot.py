import asyncio

from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage

from catalog import get_product_knowledge_rows
from config import TELEGRAM_BOT_TOKEN
from logger import logger
from routers import all_routers


def _check_product_knowledge_source() -> None:
    """Диагностика при старте: подтверждает, что AI Product Knowledge читается из Google
    Sheets. Ни на что не влияет — не используется в диалогах Алины, сбой не блокирует бота."""
    try:
        rows = get_product_knowledge_rows()
        logger.info("AI Product Knowledge source: Google Sheets, %d строк доступно", len(rows))
    except Exception as exc:  # noqa: BLE001
        logger.warning("AI Product Knowledge (Google Sheets) недоступен при старте: %s", exc)


async def main() -> None:
    bot = Bot(token=TELEGRAM_BOT_TOKEN)
    dp = Dispatcher(storage=MemoryStorage())

    for router in all_routers:
        dp.include_router(router)

    _check_product_knowledge_source()

    logger.info("Bot starting...")
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
