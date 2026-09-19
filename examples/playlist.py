"""Пример работы с плейлистами и извлечения списка элементов."""

import asyncio

from async_yt_dlp import AsyncYTDLP, AsyncYTDLPError, YTDLPOptions


async def main() -> None:
    # Пример короткого тестового плейлиста
    playlist_url = "https://www.youtube.com/playlist?list=PLrEnWoR732-BHrPp_Pm8_VleD68f9n14-"

    options = YTDLPOptions(
        extract_flat=True,  # Быстрое получение списка без глубокого парсинга каждого видео
    )

    async with AsyncYTDLP(default_options=options) as ytdlp:
        try:
            print(f"Извлечение элементов плейлиста: {playlist_url}")
            info = await ytdlp.extract_info(playlist_url, download=False)

            if not info.is_playlist:
                print("Указанный URL не является плейлистом!")
                return

            print(f"\nНазвание плейлиста: {info.title}")
            print(f"Всего видео:       {info.playlist_count}")

            if info.entries:
                print("\nСписок элементов:")
                for idx, entry in enumerate(info.entries, start=1):
                    print(
                        f"  {idx:02d}. [{entry.id}] {entry.title} ({entry.duration_seconds or '?'} сек.)"
                    )

        except AsyncYTDLPError as err:
            print(f"Ошибка извлечения плейлиста: {err}")


if __name__ == "__main__":
    asyncio.run(main())
