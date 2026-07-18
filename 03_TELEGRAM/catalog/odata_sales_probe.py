"""
odata_sales_probe.py — Разведка сущностей продаж в 1С OData.

Запуск из папки 03_TELEGRAM/:
    python3 catalog/odata_sales_probe.py

Использует кэшированный metadata.xml из предыдущей диагностики.
Если кэша нет — скачивает заново.
Настройки берутся из .env; пароль не выводится.
"""
import base64
import datetime
import json
import os
import sys
import urllib.error
import urllib.request
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Dict, List, Optional

from dotenv import load_dotenv

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

_ENV_PATH = Path(__file__).parent.parent / ".env"
load_dotenv(_ENV_PATH)

ODATA_BASE_URL: str = os.environ.get("ODATA_BASE_URL", "").rstrip("/")
ODATA_USERNAME: str = os.environ.get("ODATA_USERNAME", "")
ODATA_PASSWORD: str = os.environ.get("ODATA_PASSWORD", "")

PROJECT_ROOT = Path(__file__).parent.parent.parent
OUTPUT_DIR   = PROJECT_ROOT / "02_PRODUCT_DATABASE" / "odata_sales_probe"
METADATA_CACHE = PROJECT_ROOT / "02_PRODUCT_DATABASE" / "odata_probe" / "odata_metadata.xml"

# ---------------------------------------------------------------------------
# Keyword banks  (все в нижнем регистре)
# ---------------------------------------------------------------------------

# Ключевые слова для отбора EntitySet по теме «продажи»
SALES_PRIMARY = [
    "реализац", "продаж", "чек", "выручка", "обороты",
    "розниц", "kaspi", "ozon", "halyk",
]
SALES_SECONDARY = [
    "заказ", "отчет", "отчёт", "сайт",
    "товар", "номенклатур", "клиент", "контрагент",
    "документ", "регистр",
]

# Ключевые слова для анализа полей EntityType
FIELD_KEYS: Dict[str, List[str]] = {
    "date":    ["дата", "date", "period", "период"],
    "nom":     ["номенклатур", "товар"],
    "qty":     ["количество", "qty", "count", "объем", "объём"],
    "sum":     ["сумма", "amount", "выручка", "стоимость", "цена"],
    "client":  ["клиент", "контрагент", "покупател", "partner", "customer"],
    "channel": ["kaspi", "ozon", "halyk", "канал", "источник", "магазин",
                "сайт", "розниц", "интернет"],
    "docref":  ["документ", "doc", "заказ", "реализац", "чек", "ссылка", "ref_key",
                "регистратор"],
}

# Типы EntitySet, с которыми часто путают «продажи» — для фильтрации шума
NOISE_SUFFIXES = [
    "присоединенныефайлы", "удалить", "сертификатышифрования",
    "электронныеподписи", "_recordtype",
]

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _auth_header() -> Dict[str, str]:
    token = base64.b64encode(f"{ODATA_USERNAME}:{ODATA_PASSWORD}".encode()).decode()
    return {"Authorization": f"Basic {token}"}


def _fetch_bytes(url: str, timeout: int = 60) -> bytes:
    req = urllib.request.Request(url, headers=_auth_header())
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return resp.read()


def _check_env() -> bool:
    missing = [k for k, v in [
        ("ODATA_BASE_URL", ODATA_BASE_URL),
        ("ODATA_USERNAME", ODATA_USERNAME),
        ("ODATA_PASSWORD", ODATA_PASSWORD),
    ] if not v]
    if missing:
        print(f"[ОШИБКА] Не заданы .env: {', '.join(missing)}")
        return False
    host = ODATA_BASE_URL.split("//")[-1].split("/")[0]
    print(f"[OK] ODATA хост: {host}")
    return True


def _is_noisy(name: str) -> bool:
    low = name.lower()
    return any(low.endswith(s) or s in low for s in NOISE_SUFFIXES)


def _matches(name: str, keywords: List[str]) -> bool:
    low = name.lower()
    return any(k in low for k in keywords)


def _field_flags(fields: List[str]) -> Dict[str, bool]:
    """Проверяет, есть ли в списке полей признаки даты, номенклатуры и т.д."""
    result: Dict[str, bool] = {}
    for flag, kws in FIELD_KEYS.items():
        result[flag] = any(
            any(k in f.lower() for k in kws) for f in fields
        )
    return result


def _matching_fields(fields: List[str], flag_key: str) -> List[str]:
    kws = FIELD_KEYS.get(flag_key, [])
    return [f for f in fields if any(k in f.lower() for k in kws)]

# ---------------------------------------------------------------------------
# Metadata loading
# ---------------------------------------------------------------------------

