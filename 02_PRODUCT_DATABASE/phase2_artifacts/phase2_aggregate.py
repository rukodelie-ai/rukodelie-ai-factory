import json, csv, re
from collections import defaultdict

print("Загружаю сырые данные...", flush=True)
stock = json.load(open("/tmp/phase2_stock.json", encoding="utf-8"))
prices = json.load(open("/tmp/phase2_prices.json", encoding="utf-8"))
colors = json.load(open("/tmp/phase2_colors.json", encoding="utf-8"))
wh_map = json.load(open("/tmp/phase2_warehouses.json", encoding="utf-8"))
price_type_map = json.load(open("/tmp/phase2_price_types.json", encoding="utf-8"))

RAW_CSV = "/Users/sergey/Library/Mobile Documents/com~apple~CloudDocs/RUKODELIE_AI_FACTORY/02_PRODUCT_DATABASE/MASTER_PRODUCT_DATABASE_RAW_YARN_V1.csv"
with open(RAW_CSV, encoding="utf-8-sig") as f:
    products = {r["ref_key"]: r for r in csv.DictReader(f)}
print(f"Товаров (номенклатура): {len(products)}", flush=True)

WAREHOUSES = ["Магазин", "Интернет магазин", "Основной склад", "Резерв", "Склад Wolt",
              "Офис", "Склад OZON", "Дальний склад"]
PRICE_TYPES = sorted(set(price_type_map.values()))

# 1. Агрегация остатков: (Номенклатура_Key, Характеристика_Key, Склад_Key) -> qty
print("Агрегирую остатки...", flush=True)
stock_bal = defaultdict(float)
for r in stock:
    sign = 1 if r["RecordType"] == "Receipt" else -1
    key = (r["Номенклатура_Key"], r["Характеристика_Key"], r["Склад_Key"])
    stock_bal[key] += sign * (r.get("ВНаличии") or 0)

# 2. Последняя цена по (Номенклатура_Key, Характеристика_Key, ВидЦены_Key)
print("Агрегирую цены (последняя по периоду)...", flush=True)
latest_price = {}
for r in prices:
    key = (r["Номенклатура_Key"], r["Характеристика_Key"], r["ВидЦены_Key"])
    period = r["Period"]
    if key not in latest_price or period > latest_price[key][0]:
        latest_price[key] = (period, r["Цена"])

# 3. Цвета+фото: парсим код/название из Description формата "... (код - название)"
print("Разбираю названия и коды цветов...", flush=True)
color_pattern = re.compile(r"\(([A-Za-zА-Яа-я0-9]+)\s*-\s*(.+?)\)\s*$")
code_only_pattern = re.compile(r"\(([A-Za-zА-Яа-я0-9]+)\)\s*$")
color_pattern_comma = re.compile(r"\(([A-Za-zА-Яа-я0-9]+),\s*(.+?)\)\s*$")
color_info = {}  # (Номенклатура_Key, Характеристика_Key) -> (code, name, image_Key)
unparsed = 0
for c in colors:
    key = (c["Номенклатура_Key"], c["Характеристика_Key"])
    desc = (c.get("Description") or "").strip()
    m = color_pattern.search(desc)
    if m:
        code, name = m.group(1), m.group(2).strip()
    else:
        m2 = color_pattern_comma.search(desc)
        if m2:
            code, name = m2.group(1), m2.group(2).strip()
        else:
            m3 = code_only_pattern.search(desc)
            if m3:
                code, name = m3.group(1), ""
            else:
                code, name = "", desc
                unparsed += 1
    color_info[key] = (code, name, c.get("image_Key", ""))
print(f"Не удалось распарсить код/название по шаблону: {unparsed} из {len(colors)}", flush=True)

# 4. Собираем финальные строки: одна строка = один цвет одной номенклатуры
print("Строю итоговую таблицу...", flush=True)
rows = []
all_nom_char_keys = set(k[:2] for k in stock_bal.keys()) | set(color_info.keys())

