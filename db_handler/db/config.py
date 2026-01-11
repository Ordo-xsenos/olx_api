from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Optional
from pathlib import Path

# Определим путь к .env в корне проекта (две директории выше этого файла)
_env_path = Path(__file__).resolve().parents[2] / ".env"

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
		return [a.strip() for a in self.ADMINS.split(",") if a.strip()]

# Ленивый синглтон для настроек бота
_bot_settings_cache: BotSettings | None = None

def get_bot_settings() -> BotSettings:
	global _bot_settings_cache
	if _bot_settings_cache is None:
		_bot_settings_cache = BotSettings()
	return _bot_settings_cache
