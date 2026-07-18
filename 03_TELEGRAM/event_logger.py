"""Event Logger — журнал бизнес-событий.

Отделяет бизнес-события (заказ создан, эскалация, товар показан) от
технических логов (logger.py). Вызывающий код не знает, куда пишется
событие — сейчас это stdout с префиксом EVENT, позже без изменений
вызовов можно направить в Google Sheets `analytics` / БД.
"""
import json

from logger import logger


def log_event(event_type: str, **fields) -> None:
    payload = json.dumps(fields, ensure_ascii=False, default=str)
    logger.info("EVENT %s %s", event_type, payload)
