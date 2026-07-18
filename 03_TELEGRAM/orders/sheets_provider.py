"""SheetsOrderStorage — реализация Storage поверх Google Sheets (gspread).

Включается автоматически, когда заданы GOOGLE_SHEETS_ID и GOOGLE_CREDENTIALS_PATH
(сервисный аккаунт). Пишет одну строку на позицию заказа; строки одного заказа
объединены общим order_id — совместимо со схемой листа `orders` из PROJECT_MEMORY.

AI Seller об этом провайдере не знает — выбор делает orders/storage.py.
"""
import gspread
from google.oauth2.service_account import Credentials

from config import GOOGLE_CREDENTIALS_PATH, GOOGLE_SHEETS_ID
from logger import logger

from .model import Order

_SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]
_WORKSHEET = "orders"
_HEADER = [
    "order_id", "created_at", "client_name", "phone",
    "product", "qty", "color", "retail_price_kzt", "line_total_kzt",
    "channel", "order_total_kzt", "status", "is_return", "comment", "tg_chat_id",
]


class SheetsOrderStorage:
    def __init__(self) -> None:
        creds = Credentials.from_service_account_file(
            str(GOOGLE_CREDENTIALS_PATH), scopes=_SCOPES
        )
        client = gspread.authorize(creds)
        spreadsheet = client.open_by_key(GOOGLE_SHEETS_ID)
        self._ws = self._ensure_worksheet(spreadsheet)

    def _ensure_worksheet(self, spreadsheet):
        try:
            return spreadsheet.worksheet(_WORKSHEET)
        except gspread.WorksheetNotFound:
            ws = spreadsheet.add_worksheet(_WORKSHEET, rows=1000, cols=len(_HEADER))
            ws.append_row(_HEADER, value_input_option="USER_ENTERED")
            logger.info("Created '%s' worksheet with header", _WORKSHEET)
            return ws

    def save_order(self, order: Order) -> str:
        rows = [
            [
                order.order_id, order.created_at, order.client_name, order.phone,
                item.product, item.qty, item.color,
                item.retail_price_kzt, item.line_total_kzt,
                order.channel.value, order.total_kzt, order.status.value,
                "yes" if order.is_return else "no", order.comment, order.tg_chat_id or "",
            ]
            for item in order.items
        ]
        self._ws.append_rows(rows, value_input_option="USER_ENTERED")
        logger.info("Order saved to Sheets: %s (%d rows)", order.order_id, len(rows))
        return order.order_id
