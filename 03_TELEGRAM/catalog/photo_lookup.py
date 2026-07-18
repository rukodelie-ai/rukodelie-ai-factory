"""Получение фотографии точного цветового варианта из 1С.

Строка варианта выбирается из уже кэшируемого Google Sheets Product Knowledge.
Бинарные данные читаются из опубликованного read-only OData-регистра по прямому
составному ключу и кэшируются в памяти процесса по photo_guid.
"""
import base64
import binascii
import os
import re
from dataclasses import dataclass
from typing import Dict, Optional, Tuple

import requests

from .product_knowledge_sheets import get_product_knowledge_rows
from logger import logger

_BINARY_ENTITY = "InformationRegister_ДвоичныеДанныеФайлов"
_FILE_TYPE = "StandardODATA.Catalog_iq_ИзображенияХарактеристикПрисоединенныеФайлы"
_SELECT = "Файл,Файл_Type,ДвоичныеДанныеФайла_Type,ДвоичныеДанныеФайла_Base64Data"
_TIMEOUT_SECONDS = 30


@dataclass(frozen=True)
class ProductPhoto:
    data: bytes
    mime_type: str
    filename: str
    color_code: str
    color_name: str
    characteristic_key: str


_photo_cache: Dict[str, ProductPhoto] = {}


def _text(value: object) -> str:
    return str(value or "").strip()


def _positive_stock(value: object) -> bool:
    try:
        return float(_text(value).replace(",", ".")) > 0
    except (TypeError, ValueError):
        return False


def _mask_guid(value: str) -> str:
    return value[:4] + "…" + value[-4:] if len(value) > 12 else "<invalid>"


def _safe_filename(color_code: str, extension: str) -> str:
    safe_code = re.sub(r"[^A-Za-z0-9_-]+", "_", color_code).strip("_") or "variant"
    return "product_photo_" + safe_code + extension


def _find_variant(
    product_name: str,
    color_code: str,
    characteristic_key: Optional[str],
) -> Optional[dict]:
    product_needle = product_name.strip().casefold()
    code_needle = color_code.strip()
    characteristic_needle = (characteristic_key or "").strip().casefold()

    matches = []
    for row in get_product_knowledge_rows():
        if _text(row.get("full_name")).casefold() != product_needle:
            continue
        if _text(row.get("color_code")) != code_needle:
            continue
        if characteristic_needle and _text(row.get("characteristic_key")).casefold() != characteristic_needle:
            continue
        if not _positive_stock(row.get("stock_total")):
            continue
        matches.append(row)

    if len(matches) != 1:
        logger.warning(
            "Exact photo variant not found: product=%r color_code=%r characteristic=%s matches=%d",
            product_name,
            color_code,
            "provided" if characteristic_needle else "not-provided",
            len(matches),
        )
        return None
    return matches[0]


def _decode_photo(value: object, color_code: str) -> Optional[Tuple[bytes, str, str]]:
    if not isinstance(value, str) or not value.strip():
        return None
    try:
        decoded = base64.b64decode("".join(value.split()), validate=True)
    except (ValueError, binascii.Error):
        return None

    if decoded.startswith(b"\xff\xd8\xff") and decoded.endswith(b"\xff\xd9"):
        return decoded, "image/jpeg", _safe_filename(color_code, ".jpg")
    if decoded.startswith(b"\x89PNG\r\n\x1a\n"):
        return decoded, "image/png", _safe_filename(color_code, ".png")
    return None


def get_product_photo(
    product_name: str,
    color_code: str,
    characteristic_key: Optional[str] = None,
) -> Optional[ProductPhoto]:
    """Возвращает binary-фото только для одного точного доступного варианта."""
    if not product_name.strip() or not color_code.strip():
        return None

    row = _find_variant(product_name, color_code, characteristic_key)
    if row is None:
        return None

    photo_guid = _text(row.get("photo_guid"))
    if not photo_guid:
        logger.warning("Exact photo variant has no photo_guid: product=%r color_code=%r", product_name, color_code)
        return None

    cached = _photo_cache.get(photo_guid)
    if cached is not None:
        logger.info(
            "Product photo cache hit: guid=%s size=%d mime=%s",
            _mask_guid(photo_guid),
            len(cached.data),
            cached.mime_type,
        )
        return cached

    logger.info("Product photo cache miss: guid=%s", _mask_guid(photo_guid))
    base_url = os.environ.get("ODATA_BASE_URL", "").rstrip("/")
    username = os.environ.get("ODATA_USERNAME", "")
    password = os.environ.get("ODATA_PASSWORD", "")
    if not all((base_url, username, password)):
        logger.error("OData photo connection parameters are incomplete")
        return None

    auth_token = base64.b64encode((username + ":" + password).encode("utf-8")).decode("ascii")
    escaped_guid = photo_guid.replace("'", "''")
    key = "(Файл='" + escaped_guid + "',Файл_Type='" + _FILE_TYPE + "')"
    url = base_url + "/" + _BINARY_ENTITY + key
    headers = {
        "Authorization": "Basic " + auth_token,
        "Accept": "application/json",
        "Accept-Encoding": "identity",
    }
    params = {"$select": _SELECT, "$format": "json"}

    try:
        response = requests.get(url, headers=headers, params=params, timeout=_TIMEOUT_SECONDS)
        response.raise_for_status()
        payload = response.json()
    except requests.RequestException as exc:
        logger.error(
            "OData photo request failed: guid=%s error=%s",
            _mask_guid(photo_guid),
            type(exc).__name__,
        )
        return None
    except ValueError:
        logger.error("OData photo response is not JSON: guid=%s", _mask_guid(photo_guid))
        return None

    decoded = _decode_photo(payload.get("ДвоичныеДанныеФайла_Base64Data"), color_code)
    if decoded is None:
        logger.warning("OData photo payload is empty or invalid: guid=%s", _mask_guid(photo_guid))
        return None

    data, mime_type, filename = decoded
    photo = ProductPhoto(
        data=data,
        mime_type=mime_type,
        filename=filename,
        color_code=_text(row.get("color_code")),
        color_name=_text(row.get("color_name")),
        characteristic_key=_text(row.get("characteristic_key")),
    )
    _photo_cache[photo_guid] = photo
    logger.info(
        "Product photo loaded: guid=%s size=%d mime=%s",
        _mask_guid(photo_guid),
        len(photo.data),
        photo.mime_type,
    )
    return photo
