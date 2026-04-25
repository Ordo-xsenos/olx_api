"""
Тесты для модуля db_handler/services/webhook_serializer.py
"""
import json
from datetime import datetime, date
from decimal import Decimal

import pytest

from db_handler.services.webhook_serializer import serialize_for_webhook


class TestSerializeForWebhook:
    """Тесты функции serialize_for_webhook."""

    def test_serialize_dict_with_primitives(self) -> None:
        """Сериализация словаря с примитивными типами."""
        data = {
            "id": 123,
            "title": "Test",
            "price": 100.50,
            "active": True,
            "tags": ["a", "b", "c"],
        }
        result = serialize_for_webhook(data)
        # Проверяем что можно сериализовать в JSON
        json_str = json.dumps(result)
        assert json_str is not None

    def test_serialize_datetime(self) -> None:
        """Сериализация datetime объекта."""
        dt = datetime(2026, 3, 25, 10, 30, 0)
        data = {"created_at": dt}
        result = serialize_for_webhook(data)
        assert result["created_at"] == "2026-03-25T10:30:00"
        # Проверяем что можно сериализовать в JSON
        json.dumps(result)

    def test_serialize_date(self) -> None:
        """Сериализация date объекта."""
        d = date(2026, 3, 25)
        data = {"date": d}
        result = serialize_for_webhook(data)
        assert result["date"] == "2026-03-25"
        json.dumps(result)

    def test_serialize_decimal(self) -> None:
        """Сериализация Decimal объекта."""
        data = {"price": Decimal("100.50")}
        result = serialize_for_webhook(data)
        assert result["price"] == 100.50
        assert isinstance(result["price"], float)
        json.dumps(result)

    def test_serialize_nested_dict(self) -> None:
        """Сериализация вложенного словаря."""
        data = {
            "product": {
                "id": 123,
                "created_at": datetime(2026, 3, 25, 10, 30, 0),
                "price": Decimal("100.50"),
            }
        }
        result = serialize_for_webhook(data)
        assert result["product"]["created_at"] == "2026-03-25T10:30:00"
        assert result["product"]["price"] == 100.50
        json.dumps(result)

    def test_serialize_list_of_dicts(self) -> None:
        """Сериализация списка словарей."""
        data = [
            {
                "id": 1,
                "created_at": datetime(2026, 3, 25, 10, 0, 0),
                "price": Decimal("100.00"),
            },
            {
                "id": 2,
                "created_at": datetime(2026, 3, 26, 11, 0, 0),
                "price": Decimal("200.00"),
            },
        ]
        result = serialize_for_webhook(data)
        assert len(result) == 2
        assert result[0]["created_at"] == "2026-03-25T10:00:00"
        assert result[1]["created_at"] == "2026-03-26T11:00:00"
        json.dumps(result)

    def test_serialize_none_values(self) -> None:
        """Сериализация None значений."""
        data = {"title": None, "price": None, "active": True}
        result = serialize_for_webhook(data)
        assert result["title"] is None
        assert result["price"] is None
        json.dumps(result)

    def test_serialize_empty_dict(self) -> None:
        """Сериализация пустого словаря."""
        data = {}
        result = serialize_for_webhook(data)
        assert result == {}
        json.dumps(result)

    def test_serialize_empty_list(self) -> None:
        """Сериализация пустого списка."""
        data = []
        result = serialize_for_webhook(data)
        assert result == []
        json.dumps(result)

    def test_serialize_complex_product_data(
        self, sample_product_with_datetime: dict
    ) -> None:
        """Сериализация сложных данных продукта."""
        result = serialize_for_webhook(sample_product_with_datetime)

        # Проверяем что datetime сериализовался
        assert isinstance(result["created_at"], str)
        assert "2026-03-25" in result["created_at"]

        # Проверяем что Decimal сериализовался
        assert isinstance(result["price"], float)

        # Проверяем что можно сериализовать в JSON
        json_str = json.dumps(result)
        assert json_str is not None

    def test_serialize_mixed_types_in_list(self) -> None:
        """Сериализация смешанных типов в списке."""
        data = [
            {"value": 1},
            {"value": Decimal("2.5")},
            {"value": datetime(2026, 1, 1)},
            {"value": date(2026, 1, 1)},
            {"value": None},
        ]
        result = serialize_for_webhook(data)
        assert result[0]["value"] == 1
        assert result[1]["value"] == 2.5
        assert result[2]["value"] == "2026-01-01T00:00:00"
        assert result[3]["value"] == "2026-01-01"
        assert result[4]["value"] is None
        json.dumps(result)

    def test_serialize_preserves_structure(self) -> None:
        """Сериализация сохраняет структуру данных."""
        data = {
            "outer": {
                "inner": {
                    "deep": {
                        "value": Decimal("999.99"),
                        "timestamp": datetime(2026, 12, 31, 23, 59, 59),
                    }
                }
            }
        }
        result = serialize_for_webhook(data)
        assert result["outer"]["inner"]["deep"]["value"] == 999.99
        assert "2026-12-31" in result["outer"]["inner"]["deep"]["timestamp"]
        json.dumps(result)