def load_metadata() -> bytes:
    if METADATA_CACHE.exists():
        data = METADATA_CACHE.read_bytes()
        print(f"[OK] Metadata из кэша: {METADATA_CACHE.name} ({len(data):,} байт)")
        return data

    if not ODATA_BASE_URL:
        print("[ОШИБКА] Нет кэша и ODATA_BASE_URL не задан.")
        sys.exit(1)

    url = f"{ODATA_BASE_URL}/$metadata"
    print(f"[→] Скачиваю $metadata ...")
    data = _fetch_bytes(url)
    METADATA_CACHE.parent.mkdir(parents=True, exist_ok=True)
    METADATA_CACHE.write_bytes(data)
    print(f"[OK] Сохранено в кэш: {METADATA_CACHE}")
    return data

# ---------------------------------------------------------------------------
# Metadata parsing
# ---------------------------------------------------------------------------

def parse_metadata(xml_bytes: bytes) -> Dict[str, Dict]:
    """
    Возвращает два словаря внутри dict:
      entity_types: {type_short_name: [field_name, ...]}
      entity_sets:  {set_name: type_short_name}
    """
    root = ET.fromstring(xml_bytes)
    entity_types: Dict[str, List[str]] = {}
    entity_sets:  Dict[str, str] = {}

    for elem in root.iter():
        local = elem.tag.split("}")[-1] if "}" in elem.tag else elem.tag

        # Собираем EntityType → поля
        if local == "EntityType":
            type_name = elem.get("Name", "")
            if type_name:
                fields: List[str] = []
                for child in elem:
                    child_local = child.tag.split("}")[-1] if "}" in child.tag else child.tag
                    if child_local in ("Property", "NavigationProperty"):
                        fname = child.get("Name", "")
                        if fname:
                            fields.append(fname)
                entity_types[type_name] = fields

        # Собираем EntitySet → тип
        elif local == "EntitySet":
            set_name   = elem.get("Name", "")
            type_attr  = elem.get("EntityType", "")
            # EntityType="StandardODATA.Document_ЗаказКлиента" → берём часть после точки
            short_type = type_attr.split(".")[-1] if "." in type_attr else type_attr
            if set_name:
                entity_sets[set_name] = short_type

    return {"entity_types": entity_types, "entity_sets": entity_sets}

# ---------------------------------------------------------------------------
# Entity classification
# ---------------------------------------------------------------------------

def classify_sets(parsed: Dict) -> Dict[str, List[Dict]]:
    """
    Делит все EntitySet на три группы:
      primary   — сильное совпадение с продажами
      secondary — слабое совпадение (заказы, товары, контрагенты)
      noise     — служебные / файловые
    """
    entity_types = parsed["entity_types"]
    entity_sets  = parsed["entity_sets"]

    primary:   List[Dict] = []
    secondary: List[Dict] = []

    for set_name, type_name in entity_sets.items():
        if _is_noisy(set_name):
            continue

        fields = entity_types.get(type_name, [])
        flags  = _field_flags(fields)
        is_primary   = _matches(set_name, SALES_PRIMARY)
        is_secondary = _matches(set_name, SALES_SECONDARY)

        if not (is_primary or is_secondary):
            continue

        entry = {
            "entity_set":  set_name,
            "entity_type": type_name,
            "fields":      fields,
            "flags":       flags,
            "priority":    "primary" if is_primary else "secondary",
        }
        if is_primary:
            primary.append(entry)
        else:
            secondary.append(entry)

    # Сортируем по убыванию «богатства» полей
    key_fn = lambda e: sum(e["flags"].values())
    primary.sort(key=key_fn, reverse=True)
    secondary.sort(key=key_fn, reverse=True)

    return {"primary": primary, "secondary": secondary}

# ---------------------------------------------------------------------------
# Report generation
# ---------------------------------------------------------------------------

def save_candidates_txt(groups: Dict[str, List[Dict]]) -> Path:
    lines: List[str] = []
    total = len(groups["primary"]) + len(groups["secondary"])
    lines.append(f"Кандидаты на сущности продаж: {total}")
    lines.append(f"  Приоритетные (реализация/чеки/Kaspi/Ozon/Halyk): {len(groups['primary'])}")
    lines.append(f"  Вспомогательные (заказы/товары/контрагенты): {len(groups['secondary'])}")
    lines.append("")

    for section, title in [("primary", "ПРИОРИТЕТНЫЕ"), ("secondary", "ВСПОМОГАТЕЛЬНЫЕ")]:
        lines.append(f"=== {title} ({len(groups[section])}) ===")
        for e in groups[section]:
            flag_str = " | ".join(
                k.upper() for k, v in e["flags"].items() if v
            )
            lines.append(f"  {e['entity_set']}")
            if flag_str:
                lines.append(f"    [{flag_str}]")
        lines.append("")

    path = OUTPUT_DIR / "sales_candidate_entities.txt"
    path.write_text("\n".join(lines), encoding="utf-8")
    print(f"[OK] {path.name} ({total} кандидатов)")
    return path


