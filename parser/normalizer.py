from typing import Any, Dict, Optional
from urllib.parse import urlsplit, urlunsplit


def _canonical_url(raw_url: str) -> str:
    parts = urlsplit(raw_url)
    path = parts.path.rstrip("/") or parts.path
    return urlunsplit((parts.scheme, parts.netloc, path, "", ""))


def normalize_product(detail: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    if not detail or not detail.get("url"):
        return None

    canonical_url = _canonical_url(str(detail.get("url")))
    olx_id = detail.get("olx_id")
    if isinstance(olx_id, str) and olx_id.strip().lower() == "none":
        olx_id = None

    currency = detail.get("currency") or "UNKNOWN"
    raw_price = detail.get("original_price")
    price = raw_price if currency not in {"UNKNOWN", "NEGOTIABLE"} else None

    parameters = detail.get("parameters")
    if isinstance(parameters, list):
        params_dict: Dict[str, Any] = {}
        for item in parameters:
            if isinstance(item, str) and ":" in item:
                key, value = item.split(":", 1)
                params_dict[key.strip()] = value.strip()
            else:
                params_dict.setdefault("items", []).append(item)
        parameters = params_dict or {"items": parameters}
    elif parameters is None:
        parameters = {}

    return {
        "url": canonical_url,
        "category": detail.get("category"),
        "title": detail.get("title"),
        "price": price,
        "currency": currency,
        "location": detail.get("location"),
        "precise_location": detail.get("precise_location"),
        "parameters": parameters,
        "olx_id": olx_id,
    }
