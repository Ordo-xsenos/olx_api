"""
Тесты для обработчика /latest в handlers/start.py
"""
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from aiogram.types import Message


class TestLatestCommandHandler:
    """Тесты обработчика команды /latest."""

    @pytest.mark.asyncio
    async def test_latest_command_no_args(
        self,
        mock_message: Message,
        mock_postgres_handler: MagicMock,
        sample_products_list: list[dict],
    ) -> None:
        """Команда /latest без аргументов (должна вернуть 10 товаров)."""
        # Мокаем все зависимости
        with patch("handlers.start._ensure_user", new_callable=AsyncMock, return_value=True):
            with patch("handlers.start.list_latest_products", new_callable=AsyncMock, return_value=sample_products_list):
                mock_message.answer = AsyncMock()

                from handlers.start import latest_command_handler
                await latest_command_handler(mock_message, mock_postgres_handler)

                # Проверяем что list_latest_products был вызван с limit=10
                from handlers.start import list_latest_products
                list_latest_products.assert_called_once_with(mock_postgres_handler, limit=10)

                # Проверяем что ответ был отправлен
                mock_message.answer.assert_called_once()

    @pytest.mark.asyncio
    async def test_latest_command_with_limit(
        self,
        mock_message: Message,
        mock_postgres_handler: MagicMock,
        sample_products_list: list[dict],
    ) -> None:
        """Команда /latest с указанием лимита."""
        mock_message.text = "/latest 5"

        with patch("handlers.start._ensure_user", new_callable=AsyncMock, return_value=True):
            with patch("handlers.start.list_latest_products", new_callable=AsyncMock, return_value=sample_products_list):
                mock_message.answer = AsyncMock()

                from handlers.start import latest_command_handler
                await latest_command_handler(mock_message, mock_postgres_handler)

                # Проверяем что list_latest_products был вызван с limit=5
                from handlers.start import list_latest_products
                list_latest_products.assert_called_once_with(mock_postgres_handler, limit=5)

    @pytest.mark.asyncio
    async def test_latest_command_no_products(
        self,
        mock_message: Message,
        mock_postgres_handler: MagicMock,
    ) -> None:
        """Команда /latest когда нет товаров."""
        with patch("handlers.start._ensure_user", new_callable=AsyncMock, return_value=True):
            with patch("handlers.start.list_latest_products", new_callable=AsyncMock, return_value=[]):
                mock_message.answer = AsyncMock()

                from handlers.start import latest_command_handler
                await latest_command_handler(mock_message, mock_postgres_handler)

                # Проверяем что было отправлено сообщение "нет объявлений"
                mock_message.answer.assert_called_once()
                call_args = mock_message.answer.call_args[0][0]
                assert "нет сохраненных объявлений" in call_args.lower()

    @pytest.mark.asyncio
    async def test_latest_command_banned_user(
        self,
        mock_message: Message,
        mock_postgres_handler: MagicMock,
    ) -> None:
        """Команда /latest от заблокированного пользователя."""
        with patch("handlers.start._ensure_user", new_callable=AsyncMock, return_value=False):
            mock_message.answer = AsyncMock()

            from handlers.start import latest_command_handler
            await latest_command_handler(mock_message, mock_postgres_handler)

        # Проверяем что было отправлено сообщение о доступе
        mock_message.answer.assert_called_once()
        call_args = mock_message.answer.call_args[0][0]
        assert "доступ" in call_args.lower()

    @pytest.mark.asyncio
    async def test_latest_command_output_format(
        self,
        mock_message: Message,
        mock_postgres_handler: MagicMock,
        sample_products_list: list[dict],
    ) -> None:
        """Проверка формата вывода /latest."""
        with patch("handlers.start._ensure_user", new_callable=AsyncMock, return_value=True):
            with patch("handlers.start.list_latest_products", new_callable=AsyncMock, return_value=sample_products_list):
                mock_message.answer = AsyncMock()

                from handlers.start import latest_command_handler
                await latest_command_handler(mock_message, mock_postgres_handler)

                # Проверяем формат ответа
                mock_message.answer.assert_called_once()
                response = mock_message.answer.call_args[0][0]

                # Ответ должен содержать заголовок, цену и URL
                assert "Тестовый товар" in response
                assert "100000" in response or "100 000" in response
                assert "olx.uz" in response

    @pytest.mark.asyncio
    async def test_latest_command_webhook_called(
        self,
        mock_message: Message,
        mock_postgres_handler: MagicMock,
        sample_products_list: list[dict],
        mock_env: None,
    ) -> None:
        """Проверка что вебхук отправляется при наличии WEBHOOK_URL."""
        with patch("handlers.start._ensure_user", new_callable=AsyncMock, return_value=True):
            with patch("handlers.start.list_latest_products", new_callable=AsyncMock, return_value=sample_products_list):
                with patch("handlers.start.enqueue_webhook", new_callable=AsyncMock) as mock_enqueue:
                    with patch("handlers.start.SessionLocal") as mock_session_factory:
                        mock_session = AsyncMock()
                        mock_session_factory.return_value.__aenter__ = AsyncMock(
                            return_value=mock_session
                        )
                        mock_session_factory.return_value.__aexit__ = AsyncMock(return_value=None)

                        mock_message.answer = AsyncMock()

                        from handlers.start import latest_command_handler
                        await latest_command_handler(mock_message, mock_postgres_handler)

                        # Проверяем что enqueue_webhook был вызван
                        mock_enqueue.assert_called_once()

    @pytest.mark.asyncio
    async def test_latest_command_webhook_not_called_without_url(
        self,
        mock_message: Message,
        mock_postgres_handler: MagicMock,
        sample_products_list: list[dict],
        mock_env_no_webhook: None,
    ) -> None:
        """Проверка что вебхук не отправляется без WEBHOOK_URL."""
        with patch("handlers.start._ensure_user", new_callable=AsyncMock, return_value=True):
            with patch("handlers.start.list_latest_products", new_callable=AsyncMock, return_value=sample_products_list):
                with patch("handlers.start.enqueue_webhook", new_callable=AsyncMock) as mock_enqueue:
                    mock_message.answer = AsyncMock()

                    from handlers.start import latest_command_handler
                    await latest_command_handler(mock_message, mock_postgres_handler)

                    # Проверяем что enqueue_webhook не был вызван
                    mock_enqueue.assert_not_called()

    @pytest.mark.asyncio
    async def test_latest_command_invalid_limit(
        self,
        mock_message: Message,
        mock_postgres_handler: MagicMock,
        sample_products_list: list[dict],
    ) -> None:
        """Команда /latest с невалидным лимитом."""
        mock_message.text = "/latest abc"

        with patch("handlers.start._ensure_user", new_callable=AsyncMock, return_value=True):
            with patch("handlers.start.list_latest_products", new_callable=AsyncMock, return_value=sample_products_list):
                mock_message.answer = AsyncMock()

                from handlers.start import latest_command_handler
                await latest_command_handler(mock_message, mock_postgres_handler)

                # Должен использоваться лимит по умолчанию (10)
                from handlers.start import list_latest_products
                list_latest_products.assert_called_once_with(mock_postgres_handler, limit=10)

    @pytest.mark.asyncio
    async def test_latest_command_price_display(
        self,
        mock_message: Message,
        mock_postgres_handler: MagicMock,
    ) -> None:
        """Проверка отображения цены."""
        products = [
            {
                "id": 1,
                "title": "Товар без цены",
                "price": None,
                "currency": "UZS",
                "url": "https://olx.uz/test",
            },
            {
                "id": 2,
                "title": "Товар с ценой",
                "price": 100000,
                "currency": "UZS",
                "url": "https://olx.uz/test2",
            },
        ]

        with patch("handlers.start._ensure_user", new_callable=AsyncMock, return_value=True):
            with patch("handlers.start.list_latest_products", new_callable=AsyncMock, return_value=products):
                mock_message.answer = AsyncMock()

                from handlers.start import latest_command_handler
                await latest_command_handler(mock_message, mock_postgres_handler)

                response = mock_message.answer.call_args[0][0]
                # Проверяем что есть оба товара
                assert "Товар без цены" in response
                assert "Товар с ценой" in response
                # Проверяем что цена отображается
                assert "100000" in response or "100 000" in response
