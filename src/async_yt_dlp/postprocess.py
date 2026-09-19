"""Модуль пост-процессинга медиафайлов через библиотеку `async-ffmpeg`.

Предоставляет:
- `PostProcessResult`: типизированный результат завершенной постобработки.
- `CompressToSize`: расчет и двухпроходное сжатие видеофайла под целевой лимит размера (МБ).
- `PostDownloadPipeline`: fluent-конвейер для объединения масштабирования,
  нормализации звука, перекодирования и извлечения аудио в один шаг.
"""

from __future__ import annotations

import importlib.util
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING, Self

from async_yt_dlp.enums import AudioCodec, AudioFormat, VideoCodec, VideoContainer
from async_yt_dlp.exceptions import DependencyError, PostProcessingError
from async_yt_dlp.models import DownloadResult

if TYPE_CHECKING:
    from async_ffmpeg.client import FFmpegClient


def _require_async_ffmpeg() -> None:
    """Проверяет доступность библиотеки `async-ffmpeg` в текущем окружении.

    Raises:
        DependencyError: Если пакет `async-ffmpeg` не установлен.
    """
    if importlib.util.find_spec("async_ffmpeg") is None:
        raise DependencyError(
            "Для использования модуля postprocess требуется установить пакет async-ffmpeg. "
            "Выполните: uv add async-yt-dlp[ffmpeg] или uv add async-ffmpeg."
        )


def _resolve_source_info(
    source: DownloadResult | Path | str,
) -> tuple[Path, str | None, float | None]:
    """Извлекает файловый путь, название и длительность из результата скачивания или пути."""
    if isinstance(source, DownloadResult):
        return source.filepath, source.title, source.duration
    p = Path(source)
    return p, p.stem, None


