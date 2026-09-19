"""Адаптеры логирования и функции санитизации секретов для async-yt-dlp.

Предоставляет:
- `YTDLPLoggerAdapter`: мост между интерфейсом логгера yt-dlp и стандартным `logging.Logger`.
- `redact_options`: рекурсивную маскировку чувствительных данных (пароли, cookies, токены, proxy credentials).
- `redact_url`: безопасное отображение URL с удалением учетных данных из `user:pass@host`.
"""

from __future__ import annotations

import logging
import re
from collections.abc import Mapping
from urllib.parse import urlsplit, urlunsplit

from async_yt_dlp._constants import (
    LOGGER_NAME,
    SENSITIVE_HTTP_HEADERS,
    SENSITIVE_OPTION_KEYS,
)

logger = logging.getLogger(LOGGER_NAME)

_REDACTED_STR: str = "********"


def redact_url(url: str) -> str:
    """Удаляет пароль и учетные данные из URL, если они присутствуют.

    Например:
        `https://admin:secret123@example.com/stream` -> `https://admin:********@example.com/stream`

    Args:
        url: Исходный URL.

    Returns:
        URL с замаскированными учетными данными.
    """
    if not url or "@" not in url:
        return url

    try:
        parts = urlsplit(url)
        if parts.password:
            # Заменяем пароль на маску
            user = parts.username or ""
            netloc = f"{user}:{_REDACTED_STR}@{parts.hostname}"
            if parts.port:
                netloc += f":{parts.port}"
            return urlunsplit((parts.scheme, netloc, parts.path, parts.query, parts.fragment))
    except Exception:
        # Если разбор URL не удался, производим безопасную замену регулярным выражением
        return re.sub(r"://([^:@]+):([^@]+)@", r"://\1:********@", url)

    return url


def redact_options(options: Mapping[str, object]) -> dict[str, object]:
    """Создаёт глубокую копию словаря параметров с маскированием чувствительных данных.

    Защищает пароли, токены, заголовки авторизации и cookies от случайной
    утечки в логи или сообщения об ошибках.

    Args:
        options: Словарь опций yt-dlp или конфигурации.

    Returns:
        Новый словарь с замаскированными значениями секретных полей.
    """
    redacted: dict[str, object] = {}

    for key, value in options.items():
        key_lower = str(key).lower()

        # Проверка прямого совпадения с чувствительными ключами
        if key_lower in SENSITIVE_OPTION_KEYS or any(
            s in key_lower for s in ("password", "secret", "token")
        ):
            redacted[key] = _REDACTED_STR
            continue

        # Обработка словарей заголовков (http_headers, custom headers)
        if isinstance(value, Mapping):
            if "header" in key_lower:
                redacted_headers: dict[str, object] = {}
                for h_name, h_val in value.items():
                    if str(h_name).lower() in SENSITIVE_HTTP_HEADERS:
                        redacted_headers[h_name] = _REDACTED_STR
                    else:
                        redacted_headers[h_name] = h_val
                redacted[key] = redacted_headers
            else:
                redacted[key] = redact_options(value)
            continue

        # Обработка URL прокси со встроенными credentials
        if key_lower == "proxy" and isinstance(value, str):
            redacted[key] = redact_url(value)
            continue

        # Списки или кортежи (например, cookiesfrombrowser)
        if isinstance(value, (list, tuple)):
            if key_lower in ("cookiesfrombrowser",):
                redacted[key] = _REDACTED_STR
            else:
                redacted[key] = [redact_options(v) if isinstance(v, Mapping) else v for v in value]
            continue

        redacted[key] = value

    return redacted


class YTDLPLoggerAdapter:
    """Адаптер для интеграции механизма логирования yt-dlp со стандартным Python `logging`.

    yt-dlp ожидает объект, предоставляющий методы `debug()`, `info()`, `warning()`, `error()`.
    По соглашению yt-dlp:
    - Все отладочные сообщения и часть информационных сообщений направляются в `debug()`.
    - Сообщения с префиксом `[debug] ` являются настоящими отладочными сообщениями.
    - Прочие сообщения в `debug()` являются информационными и переводятся в `logger.info()`.
    """

    def __init__(
        self,
        target_logger: logging.Logger | None = None,
        *,
        no_warnings: bool = False,
    ) -> None:
        """Инициализирует адаптер логирования для сообщений yt-dlp.

        Args:
            target_logger: Экземпляр standard Logger. Если None, используется логгер библиотеки по умолчанию.
            no_warnings: Если True, предупреждения не передаются в логгер на уровне WARNING,
                         а понижаются до DEBUG, исключая спам в консоль.
        """
        self._logger = target_logger or logger
        self._no_warnings = no_warnings

    def debug(self, msg: str) -> None:
        """Обработка отладочных сообщений от yt-dlp."""
        if not msg:
            return
        if msg.startswith("[debug] "):
            self._logger.debug(msg[8:])
        else:
            self._logger.info(msg)

    def info(self, msg: str) -> None:
        """Обработка информационных сообщений."""
        if msg:
            self._logger.info(msg)

    def warning(self, msg: str) -> None:
        """Обработка предупреждений от yt-dlp."""
        if not msg:
            return
        if self._no_warnings:
            self._logger.debug("yt-dlp warning: %s", msg)
        else:
            self._logger.warning(msg)

    def error(self, msg: str) -> None:
        """Обработка сообщений об ошибках от yt-dlp."""
        if msg:
            self._logger.error(msg)
