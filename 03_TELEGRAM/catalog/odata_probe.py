"""
odata_probe.py — Диагностика подключения к 1С OData.

Запуск из папки 03_TELEGRAM/:
    python3 catalog/odata_probe.py

Настройки берутся ТОЛЬКО из .env — никаких паролей в коде.
Требуемые переменные .env:
    ODATA_BASE_URL   — базовый URL без слэша на конце
    ODATA_USERNAME   — логин пользователя 1С
    ODATA_PASSWORD   — пароль пользователя 1С
"""
import base64
import datetime
import os
import sys
import urllib.error
import urllib.request
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv

# .env находится в 03_TELEGRAM/ (родитель catalog/)
_ENV_PATH = Path(__file__).parent.parent / ".env"
load_dotenv(_ENV_PATH)

ODATA_BASE_URL: str = os.environ.get("ODATA_BASE_URL", "").rstrip("/")
ODATA_USERNAME: str = os.environ.get("ODATA_USERNAME", "")
ODATA_PASSWORD: str = os.environ.get("ODATA_PASSWORD", "")

OUTPUT_DIR = Path(__file__).parent.parent.parent / "02_PRODUCT_DATABASE" / "odata_probe"

# Ключевые слова для классификации сущностей (нижний регистр)
_KEYS = {
    "НОМЕНКЛАТУРА":    ["номенклатур", "товар", "продукт", "nomenclature", "product", "item", "goods"],
    "ЦЕНЫ":            ["цен", "price", "прайс"],
    "ОСТАТКИ":         ["остаток", "склад", "запас", "stock", "balance", "warehouse", "товарынаскладах",
                        "остаткитоваров"],
    "ХАРАКТЕРИСТИКИ":  ["характеристик", "characteristic", "вариант"],
    "ЕДИНИЦЫ":         ["единиц", "измерен", "упаковк", "unit", "measure", "packaging"],
    "ГРУППЫ/КАТЕГОРИИ": ["группа", "категория", "раздел", "group", "category", "section",
                         "номенклатурнаягруппа"],
}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _auth_header() -> dict[str, str]:
    token = base64.b64encode(f"{ODATA_USERNAME}:{ODATA_PASSWORD}".encode()).decode()
    return {"Authorization": f"Basic {token}"}


def _fetch(url: str, timeout: int = 30) -> bytes:
    req = urllib.request.Request(url, headers=_auth_header())
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return resp.read()


def _classify(name: str) -> list[str]:
    low = name.lower()
    return [tag for tag, kws in _KEYS.items() if any(k in low for k in kws)]


# ---------------------------------------------------------------------------
# Steps
# ---------------------------------------------------------------------------

def check_env() -> bool:
    missing = [k for k, v in [
        ("ODATA_BASE_URL", ODATA_BASE_URL),
        ("ODATA_USERNAME", ODATA_USERNAME),
        ("ODATA_PASSWORD", ODATA_PASSWORD),
    ] if not v]
    if missing:
        print(f"[ОШИБКА] Не заданы переменные .env: {', '.join(missing)}")
        print(f"         Добавь их в: {_ENV_PATH}")
        return False
    host = ODATA_BASE_URL.split("//")[-1].split("/")[0]
    print(f"[OK] ODATA_BASE_URL задан (хост: {host})")
    return True


def fetch_metadata() -> Optional[bytes]:
    url = f"{ODATA_BASE_URL}/$metadata"
    print(f"[→] Загружаю $metadata ...")
    try:
        data = _fetch(url)
        print(f"[OK] Получено {len(data):,} байт")
        return data
    except urllib.error.HTTPError as exc:
        print(f"[ОШИБКА] HTTP {exc.code}: {exc.reason}")
    except urllib.error.URLError as exc:
        print(f"[ОШИБКА] Сетевая ошибка: {exc.reason}")
    except Exception as exc:
        print(f"[ОШИБКА] {exc}")
    return None


def save_xml(data: bytes) -> Path:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    path = OUTPUT_DIR / "odata_metadata.xml"
    path.write_bytes(data)
    print(f"[OK] XML сохранён → {path}")
    return path


def parse_entities(data: bytes) -> list[dict]:
    root = ET.fromstring(data)
    entities: list[dict] = []
    seen: set[str] = set()
    for elem in root.iter():
        tag = elem.tag
        if tag.endswith("}EntitySet") or tag == "EntitySet":
            name = elem.get("Name", "").strip()
            if name and name not in seen:
                seen.add(name)
                entities.append({"name": name, "tags": _classify(name)})
    return entities


