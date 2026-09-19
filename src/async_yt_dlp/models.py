"""Типизированные модели данных для результатов экстракции и загрузки в async-yt-dlp.

Все модели являются неизменяемыми (frozen dataclass), предоставляют удобный доступ
к наиболее частым метаданным (название, длительность, автор, форматы, пути) и сохраняют
доступ к исходному словарю yt-dlp через атрибут `raw_data`.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from pathlib import Path
from typing import cast


def _safe_str(val: object) -> str | None:
    """Безопасно преобразует значение в строку или возвращает None."""
    if val is None:
        return None
    return str(val)


def _safe_int(val: object) -> int | None:
    """Безопасно преобразует значение в int или возвращает None."""
    if val is None:
        return None
    try:
        return int(float(str(val)))
    except ValueError, TypeError:
        return None


def _safe_float(val: object) -> float | None:
    """Безопасно преобразует значение в float или возвращает None."""
    if val is None:
        return None
    try:
        return float(str(val))
    except ValueError, TypeError:
        return None


@dataclass(frozen=True)
class ThumbnailInfo:
    """Информация о миниатюре (обложке) видео."""

    url: str
    width: int | None = None
    height: int | None = None
    id: str | None = None
    resolution: str | None = None

    @classmethod
    def from_ytdlp(cls, d: Mapping[str, object]) -> ThumbnailInfo:
        """Создает экземпляр ThumbnailInfo из словаря yt-dlp.

        Args:
            d: Словарь метаданных миниатюры от yt-dlp.

        Returns:
            Объект ThumbnailInfo с заполненными полями.
        """
        return cls(
            url=str(d.get("url") or ""),
            width=_safe_int(d.get("width")),
            height=_safe_int(d.get("height")),
            id=_safe_str(d.get("id")),
            resolution=_safe_str(d.get("resolution")),
        )


@dataclass(frozen=True)
class SubtitleInfo:
    """Информация о дорожке субтитров."""

    ext: str | None = None
    url: str | None = None
    name: str | None = None

    @classmethod
    def from_ytdlp(cls, d: Mapping[str, object]) -> SubtitleInfo:
        """Создает экземпляр SubtitleInfo из словаря yt-dlp.

        Args:
            d: Словарь дорожки субтитров от yt-dlp.

        Returns:
            Объект SubtitleInfo с заполненными полями.
        """
        return cls(
            ext=_safe_str(d.get("ext")),
            url=_safe_str(d.get("url")),
            name=_safe_str(d.get("name")),
        )


@dataclass(frozen=True)
class FormatInfo:
    """Информация об отдельном медиа-формате (потоке) видео или аудио.

    Attributes:
        format_id: Идентификатор формата в yt-dlp (например, '137', '22', 'ba').
        ext: Расширение контейнера (mp4, webm, m4a и т.д.).
        width: Ширина видео в пикселях.
        height: Высота видео в пикселях.
        fps: Частота кадров.
        vcodec: Название видеокодека ('none' если только аудио).
        acodec: Название аудиокодека ('none' если только видео).
        filesize: Точный размер файла в байтах (если известен).
        filesize_approx: Приблизительный размер файла в байтах.
        tbr: Суммарный битрейт (kbit/s).
        vbr: Видео-битрейт (kbit/s).
        abr: Аудио-битрейт (kbit/s).
        asr: Частота дискретизации аудио (Гц).
        format_note: Дополнительное примечание к формату (например, '720p', 'medium').
        protocol: Протокол доставки (https, m3u8_native, http_dash_segments и т.д.).
        resolution: Текстовое разрешение (например, '1920x1080').
        dynamic_range: Динамический диапазон (SDR, HDR10, DV).
        audio_channels: Количество аудио-каналов (1, 2, 6).
        has_video: Присутствует ли видео-дорожка.
        has_audio: Присутствует ли аудио-дорожка.
        raw_data: Полный исходный словарь формата от yt-dlp.
    """

    format_id: str
    ext: str | None = None
    width: int | None = None
    height: int | None = None
    fps: float | None = None
    vcodec: str | None = None
    acodec: str | None = None
    filesize: int | None = None
    filesize_approx: int | None = None
    tbr: float | None = None
    vbr: float | None = None
    abr: float | None = None
    asr: int | None = None
    format_note: str | None = None
    protocol: str | None = None
    resolution: str | None = None
    dynamic_range: str | None = None
    audio_channels: int | None = None
    has_video: bool = False
    has_audio: bool = False
    raw_data: dict[str, object] = field(default_factory=dict, repr=False)

    @classmethod
    def from_ytdlp(cls, f: Mapping[str, object]) -> FormatInfo:
        """Создает экземпляр FormatInfo из словаря формата yt-dlp.

        Args:
            f: Словарь формата от yt-dlp.

        Returns:
            Объект FormatInfo с заполненными полями.
        """
        vcodec = _safe_str(f.get("vcodec"))
        acodec = _safe_str(f.get("acodec"))
        has_video = bool(vcodec and vcodec != "none")
        has_audio = bool(acodec and acodec != "none")

        return cls(
            format_id=str(f.get("format_id") or ""),
            ext=_safe_str(f.get("ext")),
            width=_safe_int(f.get("width")),
            height=_safe_int(f.get("height")),
            fps=_safe_float(f.get("fps")),
            vcodec=vcodec,
            acodec=acodec,
            filesize=_safe_int(f.get("filesize")),
            filesize_approx=_safe_int(f.get("filesize_approx")),
            tbr=_safe_float(f.get("tbr")),
            vbr=_safe_float(f.get("vbr")),
            abr=_safe_float(f.get("abr")),
            asr=_safe_int(f.get("asr")),
            format_note=_safe_str(f.get("format_note")),
            protocol=_safe_str(f.get("protocol")),
            resolution=_safe_str(f.get("resolution")),
            dynamic_range=_safe_str(f.get("dynamic_range")),
            audio_channels=_safe_int(f.get("audio_channels")),
            has_video=has_video,
            has_audio=has_audio,
            raw_data=dict(f),
        )


@dataclass(frozen=True)
class MediaInfo:
    """Нормализованные метаданные медиа-ресурса или плейлиста.

    Предоставляет прямой типизированный доступ к наиболее важным полям,
    а также методы для экспорта в JSON-совместимый словарь.
    """

    id: str
    title: str
    description: str | None = None
    duration: float | None = None
    uploader: str | None = None
    uploader_id: str | None = None
    channel: str | None = None
    channel_id: str | None = None
    channel_url: str | None = None
    webpage_url: str = ""
    thumbnail: str | None = None
    ext: str | None = None
    filesize: int | None = None
    filesize_approx: int | None = None
    upload_date: str | None = None
    view_count: int | None = None
    like_count: int | None = None
    live_status: str | None = None
    age_limit: int | None = None
    categories: tuple[str, ...] = ()
    tags: tuple[str, ...] = ()

    # Специфично для плейлистов
    is_playlist: bool = False
    entries: tuple[MediaInfo, ...] | None = None
    playlist_count: int | None = None

    # Дополнительные структуры
    formats: tuple[FormatInfo, ...] = ()
    requested_formats: tuple[FormatInfo, ...] | None = None
    subtitles: dict[str, tuple[SubtitleInfo, ...]] = field(default_factory=dict)
    thumbnails: tuple[ThumbnailInfo, ...] = ()

    # Исходный неотфильтрованный словарь yt-dlp
    raw_data: dict[str, object] = field(default_factory=dict, repr=False)

    @property
    def duration_seconds(self) -> int | None:
        """Длительность в целых секундах."""
        return int(self.duration) if self.duration is not None else None

    def get_available_resolutions(self) -> list[int]:
        """Возвращает отсортированный по убыванию список доступных разрешений видео (высота кадра).

        Например: [2160, 1440, 1080, 720, 480, 360, 240, 144].
        Идеально подходит для формирования кнопок выбора качества в ботах и UI.
        """
        heights = {
            f.height
            for f in self.formats
            if f.has_video and f.height is not None and f.height > 0
        }
        return sorted(heights, reverse=True)

    def get_video_formats(
        self, height: int | None = None, container: str | None = None
    ) -> list[FormatInfo]:
        """Возвращает список видеопотоков, опционально отфильтрованных по высоте и/или контейнеру."""
        res: list[FormatInfo] = []
        for f in self.formats:
            if not f.has_video:
                continue
            if height is not None and f.height != height:
                continue
            if container is not None and f.ext != str(container).lstrip("."):
                continue
            res.append(f)
        return res

    def get_audio_formats(self) -> list[FormatInfo]:
        """Возвращает список доступных аудиопотоков (без видео), отсортированных по убыванию битрейта."""
        res = [f for f in self.formats if f.has_audio and not f.has_video]
        return sorted(res, key=lambda f: f.tbr or f.abr or 0.0, reverse=True)

    def get_best_video_format(
        self, height: int | None = None, container: str | None = None
    ) -> FormatInfo | None:
        """Возвращает наилучший доступный видеопоток для указанного разрешения."""
        candidates = self.get_video_formats(height=height, container=container)
        if not candidates and container is not None:
            candidates = self.get_video_formats(height=height)
        if not candidates:
            return None
        return max(candidates, key=lambda f: f.tbr or f.vbr or 0.0)

    def get_best_audio_format(self) -> FormatInfo | None:
        """Возвращает наилучший доступный аудиопоток."""
        audios = self.get_audio_formats()
        return audios[0] if audios else None

    def estimate_size(self, height: int | None = None) -> int | None:
        """Оценивает суммарный размер файла (в байтах) для скачивания в указанном разрешении.

        Суммирует размер лучшего видеопотока и лучшего аудиопотока, если видеопоток раздельный.
        """
        v_fmt = self.get_best_video_format(height=height)
        if v_fmt is None:
            return None

        v_size = v_fmt.filesize or v_fmt.filesize_approx
        if v_size is None and v_fmt.tbr and self.duration:
            v_size = int((v_fmt.tbr * 1000 / 8) * self.duration)

        if v_fmt.has_audio:
            return v_size

        a_fmt = self.get_best_audio_format()
        if a_fmt is not None:
            a_size = a_fmt.filesize or a_fmt.filesize_approx
            if a_size is None and a_fmt.tbr and self.duration:
                a_size = int((a_fmt.tbr * 1000 / 8) * self.duration)
            if a_size and v_size:
                return v_size + a_size

        return v_size

    def estimate_size_str(self, height: int | None = None) -> str:
        """Возвращает оценку размера файла в человекочитаемом виде (например, '24.50 MiB' или 'N/A')."""
        size = self.estimate_size(height=height)
        if size is None:
            return "N/A"
        if size < 1024:
            return f"{size} B"
        if size < 1024 * 1024:
            return f"{size / 1024:.2f} KiB"
        if size < 1024 * 1024 * 1024:
            return f"{size / (1024 * 1024):.2f} MiB"
        return f"{size / (1024 * 1024 * 1024):.2f} GiB"

    def to_dict(self, *, remove_private_keys: bool = False) -> dict[str, object]:
        """Возвращает безопасное JSON-serializable представление словаря метаданных.

        Использует `YoutubeDL.sanitize_info()` для исключения несериализуемых типов,
        генераторов и циклических ссылок.

        Args:
            remove_private_keys: Удалять ли приватные внутренние ключи yt-dlp.

        Returns:
            Очищенный словарь метаданных.
        """
        try:
            from yt_dlp import YoutubeDL

            return cast(
                dict[str, object],
                YoutubeDL.sanitize_info(self.raw_data, remove_private_keys=remove_private_keys),
            )
        except Exception:
            # Fallback санитизация в случае отсутствия yt_dlp
            return {
                "id": self.id,
                "title": self.title,
                "duration": self.duration,
                "uploader": self.uploader,
                "webpage_url": self.webpage_url,
                "is_playlist": self.is_playlist,
            }


    @classmethod
    def from_ytdlp(cls, d: Mapping[str, object]) -> MediaInfo:
        """Фабричный метод построения `MediaInfo` из словаря `info_dict` yt-dlp.

        Args:
            d: Словарь метаданных медиа-ресурса от yt-dlp.

        Returns:
            Экземпляр MediaInfo с нормализованными данными.
        """
        is_pl = d.get("_type") in ("playlist", "multi_video") or "entries" in d

        # Обработка вложенных элементов плейлиста
        entries_tuple: tuple[MediaInfo, ...] | None = None
        if is_pl and "entries" in d and d["entries"] is not None:
            raw_entries = d["entries"]
            parsed_entries: list[MediaInfo] = []
            if isinstance(raw_entries, list):
                for item in raw_entries:
                    if isinstance(item, Mapping):
                        parsed_entries.append(cls.from_ytdlp(item))
            entries_tuple = tuple(parsed_entries)

        # Форматы
        formats_list: list[FormatInfo] = []
        raw_formats = d.get("formats")
        if isinstance(raw_formats, list):
            for f in raw_formats:
                if isinstance(f, Mapping):
                    formats_list.append(FormatInfo.from_ytdlp(f))

        # Выбранные форматы для скачивания
        req_formats_list: list[FormatInfo] | None = None
        raw_req_formats = d.get("requested_formats")
        if isinstance(raw_req_formats, list):
            req_formats_list = [
                FormatInfo.from_ytdlp(rf) for rf in raw_req_formats if isinstance(rf, Mapping)
            ]

        # Субтитры
        subs_dict: dict[str, tuple[SubtitleInfo, ...]] = {}
        raw_subs = d.get("subtitles")
        if isinstance(raw_subs, Mapping):
            for lang, tracks in raw_subs.items():
                if isinstance(tracks, list):
                    subs_dict[str(lang)] = tuple(
                        SubtitleInfo.from_ytdlp(t) for t in tracks if isinstance(t, Mapping)
                    )

        # Миниатюры
        thumbs_list: list[ThumbnailInfo] = []
        raw_thumbs = d.get("thumbnails")
        if isinstance(raw_thumbs, list):
            for t in raw_thumbs:
                if isinstance(t, Mapping):
                    thumbs_list.append(ThumbnailInfo.from_ytdlp(t))

        categories_val = d.get("categories")
        categories_tuple: tuple[str, ...] = (
            tuple(str(c) for c in categories_val)
            if isinstance(categories_val, (list, tuple))
            else ()
        )

        tags_val = d.get("tags")
        tags_tuple: tuple[str, ...] = (
            tuple(str(t) for t in tags_val) if isinstance(tags_val, (list, tuple)) else ()
        )

        return cls(
            id=str(d.get("id") or ""),
            title=str(d.get("title") or ""),
            description=_safe_str(d.get("description")),
            duration=_safe_float(d.get("duration")),
            uploader=_safe_str(d.get("uploader")),
            uploader_id=_safe_str(d.get("uploader_id")),
            channel=_safe_str(d.get("channel")),
            channel_id=_safe_str(d.get("channel_id")),
            channel_url=_safe_str(d.get("channel_url")),
            webpage_url=str(d.get("webpage_url") or d.get("original_url") or ""),
            thumbnail=_safe_str(d.get("thumbnail")),
            ext=_safe_str(d.get("ext")),
            filesize=_safe_int(d.get("filesize")),
            filesize_approx=_safe_int(d.get("filesize_approx")),
            upload_date=_safe_str(d.get("upload_date")),
            view_count=_safe_int(d.get("view_count")),
            like_count=_safe_int(d.get("like_count")),
            live_status=_safe_str(d.get("live_status")),
            age_limit=_safe_int(d.get("age_limit")),
            categories=categories_tuple,
            tags=tags_tuple,
            is_playlist=is_pl,
            entries=entries_tuple,
            playlist_count=_safe_int(d.get("playlist_count"))
            or (len(entries_tuple) if entries_tuple else None),
            formats=tuple(formats_list),
            requested_formats=tuple(req_formats_list) if req_formats_list else None,
            subtitles=subs_dict,
            thumbnails=tuple(thumbs_list),
            raw_data=dict(d),
        )


@dataclass(frozen=True)
class DownloadResult:
    """Итоговый результат операции скачивания медиа-ресурса.

    Attributes:
        filepath: Финальный абсолютный путь к скачанному и обработанному файлу.
        info: Метаданные скачанного медиа (`MediaInfo`).
        elapsed: Время выполнения операции в секундах.
        requested_formats: Форматы, которые были фактически загружены.
    """

    filepath: Path
    info: MediaInfo
    elapsed: float
    requested_formats: tuple[FormatInfo, ...] | None = None

    @property
    def filename(self) -> str:
        """Имя финального файла."""
        return self.filepath.name

    @property
    def title(self) -> str:
        """Название медиаресурса."""
        return self.info.title

    @property
    def duration(self) -> float | None:
        """Длительность медиаресурса в секундах."""
        return self.info.duration

    @property
    def exists(self) -> bool:
        """Существует ли файл на диске."""
        return self.filepath.exists()

    @property
    def file_size(self) -> int:
        """Фактический размер готового файла на диске в байтах."""
        return self.filepath.stat().st_size if self.exists else 0