@dataclass(frozen=True, slots=True)
class PostProcessResult:
    """Результат выполнения постобработки медиафайла.

    Attributes:
        source: Исходный файл.
        output: Итоговый сгенерированный файл.
        duration_seconds: Длительность медиа в секундах (если доступна).
        success: Завершилась ли операция успешно.
        title: Название медиа (если доступно).
        details: Словарь с дополнительными техническими деталями (битрейт, статистика).
    """

    source: Path
    output: Path
    duration_seconds: float | None = None
    success: bool = True
    title: str | None = None
    details: dict[str, object] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class CompressToSize:
    """Инструмент двухпроходного сжатия медиафайла под заданный лимит размера.

    Автоматически рассчитывает оптимальный битрейт видео на основе длительности
    и резервирует 3% емкости под заголовки и метаданные контейнера MP4.

    Attributes:
        target_size_mb: Целевой размер итогового файла в мегабайтах (например, 50 для Telegram).
        video_codec: Видеокодек для сжатия (по умолчанию VideoCodec.H264 или 'libx264').
        audio_codec: Аудиокодек (по умолчанию AudioCodec.AAC или 'aac').
        audio_bitrate_kbps: Битрейт аудиопотока в кбит/с (по умолчанию 128).
        preset: Пресет кодировщика (по умолчанию 'medium').
    """

    target_size_mb: float
    video_codec: VideoCodec | str = VideoCodec.H264
    audio_codec: AudioCodec | str = AudioCodec.AAC
    audio_bitrate_kbps: int = 128
    preset: str = "medium"

    def __post_init__(self) -> None:
        """Валидирует диапазоны параметров сжатия."""
        if self.target_size_mb <= 0:
            raise ValueError(
                f"Параметр target_size_mb должен быть > 0 МБ, получено: {self.target_size_mb}"
            )
        if self.audio_bitrate_kbps <= 0:
            raise ValueError(
                f"Параметр audio_bitrate_kbps должен быть > 0 кбит/с, получено: {self.audio_bitrate_kbps}"
            )

    async def run(
        self,
        source: DownloadResult | Path | str,
        output: Path | str | None = None,
        *,
        client: FFmpegClient | None = None,
        on_progress: Callable[[object], object] | None = None,
    ) -> PostProcessResult:
        """Запускает двухпроходное сжатие видеофайла.

        Args:
            source: Объект DownloadResult или путь к исходному файлу.
            output: Пользовательский выходной путь. Если не указан, создается файл `<name>_<size>mb.mp4`.
            client: Экземпляр FFmpegClient. Если не задан, создается автоматически.
            on_progress: Опциональный callback прогресса FFmpeg.

        Returns:
            Экземпляр `PostProcessResult` с параметрами готового файла.

        Raises:
            DependencyError: Если библиотека async-ffmpeg не установлена.
            PostProcessingError: Если не удалось рассчитать параметры или выполнить сжатие.
        """
        _require_async_ffmpeg()
        from async_ffmpeg.client import FFmpegClient as ClientCls

        cli = client if client is not None else ClientCls()
        source_path, title, duration = _resolve_source_info(source)

        if not source_path.exists():
            raise PostProcessingError(f"Исходный файл для сжатия не найден: {source_path}")

        # Если длительность не была получена из метаданных yt-dlp, опрашиваем ffprobe
        if duration is None or duration <= 0:
            try:
                probe_res = await cli.probe(source_path)
                duration = probe_res.duration
            except Exception as probe_err:
                raise PostProcessingError(
                    f"Не удалось определить длительность медиафайла '{source_path}': {probe_err}"
                ) from probe_err

        if duration is None or duration <= 0:
            raise PostProcessingError(
                f"Некорректная длительность медиафайла ({duration} с), расчет битрейта невозможен."
            )

        # Расчет битрейта с учетом 3% оверхеда контейнера
        target_bytes = self.target_size_mb * 1024 * 1024
        safe_target_bytes = target_bytes * 0.97
        total_bits = safe_target_bytes * 8
        total_bps = total_bits / duration

        audio_bps = self.audio_bitrate_kbps * 1000
        video_bps = max(100_000.0, total_bps - audio_bps)
        video_kbps = int(video_bps / 1000)

        out_path = (
            Path(output)
            if output is not None
            else source_path.parent / f"{source_path.stem}_{int(self.target_size_mb)}mb.mp4"
        )

        try:
            proc_res = await cli.two_pass_transcode(
                input=source_path,
                output=out_path,
                video_codec=self.video_codec,
                bitrate=f"{video_kbps}k",
                audio_codec=self.audio_codec,
                audio_bitrate=f"{self.audio_bitrate_kbps}k",
                preset=self.preset,
                on_progress=on_progress,  # type: ignore[arg-type]
            )
        except Exception as trans_err:
            raise PostProcessingError(
                f"Ошибка во время двухпроходного сжатия: {trans_err}"
            ) from trans_err

        if not proc_res.success:
            raise PostProcessingError(
                f"FFmpeg завершился с ошибкой (код {proc_res.exit_code}): {proc_res.stderr_text}"
            )

        return PostProcessResult(
            source=source_path,
            output=out_path,
            duration_seconds=duration,
            success=True,
            title=title,
            details={
                "video_bitrate_kbps": video_kbps,
                "audio_bitrate_kbps": self.audio_bitrate_kbps,
                "raw_result": proc_res,
            },
        )


