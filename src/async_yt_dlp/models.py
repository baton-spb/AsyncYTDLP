"""Типизированные модели данных для результатов экстракции и загрузки в async-yt-dlp.

Все модели являются неизменяемыми (frozen dataclass), предоставляют удобный доступ
к наиболее частым метаданным (название, длительность, автор, форматы, пути) и сохраняют
доступ к исходному словарю yt-dlp через атрибут `raw_data`.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, cast


@dataclass(frozen=True)
class ThumbnailInfo:
    """Информация о миниатюре (обложке) видео."""

    url: str
    width: int | None = None
    height: int | None = None
    id: str | None = None
    resolution: str | None = None

    @classmethod
    def from_ytdlp(cls, d: dict[str, Any]) -> ThumbnailInfo:
        return cls(
            url=str(d.get("url") or ""),
            width=d.get("width"),
            height=d.get("height"),
            id=d.get("id"),
            resolution=d.get("resolution"),
        )


@dataclass(frozen=True)
class SubtitleInfo:
    """Информация о дорожке субтитров."""

    ext: str | None = None
    url: str | None = None
    name: str | None = None

    @classmethod
    def from_ytdlp(cls, d: dict[str, Any]) -> SubtitleInfo:
        return cls(
            ext=d.get("ext"),
            url=d.get("url"),
            name=d.get("name"),
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
    raw_data: dict[str, Any] = field(default_factory=dict, repr=False)

    @classmethod
    def from_ytdlp(cls, f: dict[str, Any]) -> FormatInfo:
        vcodec = f.get("vcodec")
        acodec = f.get("acodec")
        has_video = bool(vcodec and vcodec != "none")
        has_audio = bool(acodec and acodec != "none")

        return cls(
            format_id=str(f.get("format_id") or ""),
            ext=f.get("ext"),
            width=f.get("width"),
            height=f.get("height"),
            fps=float(f["fps"]) if f.get("fps") is not None else None,
            vcodec=vcodec,
            acodec=acodec,
            filesize=f.get("filesize"),
            filesize_approx=f.get("filesize_approx"),
            tbr=float(f["tbr"]) if f.get("tbr") is not None else None,
            vbr=float(f["vbr"]) if f.get("vbr") is not None else None,
            abr=float(f["abr"]) if f.get("abr") is not None else None,
            asr=f.get("asr"),
            format_note=f.get("format_note"),
            protocol=f.get("protocol"),
            resolution=f.get("resolution"),
            dynamic_range=f.get("dynamic_range"),
            audio_channels=f.get("audio_channels"),
            has_video=has_video,
            has_audio=has_audio,
            raw_data=f,
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
    raw_data: dict[str, Any] = field(default_factory=dict, repr=False)

    @property
    def duration_seconds(self) -> int | None:
        """Длительность в целых секундах."""
        return int(self.duration) if self.duration is not None else None

    def to_dict(self, *, remove_private_keys: bool = False) -> dict[str, Any]:
        """Возвращает безопасное JSON-serializable представление словаря метаданных.

        Использует `YoutubeDL.sanitize_info()` для исключения несериализуемых типов,
        генераторов и циклических ссылок.
        """
        try:
            from yt_dlp import YoutubeDL

            return cast(
                dict[str, Any],
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
    def from_ytdlp(cls, d: dict[str, Any]) -> MediaInfo:
        """Фабричный метод построения `MediaInfo` из словаря `info_dict` yt-dlp."""
        is_pl = d.get("_type") in ("playlist", "multi_video") or "entries" in d

        # Обработка вложенных элементов плейлиста
        entries_tuple: tuple[MediaInfo, ...] | None = None
        if is_pl and "entries" in d and d["entries"] is not None:
            raw_entries = d["entries"]
            parsed_entries: list[MediaInfo] = []
            for item in raw_entries:
                if isinstance(item, dict):
                    parsed_entries.append(cls.from_ytdlp(item))
            entries_tuple = tuple(parsed_entries)

        # Форматы
        formats_list: list[FormatInfo] = []
        for f in d.get("formats") or []:
            if isinstance(f, dict):
                formats_list.append(FormatInfo.from_ytdlp(f))

        # Выбранные форматы для скачивания
        req_formats_list: list[FormatInfo] | None = None
        if d.get("requested_formats"):
            req_formats_list = [
                FormatInfo.from_ytdlp(rf) for rf in d["requested_formats"] if isinstance(rf, dict)
            ]

        # Субтитры
        subs_dict: dict[str, tuple[SubtitleInfo, ...]] = {}
        if "subtitles" in d and isinstance(d["subtitles"], dict):
            for lang, tracks in d["subtitles"].items():
                if isinstance(tracks, list):
                    subs_dict[lang] = tuple(
                        SubtitleInfo.from_ytdlp(t) for t in tracks if isinstance(t, dict)
                    )

        # Миниатюры
        thumbs_list: list[ThumbnailInfo] = []
        for t in d.get("thumbnails") or []:
            if isinstance(t, dict):
                thumbs_list.append(ThumbnailInfo.from_ytdlp(t))

        return cls(
            id=str(d.get("id") or ""),
            title=str(d.get("title") or ""),
            description=d.get("description"),
            duration=float(d["duration"]) if d.get("duration") is not None else None,
            uploader=d.get("uploader"),
            uploader_id=d.get("uploader_id"),
            channel=d.get("channel"),
            channel_id=d.get("channel_id"),
            channel_url=d.get("channel_url"),
            webpage_url=str(d.get("webpage_url") or d.get("original_url") or ""),
            thumbnail=d.get("thumbnail"),
            ext=d.get("ext"),
            filesize=d.get("filesize"),
            filesize_approx=d.get("filesize_approx"),
            upload_date=d.get("upload_date"),
            view_count=d.get("view_count"),
            like_count=d.get("like_count"),
            live_status=d.get("live_status"),
            age_limit=d.get("age_limit"),
            categories=tuple(d.get("categories") or ()),
            tags=tuple(d.get("tags") or ()),
            is_playlist=is_pl,
            entries=entries_tuple,
            playlist_count=d.get("playlist_count")
            or (len(entries_tuple) if entries_tuple else None),
            formats=tuple(formats_list),
            requested_formats=tuple(req_formats_list) if req_formats_list else None,
            subtitles=subs_dict,
            thumbnails=tuple(thumbs_list),
            raw_data=d,
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
    def exists(self) -> bool:
        """Существует ли файл на диске."""
        return self.filepath.exists()

    @property
    def file_size(self) -> int:
        """Фактический размер готового файла на диске в байтах."""
        return self.filepath.stat().st_size if self.exists else 0
