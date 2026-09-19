"""Утилиты первичной валидации и нормализации входных данных для async-yt-dlp."""

from __future__ import annotations

import re
from pathlib import Path
from urllib.parse import urlsplit

from async_yt_dlp.exceptions import ValidationError

# Допустимые схемы для стандартных сетевых URL
_ALLOWED_SCHEMES: frozenset[str] = frozenset(
    {
        "http",
        "https",
        "ftp",
        "ftps",
        "mms",
        "rtsp",
        "rtmp",
    }
)

# Специфические префиксы поисковых и специальных запросов yt-dlp
# (например, "ytsearch:python", "scsearch:ambient", "gvsearch10:test")
_SPECIAL_PREFIX_PATTERN = re.compile(r"^[a-zA-Z0-9_\-]+(?:search\d*|rec|fav):", re.IGNORECASE)


def validate_url(url: str, *, allow_file_urls: bool = False) -> str:
    """Выполняет базовую проверку и нормализацию URL или поискового запроса.

    Функция проверяет общую корректность формата строки, отсутствие null-байтов
    и допустимость схемы протокола. Она НЕ дублирует внутренний список поддерживаемых
    сайтов yt-dlp, оставляя распознавание конкретных провайдеров ядру yt-dlp.

    Args:
        url: Входной URL или строка запроса.
        allow_file_urls: Разрешать ли схему `file://` (по умолчанию отключено из соображений безопасности).

    Returns:
        Очищенный от концевых пробелов URL.

    Raises:
        ValidationError: Если URL пуст, содержит запрещенные символы или недопустимую схему.
    """
    if not isinstance(url, str):
        raise ValidationError(f"URL должен быть строкой, получено: {type(url).__name__}")

    cleaned = url.strip()
    if not cleaned:
        raise ValidationError("URL не может быть пустым.")

    if "\x00" in cleaned:
        raise ValidationError("URL содержит недопустимый null-байт.")

    # Проверка на специальные поисковые префиксы yt-dlp (например, ytsearch:...)
    if _SPECIAL_PREFIX_PATTERN.match(cleaned):
        return cleaned

    # Стандартный разбор URL
    try:
        parts = urlsplit(cleaned)
    except Exception as exc:
        raise ValidationError(f"Некорректная структура URL: {exc}") from exc

    scheme = parts.scheme.lower()
    if not scheme:
        # Если схемы нет, yt-dlp может использовать default_search или протокол по умолчанию,
        # но для безопасности требуем непустой хост или префикс, если это не относительный поиск
        if " " in cleaned:
            # Текстовый поисковый запрос
            return cleaned
        # Возможно, передан URL без схемы (например, "youtube.com/watch?v=...")
        return cleaned

    if scheme == "file":
        if not allow_file_urls:
            raise ValidationError(
                "Схема 'file://' отключена по умолчанию для предотвращения несанкционированного доступа. "
                "Включите 'allow_file_urls=True' в настройках, если это необходимо."
            )
        return cleaned

    if scheme not in _ALLOWED_SCHEMES:
        raise ValidationError(
            f"Неподдерживаемая схема URL: '{scheme}'. Допустимы: {sorted(_ALLOWED_SCHEMES)}"
        )

    if not parts.netloc:
        raise ValidationError(f"В URL отсутствует сетевой адрес (host): '{cleaned}'")

    return cleaned


def validate_path(
    path: Path | str,
    *,
    must_exist: bool = False,
    create_parent: bool = False,
    create_dir: bool = False,
) -> Path:
    """Проверяет корректность файлового пути.

    Args:
        path: Путь к каталогу или файлу.
        must_exist: Должен ли путь обязательно существовать на диске.
        create_parent: Создавать ли родительский каталог при его отсутствии.
        create_dir: Создавать ли сам каталог при его отсутствии.

    Returns:
        Экземпляр `pathlib.Path` с раскрытым домашним каталогом (`~`).

    Raises:
        ValidationError: При некорректном пути или отсутствии требуемого пути.
    """
    if not path:
        raise ValidationError("Путь не может быть пустым.")

    try:
        resolved = Path(path).expanduser()
    except Exception as exc:
        raise ValidationError(f"Некорректный путь: {path} ({exc})") from exc

    if "\x00" in str(resolved):
        raise ValidationError(f"Путь содержит null-байт: {path}")

    if must_exist and not resolved.exists():
        raise ValidationError(f"Указанный путь не существует: {resolved}")

    if create_dir:
        try:
            resolved.mkdir(parents=True, exist_ok=True)
        except OSError as exc:
            raise ValidationError(f"Не удалось создать директорию {resolved}: {exc}") from exc
    elif create_parent:
        try:
            resolved.parent.mkdir(parents=True, exist_ok=True)
        except OSError as exc:
            raise ValidationError(
                f"Не удалось создать родительскую директорию для пути {resolved}: {exc}"
            ) from exc

    return resolved
