"""Пример извлечения аудиодорожки с конвертацией в MP3 и встраиванием обложки."""

import asyncio
from pathlib import Path

from async_yt_dlp import AsyncYTDLP, AsyncYTDLPError, YTDLPOptions


async def main() -> None:
    url = "https://www.youtube.com/watch?v=BaW_jenozKc"

    # Конфигурация для извлечения наилучшего аудио и конвертации в MP3
    options = YTDLPOptions(
        format="bestaudio/best",
        extract_audio=True,
        audio_format="mp3",
        audio_quality="192K",
        embed_thumbnail=True,
        embed_metadata=True,
        output_path=Path("./downloads/audio"),
        output_template="%(title)s.%(ext)s",
    )

    async with AsyncYTDLP(default_options=options) as ytdlp:
        # Проверяем доступность ffmpeg перед запуском постобработки
        deps = await ytdlp.check_dependencies()
        if not deps.ffmpeg_available:
            print(
                "Предупреждение: ffmpeg не найден в системе. Извлечение аудио может завершиться ошибкой."
            )

        try:
            print(f"Запуск извлечения аудио для: {url}")
            result = await ytdlp.download(url)

            print("\n Аудио успешно извлечено!")
            print(f"Итоговый файл: {result.filepath}")
            print(f"Размер:        {result.file_size / (1024 * 1024):.2f} MiB")

        except AsyncYTDLPError as err:
            print(f"Ошибка извлечения аудио: {err}")


if __name__ == "__main__":
    asyncio.run(main())
