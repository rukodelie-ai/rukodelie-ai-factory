"""product_knowledge_sheets.py — чтение AI Product Knowledge (категория «Пряжа») из Google Sheets.

Источник данных — GOOGLE_SHEETS_PRODUCT_KNOWLEDGE_ID (отдельная таблица от GOOGLE_SHEETS_ID,
который используется для заказов, см. orders/sheets_provider.py). Тот же паттерн подключения
(gspread + сервисный аккаунт), что уже используется в проекте.

Модуль читает данные один раз, кэширует их в памяти и формирует товарный контекст
для AI Seller. Внутренняя разбивка остатков по складам в контекст не передаётся.
"""
import gspread
from google.oauth2.service_account import Credentials
from typing import Optional

from config import GOOGLE_CREDENTIALS_PATH, GOOGLE_SHEETS_PRODUCT_KNOWLEDGE_ID
from logger import logger

_SCOPES = ["https://www.googleapis.com/auth/spreadsheets.readonly"]
_WORKSHEET = "AI_Product_Knowledge_Yarn_V1"
_cached_rows: Optional[list[dict]] = None


def get_product_knowledge_rows() -> list[dict]:
    """Возвращает все строки AI Product Knowledge (товар x цвет) из Google Sheets.

    Значения читаются без авто-приведения типов (numericise_ignore=["all"]), чтобы не терять
    ведущие нули в code_1c/color_code — те же поля, что в исходном CSV.
    """
    global _cached_rows
    if _cached_rows is not None:
        return _cached_rows

    creds = Credentials.from_service_account_file(
        str(GOOGLE_CREDENTIALS_PATH), scopes=_SCOPES
    )
    client = gspread.authorize(creds)
    spreadsheet = client.open_by_key(GOOGLE_SHEETS_PRODUCT_KNOWLEDGE_ID)
    ws = spreadsheet.worksheet(_WORKSHEET)
    _cached_rows = ws.get_all_records(numericise_ignore=["all"])
    logger.info("AI Product Knowledge (Google Sheets): загружено %d строк", len(_cached_rows))
    return _cached_rows


def _positive_stock(value: object) -> bool:
    """Доступность варианта определяется только готовым полем stock_total."""
    try:
        return float(str(value).replace(",", ".")) > 0
    except (TypeError, ValueError):
        return False


def get_product_knowledge_text() -> str:
    """Формирует компактный каталог для AI Seller из строк Google Sheets.

    В каталог попадают только варианты с положительным stock_total. Внутренняя
    разбивка stock_* намеренно не читается и не передаётся модели или клиенту.
    """
    products: dict[tuple[str, str], dict] = {}

    for row in get_product_knowledge_rows():
        if not _positive_stock(row.get("stock_total")):
            continue

        key = (str(row.get("ref_key", "")), str(row.get("code_1c", "")))
        product = products.setdefault(key, {
            "name": str(row.get("full_name", "")).strip(),
            "brand": str(row.get("brand", "")).strip(),
            "series": str(row.get("series", "")).strip(),
            "code_1c": str(row.get("code_1c", "")).strip(),
            "price": str(row.get("price_retail", "")).strip(),
            "composition": str(row.get("composition", "")).strip(),
            "weight": str(row.get("weight_g", "")).strip(),
            "length": str(row.get("length", "")).strip(),
            "variants": [],
        })
        color_code = str(row.get("color_code", "")).strip()
        color_name = str(row.get("color_name", "")).strip()
        stock_total = str(row.get("stock_total", "")).strip()
        color = " / ".join(part for part in (color_code, color_name) if part)
        product["variants"].append(f"{color or 'без цвета'}: {stock_total}")

    if not products:
        return "Нет товаров в наличии."

    lines = [
        "КАТАЛОГ ИЗ GOOGLE SHEETS (только варианты с stock_total > 0). "
        "Указан общий остаток; внутренние склады клиенту не упоминать:"
    ]
    for product in products.values():
        details = [
            product["name"],
            f"бренд: {product['brand']}",
            f"серия: {product['series']}",
            f"код 1С: {product['code_1c']}",
            f"цена: {product['price']}₸",
            f"состав: {product['composition']}",
            f"вес: {product['weight']} г",
            f"длина: {product['length']}",
            "цвета (код / название: общий остаток): " + "; ".join(product["variants"]),
        ]
        lines.append(" | ".join(details))

    return "\n".join(lines)
