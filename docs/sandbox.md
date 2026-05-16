# Модуль SANDBOX

## Назначение

`sandbox` — изолированный сервис выполнения пользовательских стратегий и бэктестинга.

Задачи:
- Получить OHLCV из PostgreSQL по символу и таймфрейму
- Подготовить окружение (pypine namespace с restricted builtins)
- Выполнить скрипт пользователя
- Вернуть результаты бэктеста

---

## Архитектура

```
nginx :80
  └── /api/sandbox/* → gateway :8000
                          └── /sandbox/* → sandbox :8010
                                              ├── db.py         (PostgreSQL)
                                              ├── pypine.py     (DSL-библиотека)
                                              └── backtester.py (движок)
```

---

## Файлы

| Файл | Роль |
|---|---|
| `main.py` | FastAPI сервис, эндпоинты |
| `backtester.py` | Движок бэктеста — симуляция сделок, статистика |
| `pypine.py` | DSL-библиотека (ta.*, Series, utilities) |
| `db.py` | Запрос свечей из PostgreSQL |

---

## Зависимости

| Библиотека | Назначение |
|---|---|
| `numba` | JIT-компиляция: ema/rma/wma/supertrend/alma/kama/основной торговый цикл |
| `bottleneck` | Быстрые rolling-операции: sma/highest/lowest/stdev/median/variance |
| `numpy` | Базовые массивы и векторные операции |
| `psycopg2-binary` | Подключение к PostgreSQL |

---

## API

### `GET /health`

```json
{"status": "ok"}
```

---

### `POST /backtest`

Запуск бэктеста.

**Тело запроса:**
```json
{
  "symbol":             "BTCUSDT",
  "timeframe":          "1h",
  "script":             "def strategy(open, high, low, close, volume, time):\n    ...",
  "initial_balance":    10000,
  "commission_percent": 0.1,
  "slippage_percent":   0.05
}
```

| Поле | Тип | Обязательное | По умолчанию |
|---|---|---|---|
| `symbol` | string | да | — |
| `timeframe` | string | да | — |
| `script` | string | да | — |
| `initial_balance` | float | нет | `10000` |
| `commission_percent` | float | нет | `0.1` |
| `slippage_percent` | float | нет | `0.0` |

**Успешный ответ (200):**
```json
{
  "symbol":                   "BTCUSDT",
  "timeframe":                "1h",
  "initial_balance":          10000.0,
  "final_balance":            11234.56,
  "net_profit":               1234.56,
  "net_profit_percent":       12.35,
  "buy_and_hold_percent":     8.21,
  "total_trades":             42,
  "winning_trades":           25,
  "losing_trades":            17,
  "winrate_percent":          59.52,
  "profit_factor":            1.43,
  "sharpe_ratio":             1.21,
  "max_drawdown_percent":     8.21,
  "avg_trade_percent":        0.29,
  "best_trade_percent":       4.98,
  "worst_trade_percent":     -2.31,
  "max_consecutive_wins":     5,
  "max_consecutive_losses":   3,
  "avg_hold_bars":            12.4,
  "total_commission_paid":    87.32,
  "monthly_returns": [
    {"year": 2024, "month": 1, "return_percent": 3.21},
    {"year": 2024, "month": 2, "return_percent": -1.05}
  ],
  "trades": [
    {
      "side":        "long",
      "entry_time":  1700000000.0,
      "exit_time":   1700003600.0,
      "entry_price": 30000.0,
      "exit_price":  30500.0,
      "pnl_usdt":    150.0,
      "pnl_percent": 1.67,
      "exit_reason": "signal"
    }
  ],
  "equity_curve": [10000.0, 10045.2, ...],
  "equity_times": [1700000000.0, 1700003600.0, ...]
}
```

**Поля ответа:**

| Поле | Описание |
|---|---|
| `buy_and_hold_percent` | Доходность стратегии "купи и держи" за период |
| `sharpe_ratio` | Sharpe ratio по доходностям сделок (без риск-фри ставки) |
| `max_consecutive_wins/losses` | Максимальная серия выигрышных / проигрышных сделок |
| `avg_hold_bars` | Среднее количество баров в позиции |
| `total_commission_paid` | Суммарные комиссии за все сделки |
| `monthly_returns` | Разбивка доходности по месяцам (пусто если timestamps не реальные) |
| `equity_curve` | До 300 точек equity (прореживается равномерно) |
| `equity_times` | Timestamps, соответствующие точкам equity_curve |
| `exit_reason` | Причина закрытия: `signal`, `stop_loss`, `take_profit`, `end_of_backtest` |

**Ошибки:**

| Код | Причина |
|---|---|
| `404` | Нет свечей для symbol/timeframe в БД |
| `422` | Скрипт не содержит функцию `strategy()` |
| `422` | `strategy()` не возвращает `dict` |
| `422` | Синтаксическая или runtime ошибка в скрипте |
| `502` | Sandbox сервис недоступен |