def save_entities(entities: list[dict]) -> Path:
    lines: list[str] = [f"Всего сущностей: {len(entities)}", ""]

    for tag in _KEYS:
        matched = sorted(e["name"] for e in entities if tag in e["tags"])
        if matched:
            lines.append(f"=== {tag} ({len(matched)}) ===")
            lines.extend(f"  {n}" for n in matched)
            lines.append("")

    lines.append(f"=== ВСЕ СУЩНОСТИ ({len(entities)}) ===")
    for e in sorted(entities, key=lambda x: x["name"]):
        suffix = f"  [{', '.join(e['tags'])}]" if e["tags"] else ""
        lines.append(f"  {e['name']}{suffix}")

    path = OUTPUT_DIR / "odata_entities.txt"
    path.write_text("\n".join(lines), encoding="utf-8")
    print(f"[OK] Список сущностей → {path}")
    return path


def write_report(entities: list[dict], status: str) -> Path:
    def by_tag(tag: str) -> list[str]:
        return sorted(e["name"] for e in entities if tag in e["tags"])

    nom   = by_tag("НОМЕНКЛАТУРА")
    price = by_tag("ЦЕНЫ")
    stock = by_tag("ОСТАТКИ")
    chars = by_tag("ХАРАКТЕРИСТИКИ")
    units = by_tag("ЕДИНИЦЫ")
    grps  = by_tag("ГРУППЫ/КАТЕГОРИИ")

    host = ODATA_BASE_URL.split("//")[-1].split("/")[0] if ODATA_BASE_URL else "?"

    def rows(lst: list[str]) -> list[str]:
        return [f"- `{n}`" for n in lst] if lst else ["- *(не найдено)*"]

    sections = [
        "# ODATA PROBE REPORT",
        f"**Дата:** {datetime.date.today()}",
        f"**Хост:** `{host}` *(полный URL без логина/пароля)*",
        f"**Статус подключения:** {status}",
        f"**Всего сущностей найдено:** {len(entities)}",
        "",
        "---",
        "",
        "## Сущности по категориям",
        "",
        f"### Номенклатура / Товары ({len(nom)})",
        *rows(nom), "",
        f"### Цены ({len(price)})",
        *rows(price), "",
        f"### Остатки ({len(stock)})",
        *rows(stock), "",
        f"### Характеристики ({len(chars)})",
        *rows(chars), "",
        f"### Единицы измерения ({len(units)})",
        *rows(units), "",
        f"### Группы / Категории ({len(grps)})",
        *rows(grps), "",
        "---",
        "",
        "## Чеклист готовности к odata_provider.py",
        "",
        f"| Данные | Найдено | Сущности |",
        f"|--------|---------|----------|",
        f"| Номенклатура | {'✅' if nom else '❌'} | {', '.join(f'`{n}`' for n in nom) or '—'} |",
        f"| Цены | {'✅' if price else '❌'} | {', '.join(f'`{n}`' for n in price) or '—'} |",
        f"| Остатки | {'✅' if stock else '❌'} | {', '.join(f'`{n}`' for n in stock) or '—'} |",
        f"| Характеристики | {'✅' if chars else '❌'} | {', '.join(f'`{n}`' for n in chars) or '—'} |",
        f"| Единицы | {'✅' if units else '❌'} | {', '.join(f'`{n}`' for n in units) or '—'} |",
        f"| Категории | {'✅' if grps else '❌'} | {', '.join(f'`{n}`' for n in grps) or '—'} |",
        "",
        "---",
        "",
        "## Вопросы для Артёма",
        "",
        "- Как называется поле артикула в `Catalog_Номенклатура`?",
        "- Какой регистр цен (`InformationRegister_*`) использовать?",
        "- Как связаны записи остатков с Номенклатурой (поле-ключ)?",
        "- Какой тип цен — закупочная, розничная, оптовая?",
        "- Есть ли в 1С поля для фотографий или ссылок на изображения?",
        "- Доступен ли статус наличия (в наличии / нет) напрямую или только через расчёт остатков?",
    ]

    path = OUTPUT_DIR / "ODATA_PROBE_REPORT.md"
    path.write_text("\n".join(sections), encoding="utf-8")
    print(f"[OK] Отчёт → {path}")
    return path


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    print("=" * 60)
    print("OData 1С Probe")
    print("=" * 60)
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    if not check_env():
        write_report([], "❌ ПЕРЕМЕННЫЕ .env НЕ ЗАДАНЫ")
        sys.exit(1)

    xml_data = fetch_metadata()
    if xml_data is None:
        write_report([], "❌ ОШИБКА ПОДКЛЮЧЕНИЯ")
        sys.exit(1)

    save_xml(xml_data)
    entities = parse_entities(xml_data)
    print(f"[OK] Разобрано сущностей: {len(entities)}")

    save_entities(entities)
    write_report(entities, "✅ УСПЕШНО")

    print("")
    print("=" * 60)
    print("Готово. Результаты: 02_PRODUCT_DATABASE/odata_probe/")
    print("=" * 60)


if __name__ == "__main__":
    main()
