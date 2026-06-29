import csv
from pathlib import Path

from config import CATALOG_PATH
from logger import logger


def get_catalog_text() -> str:
    path = (Path(__file__).parent.parent / CATALOG_PATH).resolve() if not CATALOG_PATH.is_absolute() else CATALOG_PATH
    if not path.exists():
        logger.warning("Catalog not found: %s", path)
        return "Каталог временно недоступен."

    lines: list[str] = []
    with open(path, encoding="utf-8") as f:
        for row in csv.DictReader(f):
            if row.get("status", "").strip() != "published":
                continue
            line = (
                f"{row['name']} | {row['category_l1']} | {row['price_kzt']}₸"
                f" | Остаток: {row['stock']} {row['unit']}"
                f" | Продажа: {row['sale_mode']}, мин: {row['min_sale_qty']}"
            )
            if row.get("pack_qty"):
                line += f", упак: {row['pack_qty']}"
            if row.get("colors_available") and row["colors_available"] != "-":
                line += f" | Цвета: {row['colors_available']}"
            lines.append(line)

    if not lines:
        return "Нет опубликованных товаров."

    return "КАТАЛОГ (только published):\n" + "\n".join(lines)