---

## Движок бэктеста

### Логика исполнения

- За раз открыта не более одной позиции (лонг или шорт)
- Пока открыт лонг — сигналы шорта игнорируются, и наоборот
- На каждом баре сначала проверяются SL/TP (по `high`/`low`), потом сигналы стратегии
- Если на баре сработал SL/TP — новые входы на этом же баре не проверяются
- Позиция размером `position_size * balance` (по умолчанию 100% баланса)
- Незакрытая позиция принудительно закрывается по последней свече

### Slippage

Проскальзывание применяется к цене входа и выхода:

| Действие | Формула |
|---|---|
| Лонг — вход | `entry_price = close * (1 + slippage_rate)` |
| Лонг — выход | `exit_price = close * (1 - slippage_rate)` |
| Шорт — вход | `entry_price = close * (1 - slippage_rate)` |
| Шорт — выход | `exit_price = close * (1 + slippage_rate)` |

### Stop Loss / Take Profit

Задаются в стратегии как `sl_percent` и `tp_percent` (процент от цены входа).

Уровни рассчитываются при входе:

| Тип | Long | Short |
|---|---|---|
| SL | `entry * (1 - sl% / 100)` | `entry * (1 + sl% / 100)` |
| TP | `entry * (1 + tp% / 100)` | `entry * (1 - tp% / 100)` |

Проверяются по `low[i] <= sl_price` (long) и `high[i] >= sl_price` (short). При одновременном срабатывании SL и TP на одном баре — приоритет у SL (консервативно).

### Формула PnL

**Лонг:** `pnl = position_size * (exit_price - entry_price) / entry_price`  
**Шорт:** `pnl = position_size * (entry_price - exit_price) / entry_price`  
**Комиссия:** `position_size * commission_percent / 100` — списывается при входе и при выходе.

### Статистика

| Поле | Формула |
|---|---|
| `net_profit_percent` | `(final - initial) / initial * 100` |
| `buy_and_hold_percent` | `(close[-1] - close[0]) / close[0] * 100` |
| `winrate_percent` | `winning / total * 100` |
| `profit_factor` | `gross_profit / gross_loss` |
| `sharpe_ratio` | `mean(pnl_pct) / std(pnl_pct)` по всем сделкам |
| `max_drawdown_percent` | Максимальная просадка от пика equity |
| `avg_hold_bars` | Среднее `exit_bar - entry_bar` |
| `total_commission_paid` | Сумма всех комиссий |

---

## Параметры стратегии

Помимо сигнальных массивов, `strategy()` может вернуть управляющие параметры:

```python
return {
    "long_entry":    ...,
    "long_exit":     ...,

    "sl_percent":    2.0,          # стоп-лосс 2% (скаляр)
    "tp_percent":    6.0,          # тейк-профит 6% (скаляр)
    "position_size": 0.5,          # 50% баланса (скаляр или массив float 0–1)
}
```

`position_size` как массив позволяет динамически управлять размером:
```python
rsi = ta.rsi(close, 14)
size = np.clip((50 - rsi) / 50, 0.1, 1.0)  # больше позиция при экстремальных RSI
return {"long_entry": rsi < 30, "position_size": size}
```

---

## Безопасность

Пользовательский скрипт выполняется через `exec()` с ограниченным namespace:

**Restricted `__builtins__`** — доступны только безопасные встроенные:  
`abs`, `bool`, `dict`, `enumerate`, `float`, `int`, `isinstance`, `len`, `list`, `max`, `min`, `range`, `round`, `set`, `sorted`, `str`, `sum`, `tuple`, `zip`

**Запрещено:** `import`, `exec`, `eval`, `open`, `__import__`, и любые другие системные функции — отсутствуют в namespace.

Дополнительные слои безопасности (AST-валидатор, LLM-проверка) — в планах.

---

## База данных

```sql
SELECT open_time, open_price, high_price, low_price, close_price, volume
FROM crypto_candles
WHERE symbol = %s AND time_frame = %s
ORDER BY open_time ASC
```

Конфигурация подключения через `DB_URL` (libpq DSN).

---

## Окружение стратегии

В `exec`-namespace доступны:

```python
np            # numpy
ta            # все индикаторы

# Utilities
crossover, crossunder
nz, na, fixnan
valuewhen, barssince
highest_bars, lowest_bars
rising, falling
cum, change_pct, zscore, bar_index, ha
```

---

## Docker

```yaml
sandbox:
  build:
    context: ./backend/sandbox
    dockerfile: Dockerfile.sandbox
  ports:
    - "8010:8010"
  depends_on:
    db:
      condition: service_healthy
  environment:
    - DB_URL=${DB_CONNECTION_STRING}
```

Пересборка после изменений:
```bash
docker compose up -d --build sandbox
```
