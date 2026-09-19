"""Внутренние константы и параметры по умолчанию для async-yt-dlp."""

from typing import Final

# Версия библиотеки (соответствует Semantic Versioning)
__version__: Final[str] = "0.1.2"

# Имя корневого логгера библиотеки
LOGGER_NAME: Final[str] = "async_yt_dlp"

# Значения параллельности по умолчанию
DEFAULT_MAX_CONCURRENCY: Final[int] = 4

# Максимальный размер внутренней очереди по умолчанию
DEFAULT_QUEUE_SIZE: Final[int] = 100

# Минимальный интервал троттлинга progress events (в секундах)
DEFAULT_THROTTLE_INTERVAL: Final[float] = 0.5

# Размер очереди событий прогресса для одного скачивания
DEFAULT_PROGRESS_QUEUE_SIZE: Final[int] = 256

# Шаблон имени файла по умолчанию для yt-dlp
DEFAULT_OUTPUT_TEMPLATE: Final[str] = "%(title)s [%(id)s].%(ext)s"

# Список чувствительных ключей опций, которые должны маскироваться при логировании
SENSITIVE_OPTION_KEYS: Final[frozenset[str]] = frozenset(
    {
        "password",
        "videopassword",
        "username",
        "twofactor",
        "client_certificate_password",
        "cookiefile",
        "ap_password",
        "token",
        "api_key",
    }
)

# Чувствительные HTTP-заголовки, значения которых маскируются
SENSITIVE_HTTP_HEADERS: Final[frozenset[str]] = frozenset(
    {
        "authorization",
        "cookie",
        "set-cookie",
        "proxy-authorization",
        "x-api-key",
    }
)