def save_fields_json(groups: Dict[str, List[Dict]]) -> Path:
    result: Dict = {}
    for section in ("primary", "secondary"):
        for e in groups[section]:
            result[e["entity_set"]] = {
                "entity_type":  e["entity_type"],
                "priority":     e["priority"],
                "field_count":  len(e["fields"]),
                "fields":       e["fields"],
                "flags":        e["flags"],
                "key_fields": {
                    flag: _matching_fields(e["fields"], flag)
                    for flag in FIELD_KEYS
                },
            }

    path = OUTPUT_DIR / "sales_candidate_fields.json"
    path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"[OK] {path.name} ({len(result)} сущностей)")
    return path


def _top_candidates(groups: Dict[str, List[Dict]], flag: str, n: int = 5) -> List[str]:
    """Возвращает имена EntitySet с признаком flag, отсортированные по кол-ву полей."""
    matches = [
        e for section in ("primary", "secondary")
        for e in groups[section]
        if e["flags"].get(flag)
    ]
    matches.sort(key=lambda e: len(e["fields"]), reverse=True)
    return [e["entity_set"] for e in matches[:n]]


def save_report(groups: Dict[str, List[Dict]]) -> Path:
    host = ODATA_BASE_URL.split("//")[-1].split("/")[0] if ODATA_BASE_URL else "?"
    total = len(groups["primary"]) + len(groups["secondary"])
    today = datetime.date.today()

    # Находим конкретных кандидатов по типам
    def top(flag: str, n: int = 5) -> str:
        names = _top_candidates(groups, flag, n)
        return "\n".join(f"- `{n}`" for n in names) if names else "- *(не найдено)*"

    def best_primary() -> str:
        return "\n".join(
            f"- `{e['entity_set']}` [{', '.join(k.upper() for k, v in e['flags'].items() if v)}]"
            for e in groups["primary"][:10]
        ) or "*(нет)*"

    # Kaspi / Ozon / Halyk / site specific
    def channel_entities(keyword: str) -> List[str]:
        return [
            e["entity_set"] for section in ("primary", "secondary")
            for e in groups[section]
            if keyword in e["entity_set"].lower()
        ]

    kaspi_ents  = channel_entities("kaspi")
    ozon_ents   = channel_entities("ozon")
    halyk_ents  = channel_entities("halyk")
    site_ents   = channel_entities("iq_")

    def ul(lst: List[str]) -> str:
        return "\n".join(f"- `{n}`" for n in lst) if lst else "- *(нет)*"

    has_date    = bool(_top_candidates(groups, "date"))
    has_nom     = bool(_top_candidates(groups, "nom"))
    has_qty     = bool(_top_candidates(groups, "qty"))
    has_sum     = bool(_top_candidates(groups, "sum"))
    has_client  = bool(_top_candidates(groups, "client"))
    has_channel = bool(kaspi_ents or ozon_ents or halyk_ents)

    can_top = has_date and has_nom and has_qty

    sections = [
        "# ODATA SALES PROBE REPORT",
        f"**Дата:** {today}",
        f"**Хост:** `{host}`",
        f"**Кандидатов найдено:** {total} ({len(groups['primary'])} приоритетных + {len(groups['secondary'])} вспомогательных)",
        "",
        "---",
        "",
        "## 1. Можно ли через OData получить продажи?",
        "",
        f"{'✅ Да' if can_top else '⚠️ Частично'} — сущности с датой, номенклатурой и количеством {'найдены' if can_top else 'найдены не полностью'}.",
        "",
        "---",
        "",
        "## 2. Наиболее вероятные сущности продаж (приоритетные)",
        "",
        best_primary(),
        "",
        "---",
        "",
        "## 3. Где строки продаж / состав заказа?",
        "",
        "Искать в сущностях с суффиксом `_Товары`, `_ТоварыУслуги`, `_ТабличнаяЧасть`",
        "или в `AccumulationRegister_*` с полем Номенклатура.",
        "",
        top("nom"),
        "",
        "---",
        "",
        "## 4–8. Где ключевые поля?",
        "",
        "| Поле | Есть? | Топ-сущности |",
        "|------|-------|-------------|",
        f"| Дата продажи | {'✅' if has_date else '❌'} | {', '.join(f'`{n}`' for n in _top_candidates(groups, 'date', 3)) or '—'} |",
        f"| Номенклатура | {'✅' if has_nom else '❌'} | {', '.join(f'`{n}`' for n in _top_candidates(groups, 'nom', 3)) or '—'} |",
        f"| Количество | {'✅' if has_qty else '❌'} | {', '.join(f'`{n}`' for n in _top_candidates(groups, 'qty', 3)) or '—'} |",
        f"| Сумма | {'✅' if has_sum else '❌'} | {', '.join(f'`{n}`' for n in _top_candidates(groups, 'sum', 3)) or '—'} |",
        f"| Клиент/Контрагент | {'✅' if has_client else '❌'} | {', '.join(f'`{n}`' for n in _top_candidates(groups, 'client', 3)) or '—'} |",
        "",
        "---",
        "",
        "## 9. Разделение по каналам продаж",
        "",
        f"### Kaspi.kz ({len(kaspi_ents)} сущностей)",
        ul(kaspi_ents),
        "",
        f"### Ozon ({len(ozon_ents)} сущностей)",
        ul(ozon_ents),
        "",
        f"### Halyk ({len(halyk_ents)} сущностей)",
        ul(halyk_ents),
        "",
        f"### Сайт / iq_ ({len(site_ents)} сущностей)",
        ul(site_ents),
        "",
        "---",
        "",
        "## 10. Достаточно ли данных для ТОП товаров?",
        "",
        f"| Период | Возможно? | Условие |",
        f"|--------|-----------|---------|",
        f"| Год | {'✅' if can_top else '❌'} | Нужны дата + номенклатура + количество |",
        f"| Полгода | {'✅' if can_top else '❌'} | То же |",
        f"| Квартал | {'✅' if can_top else '❌'} | То же |",
        f"| Месяц | {'✅' if can_top else '❌'} | То же |",
        "",
        "---",
        "",
        "## 11. Что нужно для сравнения с ручным ТОП-100",
        "",
        "1. Получить от владельца Excel/CSV с ТОП-100 из 1С (артикул + количество продаж)",
        "2. Из OData запросить `AccumulationRegister_*` (продажи) за тот же период",
        "3. Соединить по полю Номенклатура.Ref_Key или Артикул",
        "4. Сравнить ранги: совпадают ли ТОП-10, ТОП-50, ТОП-100",
        "",
        "---",
        "",
        "## 12. Вопросы для Артёма / Евгения",
        "",
        "1. **Основной регистр продаж:** Какой регистр накопления используется для учёта",
        "   розничных и оптовых продаж? (`ПродажиОбороты`, `РеализацияТоваров`, другое?)",
        "2. **Документ реализации:** Как называется основной документ продажи —",
        "   `Document_РеализацияТоваровУслуг` или `Document_ЧекККМ` (для розницы)?",
        "3. **Kaspi:** Продажи через Kaspi проходят отдельным документом или",
        "   попадают в общий регистр продаж?",
        "4. **Период данных:** С какой даты в 1С хранятся данные о продажах?",
        "   (нужно для ТОП за год/полгода)",
        "5. **Виртуальные таблицы:** Доступны ли через OData виртуальные таблицы",
        "   `AccumulationRegister_*_Оборот` или `AccumulationRegister_*_ОстаткиИОбороты`?",
        "   (они дают агрегаты без перебора строк)",
        "",
        "---",
        "",
        "## Следующий шаг",
        "",
        "После ответов Артёма: создать `catalog/odata_sales_reader.py` — скрипт,",
        "который запросит первые 10 записей из ключевого регистра продаж и покажет реальные данные.",
    ]

    path = OUTPUT_DIR / "ODATA_SALES_PROBE_REPORT.md"
    path.write_text("\n".join(sections), encoding="utf-8")
    print(f"[OK] {path.name}")
    return path

# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    print("=" * 60)
    print("OData 1С Sales Probe")
    print("=" * 60)
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    if not _check_env() and not METADATA_CACHE.exists():
        sys.exit(1)

    xml_bytes = load_metadata()

    print("[→] Разбираю metadata ...")
    parsed = parse_metadata(xml_bytes)
    n_types = len(parsed["entity_types"])
    n_sets  = len(parsed["entity_sets"])
    print(f"[OK] EntityType: {n_types} | EntitySet: {n_sets}")

    print("[→] Классифицирую сущности продаж ...")
    groups = classify_sets(parsed)
    print(f"[OK] Приоритетных: {len(groups['primary'])} | Вспомогательных: {len(groups['secondary'])}")

    save_candidates_txt(groups)
    save_fields_json(groups)
    save_report(groups)

    print("")
    print("=" * 60)
    print("Готово. Результаты: 02_PRODUCT_DATABASE/odata_sales_probe/")
    print("=" * 60)


if __name__ == "__main__":
    main()
