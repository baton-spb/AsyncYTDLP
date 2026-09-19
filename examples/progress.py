"""Пример отображения прогресса в реальном времени через async generator."""

import asyncio

from async_yt_dlp import AsyncYTDLP, AsyncYTDLPError, DownloadStatus


async def main() -> None:
    url = "https://www.youtube.com/watch?v=BaW_jenozKc"

    async with AsyncYTDLP() as ytdlp:
        try:
            print(f"Подключение и запуск стрима прогресса для: {url}\n")

            async for event in ytdlp.download_with_progress(url, throttle_interval=0.3):
                match event.status:
                    case DownloadStatus.DOWNLOADING:
                        pct = f"{event.percent:.1f}%" if event.percent is not None else "N/A"
                        print(
                            f"\r[Загрузка] {pct:>6} | Скорость: {event.speed_str:>10} "
                            f"| Скачано: {event.downloaded_str:>10} | ETA: {event.eta_str}",
                            end="",
                            flush=True,
                        )
                    case DownloadStatus.FINISHED:
                        print(f"\n[Загрузка завершена] Файл: {event.filename}")
                    case DownloadStatus.POST_PROCESSING:
                        print(
                            f"[Постобработка] Выполняется: {event.postprocessor} ({event.postprocessor_status})"
                        )
                    case DownloadStatus.COMPLETE:
                        print("\n[Готово] Вся обработка успешно завершена!")
                    case DownloadStatus.ERROR:
                        print(f"\n[Ошибка] {event.error}")

        except AsyncYTDLPError as err:
            print(f"\nОшибка операции: {err}")


if __name__ == "__main__":
    asyncio.run(main())
