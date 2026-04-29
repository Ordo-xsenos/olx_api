from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from db_handler.services.persistense import _deduplicate_by_url, save_parsed_data


class TestDeduplicateByUrl:
    def test_keeps_last_item_for_duplicate_url(self) -> None:
        items = [
            {"url": "https://example.com/1", "title": "first"},
            {"url": "https://example.com/2", "title": "second"},
            {"url": "https://example.com/1", "title": "updated"},
        ]

        result = _deduplicate_by_url(items)

        assert result == [
            {"url": "https://example.com/2", "title": "second"},
            {"url": "https://example.com/1", "title": "updated"},
        ]


class TestSaveParsedData:
    @pytest.mark.asyncio
    async def test_deduplicates_duplicate_urls_before_execute(self) -> None:
        session = AsyncMock()
        session.execute = AsyncMock()
        session.commit = AsyncMock()
        session.rollback = AsyncMock()

        session_factory = MagicMock()
        session_factory.__aenter__.return_value = session
        session_factory.__aexit__.return_value = None

        items = [
            {
                "title": "first",
                "category": "cat",
                "price": 1,
                "currency": "USD",
                "location": "Tashkent",
                "precise_location": "Yunusabad",
                "parameters": {},
                "olx_id": "1",
                "url": "https://example.com/1",
            },
            {
                "title": "updated",
                "category": "cat",
                "price": 2,
                "currency": "USD",
                "location": "Tashkent",
                "precise_location": "Yunusabad",
                "parameters": {},
                "olx_id": "2",
                "url": "https://example.com/1",
            },
        ]

        with patch("db_handler.services.persistense.SessionLocal", return_value=session_factory):
            await save_parsed_data(items)

        assert session.execute.await_count == 1
        assert session.commit.await_count == 1
        session.rollback.assert_not_awaited()