class PostDownloadPipeline:
    """Fluent-конвейер постобработки загруженных файлов через FFmpeg.

    Позволяет в единой цепочке вызовов задавать масштабирование, нормализацию звука,
    смену кодеков или извлечение аудиодорожки.
    """

    def __init__(self, *, client: FFmpegClient | None = None) -> None:
        """Инициализирует пустой конвейер постобработки."""
        self._client = client
        self._scale_dims: tuple[int, int] | None = None
        self._normalize_audio: bool = False
        self._loudnorm_target: float = -16.0
        self._trim_range: tuple[float | None, float | None, float | None] | None = None
        self._video_codec: str | None = None
        self._crf: int | None = None
        self._preset: str | None = None
        self._audio_codec: str | None = None
        self._audio_bitrate: str | None = None
        self._extract_audio_mode: bool = False
        self._remux_ext: str | None = None
        self._compress_target_mb: float | None = None

    def scale(self, width: int | tuple[int, int], height: int | None = None) -> Self:
        """Задает масштабирование видео в целевое разрешение.

        Args:
            width: Ширина кадра или кортеж (ширина, высота), например `Resolution.HD_720P`.
            height: Высота кадра (необязательна, если передан кортеж в `width`).
        """
        if isinstance(width, tuple):
            w, h = width
        elif height is not None:
            w, h = width, height
        else:
            raise ValueError(
                "Необходимо указать высоту height или передать кортеж (ширина, высота)"
            )

        if w <= 0 or h <= 0:
            raise ValueError(f"Размеры кадра должны быть строго положительными, получено: {w}x{h}")

        self._scale_dims = (w, h)
        return self

    def normalize_audio(self, target_i: float = -16.0) -> Self:
        """Включает нормализацию громкости по стандарту EBU R128 (loudnorm).

        Args:
            target_i: Целевая интегральная громкость в LUFS (по умолчанию -16 LUFS для веба/подкастов).
        """
        self._normalize_audio = True
        self._loudnorm_target = target_i
        return self

    def trim(
        self,
        *,
        start: float | None = None,
        end: float | None = None,
        duration: float | None = None,
    ) -> Self:
        """Задает интервал обрезки медиафайла.

        Args:
            start: Начало фрагмента в секундах (>= 0).
            end: Конец фрагмента в секундах.
            duration: Длительность фрагмента в секундах (> 0).
        """
        if start is not None and start < 0:
            raise ValueError(f"Параметр start должен быть >= 0 секунд, получено: {start}")
        if duration is not None and duration <= 0:
            raise ValueError(f"Параметр duration должен быть > 0 секунд, получено: {duration}")
        if start is not None and end is not None and end <= start:
            raise ValueError(
                f"Конечная метка end ({end}) должна быть больше начальной start ({start})"
            )

        self._trim_range = (start, end, duration)
        return self

    def video_codec(
        self,
        codec: VideoCodec | str = VideoCodec.H264,
        *,
        crf: int | None = 23,
        preset: str | None = "medium",
    ) -> Self:
        """Настраивает видеокодек и параметры сжатия.

        Args:
            codec: Имя или перечисление видеокодека (например, VideoCodec.H264, 'libx264', 'copy').
            crf: Фактор постоянного качества (CRF, диапазон 0..51).
            preset: Пресет кодирования (например, 'fast', 'medium', 'slow').
        """
        if crf is not None and not (0 <= crf <= 51):
            raise ValueError(f"Параметр crf должен быть в диапазоне от 0 до 51, получено: {crf}")

        self._video_codec = str(codec)
        self._crf = crf
        self._preset = preset
        return self

    def audio_codec(
        self,
        codec: AudioCodec | str = AudioCodec.AAC,
        *,
        bitrate: str = "192k",
    ) -> Self:
        """Настраивает параметры аудиокодека.

        Args:
            codec: Имя или перечисление аудиокодека (например, AudioCodec.AAC, 'libmp3lame', 'copy').
            bitrate: Битрейт аудиопотока (например, '192k', '320k').
        """
        self._audio_codec = str(codec)
        self._audio_bitrate = bitrate
        return self

    def extract_audio(
        self,
        codec: AudioFormat | AudioCodec | str = AudioFormat.MP3,
        *,
        bitrate: str = "320k",
    ) -> Self:
        """Переводит конвейер в режим чистого извлечения аудиодорожки без видео.

        Args:
            codec: Целевой формат или кодек аудио (например, AudioFormat.MP3, 'mp3', 'flac').
            bitrate: Битрейт аудиопотока.
        """
        self._extract_audio_mode = True
        self._audio_codec = str(codec)
        self._audio_bitrate = bitrate
        return self

    def remux(self, container: VideoContainer | str = VideoContainer.MP4) -> Self:
        """Включает быструю смену контейнера (stream copy) без перекодирования.

        Args:
            container: Целевой контейнер или расширение (например, VideoContainer.MP4, 'mkv').
        """
        self._remux_ext = str(container).lstrip(".")
        return self

    def compress_to_size(self, target_size_mb: float) -> Self:
        """Задает целевое сжатие файла под лимит размера в МБ.

        Args:
            target_size_mb: Максимальный размер в мегабайтах (должен быть > 0).
        """
        if target_size_mb <= 0:
            raise ValueError(
                f"Параметр target_size_mb должен быть > 0 МБ, получено: {target_size_mb}"
            )
        self._compress_target_mb = target_size_mb
        return self

    async def run(
        self,
        download: DownloadResult | Path | str,
        output: Path | str | None = None,
        *,
        on_progress: Callable[[object], object] | None = None,
    ) -> PostProcessResult:
        """Выполняет сконфигурированный конвейер над указанным файлом.

        Args:
            download: Результат скачивания DownloadResult или путь к файлу.
            output: Пользовательский путь к выходному файлу (если None, генерируется рядом).
            on_progress: Опциональный callback прогресса выполнения.

        Returns:
            Экземпляр `PostProcessResult`.

        Raises:
            DependencyError: Если async-ffmpeg не установлен.
            PostProcessingError: При ошибке выполнения FFmpeg.
        """
        _require_async_ffmpeg()
        from async_ffmpeg.client import FFmpegClient as ClientCls

        cli = self._client if self._client is not None else ClientCls()
        source_path, title, _duration = _resolve_source_info(download)

        if not source_path.exists():
            raise PostProcessingError(f"Исходный файл для постобработки не найден: {source_path}")

        # 1. Режим сжатия до размера
        if self._compress_target_mb is not None:
            compressor = CompressToSize(
                target_size_mb=self._compress_target_mb,
                video_codec=self._video_codec or "libx264",
                audio_codec=self._audio_codec or "aac",
                audio_bitrate_kbps=128,
                preset=self._preset or "medium",
            )
            return await compressor.run(
                source=source_path,
                output=output,
                client=cli,
                on_progress=on_progress,
            )

        # 2. Режим извлечения звуковой дорожки
        if self._extract_audio_mode:
            target_codec = self._audio_codec or "mp3"
            target_bitrate = self._audio_bitrate or "320k"
            ext = "mp3" if "mp3" in target_codec else ("m4a" if "aac" in target_codec else "mp3")
            out_path = Path(output) if output else source_path.parent / f"{source_path.stem}.{ext}"

            try:
                proc_res = await cli.extract_audio(
                    input=source_path,
                    output=out_path,
                    codec=target_codec,
                    bitrate=target_bitrate,
                    on_progress=on_progress,  # type: ignore[arg-type]
                )
            except Exception as extract_err:
                raise PostProcessingError(
                    f"Ошибка извлечения аудио: {extract_err}"
                ) from extract_err

            if not proc_res.success:
                raise PostProcessingError(
                    f"FFmpeg extract_audio завершился с ошибкой: {proc_res.stderr_text}"
                )

            return PostProcessResult(
                source=source_path,
                output=out_path,
                duration_seconds=proc_res.duration_seconds,
                success=True,
                title=title,
                details={"raw_result": proc_res},
            )

        # 3. Режим быстрой смены контейнера (remux)
        if self._remux_ext is not None and not self._scale_dims and not self._normalize_audio:
            out_path = (
                Path(output)
                if output
                else source_path.parent / f"{source_path.stem}_remux.{self._remux_ext}"
            )
            try:
                proc_res = await cli.convert(
                    input=source_path,
                    output=out_path,
                    copy=True,
                    on_progress=on_progress,  # type: ignore[arg-type]
                )
            except Exception as conv_err:
                raise PostProcessingError(f"Ошибка смены контейнера: {conv_err}") from conv_err

            if not proc_res.success:
                raise PostProcessingError(
                    f"FFmpeg convert завершился с ошибкой: {proc_res.stderr_text}"
                )

            return PostProcessResult(
                source=source_path,
                output=out_path,
                duration_seconds=proc_res.duration_seconds,
                success=True,
                title=title,
                details={"raw_result": proc_res},
            )

        # 4. Комплексный конвейер фильтров (MediaPipeline)
        pipe = cli.pipeline(source_path)

        if self._scale_dims:
            pipe.scale(self._scale_dims[0], self._scale_dims[1])

        if self._normalize_audio:
            pipe.normalize_audio(target_lufs=self._loudnorm_target)

        if self._trim_range:
            t_start, t_end, t_dur = self._trim_range
            pipe.trim(start=t_start, end=t_end, duration=t_dur)

        if self._video_codec:
            pipe.video_codec(self._video_codec, crf=self._crf, preset=self._preset)

        if self._audio_codec:
            pipe.audio_codec(self._audio_codec, bitrate=self._audio_bitrate)

        out_path = (
            Path(output) if output else source_path.parent / f"{source_path.stem}_processed.mp4"
        )
        pipe.output(out_path)

        try:
            proc_res = await pipe.run(on_progress=on_progress)  # type: ignore[arg-type]
        except Exception as pipe_err:
            raise PostProcessingError(f"Ошибка выполнения конвейера: {pipe_err}") from pipe_err

        if not proc_res.success:
            raise PostProcessingError(
                f"FFmpeg pipeline завершился с ошибкой: {proc_res.stderr_text}"
            )

        return PostProcessResult(
            source=source_path,
            output=out_path,
            duration_seconds=proc_res.duration_seconds,
            success=True,
            title=title,
            details={"raw_result": proc_res},
        )
