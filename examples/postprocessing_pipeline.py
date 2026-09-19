"""Пример совместного использования AsyncYT-DLP и aio-ffmpeg: постобработка и сжатие."""

from __future__ import annotations

import asyncio
from pathlib import Path

from async_yt_dlp import (
    AsyncYTDLP,
    CompressToSize,
    FormatSelector,
    PostDownloadPipeline,
    YTDLPOptions,
)


async def main() -> None:
    url = "https://www.youtube.com/watch?v=BaW_jenozKc"
    out_dir = Path("./downloaded_media")
    out_dir.mkdir(exist_ok=True)

    # 1. Скачивание исходного видео в высоком качестве
    options = YTDLPOptions(
        format=FormatSelector.preset_max_quality(),
        output_path=out_dir,
    )

    async with AsyncYTDLP(options=options) as ytdlp:
        print(f"Скачивание видео: {url}")
        download_res = await ytdlp.download(url)
        print(f"Скачано: {download_res.filepath} ({download_res.file_size / 1024 / 1024:.2f} МБ)")

    # 2. Постобработка: нормализация громкости (loudnorm) + масштабирование до 720p
    print("\nЗапуск конвейера постобработки PostDownloadPipeline (720p + loudnorm EBU R128)...")
    pipeline = (
        PostDownloadPipeline()
        .scale(1280, 720)
        .normalize_audio(target_i=-16.0)
        .video_codec("libx264", crf=23, preset="fast")
        .audio_codec("aac", bitrate="192k")
    )
    processed_res = await pipeline.run(download_res)
    print(
        f"Готово: {processed_res.output} ({processed_res.output.stat().st_size / 1024 / 1024:.2f} МБ)"
    )

    # 3. Сжатие под лимит Telegram (например, 25 МБ)
    print("\nЦелевое двухпроходное сжатие CompressToSize под 25 МБ...")
    compressor = CompressToSize(target_size_mb=25.0)
    compressed_res = await compressor.run(download_res)
    print(f"Сжато для Telegram: {compressed_res.output}")
    print(f"Фактический размер: {compressed_res.output.stat().st_size / 1024 / 1024:.2f} МБ")


if __name__ == "__main__":
    asyncio.run(main())
