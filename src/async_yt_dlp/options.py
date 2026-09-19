"""Типизированная конфигурация параметров для yt-dlp и библиотеки async-yt-dlp.

Предоставляет класс `YTDLPOptions` (frozen dataclass), сочетающий:
- Строго типизированные поля для большинства частых настроек.
- Автоматическое построение цепочек стандартных postprocessors yt-dlp (аудио, субтитры, обложки).
- Поле `raw_options` для передачи любых низкоуровневых параметров `yt-dlp` (forward compatibility).
- Детерминированное слияние опций разных уровней (библиотека -> клиент -> операция).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from async_yt_dlp._constants import DEFAULT_OUTPUT_TEMPLATE
from async_yt_dlp._logging import redact_options
from async_yt_dlp.enums import AudioFormat, VideoContainer
from async_yt_dlp.format import FormatSelector


@dataclass(frozen=True)
class YTDLPOptions:
    """Неизменяемый (frozen) набор параметров для YoutubeDL.

    Позволяет настраивать выбор форматов, файловые пути, постобработку,
    сетевые соединения, аутентификацию и поведение загрузчика.

    Для параметров, ещё не имеющих прямого типизированного поля,
    используйте словарь `raw_options`, значения из которого имеют наивысший приоритет.
    """

    # Выбор формата медиа
    format: str | FormatSelector | None = None
    format_sort: list[str] | str | None = None
    format_sort_force: bool | None = None

    # Файловая система и пути
    output_template: str | None = None
    output_path: Path | str | None = None
    temp_path: Path | str | None = None
    paths: dict[str, Path | str] | None = None
    restrict_filenames: bool | None = None
    windows_filenames: bool | None = None
    no_overwrites: bool | None = None
    continue_download: bool | None = None
    use_part_files: bool | None = None

    # Сеть и прокси
    proxy: str | None = None
    socket_timeout: float | None = None
    source_address: str | None = None
    impersonate: str | None = None
    allow_file_urls: bool = False
    http_headers: dict[str, str] | None = None

    # Аутентификация и cookies
    cookies_file: Path | str | None = None
    cookies_from_browser: tuple[str, ...] | str | None = None
    username: str | None = None
    password: str | None = None
    video_password: str | None = None

    # Повторные попытки и лимиты
    retries: int | None = None
    fragment_retries: int | None = None
    file_access_retries: int | None = None
    extractor_retries: int | None = None
    rate_limit: int | None = None
    throttled_rate_limit: int | None = None
    concurrent_fragments: int | None = None

    # Постобработка
    extract_audio: bool | None = None
    audio_format: AudioFormat | str | None = None  # mp3, m4a, flac, opus, wav, aac, best
    audio_quality: str | int | None = None  # 0-10 или битрейт (например, "192K")
    remux_video: VideoContainer | str | None = None  # mp4, mkv, webm и др.
    recode_video: VideoContainer | str | None = None
    embed_thumbnail: bool | None = None
    embed_metadata: bool | None = None
    embed_subtitles: bool | None = None
    ffmpeg_location: Path | str | None = None
    postprocessors: tuple[dict[str, object], ...] | None = None

    # Субтитры и миниатюры
    write_subtitles: bool | None = None
    write_auto_subtitles: bool | None = None
    subtitles_langs: tuple[str, ...] | None = None
    subtitles_format: str | None = None
    write_thumbnail: bool | None = None
    write_all_thumbnails: bool | None = None

    # Метаданные и информация
    write_info_json: bool | None = None
    clean_info_json: bool | None = None
    write_description: bool | None = None

    # Поведение экстракции
    extract_flat: bool | str | None = None
    ignore_errors: bool | None = None
    simulate: bool | None = None
    skip_download: bool | None = None
    extractor_args: dict[str, object] | None = None
    js_runtimes: tuple[str, ...] | list[str] | dict[str, object] | None = None

    # Логирование и консольный вывод (по умолчанию выключены для библиотечного использования)
    quiet: bool = True
    no_warnings: bool = True
    verbose: bool = False

    # Произвольные низкоуровневые опции yt-dlp (наивысший приоритет)
    raw_options: dict[str, object] = field(default_factory=dict)

    def __post_init__(self) -> None:
        """Выполняет строгую валидацию диапазонов числовых параметров."""
        if self.socket_timeout is not None and self.socket_timeout <= 0:
            raise ValueError(
                f"Параметр socket_timeout должен быть > 0 секунд, получено: {self.socket_timeout}"
            )
        if self.retries is not None and self.retries < 0:
            raise ValueError(f"Параметр retries должен быть >= 0, получено: {self.retries}")
        if self.fragment_retries is not None and self.fragment_retries < 0:
            raise ValueError(
                f"Параметр fragment_retries должен быть >= 0, получено: {self.fragment_retries}"
            )
        if self.extractor_retries is not None and self.extractor_retries < 0:
            raise ValueError(
                f"Параметр extractor_retries должен быть >= 0, получено: {self.extractor_retries}"
            )
        if self.file_access_retries is not None and self.file_access_retries < 0:
            raise ValueError(
                f"Параметр file_access_retries должен быть >= 0, получено: {self.file_access_retries}"
            )
        if self.rate_limit is not None and self.rate_limit <= 0:
            raise ValueError(
                f"Параметр rate_limit должен быть > 0 байт/с, получено: {self.rate_limit}"
            )
        if self.throttled_rate_limit is not None and self.throttled_rate_limit <= 0:
            raise ValueError(
                f"Параметр throttled_rate_limit должен быть > 0 байт/с, получено: {self.throttled_rate_limit}"
            )
        if self.concurrent_fragments is not None and self.concurrent_fragments < 1:
            raise ValueError(
                f"Параметр concurrent_fragments должен быть >= 1, получено: {self.concurrent_fragments}"
            )
        if isinstance(self.audio_quality, int) and not (0 <= self.audio_quality <= 10):
            raise ValueError(
                f"Численный параметр audio_quality (VBR) должен быть в диапазоне от 0 до 10, получено: {self.audio_quality}"
            )

    def to_ytdlp_params(self) -> dict[str, object]:
        """Преобразует типизированные настройки в словарь параметров `params` для `YoutubeDL`.

        Автоматически генерирует корректную конфигурацию postprocessors для ffmpeg,
        настраивает структуру путей `paths` и шаблонов `outtmpl`.

        Returns:
            Словарь аргументов для передачи в `YoutubeDL(params)`.
        """
        params: dict[str, object] = {
            # Базовые параметры библиотеки
            "quiet": self.quiet,
            "no_warnings": self.no_warnings,
            "verbose": self.verbose,
            "noprogress": True,  # Прогресс отслеживается через async bridge, отключаем терминальный вывод
        }

        # Выбор формата
        if self.format is not None:
            params["format"] = str(self.format)
        if self.format_sort is not None:
            params["format_sort"] = (
                self.format_sort if isinstance(self.format_sort, list) else [self.format_sort]
            )
        if self.format_sort_force is not None:
            params["format_sort_force"] = self.format_sort_force

        # Шаблон вывода
        if self.output_template is not None:
            params["outtmpl"] = {"default": self.output_template}
        else:
            params["outtmpl"] = {"default": DEFAULT_OUTPUT_TEMPLATE}

        # Пути
        paths_dict: dict[str, str] = {}
        if self.paths:
            for k, v in self.paths.items():
                paths_dict[k] = str(v)
        if self.output_path is not None:
            paths_dict["home"] = str(self.output_path)
        if self.temp_path is not None:
            paths_dict["temp"] = str(self.temp_path)
        if paths_dict:
            params["paths"] = paths_dict

        # Файловые флаги
        if self.restrict_filenames is not None:
            params["restrictfilenames"] = self.restrict_filenames
        if self.windows_filenames is not None:
            params["windowsfilenames"] = self.windows_filenames
        if self.no_overwrites is not None:
            params["overwrites"] = not self.no_overwrites
        if self.continue_download is not None:
            params["continuedl"] = self.continue_download
        if self.use_part_files is not None:
            params["nopart"] = not self.use_part_files

        # Сеть
        if self.proxy is not None:
            params["proxy"] = self.proxy
        if self.socket_timeout is not None:
            params["socket_timeout"] = self.socket_timeout
        if self.source_address is not None:
            params["source_address"] = self.source_address
        if self.impersonate is not None:
            params["impersonate"] = self.impersonate
        if self.allow_file_urls:
            params["enable_file_urls"] = True
        if self.http_headers:
            params["http_headers"] = dict(self.http_headers)

        # Cookies и авторизация
        if self.cookies_file is not None:
            params["cookiefile"] = str(self.cookies_file)
        if self.cookies_from_browser is not None:
            if isinstance(self.cookies_from_browser, tuple):
                params["cookiesfrombrowser"] = self.cookies_from_browser
            else:
                params["cookiesfrombrowser"] = (self.cookies_from_browser,)
        if self.username is not None:
            params["username"] = self.username
        if self.password is not None:
            params["password"] = self.password
        if self.video_password is not None:
            params["videopassword"] = self.video_password

        # Повторные попытки
        if self.retries is not None:
            params["retries"] = self.retries
        if self.fragment_retries is not None:
            params["fragment_retries"] = self.fragment_retries
        if self.file_access_retries is not None:
            params["file_access_retries"] = self.file_access_retries
        if self.extractor_retries is not None:
            params["extractor_retries"] = self.extractor_retries
        if self.rate_limit is not None:
            params["ratelimit"] = self.rate_limit
        if self.throttled_rate_limit is not None:
            params["throttledratelimit"] = self.throttled_rate_limit
        if self.concurrent_fragments is not None:
            params["concurrent_fragment_downloads"] = self.concurrent_fragments

        # Флаги симуляции и пропуска
        if self.simulate is not None:
            params["simulate"] = self.simulate
        if self.skip_download is not None:
            params["skip_download"] = self.skip_download
        if self.ignore_errors is not None:
            params["ignoreerrors"] = self.ignore_errors
        if self.extract_flat is not None:
            params["extract_flat"] = self.extract_flat
        if self.extractor_args is not None:
            params["extractor_args"] = dict(self.extractor_args)
        if self.js_runtimes is not None:
            if isinstance(self.js_runtimes, dict):
                params["js_runtimes"] = self.js_runtimes
            else:
                params["js_runtimes"] = {rt: {} for rt in self.js_runtimes}

        # Субтитры и миниатюры
        if self.write_subtitles is not None:
            params["writesubtitles"] = self.write_subtitles
        if self.write_auto_subtitles is not None:
            params["writeautomaticsubs"] = self.write_auto_subtitles
        if self.subtitles_langs is not None:
            params["subtitleslangs"] = list(self.subtitles_langs)
        if self.subtitles_format is not None:
            params["subtitlesformat"] = self.subtitles_format
        if self.write_thumbnail is not None:
            params["writethumbnail"] = self.write_thumbnail
        if self.write_all_thumbnails is not None:
            params["write_all_thumbnails"] = self.write_all_thumbnails

        # Метаданные
        if self.write_info_json is not None:
            params["writeinfojson"] = self.write_info_json
        if self.clean_info_json is not None:
            params["clean_infojson"] = self.clean_info_json
        if self.write_description is not None:
            params["writedescription"] = self.write_description

        # ffmpeg
        if self.ffmpeg_location is not None:
            params["ffmpeg_location"] = str(self.ffmpeg_location)

        # Сборка цепочки postprocessors
        pps: list[dict[str, object]] = []
        if self.postprocessors:
            pps.extend(dict(pp) for pp in self.postprocessors)

        if self.extract_audio:
            audio_pp: dict[str, object] = {"key": "FFmpegExtractAudio"}
            if self.audio_format:
                audio_pp["preferredcodec"] = str(self.audio_format)
            if self.audio_quality is not None:
                audio_pp["preferredquality"] = str(self.audio_quality)
            pps.append(audio_pp)

        if self.remux_video:
            pps.append({"key": "FFmpegVideoRemuxer", "preferedformat": str(self.remux_video)})

        if self.recode_video:
            pps.append({"key": "FFmpegVideoConvertor", "preferedformat": str(self.recode_video)})

        if self.embed_thumbnail:
            pps.append({"key": "EmbedThumbnail"})

        if self.embed_metadata:
            pps.append({"key": "FFmpegMetadata"})

        if self.embed_subtitles:
            pps.append({"key": "FFmpegEmbedSubtitle"})

        if pps:
            params["postprocessors"] = pps

        # Наложение пользовательских raw_options (наивысший приоритет)
        if self.raw_options:
            params.update(self.raw_options)

        return params

    def merge(self, other: YTDLPOptions | None) -> YTDLPOptions:
        """Сливает текущие параметры с другими с учетом приоритета.

        Значения из `other` замещают значения текущего объекта, если они не `None`.
        Словари (`raw_options`, `paths`, `http_headers`, `extractor_args`) объединяются.

        Args:
            other: Переопределяющие параметры (например, переданные в конкретный метод).

        Returns:
            Новый экземпляр `YTDLPOptions`.
        """
        if other is None:
            return self

        merged_raw = dict(self.raw_options)
        merged_raw.update(other.raw_options)

        merged_paths: dict[str, Path | str] = {}
        if self.paths:
            merged_paths.update(self.paths)
        if other.paths:
            merged_paths.update(other.paths)

        merged_headers: dict[str, str] = {}
        if self.http_headers:
            merged_headers.update(self.http_headers)
        if other.http_headers:
            merged_headers.update(other.http_headers)

        merged_extractor_args: dict[str, object] = {}
        if self.extractor_args:
            merged_extractor_args.update(self.extractor_args)
        if other.extractor_args:
            merged_extractor_args.update(other.extractor_args)

        # Объединение списков постпроцессоров
        merged_pps: tuple[dict[str, object], ...] | None = None
        if self.postprocessors or other.postprocessors:
            base_pps = list(self.postprocessors or ())
            override_pps = list(other.postprocessors or ())
            merged_pps = tuple(base_pps + override_pps)

        return YTDLPOptions(
            format=other.format if other.format is not None else self.format,
            format_sort=other.format_sort if other.format_sort is not None else self.format_sort,
            format_sort_force=other.format_sort_force
            if other.format_sort_force is not None
            else self.format_sort_force,
            output_template=other.output_template
            if other.output_template is not None
            else self.output_template,
            output_path=other.output_path if other.output_path is not None else self.output_path,
            temp_path=other.temp_path if other.temp_path is not None else self.temp_path,
            paths=merged_paths if merged_paths else None,
            restrict_filenames=other.restrict_filenames
            if other.restrict_filenames is not None
            else self.restrict_filenames,
            windows_filenames=other.windows_filenames
            if other.windows_filenames is not None
            else self.windows_filenames,
            no_overwrites=other.no_overwrites
            if other.no_overwrites is not None
            else self.no_overwrites,
            continue_download=other.continue_download
            if other.continue_download is not None
            else self.continue_download,
            use_part_files=other.use_part_files
            if other.use_part_files is not None
            else self.use_part_files,
            proxy=other.proxy if other.proxy is not None else self.proxy,
            socket_timeout=other.socket_timeout
            if other.socket_timeout is not None
            else self.socket_timeout,
            source_address=other.source_address
            if other.source_address is not None
            else self.source_address,
            impersonate=other.impersonate if other.impersonate is not None else self.impersonate,
            allow_file_urls=other.allow_file_urls or self.allow_file_urls,
            http_headers=merged_headers if merged_headers else None,
            cookies_file=other.cookies_file
            if other.cookies_file is not None
            else self.cookies_file,
            cookies_from_browser=other.cookies_from_browser
            if other.cookies_from_browser is not None
            else self.cookies_from_browser,
            username=other.username if other.username is not None else self.username,
            password=other.password if other.password is not None else self.password,
            video_password=other.video_password
            if other.video_password is not None
            else self.video_password,
            retries=other.retries if other.retries is not None else self.retries,
            fragment_retries=other.fragment_retries
            if other.fragment_retries is not None
            else self.fragment_retries,
            file_access_retries=other.file_access_retries
            if other.file_access_retries is not None
            else self.file_access_retries,
            extractor_retries=other.extractor_retries
            if other.extractor_retries is not None
            else self.extractor_retries,
            rate_limit=other.rate_limit if other.rate_limit is not None else self.rate_limit,
            throttled_rate_limit=other.throttled_rate_limit
            if other.throttled_rate_limit is not None
            else self.throttled_rate_limit,
            concurrent_fragments=other.concurrent_fragments
            if other.concurrent_fragments is not None
            else self.concurrent_fragments,
            extract_audio=other.extract_audio
            if other.extract_audio is not None
            else self.extract_audio,
            audio_format=other.audio_format
            if other.audio_format is not None
            else self.audio_format,
            audio_quality=other.audio_quality
            if other.audio_quality is not None
            else self.audio_quality,
            remux_video=other.remux_video if other.remux_video is not None else self.remux_video,
            recode_video=other.recode_video
            if other.recode_video is not None
            else self.recode_video,
            embed_thumbnail=other.embed_thumbnail
            if other.embed_thumbnail is not None
            else self.embed_thumbnail,
            embed_metadata=other.embed_metadata
            if other.embed_metadata is not None
            else self.embed_metadata,
            embed_subtitles=other.embed_subtitles
            if other.embed_subtitles is not None
            else self.embed_subtitles,
            ffmpeg_location=other.ffmpeg_location
            if other.ffmpeg_location is not None
            else self.ffmpeg_location,
            postprocessors=merged_pps,
            write_subtitles=other.write_subtitles
            if other.write_subtitles is not None
            else self.write_subtitles,
            write_auto_subtitles=other.write_auto_subtitles
            if other.write_auto_subtitles is not None
            else self.write_auto_subtitles,
            subtitles_langs=other.subtitles_langs
            if other.subtitles_langs is not None
            else self.subtitles_langs,
            subtitles_format=other.subtitles_format
            if other.subtitles_format is not None
            else self.subtitles_format,
            write_thumbnail=other.write_thumbnail
            if other.write_thumbnail is not None
            else self.write_thumbnail,
            write_all_thumbnails=other.write_all_thumbnails
            if other.write_all_thumbnails is not None
            else self.write_all_thumbnails,
            write_info_json=other.write_info_json
            if other.write_info_json is not None
            else self.write_info_json,
            clean_info_json=other.clean_info_json
            if other.clean_info_json is not None
            else self.clean_info_json,
            write_description=other.write_description
            if other.write_description is not None
            else self.write_description,
            extract_flat=other.extract_flat
            if other.extract_flat is not None
            else self.extract_flat,
            ignore_errors=other.ignore_errors
            if other.ignore_errors is not None
            else self.ignore_errors,
            simulate=other.simulate if other.simulate is not None else self.simulate,
            skip_download=other.skip_download
            if other.skip_download is not None
            else self.skip_download,
            extractor_args=merged_extractor_args if merged_extractor_args else None,
            js_runtimes=other.js_runtimes if other.js_runtimes is not None else self.js_runtimes,
            quiet=other.quiet,
            no_warnings=other.no_warnings,
            verbose=other.verbose,
            raw_options=merged_raw,
        )

    def to_safe_dict(self) -> dict[str, object]:
        """Возвращает словарь параметров с маскированием паролей и секретов для логирования."""
        return redact_options(self.to_ytdlp_params())