for nom_key, char_key in all_nom_char_keys:
    prod = products.get(nom_key)
    if not prod:
        continue  # не из категории Пряжа (не должно случаться, но на всякий случай)
    code, name, image_key = color_info.get((nom_key, char_key), ("", "", ""))

    wh_qty = {}
    for wh_guid, wh_name in wh_map.items():
        q = stock_bal.get((nom_key, char_key, wh_guid), 0)
        if wh_name in wh_qty:
            wh_qty[wh_name] += q
        else:
            wh_qty[wh_name] = q
    total_stock = sum(wh_qty.values())

    price_str_parts = []
    for pt_guid, pt_name in price_type_map.items():
        v = latest_price.get((nom_key, char_key, pt_guid))
        if v:
            price_str_parts.append(f"{pt_name}={v[1]}")
    prices_all = "; ".join(price_str_parts)
    retail_price = None
    for pt_guid, pt_name in price_type_map.items():
        if pt_name == "Розничная":
            v = latest_price.get((nom_key, char_key, pt_guid))
            retail_price = v[1] if v else ""

    row = {
        "brand": prod["brand"],
        "series": prod["name"].strip(),
        "code_1c": prod["code_1c"],
        "ref_key": nom_key,
        "characteristic_key": char_key,
        "color_code": code,
        "color_name": name,
        "photo_guid": image_key,
    }
    for wh in WAREHOUSES:
        row[f"stock_{wh}"] = round(wh_qty.get(wh, 0), 3)
    row["stock_total"] = round(total_stock, 3)
    row["price_retail"] = retail_price
    row["prices_all"] = prices_all
    row["composition"] = prod["composition"]
    row["weight_g"] = prod["weight_g"]
    row["length"] = prod["length"]
    row["category_l2_brand_folder"] = prod["category_l2"]
    row["full_name"] = prod["full_name"]
    rows.append(row)

print(f"Строк (товар x цвет): {len(rows)}", flush=True)

fieldnames = ["brand","series","code_1c","ref_key","characteristic_key","color_code","color_name",
              "photo_guid"] + [f"stock_{wh}" for wh in WAREHOUSES] + ["stock_total","price_retail",
              "prices_all","composition","weight_g","length","category_l2_brand_folder","full_name"]

OUT = "/tmp/AI_PRODUCT_KNOWLEDGE_YARN_V1.csv"
with open(OUT, "w", encoding="utf-8-sig", newline="") as f:
    w = csv.DictWriter(f, fieldnames=fieldnames)
    w.writeheader()
    w.writerows(rows)
print(f"Сохранено: {OUT}", flush=True)

# --- контроль и итоговая сводка ---
grand_total_colors = sum(r["stock_total"] for r in rows)
wh_totals = {wh: sum(r[f"stock_{wh}"] for r in rows) for wh in WAREHOUSES}
grand_total_wh = sum(wh_totals.values())

print("\n=== ИТОГОВАЯ СВОДКА ===")
print(f"Всего производителей: {len(set(r['brand'] for r in rows if r['brand']))}")
print(f"Всего серий (наименований номенклатуры): {len(set(r['ref_key'] for r in rows))}")
print(f"Всего товаров (номенклатура) обработано: {len(products)}")
print(f"Всего цветовых вариантов (строк): {len(rows)}")
print(f"Всего фотографий (уникальных photo_guid, не пустых): {len(set(r['photo_guid'] for r in rows if r['photo_guid']))}")
print("\nОстаток по складам:")
for wh, v in wh_totals.items():
    print(f"  {wh}: {v:.2f}")
print(f"\nОБЩИЙ ОСТАТОК (сумма по цветам): {grand_total_colors:.3f}")
print(f"ОБЩИЙ ОСТАТОК (сумма по складам): {grand_total_wh:.3f}")
print(f"РАЗНИЦА: {abs(grand_total_colors - grand_total_wh):.6f}")
print(f"Записей в итоговой базе: {len(rows)}")

neg = [r for r in rows if r["stock_total"] < -0.0001]
print(f"\nСтрок с отрицательным ИТОГО: {len(neg)}")
