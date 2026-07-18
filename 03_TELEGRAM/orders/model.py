"""Order Model — доменная модель заказа Rukodelie.kz.

Бизнес-логика (утверждена в PROJECT_MEMORY / брифе владельца):
  • магазин и сайт используют розничную цену;
  • Kaspi = розничная + 15 %;
  • возвраты учитываются (is_return + статус RETURNED);
  • total считается на лету из позиций и канала.

Модель ничего не знает о том, где заказ хранится (Dependency Inversion).
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import Enum

# Наценка канала Kaspi к розничной цене.
KASPI_MARKUP = 0.15


class SalesChannel(str, Enum):
    SITE = "site"    # интернет-магазин — розничная цена
    STORE = "store"  # розничный магазин — розничная цена
    KASPI = "kaspi"  # Kaspi — розница + 15 %


class OrderStatus(str, Enum):
    NEW = "new"
    CONFIRMED = "confirmed"
    PAID = "paid"
    ASSEMBLING = "assembling"
    SHIPPED = "shipped"
    DELIVERED = "delivered"
    CLOSED = "closed"
    RETURNED = "returned"


def _generate_order_id() -> str:
    # Уникален в пределах микросекунды — достаточно для MVP-объёмов.
    return "R-" + datetime.now().strftime("%Y%m%d-%H%M%S-%f")


@dataclass
class OrderItem:
    product: str
    qty: int
    color: str = ""
    retail_price_kzt: float = 0.0  # розничная цена за единицу из каталога

    @property
    def line_total_kzt(self) -> float:
        return round(self.retail_price_kzt * self.qty, 2)


@dataclass
class Order:
    client_name: str
    phone: str
    items: list[OrderItem]
    channel: SalesChannel = SalesChannel.SITE
    tg_chat_id: int | None = None
    status: OrderStatus = OrderStatus.NEW
    is_return: bool = False
    comment: str = ""
    order_id: str = ""
    created_at: str = ""

    def __post_init__(self) -> None:
        if not self.order_id:
            self.order_id = _generate_order_id()
        if not self.created_at:
            self.created_at = datetime.now().isoformat(timespec="seconds")

    @property
    def channel_multiplier(self) -> float:
        return 1.0 + KASPI_MARKUP if self.channel == SalesChannel.KASPI else 1.0

    @property
    def subtotal_kzt(self) -> float:
        """Сумма позиций по розничной цене, без наценки канала."""
        return round(sum(item.line_total_kzt for item in self.items), 2)

    @property
    def total_kzt(self) -> float:
        """Итог с учётом канала (Kaspi = +15 %)."""
        return round(self.subtotal_kzt * self.channel_multiplier, 2)
