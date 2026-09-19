"""Пример параллельного скачивания нескольких URL через download_many."""

import asyncio

from async_yt_dlp import AsyncYTDLP, DownloadResult, ErrorPolicy, YTDLPOptions


async def main() -> None:
    # Несколько тестовых URL
    urls = [
        "https://www.youtube.com/watch?v=BaW_jenozKc",
        "https://www.youtube.com/watch?v=jNQXAC9IVRw",
    ]

    # Настраиваем клиент на максимум 2 одновременные загрузки
    async with AsyncYTDLP(
        max_concurrency=2,
        default_options=YTDLPOptions(simulate=True),
    ) as ytdlp:
        print(f"Запуск пакетного скачивания {len(urls)} ресурсов (max_concurrency=2)...")

        results = await ytdlp.download_many(
            urls,
            on_error=ErrorPolicy.COLLECT,  # Собираем как успехи, так и ошибки
        )

        print("\nРезультаты обработки:")
        for idx, item in enumerate(results, start=1):
            if isinstance(item, DownloadResult):
                print(f"  {idx}. [Успех] {item.info.title} (затрачено: {item.elapsed:.2f} с)")
            else:
                print(f"  {idx}. [Ошибка] {item}")


if __name__ == "__main__":
    asyncio.run(main())
