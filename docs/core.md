# Модуль Core

## Назначение

`core` — высокопроизводительный C++ сервис, отвечающий за весь поток рыночных данных:

- Подключается к Binance WebSocket и получает свечи в реальном времени
- Синхронизирует историческую глубину при запуске
- Записывает все данные в PostgreSQL
- Отдаёт свечи по HTTP-запросу (используется gateway)

Core написан на C++17 и намеренно не взаимодействует с Python-сервисами во время работы — он пишет в БД, остальные читают.

---

## Архитектура

```
Binance WebSocket API
        │  (IXWebSocket, stream для каждого symbol+tf)
        ▼
  live_data_update()   ← real-time свечи
        │
        ▼
  PostgreSQL :5432
  (таблица crypto_candles)
        ▲
  sync_data::threads() ← история при старте (параллельные потоки)
        │
  Binance REST API
```

```
HTTP :18080 (Crow)
  └── GET /coin/{symbol}?tf=&offset=
            └── handlers::get_candles_data()
                      └── SELECT FROM crypto_candles
```

---

## Файлы

| Файл | Роль |
|---|---|
| `src/main.cpp` | Точка входа: инициализация пула, запуск потоков, HTTP-сервер |
| `src/config.hpp` | Загрузка `params.json` (CRYPTO, TF, LIMITS) |
| `src/DB_pool.hpp` | Пул соединений к PostgreSQL (libpqxx) |
| `src/Data_stream/Live_data.cpp/hpp` | WebSocket-клиент Binance, обновление свечей |
| `src/Data_stream/History_data.cpp/hpp` | Синхронизация исторических данных через REST |
| `src/Data_stream/Threads.cpp/hpp` | Управление потоками синхронизации |
| `src/Handlers/Candles_data.cpp/hpp` | HTTP-хэндлер — SELECT из БД, формирование JSON |
| `src/Routes/Routes.cpp/hpp` | Регистрация маршрутов Crow, валидация параметров |

---

## Зависимости

| Библиотека | Назначение |
|---|---|
| [Crow](https://crowcpp.org/) | HTTP-фреймворк (header-only) |
| [IXWebSocket](https://github.com/machinezone/IXWebSocket) | WebSocket-клиент |
| [libpqxx](https://pqxx.org/) | PostgreSQL C++ driver |
| [nlohmann/json](https://github.com/nlohmann/json) | JSON (header-only) |
| [cpp-httplib](https://github.com/yhirose/cpp-httplib) | HTTP-клиент для REST-запросов к Binance |

Зависимости управляются через `vcpkg.json`.

---

## Конфигурация

Core читает `params.json` из рабочей директории (монтируется как volume):

```json
{
  "crypto_list": ["BTCUSDT", "ETHUSDT", "SOLUSDT", "TONUSDT"],
  "timeframes":  ["1s", "1m", "5m", "15m", "1h", "4h", "1d"],
  "candles_amount": {
    "1d":  1825,
    "4h":  2190,
    "1h":  8760,
    "15m": 672,
    "5m":  2016,
    "1m":  4320,
    "1s":  3600
  }
}
```

Чтобы добавить монету — добавить в `crypto_list` и пересобрать core.

---

## API

### `GET /coin/{symbol}`

Возвращает свечи из PostgreSQL.

**Параметры:**

| Параметр | Тип | По умолчанию | Описание |
|---|---|---|---|
| `symbol` | path | — | Символ. Если неизвестный — фолбэк на `BTCUSDT` |
| `tf` | query | `1d` | Таймфрейм. Если неизвестный — фолбэк на `1d` |
| `offset` | query | `0` | Смещение от конца. Ограничен `LIMITS[tf] - 200` |

**Ответ:**
```json
{
  "symbol": "BTCUSDT",
  "time_frame": "1h",
  "data": [
    {
      "open_time": 1700000000000,
      "open":  30000.0,
      "high":  30500.0,
      "low":   29800.0,
      "close": 30200.0,
      "volume": 123.45,
      "is_grow": true
    }
  ]
}
```

---

## Поток живых данных

При запуске `live_data_update()` открывает один WebSocket к Binance комбинированному стриму:

```
wss://stream.binance.com/stream?streams=btcusdt@kline_1m/btcusdt@kline_1h/...
```

Каждое входящее событие `kline`:
1. Обновляет текущую свечу в `crypto_candles` (UPSERT по `symbol + time_frame + open_time`)
2. Если свеча закрыта (`is_closed == true`) — финализирует запись

---

## Синхронизация истории

При старте `sync_data::threads()` запускает параллельные потоки — по одному на каждый `(symbol, timeframe)`. Каждый поток:

1. Смотрит, сколько свечей уже есть в БД
2. Дозапрашивает недостающие через Binance REST API (`GET /api/v3/klines`)
3. Вставляет батчами (INSERT ... ON CONFLICT DO NOTHING)

Глубина синхронизации задана в `params.json` → `candles_amount`.

---

## Docker

```yaml
core:
  build:
    context: ./backend/core
    dockerfile: Dockerfile.core
  ports:
    - "18080:18080"
  depends_on:
    db:
      condition: service_healthy
  volumes:
    - ./params.json:/app/params.json
  environment:
    - DB_URL=${DB_CONNECTION_STRING}
    - LIVE_INTERVAL_MS=${LIVE_INTERVAL_MS}
```

Сборка через многоступенчатый Dockerfile: builder-stage компилирует с vcpkg, итоговый образ — минимальный runtime без исходников.
