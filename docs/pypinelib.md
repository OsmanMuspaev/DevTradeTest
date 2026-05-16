# PYPINE LIBRARY DOCUMENTATION

## Назначение

**pypine** — Python DSL-слой, повторяющий стиль и удобство PineScript для написания торговых стратегий.

Цели:
- Короткий синтаксис как в PineScript
- Готовые функции технического анализа (`ta.*`)
- Доступ к предыдущим барам через `series[n]` как в PineScript
- Запуск пользовательских стратегий внутри sandbox

**Зависимости:** `numpy`, `numba` (JIT-компиляция рекурсивных функций), `bottleneck` (быстрые rolling-операции).

---

## Series — доступ к предыдущим барам

Все входные массивы (`open`, `high`, `low`, `close`, `volume`, `time`) передаются в стратегию как объекты `Series`.

`Series` — это numpy ndarray с переопределённым `__getitem__`:

```python
close[0]  # текущий бар (весь массив)
close[1]  # предыдущий бар (сдвиг на 1, первый элемент = NaN)
close[2]  # два бара назад
```

Пример:
```python
def strategy(open, high, low, close, volume, time):
    prev_close = close[1]
    gap_up     = open > close[1]
    return {"long_entry": gap_up & (close > close[1])}
```

Все стандартные numpy операции работают без изменений.

---

## Индикаторы `ta.*`

### Скользящие средние

| Функция | Описание |
|---|---|
| `ta.ema(src, length)` | Экспоненциальная средняя |
| `ta.rma(src, length)` | Сглаженная средняя (используется в RSI/ATR) |
| `ta.sma(src, length)` | Простая средняя |
| `ta.wma(src, length)` | Взвешенная средняя |
| `ta.vwma(src, volume, length)` | Объёмно-взвешенная средняя |
| `ta.hma(src, length)` | Hull MA — быстрее SMA, меньше запаздывание |
| `ta.dema(src, length)` | Double EMA — меньше запаздывания чем EMA |
| `ta.tema(src, length)` | Triple EMA — ещё меньше запаздывания |
| `ta.zlma(src, length)` | Zero-Lag EMA |
| `ta.alma(src, length, offset=0.85, sigma=6)` | Arnaud Legoux MA — Gaussian-взвешенная |
| `ta.kama(src, length=10, fast=2, slow=30)` | Kaufman Adaptive MA — адаптируется к волатильности |

### Волатильность

| Функция | Описание |
|---|---|
| `ta.stdev(src, length)` | Стандартное отклонение |
| `ta.variance(src, length)` | Дисперсия (ddof=0) |
| `ta.tr(high, low, close)` | True Range |
| `ta.atr(high, low, close, length=14)` | ATR (через RMA) |
| `ta.natr(high, low, close, length=14)` | Normalized ATR: `atr / close * 100` |
| `ta.bb(src, length=20, mult=2.0)` | Bollinger Bands → `(upper, middle, lower)` |
| `ta.bbw(src, length=20, mult=2.0)` | Bollinger Bands Width |

### Осцилляторы

| Функция | Описание |
|---|---|
| `ta.change(src, length=1)` | Разница с n баров назад |
| `ta.mom(src, length=10)` | Momentum: `close - close[n]` |
| `ta.roc(src, length=9)` | Rate of Change (%) |
| `ta.rsi(src, length=14)` | RSI |
| `ta.macd(src, fast=12, slow=26, signal=9)` | MACD → `(line, signal, histogram)` |
| `ta.stoch(high, low, close, k=14, d=3, smooth_k=3)` | Stochastic → `(%K, %D)` |
| `ta.cci(high, low, close, length=20)` | Commodity Channel Index |
| `ta.mfi(high, low, close, volume, length=14)` | Money Flow Index |
| `ta.williamsr(high, low, close, length=14)` | Williams %R (0 до -100) |
| `ta.tsi(src, short=13, long=25)` | True Strength Index (-100 до 100) |
| `ta.dpo(src, length=21)` | Detrended Price Oscillator |
| `ta.dmi(high, low, close, length=14)` | DMI/ADX → `(plus_di, minus_di, adx)` |

### Объём

| Функция | Описание |
|---|---|
| `ta.obv(close, volume)` | On-Balance Volume |
| `ta.vwap(high, low, close, volume)` | VWAP (кумулятивный, без сброса по сессии) |
| `ta.cmf(high, low, close, volume, length=20)` | Chaikin Money Flow (-1 до 1) |

### Каналы

| Функция | Описание |
|---|---|
| `ta.keltner(high, low, close, length=20, mult=2.0)` | Keltner Channels → `(upper, middle, lower)` |
| `ta.donchian(high, low, length=20)` | Donchian Channels → `(upper, middle, lower)` |

### Тренд

| Функция | Описание |
|---|---|
| `ta.supertrend(high, low, close, length=10, mult=3.0)` | Supertrend → `(line, direction)` — direction: `-1` = аптренд, `1` = даунтренд |

### Уровни

| Функция | Описание |
|---|---|
| `ta.highest(src, length)` | Максимум за период |
| `ta.lowest(src, length)` | Минимум за период |
| `ta.pivothigh(src, left_bars, right_bars)` | Пивот-максимум (подтверждается через right_bars) |
| `ta.pivotlow(src, left_bars, right_bars)` | Пивот-минимум |

### Статистика

