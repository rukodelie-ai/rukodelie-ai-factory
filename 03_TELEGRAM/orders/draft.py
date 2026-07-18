"""Минимальная FSM оформления заказа.

Разговор ведёт AI Seller (Алина) сам — здесь только:
  • состояние сессии продажи (защита от повторного оформления);
  • допустимые переходы статуса заказа (жизненный цикл из PROJECT_MEMORY).

Состояние сессии живёт в RAM (решение #13 — как и история диалога).
"""
from enum import Enum

from .model import OrderStatus


class SaleState(str, Enum):
    BROWSING = "browsing"          # клиент выбирает / консультируется
    ORDER_PLACED = "order_placed"  # create_order сработал, заказ сохранён


# Жизненный цикл заказа: new → confirmed → paid → assembling → shipped
#                          → delivered → closed; RETURNED — из любого активного.
_ALLOWED_TRANSITIONS: dict[OrderStatus, set[OrderStatus]] = {
    OrderStatus.NEW: {OrderStatus.CONFIRMED, OrderStatus.RETURNED},
    OrderStatus.CONFIRMED: {OrderStatus.PAID, OrderStatus.RETURNED},
    OrderStatus.PAID: {OrderStatus.ASSEMBLING, OrderStatus.RETURNED},
    OrderStatus.ASSEMBLING: {OrderStatus.SHIPPED, OrderStatus.RETURNED},
    OrderStatus.SHIPPED: {OrderStatus.DELIVERED, OrderStatus.RETURNED},
    OrderStatus.DELIVERED: {OrderStatus.CLOSED, OrderStatus.RETURNED},
    OrderStatus.CLOSED: set(),
    OrderStatus.RETURNED: set(),
}


def can_transition(src: OrderStatus, dst: OrderStatus) -> bool:
    return dst in _ALLOWED_TRANSITIONS.get(src, set())


# --- Состояние сессии продажи (RAM) ---
_session: dict[int, SaleState] = {}


def get_state(user_id: int) -> SaleState:
    return _session.get(user_id, SaleState.BROWSING)


def set_state(user_id: int, state: SaleState) -> None:
    _session[user_id] = state


def reset_state(user_id: int) -> None:
    _session[user_id] = SaleState.BROWSING
