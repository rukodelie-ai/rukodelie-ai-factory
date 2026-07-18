"""LocalOrderStorage — первая рабочая реализация Storage (JSONL).

Пишет каждый заказ строкой JSON в локальный файл. Не требует внешних
сервисов — с ней первый автоматический заказ возможен уже сегодня.
Заменяется на SheetsOrderStorage без изменения AI Seller (Dependency Inversion).
"""
import json
from dataclasses import asdict
from pathlib import Path

from config import ORDERS_LOG_PATH
from logger import logger

from .model import Order


class LocalOrderStorage:
    def __init__(self, path: Path = ORDERS_LOG_PATH) -> None:
        self.path = path
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def save_order(self, order: Order) -> str:
        record = asdict(order)
        record["channel"] = order.channel.value
        record["status"] = order.status.value
        record["subtotal_kzt"] = order.subtotal_kzt
        record["total_kzt"] = order.total_kzt
        with open(self.path, "a", encoding="utf-8") as f:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")
        logger.info("Order saved locally: %s (%.0f₸)", order.order_id, order.total_kzt)
        return order.order_id
