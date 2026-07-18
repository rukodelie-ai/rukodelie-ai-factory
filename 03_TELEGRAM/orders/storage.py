"""Storage Layer — единый интерфейс сохранения заказов.

AI Seller вызывает только save_order(order) и не знает, куда пишется заказ.
Провайдер выбирается один раз при первом сохранении:
  • Google Sheets — если заданы GOOGLE_SHEETS_ID и GOOGLE_CREDENTIALS_PATH;
  • иначе — локальный JSONL (работает без внешней настройки).

Смена хранилища (Sheets → PostgreSQL / CRM / ERP) не затрагивает AI Seller.
"""
from __future__ import annotations

from typing import Protocol

from config import GOOGLE_CREDENTIALS_PATH, GOOGLE_SHEETS_ID, ORDERS_LOG_PATH
from event_logger import log_event
from logger import logger

from .model import Order


class OrderStorage(Protocol):
    def save_order(self, order: Order) -> str: ...


_backend: OrderStorage | None = None


def _select_backend() -> OrderStorage:
    sheets_ready = bool(
        GOOGLE_SHEETS_ID
        and GOOGLE_CREDENTIALS_PATH
        and GOOGLE_CREDENTIALS_PATH.exists()
    )
    if sheets_ready:
        try:
            from .sheets_provider import SheetsOrderStorage

            backend = SheetsOrderStorage()
            logger.info("Order storage backend: Google Sheets")
            return backend
        except Exception as exc:  # noqa: BLE001 — деградируем, не падаем
            logger.error("Sheets storage init failed → local fallback: %s", exc)

    from .local_provider import LocalOrderStorage

    logger.info("Order storage backend: local JSONL (%s)", ORDERS_LOG_PATH)
    return LocalOrderStorage()


def save_order(order: Order) -> str:
    """Сохранить заказ в текущем хранилище. Возвращает order_id."""
    global _backend
    if _backend is None:
        _backend = _select_backend()
    order_id = _backend.save_order(order)
    log_event(
        "order_saved",
        order_id=order_id,
        backend=type(_backend).__name__,
        total_kzt=order.total_kzt,
        channel=order.channel.value,
    )
    return order_id