| Функция | Описание |
|---|---|
| `ta.percentrank(src, length)` | Перцентильный ранг 0–100 |
| `ta.correlation(src1, src2, length)` | Скользящая корреляция Пирсона |
| `ta.linreg(src, length, offset=0)` | Линейная регрессия, offset=0 — последний бар |
| `ta.median(src, length)` | Скользящая медиана |

---

## Series utilities

| Функция | Описание |
|---|---|
| `crossover(a, b)` | True на баре где `a` пересекает `b` снизу вверх |
| `crossunder(a, b)` | True на баре где `a` пересекает `b` сверху вниз |
| `nz(x, val=0.0)` | Заменяет NaN на val |
| `na(x)` | True там где NaN |
| `fixnan(x)` | Forward-fill: заменяет NaN последним валидным значением |
| `valuewhen(condition, series, occurrence=0)` | Значение series при последнем срабатывании condition |
| `barssince(condition)` | Баров с последнего срабатывания condition |
| `highest_bars(src, length)` | Баров назад до максимума в окне |
| `lowest_bars(src, length)` | Баров назад до минимума в окне |
| `rising(src, length)` | True если src строго растёт length баров подряд |
| `falling(src, length)` | True если src строго падает length баров подряд |
| `cum(src)` | Кумулятивная сумма |
| `change_pct(src, length=1)` | Процентное изменение за length баров |
| `zscore(src, length)` | Z-score: `(src - sma) / stdev` |
| `bar_index(src)` | Массив индексов баров: `[0, 1, 2, ...]` |
| `ha(open, high, low, close)` | Heikin Ashi свечи → `(ha_open, ha_high, ha_low, ha_close)` |

---

## Формат функции strategy

Пользовательский скрипт должен определять функцию `strategy(open, high, low, close, volume, time)`:

```python
def strategy(open, high, low, close, volume, time):
    # ... логика ...
    return {
        "long_entry":  <bool array>,   # опционально
        "long_exit":   <bool array>,   # опционально
        "short_entry": <bool array>,   # опционально
        "short_exit":  <bool array>,   # опционально

        # Управление позицией (опционально)
        "sl_percent":    2.0,          # stop-loss 2% от цены входа
        "tp_percent":    4.0,          # take-profit 4% от цены входа
        "position_size": 0.5,          # 50% баланса на сделку (0.0–1.0)
                                       # может быть скаляром или массивом
    }
```

- Функция обязательна, иначе → ошибка 422
- Возвращаемый объект должен быть `dict`, иначе → ошибка 422
- Все отсутствующие сигнальные ключи заменяются массивом `False`
- Одновременно может быть открыта только одна позиция
- `sl_percent` / `tp_percent`: проверяются по `high`/`low` каждого бара (не только по close)
- `position_size`: если массив — берётся значение на баре входа

---

## Примеры стратегий

### EMA Crossover (long only)
```python
def strategy(open, high, low, close, volume, time):
    ema20 = ta.ema(close, 20)
    ema50 = ta.ema(close, 50)
    return {
        "long_entry": crossover(ema20, ema50),
        "long_exit":  crossunder(ema20, ema50),
    }
```

### RSI (long + short)
```python
def strategy(open, high, low, close, volume, time):
    rsi = ta.rsi(close, 14)
    return {
        "long_entry":  rsi < 30,
        "long_exit":   rsi > 60,
        "short_entry": rsi > 70,
        "short_exit":  rsi < 40,
    }
```

### Bollinger Bands + предыдущий бар
```python
def strategy(open, high, low, close, volume, time):
    upper, middle, lower = ta.bb(close, 20, 2.0)
    return {
        "long_entry": (close < lower) & (close[1] > lower[1]),
        "long_exit":  close > middle,
    }
```

### Supertrend
```python
def strategy(open, high, low, close, volume, time):
    line, direction = ta.supertrend(high, low, close, length=10, mult=3.0)
    zero = np.zeros(len(close))
    return {
        "long_entry":  crossover(direction,  zero),
        "short_entry": crossunder(direction, zero),
        "long_exit":   direction == 1,
        "short_exit":  direction == -1,
    }
```

### Heikin Ashi + ATR stop-loss
```python
def strategy(open, high, low, close, volume, time):
    ha_open, ha_high, ha_low, ha_close = ha(open, high, low, close)
    trend_up   = ha_close > ha_open
    trend_down = ha_close < ha_open
    return {
        "long_entry":  trend_up  & ~trend_up[1],
        "long_exit":   trend_down,
        "short_entry": trend_down & ~trend_down[1],
        "short_exit":  trend_up,
        "sl_percent":  1.5,
        "tp_percent":  3.0,
    }
```

### KAMA + динамический размер позиции
```python
def strategy(open, high, low, close, volume, time):
    kama_fast = ta.kama(close, length=10, fast=2, slow=10)
    kama_slow = ta.kama(close, length=30, fast=2, slow=30)
    rsi = ta.rsi(close, 14)
    # Чем ближе RSI к экстремуму — тем больше позиция
    size = np.clip((50 - np.abs(rsi - 50)) / 50, 0.1, 1.0)
    return {
        "long_entry":  crossover(kama_fast,  kama_slow),
        "long_exit":   crossunder(kama_fast, kama_slow),
        "position_size": size,
    }
```

### Z-score mean reversion
```python
def strategy(open, high, low, close, volume, time):
    z = zscore(close, 20)
    return {
        "long_entry":  z < -2.0,
        "long_exit":   z > 0.0,
        "short_entry": z >  2.0,
        "short_exit":  z < 0.0,
    }
```
