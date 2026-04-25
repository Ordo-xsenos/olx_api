from datetime import datetime, date
from decimal import Decimal
from typing import Any


def serialize_for_webhook(data: Any) -> Any:
    """
    Преобразует данные в JSON-сериализуемый формат.
    datetime/date -> ISO строки
    Decimal -> float
    """
    if isinstance(data, dict):
        return {key: serialize_for_webhook(value) for key, value in data.items()}
    if isinstance(data, list):
        return [serialize_for_webhook(item) for item in data]
    if isinstance(data, (datetime, date)):
        return data.isoformat()
    if isinstance(data, Decimal):
        return float(data)
    return data
