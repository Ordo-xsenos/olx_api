from typing import Dict, Any
from datetime import datetime


def normalize_real_estate(data: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "title": data.get("title"),
		"created_at": datetime.utcnow(),
        "price_value": data.get("price_value"),
        "currency": data.get("currency"),
        "location": data.get("location"),
        "precise_location": data.get("precise_location"),
        "parameters": data.get("parameters") or {},
        "olx_id": data.get("ID"),
        "url": data.get("Ссылка"),
    }
