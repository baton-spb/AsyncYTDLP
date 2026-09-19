"""Объектный построитель шаблонов путей и имен файлов для yt-dlp (OutputTemplate).

Предоставляет:
- Неизменяемый fluent-построитель шаблонов вывода yt-dlp без необходимости
  ручного написания строк вида `%(title)s [%(id)s].%(ext)s`.
- Готовые пресеты для типичных сценариев (только название, название с id, плейлисты, каналы).
- Поддержку операторов композиции: `/` для разделителя каталогов, `+` для конкатенации.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class OutputTemplate:
    """Неизменяемый (frozen) объектный построитель шаблона имени файла / пути yt-dlp.

    Примеры использования:
    ```python
    # 1. Готовые пресеты:
    template = OutputTemplate.title_only()     # "%(title)s.%(ext)s"
    template = OutputTemplate.title_and_id()   # "%(title)s [%(id)s].%(ext)s"
    template = OutputTemplate.playlist()       # "%(playlist_title)s/%(playlist_index)02d - %(title)s.%(ext)s"

    # 2. Fluent-конструктор:
    template = (
        OutputTemplate()
        .channel()
        .dir()
        .playlist_index(2)
        .text(" - ")
        .title()
        .ext()
    )

    # 3. Композиция через оператор / (каталоги):
    template = OutputTemplate.channel() / OutputTemplate.title_only()
    # Результат: "%(uploader)s/%(upload_date)s - %(title)s/%(title)s.%(ext)s"
    ```
    """

    _parts: tuple[str, ...] = ()

    @classmethod
    def custom(cls, raw: str) -> OutputTemplate:
        """Создает шаблон из произвольной готовой строки.

        Args:
            raw: Произвольная строка шаблона yt-dlp.
        """
        return cls(_parts=(raw,))

    def _append(self, token: str) -> OutputTemplate:
        """Возвращает новый экземпляр шаблона с добавленным токеном."""
        return OutputTemplate(_parts=(*self._parts, token))

    # --- Токены метаданных ---

    def title(self) -> OutputTemplate:
        """Добавляет название медиа (`%(title)s`)."""
        return self._append("%(title)s")

    def id(self) -> OutputTemplate:
        """Добавляет уникальный идентификатор видео (`%(id)s`)."""
        return self._append("%(id)s")

    def ext(self) -> OutputTemplate:
        """Добавляет расширение файла (`.%(ext)s` или `%(ext)s`, если точка уже предшествует)."""
        if self._parts and self._parts[-1].endswith("."):
            return self._append("%(ext)s")
        return self._append(".%(ext)s")

    def uploader(self) -> OutputTemplate:
        """Добавляет имя автора/загрузчика (`%(uploader)s`)."""
        return self._append("%(uploader)s")

    def channel(self) -> OutputTemplate:
        """Добавляет название канала (`%(channel)s`)."""
        return self._append("%(channel)s")

    def upload_date(self) -> OutputTemplate:
        """Добавляет дату загрузки в формате ГГГГММДД (`%(upload_date)s`)."""
        return self._append("%(upload_date)s")

    def playlist_title(self) -> OutputTemplate:
        """Добавляет название плейлиста (`%(playlist_title)s`)."""
        return self._append("%(playlist_title)s")

    def playlist_index(self, width: int = 2) -> OutputTemplate:
        """Добавляет порядковый номер в плейлисте с заполнением нулями.

        Args:
            width: Количество цифр (по умолчанию 2, например 01, 02).
        """
        fmt = f"%(playlist_index)0{width}d" if width > 1 else "%(playlist_index)s"
        return self._append(fmt)

    def resolution(self) -> OutputTemplate:
        """Добавляет разрешение видео, например '1080p' (`%(resolution)s`)."""
        return self._append("%(resolution)s")

    def duration(self) -> OutputTemplate:
        """Добавляет длительность медиа в секундах (`%(duration)s`)."""
        return self._append("%(duration)s")

    def epoch(self) -> OutputTemplate:
        """Добавляет временную метку UNIX времени создания (`%(epoch)s`)."""
        return self._append("%(epoch)s")

    # --- Текст и структура ---

    def text(self, s: str) -> OutputTemplate:
        """Добавляет произвольную строку текста.

        Args:
            s: Текст разделителя или суффикса (например, ' - ', ' [', ']').
        """
        return self._append(s)

    def dir(self, sub_path: str | OutputTemplate | None = None) -> OutputTemplate:
        """Добавляет разделитель каталогов `/` и опционально следующий сегмент пути.

        Args:
            sub_path: Необязательный сегмент директории или шаблона.
        """
        res = self._append("/")
        if sub_path is not None:
            if isinstance(sub_path, OutputTemplate):
                return OutputTemplate(_parts=(*res._parts, *sub_path._parts))
            return res._append(str(sub_path))
        return res

    # --- Операторы композиции ---

    def __truediv__(self, other: OutputTemplate | str) -> OutputTemplate:
        """Оператор `/` для объединения шаблонов через разделитель каталогов."""
        current_str = self.build()
        if not current_str.endswith("/"):
            current_str += "/"
        if isinstance(other, OutputTemplate):
            return OutputTemplate(_parts=(current_str, *other._parts))
        return OutputTemplate(_parts=(current_str, str(other)))

    def __add__(self, other: OutputTemplate | str) -> OutputTemplate:
        """Оператор `+` для конкатенации шаблонов."""
        if isinstance(other, OutputTemplate):
            return OutputTemplate(_parts=(*self._parts, *other._parts))
        return OutputTemplate(_parts=(*self._parts, str(other)))

    def build(self) -> str:
        """Компилирует шаблон в итоговую строку для yt-dlp.

        Returns:
            Строка шаблона путей (например, `%(title)s.%(ext)s`).
        """
        if not self._parts:
            return "%(title)s [%(id)s].%(ext)s"
        return "".join(self._parts)

    def __str__(self) -> str:
        return self.build()

    def __repr__(self) -> str:
        return f"OutputTemplate({self.build()!r})"

    # --- Готовые производственные пресеты ---

    @classmethod
    def default(cls) -> OutputTemplate:
        """Стандартный безопасный шаблон: 'Название [ID].расширение'."""
        return cls(_parts=("%(title)s [%(id)s].%(ext)s",))

    @classmethod
    def preset_default(cls) -> OutputTemplate:
        """Псевдоним для default()."""
        return cls.default()

    @classmethod
    def title_only(cls) -> OutputTemplate:
        """Только название: 'Название.расширение'."""
        return cls(_parts=("%(title)s.%(ext)s",))

    @classmethod
    def preset_title_only(cls) -> OutputTemplate:
        """Псевдоним для title_only()."""
        return cls.title_only()

    @classmethod
    def title_and_id(cls) -> OutputTemplate:
        """Название с идентификатором в скобках: 'Название [ID].расширение'."""
        return cls(_parts=("%(title)s [%(id)s].%(ext)s",))

    @classmethod
    def preset_title_and_id(cls) -> OutputTemplate:
        """Псевдоним для title_and_id()."""
        return cls.title_and_id()

    @classmethod
    def playlist_folder(cls, padding: int = 2) -> OutputTemplate:
        """Шаблон для плейлиста: 'Название_плейлиста/01 - Название.расширение'.

        Args:
            padding: Разрядность номера трека (по умолчанию 2).
        """
        idx_fmt = f"%(playlist_index)0{padding}d" if padding > 1 else "%(playlist_index)s"
        return cls(_parts=(f"%(playlist_title)s/{idx_fmt} - %(title)s.%(ext)s",))

    @classmethod
    def preset_playlist(cls, padding: int = 2) -> OutputTemplate:
        """Псевдоним для playlist_folder()."""
        return cls.playlist_folder(padding=padding)

    @classmethod
    def channel_folder(cls) -> OutputTemplate:
        """Шаблон с группировкой по каналу и дате: 'Канал/ГГГГММДД - Название.расширение'."""
        return cls(_parts=("%(uploader)s/%(upload_date)s - %(title)s.%(ext)s",))

    @classmethod
    def preset_channel(cls) -> OutputTemplate:
        """Псевдоним для channel_folder()."""
        return cls.channel_folder()

    @classmethod
    def dated(cls) -> OutputTemplate:
        """Шаблон с датой загрузки: 'ГГГГММДД - Название.расширение'."""
        return cls(_parts=("%(upload_date)s - %(title)s.%(ext)s",))

    @classmethod
    def preset_dated(cls) -> OutputTemplate:
        """Псевдоним для dated()."""
        return cls.dated()

    @classmethod
    def id_only(cls) -> OutputTemplate:
        """Только идентификатор: 'ID.расширение'."""
        return cls(_parts=("%(id)s.%(ext)s",))

    @classmethod
    def preset_id_only(cls) -> OutputTemplate:
        """Псевдоним для id_only()."""
        return cls.id_only()
