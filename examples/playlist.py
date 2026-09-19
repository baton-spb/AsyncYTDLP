"""Пример работы с плейлистами: извлечение списка и последовательная потоковая загрузка."""

from __future__ import annotations

import asyncio

from async_yt_dlp import (
    AsyncYTDLP,
    AsyncYTDLPError,
    DownloadResult,
    ErrorPolicy,
    FormatSelector,
    YTDLPOptions,
)


async def main() -> None:
    playlist_url = "https://www.youtube.com/playlist?list=PLrEnWoR732-BHrPp_Pm8_VleD68f9n14-"

    # Выбираем легкий формат 720p через удобный пресет FormatSelector
    options = YTDLPOptions(
        format=FormatSelector.preset_720p(),
    )

    async with AsyncYTDLP(default_options=options) as ytdlp:
        try:
            print(f"1. Извлечение метаданных плейлиста: {playlist_url}")
            info = await ytdlp.extract_info(playlist_url, download=False)

            if not info.is_playlist:
                print("Указанный URL не является плейлистом!")
                return

            print(f"Название: {info.title}")
            print(f"Всего видео: {info.playlist_count}")

            # 2. Потоковая загрузка первых 2 видео через асинхронный генератор
            print("\n2. Запуск потоковой загрузки первых двух элементов (max_items=2):")
            async for item in ytdlp.download_playlist(
                playlist_url,
                max_items=2,
                on_error=ErrorPolicy.COLLECT,
            ):
                if isinstance(item, DownloadResult):
                    print(
                        f" -> Успешно скачано: {item.title} -> {item.filepath} ({item.elapsed:.1f} c)"
                    )
                else:
                    print(f" -> Ошибка при скачивании элемента: {item}")

        except AsyncYTDLPError as err:
            print(f"Ошибка при работе с плейлистом: {err}")


if __name__ == "__main__":
    asyncio.run(main())
