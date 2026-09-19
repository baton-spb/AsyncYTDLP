# Отслеживание прогресса и асинхронный мост (ProgressBridge)

В `async-yt-dlp` реализована надежная система трансляции прогресса скачивания
и стадий постобработки из синхронного кода `yt-dlp` в асинхронный event loop.

---

## 1. Структура `ProgressEvent`

Каждое событие прогресса инкапсулировано в неизменяемый класс `ProgressEvent`:

| Поле | Тип | Описание |
| :--- | :--- | :--- |
| `status` | `DownloadStatus` | `DOWNLOADING`, `FINISHED`, `POST_PROCESSING`, `COMPLETE`, `ERROR` |
| `downloaded_bytes` | `int \| None` | Количество скачанных байт |
| `total_bytes` | `int \| None` | Точный общий размер файла (если известен серверу) |
| `total_bytes_estimate` | `int \| None` | Оценочный общий размер потока |
| `speed` | `float \| None` | Текущая скорость (байт/с) |
| `eta` | `float \| None` | Оставшееся время до конца загрузки (секунды) |
| `elapsed` | `float \| None` | Затраченное время с начала операции |
| `filename` | `str \| None` | Имя целевого файла |
| `postprocessor` | `str \| None` | Название активного постпроцессора (`FFmpegExtractAudio`, `Fixup` и т.д.) |

### Вычисляемые свойства:
- `event.percent`: процент выполнения (от `0.0` до `100.0` или `None`).
- `event.speed_str`: человекочитаемая скорость (например: `2.45 MiB/s`).
- `event.eta_str`: форматированное время до окончания (например: `01:45`).
- `event.downloaded_str`: форматированный объем скачанного (например: `14.20 MiB`).
- `event.total_str`: форматированный общий объем.

---

## 2. Способы получения прогресса

### Вариант 1: Асинхронный генератор `download_with_progress` (Рекомендуется)
Идеально подходит для UI, веб-сокетов, Server-Sent Events (SSE) или консольных утилит:

```python
async for event in ytdlp.download_with_progress(url, throttle_interval=0.5):
    if event.status == DownloadStatus.DOWNLOADING:
        print(f"{event.percent:.1f}% со скоростью {event.speed_str}")
```

### Вариант 2: Коллбэк `on_progress` в методе `download`
Поддерживает как синхронные, так и асинхронные функции:

```python
async def my_callback(event: ProgressEvent):
    await websocket.send_json({"percent": event.percent, "speed": event.speed_str})


result = await ytdlp.download(url, on_progress=my_callback)
```

---

## 3. Троттлинг и защита от перегрузки

Синхронный загрузчик `yt-dlp` может вызывать хуки прогресса сотни раз в секунду при быстром интернет-соединении. Передача каждого такого вызова в асинхронный цикл вызвала бы перегрузку event loop и зависание интерфейса.

`ProgressBridge` автоматически решает эту проблему:
- **Троттлинг `DOWNLOADING`**: промежуточные события скачивания фильтруются с интервалом `throttle_interval` (по умолчанию `0.5` сек).
- **Гарантированная доставка ключевых событий**: события `FINISHED`, `POST_PROCESSING`, `COMPLETE` и `ERROR` **никогда не отбрасываются** троттлингом.
- **Ограниченная очередь (`Queue`)**: очередь событий имеет фиксированный размер, предотвращая утечки памяти при медленном чтении клиентом.
