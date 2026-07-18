import os, base64, urllib.request, urllib.parse, json, sys, time, csv
from dotenv import load_dotenv
load_dotenv("/Users/sergey/Library/Mobile Documents/com~apple~CloudDocs/RUKODELIE_AI_FACTORY/03_TELEGRAM/.env")
BASE = os.environ.get("ODATA_BASE_URL","").rstrip("/")
USER = os.environ.get("ODATA_USERNAME","")
PW = os.environ.get("ODATA_PASSWORD","")

def fetch(entity, params, retries=3, timeout=60):
    qs = urllib.parse.urlencode(params, quote_via=urllib.parse.quote)
    url = f"{BASE}/{urllib.parse.quote(entity)}?{qs}"
    token = base64.b64encode(f"{USER}:{PW}".encode()).decode()
    req = urllib.request.Request(url, headers={"Authorization": f"Basic {token}", "Accept":"application/json"})
    for attempt in range(retries):
        try:
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                return json.loads(resp.read())["value"]
        except Exception as e:
            print(f"  [retry {attempt}] {entity}: {e}", flush=True)
            time.sleep(2)
    return []

def batched(lst, n):
    for i in range(0, len(lst), n):
        yield lst[i:i+n]

def or_filter(field, guids):
    return " or ".join(f"{field} eq guid'{g}'" for g in guids)

RAW_CSV = "/Users/sergey/Library/Mobile Documents/com~apple~CloudDocs/RUKODELIE_AI_FACTORY/02_PRODUCT_DATABASE/MASTER_PRODUCT_DATABASE_RAW_YARN_V1.csv"
with open(RAW_CSV, encoding="utf-8-sig") as f:
    products = list(csv.DictReader(f))
guids = [p["ref_key"] for p in products]
print(f"Товаров категории Пряжа: {len(guids)}", flush=True)
total_batches = (len(guids) + 7) // 8

# --- 1. Остатки (Характеристика_Key + Склад_Key) ---
print(f"=== Остатки: {total_batches} батчей ===", flush=True)
all_stock = []
for i, batch in enumerate(batched(guids, 8)):
    res = fetch("AccumulationRegister_СвободныеОстатки_RecordType", {
        "$filter": or_filter("Номенклатура_Key", batch),
        "$select": "Номенклатура_Key,Характеристика_Key,Склад_Key,ВНаличии,RecordType",
        "$format": "json",
    })
    all_stock.extend(res)
    print(f"  батч {i+1}/{total_batches}: +{len(res)} (всего {len(all_stock)})", flush=True)
json.dump(all_stock, open("/tmp/phase2_stock.json","w",encoding="utf-8"), ensure_ascii=False)

# --- 2. Цены (Характеристика_Key) ---
print(f"\n=== Цены: {total_batches} батчей ===", flush=True)
all_prices = []
for i, batch in enumerate(batched(guids, 8)):
    res = fetch("InformationRegister_ЦеныНоменклатуры_RecordType", {
        "$filter": or_filter("Номенклатура_Key", batch),
        "$select": "Номенклатура_Key,Характеристика_Key,ВидЦены_Key,Цена,Period",
        "$format": "json",
    })
    all_prices.extend(res)
    print(f"  батч {i+1}/{total_batches}: +{len(res)} (всего {len(all_prices)})", flush=True)
json.dump(all_prices, open("/tmp/phase2_prices.json","w",encoding="utf-8"), ensure_ascii=False)

# --- 3. Цвета + фото ---
print(f"\n=== Цвета/фото: {total_batches} батчей ===", flush=True)
all_colors = []
for i, batch in enumerate(batched(guids, 8)):
    res = fetch("Catalog_iq_ИзображенияХарактеристик", {
        "$filter": or_filter("Номенклатура_Key", batch),
        "$select": "Номенклатура_Key,Характеристика_Key,Description,image_Key",
        "$format": "json",
    })
    all_colors.extend(res)
    print(f"  батч {i+1}/{total_batches}: +{len(res)} (всего {len(all_colors)})", flush=True)
json.dump(all_colors, open("/tmp/phase2_colors.json","w",encoding="utf-8"), ensure_ascii=False)

# --- справочники ---
warehouses = fetch("Catalog_Склады", {"$select":"Ref_Key,Description","$format":"json"})
json.dump({w["Ref_Key"]: w["Description"] for w in warehouses}, open("/tmp/phase2_warehouses.json","w",encoding="utf-8"), ensure_ascii=False)
price_types = fetch("Catalog_ВидыЦен", {"$select":"Ref_Key,Description","$format":"json"})
json.dump({p["Ref_Key"]: p["Description"] for p in price_types}, open("/tmp/phase2_price_types.json","w",encoding="utf-8"), ensure_ascii=False)

print("\nГОТОВО: stock/prices/colors/справочники сохранены в /tmp/phase2_*.json", flush=True)
