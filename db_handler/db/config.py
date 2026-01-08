from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Optional
from pathlib import Path
from urllib.parse import urlparse, parse_qsl, urlencode, urlunparse

# Определим путь к .env в корне проекта (две директории выше этого файла)
_env_path = Path(__file__).resolve().parents[2] / '.env'

# Параметры, которые не следует передавать в asyncpg.connect
_DB_URL_FORBIDDEN_QS = {"pgbouncer", "connection_limit"}


def database_url_cleaner(url: str) -> str:
	"""Возвращает URL без запрещённых query-параметров (например, pgbouncer).
	Используется для очистки DSN до передачи в драйвер/SQLAlchemy.
	"""
	parsed = urlparse(url)
	if not parsed.query:
		return url
	qs = parse_qsl(parsed.query, keep_blank_values=True)
	qs_filtered = [(k, v) for k, v in qs if k not in _DB_URL_FORBIDDEN_QS]
	new_query = urlencode(qs_filtered, doseq=True)
	parsed = parsed._replace(query=new_query)
	return urlunparse(parsed)

class DatabaseSettings(BaseSettings):
	# Указываем файл с переменными окружения (абсолютный путь)
	# и указываем extra='ignore', чтобы игнорировать лишние ключи в .env
	model_config = SettingsConfigDict(env_file=str(_env_path), env_file_encoding="utf-8", extra="ignore")

	# Поддерживаем оба варианта: либо полный DATABASE_URL, либо отдельные DB_* переменные
	DATABASE_URL: Optional[str] = None
	DB_USER: Optional[str] = None
	DB_PASSWORD: Optional[str] = None
	DB_HOST: Optional[str] = None
	DB_PORT: Optional[int] = None
	DB_NAME: Optional[str] = None

	@property
	def database_url(self) -> str:
		"""
		Возвращает строку подключения для SQLAlchemy.
		Если в окружении задан `DATABASE_URL`, используем его и при необходимости
		подменяем префикс на `postgresql+asyncpg://` для async драйвера.
		Иначе собираем URL из отдельных переменных `DB_*`.
		Убираем неподдерживаемые query-параметры (например, pgbouncer),
		чтобы они не передавались в asyncpg.connect().
		"""
		if self.DATABASE_URL:
			url = self.DATABASE_URL
			# Если указан синхронный префикс 'postgresql://', заменим на asyncpg
			if url.startswith("postgresql://"):
				url = url.replace("postgresql://", "postgresql+asyncpg://", 1)
			# Удаляем запрещённые параметры из query
			url = database_url_cleaner(url)
			return url

		# Если DATABASE_URL не задан — проверим отдельные поля
		if not (self.DB_USER and self.DB_PASSWORD and self.DB_HOST and self.DB_PORT and self.DB_NAME):
			raise ValueError(
				"DATABASE_URL не задан и не все DB_* переменные присутствуют."
			)
		return f"postgresql+asyncpg://{self.DB_USER}:{self.DB_PASSWORD}@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"

# Ленивый синглтон для настроек базы данных
_settings_cache: DatabaseSettings | None = None

def get_database_settings() -> DatabaseSettings:
	global _settings_cache
	if _settings_cache is None:
		_settings_cache = DatabaseSettings()
	return _settings_cache

# -------------------------------------------------------------------------
# Настройки бота Telegram — отдельная модель, pydantic будет валидировать
# только те переменные, которые объявлены в этом классе.
# -------------------------------------------------------------------------
class BotSettings(BaseSettings):
	model_config = SettingsConfigDict(env_file=str(_env_path), env_file_encoding="utf-8", extra="ignore")

	TOKEN: str
	ADMINS: Optional[str] = None  # хранится как 'id1,id2', можно добавить парсер ниже

	@property
	def admins_list(self) -> list[str]:
		if not self.ADMINS:
			return []
		return [a.strip() for a in self.ADMINS.split(',') if a.strip()]

# Ленивый синглтон для настроек бота
_bot_settings_cache: BotSettings | None = None

def get_bot_settings() -> BotSettings:
	global _bot_settings_cache
	if _bot_settings_cache is None:
		_bot_settings_cache = BotSettings()
	return _bot_settings_cache
