"""Пример скачивания видео с настройкой выходного каталога."""

import asyncio
from pathlib import Path

from async_yt_dlp import AsyncYTDLP, AsyncYTDLPError, YTDLPOptions


async def main() -> None:
    url = "https://www.youtube.com/watch?v=BaW_jenozKc"
    downloads_dir = Path("./downloads")

    # Конфигурация клиента с ограничением формата и выбором каталога
    options = YTDLPOptions(
        format="bestvideo[height<=720]+bestaudio/best[height<=720]",
        output_path=downloads_dir,
        output_template="%(title)s [%(id)s].%(ext)s",
    )

    async with AsyncYTDLP(default_options=options) as ytdlp:
        try:
            print(f"Запуск скачивания: {url}")
            result = await ytdlp.download(url)

            print("\n Скачивание успешно завершено!")
            print(f"Файл:         {result.filepath}")
            print(f"Размер:       {result.file_size / (1024 * 1024):.2f} MiB")
            print(f"Затрачено:    {result.elapsed:.2f} сек.")

        except AsyncYTDLPError as err:
            print(f"Ошибка при скачивании: {err}")


if __name__ == "__main__":
    asyncio.run(main())
