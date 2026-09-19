"""Пример корректной отмены операции и обработки таймаутов."""

import asyncio

from async_yt_dlp import AsyncYTDLP, AsyncYTDLPError, YTDLPOptions


async def main() -> None:
    url = "https://www.youtube.com/watch?v=BaW_jenozKc"

    async with AsyncYTDLP() as ytdlp:
        print("1. Пример отмены фоновой задачи через asyncio Task.cancel():")
        download_task = asyncio.create_task(
            ytdlp.download(url, options=YTDLPOptions(simulate=True))
        )

        # Даем задаче запуститься и через короткое время отменяем
        await asyncio.sleep(0.05)
        download_task.cancel()

        try:
            await download_task
        except asyncio.CancelledError:
            print(" Задача была успешно отменена на уровне asyncio!")
            print(
                " Обратите внимание: фоновый поток yt-dlp завершится естественным образом, "
                "но корутина немедленно прекратила ожидание."
            )

        print("\n2. Пример использования жесткого таймаута через asyncio.timeout():")
        try:
            async with asyncio.timeout(0.01):  # Намеренно микроскопический таймаут
                await ytdlp.extract_info(url)
        except TimeoutError:
            print(" Операция прервана по истечении допустимого таймаута (TimeoutError)!")
        except AsyncYTDLPError as err:
            print(f"Ошибка библиотеки: {err}")


if __name__ == "__main__":
    asyncio.run(main())
