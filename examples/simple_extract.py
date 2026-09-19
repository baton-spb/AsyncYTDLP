"""Пример простого извлечения метаданных видео без его скачивания."""

import asyncio

from async_yt_dlp import AsyncYTDLP, AsyncYTDLPError


async def main() -> None:
    url = "https://www.youtube.com/watch?v=BaW_jenozKc"

    print(f"Извлечение метаданных для: {url}")

    async with AsyncYTDLP() as ytdlp:
        try:
            info = await ytdlp.extract_info(url, download=False)

            print("\n--- Информация о медиа ---")
            print(f"ID:           {info.id}")
            print(f"Название:     {info.title}")
            print(f"Автор/Канал:  {info.uploader or info.channel}")
            print(f"Длительность: {info.duration_seconds} сек.")
            print(f"Просмотры:    {info.view_count}")
            print(f"Лайки:        {info.like_count}")
            print(f"Доступно форматов: {len(info.formats)}")

            # Вывод лучших доступных форматов
            print("\nПримеры форматов:")
            for fmt in info.formats[:5]:
                print(
                    f"  - Формат {fmt.format_id}: {fmt.resolution or 'audio only'} "
                    f"({fmt.ext}, {fmt.vcodec or 'none'}/{fmt.acodec or 'none'})"
                )

        except AsyncYTDLPError as err:
            print(f"Ошибка извлечения: {err}")


if __name__ == "__main__":
    asyncio.run(main())
