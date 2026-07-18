"""Dialog Memory — единый интерфейс истории диалогов.

AI Seller и роутеры работают с историей через этот модуль и не знают,
где она хранится. Первая реализация — RAM (решение #13: SQLite не нужен
до ~100 сессий; при рестарте история сбрасывается — допустимо для MVP).

Замена на Redis / БД не затрагивает AI Seller (Dependency Inversion).
"""
from typing import Protocol

from config import MAX_HISTORY


class DialogMemory(Protocol):
    def get_history(self, user_id: int) -> list[dict]: ...
    def set_history(self, user_id: int, history: list[dict]) -> None: ...
    def reset(self, user_id: int) -> None: ...


class RamDialogMemory:
    def __init__(self) -> None:
        self._store: dict[int, list[dict]] = {}

    def get_history(self, user_id: int) -> list[dict]:
        return self._store.get(user_id, [])

    def set_history(self, user_id: int, history: list[dict]) -> None:
        # Храним не больше MAX_HISTORY последних сообщений.
        self._store[user_id] = history[-MAX_HISTORY:]

    def reset(self, user_id: int) -> None:
        self._store[user_id] = []


# Единственный экземпляр памяти диалогов для всего бота.
memory: DialogMemory = RamDialogMemory()
