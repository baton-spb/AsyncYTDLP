"""Построитель выражений выбора формата (FormatSelector) для yt-dlp.

Предоставляет строго типизированный fluent-интерфейс для конструирования
селекторов качества, разрешения, кодеков и контейнеров без ручного написания
сложных синтаксических конструкций yt-dlp.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from async_yt_dlp.enums import VideoContainer


@dataclass(frozen=True, slots=True)
class FormatSelector:
    """Неизменяемый fluent-построитель строки выбора формата yt-dlp.

    Поддерживает цепочки условий, объединение видео и аудио через `+`,
    запасные варианты через `/`, а также готовые производственные пресеты.

    Примеры:
    ```python
    # Лучшее видео до 1080p + лучшее аудио, либо лучший общий поток
    fmt = (
        FormatSelector.video()
        .max_height(1080)
        .merge(FormatSelector.audio())
        .fallback(FormatSelector.any_stream().max_height(1080))
        .fallback(FormatSelector.any_stream())
    )
    # Выведет: 'bestvideo[height<=1080]+bestaudio/best[height<=1080]/best'
    str(fmt)

    # Использование готового пресета для совместимости
    fmt = FormatSelector.preset_compatibility()
    ```
    """

    _raw: str | None = None
    _base: str = "best"
    _filters: tuple[str, ...] = ()
    _merges: tuple[FormatSelector, ...] = ()
    _fallbacks: tuple[FormatSelector, ...] = ()

    @classmethod
    def custom(cls, expression: str) -> FormatSelector:
        """Создает селектор из произвольной готовой строки yt-dlp.

        Args:
            expression: Строка формата yt-dlp (например, 'bv*+ba/b').

        Returns:
            Экземпляр `FormatSelector`.
        """
        return cls(_raw=expression.strip())

    @classmethod
    def video(cls) -> FormatSelector:
        """Создает селектор с базой только видеопотока (`bestvideo*`)."""
        return cls(_base="bestvideo*")

    @classmethod
    def audio(cls) -> FormatSelector:
        """Создает селектор с базой только аудиопотока (`bestaudio*`)."""
        return cls(_base="bestaudio*")

    @classmethod
    def any_stream(cls) -> FormatSelector:
        """Создает селектор с базой любого комплексного потока (`best`)."""
        return cls(_base="best")

    @classmethod
    def worst(cls) -> FormatSelector:
        """Создает селектор наименьшего качества (`worst`)."""
        return cls(_base="worst")

    def max_height(self, height: int) -> FormatSelector:
        """Ограничивает максимальную высоту кадра (вертикальное разрешение).

        Args:
            height: Максимальная высота в пикселях (например, 1080, 720).
        """
        return self._add_filter(f"height<={height}")

    def min_height(self, height: int) -> FormatSelector:
        """Ограничивает минимальную высоту кадра.

        Args:
            height: Минимальная высота в пикселях.
        """
        return self._add_filter(f"height>={height}")

    def exact_height(self, height: int) -> FormatSelector:
        """Требует точное совпадение высоты кадра.

        Args:
            height: Высота в пикселях.
        """
        return self._add_filter(f"height={height}")

    def max_fps(self, fps: int | float) -> FormatSelector:
        """Ограничивает максимальную частоту кадров в секунду.

        Args:
            fps: Максимальное число кадров (например, 60, 30).
        """
        return self._add_filter(f"fps<={fps}")

    def ext(self, extension: VideoContainer | str) -> FormatSelector:
        """Ограничивает расширение контейнера потока (например, VideoContainer.MP4, 'mp4', 'webm').

        Args:
            extension: Имя контейнера без точки или перечисление VideoContainer.
        """
        clean_ext = str(extension).lstrip(".")
        return self._add_filter(f"ext={clean_ext}")

    def container(self, container: VideoContainer | str) -> FormatSelector:
        """Ограничивает расширение контейнера потока (псевдоним для .ext()).

        Args:
            container: Имя контейнера или перечисление VideoContainer.
        """
        return self.ext(container)

    def vcodec(self, codec: str, *, prefix: bool = False) -> FormatSelector:
        """Фильтрует видеопоток по имени видеокодека.

        Args:
            codec: Имя кодека (например, 'avc1', 'h264', 'vp9', 'av01').
            prefix: Если True, используется сопоставление по префиксу `vcodec^=codec`.
        """
        op = "^=" if prefix else "="
        return self._add_filter(f"vcodec{op}{codec}")

    def acodec(self, codec: str, *, prefix: bool = False) -> FormatSelector:
        """Фильтрует аудиопоток по имени аудиокодека.

        Args:
            codec: Имя кодека (например, 'mp4a', 'aac', 'opus').
            prefix: Если True, используется сопоставление по префиксу `acodec^=codec`.
        """
        op = "^=" if prefix else "="
        return self._add_filter(f"acodec{op}{codec}")

    def max_filesize(self, size: int | str) -> FormatSelector:
        """Ограничивает максимальный размер файла или потока.

        Args:
            size: Размер в байтах (int) либо строка с суффиксом (например, '50M', '2G').
        """
        val = f"{size}B" if isinstance(size, int) else str(size)
        return self._add_filter(f"filesize<={val}")

    def filter(self, raw_filter: str) -> FormatSelector:
        """Добавляет произвольное условие фильтрации `[condition]`.

        Args:
            raw_filter: Строка условия без внешних квадратных скобок.
        """
        clean = raw_filter.strip("[]")
        return self._add_filter(clean)

    def _add_filter(self, filter_expr: str) -> FormatSelector:
        """Внутренний метод добавления фильтра в текущую ветку."""
        if self._raw is not None:
            raise ValueError("Невозможно добавлять фильтры к кастомному сырому выражению формата.")
        return FormatSelector(
            _raw=None,
            _base=self._base,
            _filters=(*self._filters, filter_expr),
            _merges=self._merges,
            _fallbacks=self._fallbacks,
        )

    def merge(self, other: FormatSelector | str) -> FormatSelector:
        """Объединяет текущий поток с другим потоком через `+` (обычно видео + аудио).

        Args:
            other: Другой селектор или строка формата.
        """
        other_sel = other if isinstance(other, FormatSelector) else FormatSelector.custom(other)
        return FormatSelector(
            _raw=self._raw,
            _base=self._base,
            _filters=self._filters,
            _merges=(*self._merges, other_sel),
            _fallbacks=self._fallbacks,
        )

    def fallback(self, other: FormatSelector | str) -> FormatSelector:
        """Добавляет запасной вариант выбора через `/`.

        Args:
            other: Запасной селектор формата.
        """
        other_sel = other if isinstance(other, FormatSelector) else FormatSelector.custom(other)
        return FormatSelector(
            _raw=self._raw,
            _base=self._base,
            _filters=self._filters,
            _merges=self._merges,
            _fallbacks=(*self._fallbacks, other_sel),
        )

    def __add__(self, other: FormatSelector | str) -> FormatSelector:
        """Синтаксический сахар для метода `merge` (`self + other`)."""
        return self.merge(other)

    def __truediv__(self, other: FormatSelector | str) -> FormatSelector:
        """Синтаксический сахар для метода `fallback` (`self / other`)."""
        return self.fallback(other)

    def build(self) -> str:
        """Компилирует селектор в итоговую строку формата yt-dlp.

        Returns:
            Строковое выражение для параметра `--format`.
        """
        if self._raw is not None:
            primary = self._raw
        else:
            filter_str = "".join(f"[{f}]" for f in self._filters)
            primary = f"{self._base}{filter_str}"

        if self._merges:
            merged_parts = [primary] + [m.build() for m in self._merges]
            primary = "+".join(merged_parts)

        if self._fallbacks:
            all_fallbacks = [primary] + [fb.build() for fb in self._fallbacks]
            return "/".join(all_fallbacks)

        return primary

    def __str__(self) -> str:
        """Возвращает строковое представление скомпилированного селектора."""
        return self.build()

    def __repr__(self) -> str:
        """Строковое представление для отладки."""
        return f"FormatSelector({self.build()!r})"

    # --- Готовые пресеты ---

    @classmethod
    def preset_1080p(cls, container: VideoContainer | str | None = None) -> FormatSelector:
        """Пресет Full HD 1080p: лучшее видео до 1080p + лучшее аудио с падением на лучший общий поток.

        Args:
            container: Опциональное ограничение контейнера (например, VideoContainer.MP4).
        """
        if container is not None:
            c = str(container).lstrip(".")
            return (
                cls.video()
                .max_height(1080)
                .ext(c)
                .merge(cls.audio())
                .fallback(cls.video().max_height(1080).merge(cls.audio()))
                .fallback(cls.any_stream().ext(c))
                .fallback(cls.any_stream().max_height(1080))
                .fallback(cls.any_stream())
            )
        return (
            cls.video()
            .max_height(1080)
            .merge(cls.audio())
            .fallback(cls.any_stream().max_height(1080))
            .fallback(cls.any_stream())
        )

    @classmethod
    def preset_720p(cls, container: VideoContainer | str | None = None) -> FormatSelector:
        """Пресет HD 720p: лучшее видео до 720p + лучшее аудио с падением на лучший общий поток.

        Args:
            container: Опциональное ограничение контейнера (например, VideoContainer.MP4).
        """
        if container is not None:
            c = str(container).lstrip(".")
            return (
                cls.video()
                .max_height(720)
                .ext(c)
                .merge(cls.audio())
                .fallback(cls.video().max_height(720).merge(cls.audio()))
                .fallback(cls.any_stream().ext(c))
                .fallback(cls.any_stream().max_height(720))
                .fallback(cls.any_stream())
            )
        return (
            cls.video()
            .max_height(720)
            .merge(cls.audio())
            .fallback(cls.any_stream().max_height(720))
            .fallback(cls.any_stream())
        )

    @classmethod
    def preset_audio_only(cls, codec: str = "m4a") -> FormatSelector:
        """Пресет только аудио: лучший аудиопоток с приоритетом заданного кодека/контейнера.

        Args:
            codec: Желаемый формат аудио (например, 'm4a', 'mp3', 'opus').
        """
        return cls.audio().ext(codec).fallback(cls.audio()).fallback(cls.any_stream())

    @classmethod
    def preset_compatibility(cls) -> FormatSelector:
        """Пресет максимальной совместимости: h264 (avc1) видео + aac (mp4a) аудио в контейнере mp4."""
        return (
            cls.video()
            .vcodec("avc", prefix=True)
            .ext("mp4")
            .merge(cls.audio().acodec("mp4a", prefix=True).ext("m4a"))
            .fallback(cls.video().vcodec("avc", prefix=True).merge(cls.audio()))
            .fallback(cls.any_stream().ext("mp4"))
            .fallback(cls.any_stream())
        )

    @classmethod
    def preset_telegram(cls, max_size_mb: int = 50) -> FormatSelector:
        """Пресет для Telegram-ботов с ограничением размера файла.

        Args:
            max_size_mb: Максимальный размер файла в мегабайтах (по умолчанию 50 МБ).
        """
        return (
            cls.any_stream()
            .max_height(1080)
            .max_filesize(f"{max_size_mb}M")
            .fallback(cls.video().max_filesize(f"{max_size_mb}M").merge(cls.audio()))
            .fallback(cls.any_stream().max_filesize(f"{max_size_mb}M"))
            .fallback(cls.worst())
        )

    @classmethod
    def preset_max_quality(cls, container: VideoContainer | str | None = None) -> FormatSelector:
        """Пресет максимального качества: наилучшее видео любого разрешения + наилучшее аудио.

        Args:
            container: Опциональное ограничение контейнера (например, VideoContainer.MP4).
        """
        if container is not None:
            c = str(container).lstrip(".")
            return (
                cls.video()
                .ext(c)
                .merge(cls.audio())
                .fallback(cls.video().merge(cls.audio()))
                .fallback(cls.any_stream().ext(c))
                .fallback(cls.any_stream())
            )
        return cls.video().merge(cls.audio()).fallback(cls.any_stream())
