from typing import Any, Dict, Optional


def normalize_product(detail: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    if not detail or not detail.get("url"):
        return None

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
        "url": detail.get("url"),
        "category": detail.get("category"),
        "title": detail.get("title"),
        "price": price,
        "currency": currency,
        "location": detail.get("location"),
        "precise_location": detail.get("precise_location"),
        "parameters": parameters,
        "olx_id": detail.get("olx_id"),
    }
