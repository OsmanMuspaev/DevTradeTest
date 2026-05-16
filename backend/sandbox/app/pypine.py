import numpy as np
import bottleneck as bn
from numba import njit


# =========================================================
# SERIES — PineScript-style bar access
# =========================================================

class Series(np.ndarray):
    """
    Numpy array with PineScript-style indexing:
        series[0]  → current bar (same as the array itself)
        series[1]  → previous bar values
        series[n]  → n bars ago (NaN for first n positions)
    All numpy operations (arithmetic, comparison, ufuncs) work normally.
    """

    def __new__(cls, data):
        return np.asarray(data, dtype=float).view(cls)

    def __array_finalize__(self, obj):
        pass

    def __getitem__(self, key):
        if isinstance(key, (int, np.integer)) and int(key) >= 0:
            n = int(key)
            if n == 0:
                return np.asarray(self)
            out = np.full(len(self), np.nan, dtype=float)
            out[n:] = np.asarray(self)[:-n]
            return out
        return super().__getitem__(key)


# =========================================================
# CONTEXT (for standalone use outside backtester)
# =========================================================

class _CTX:
    open   = None
    high   = None
    low    = None
    close  = None
    volume = None
    time   = None


def set_ohlcv(data: dict):
    _CTX.open   = Series(data["open"])
    _CTX.high   = Series(data["high"])
    _CTX.low    = Series(data["low"])
    _CTX.close  = Series(data["close"])
    _CTX.volume = Series(data["volume"])
    _CTX.time   = Series(data.get("time", np.arange(len(data["close"]))))


# =========================================================
# JIT-compiled core loops
# =========================================================

@njit(cache=True)
def _ema_loop(src, alpha):
    out = np.empty(len(src))
    out[0] = src[0]
    for i in range(1, len(src)):
        out[i] = alpha * src[i] + (1.0 - alpha) * out[i - 1]
    return out


@njit(cache=True)
def _rma_loop(src, alpha):
    out = np.empty(len(src))
    out[0] = src[0]
    for i in range(1, len(src)):
        out[i] = alpha * src[i] + (1.0 - alpha) * out[i - 1]
    return out


@njit(cache=True)
def _wma_loop(src, length):
    n = len(src)
    out = np.empty(n)
    for i in range(n):
        start = max(0, i - length + 1)
        wl = i - start + 1
        s = 0.0
        w = 0.0
        for j in range(wl):
            weight = float(j + 1)
            s += src[start + j] * weight
            w += weight
        out[i] = s / w
    return out


@njit(cache=True)
def _vwma_loop(src, volume, length):
    n = len(src)
    out = np.empty(n)
    for i in range(n):
        start = max(0, i - length + 1)
        sv = 0.0
        tv = 0.0
        for j in range(start, i + 1):
            sv += src[j] * volume[j]
            tv += volume[j]
        out[i] = sv / tv if tv != 0.0 else 0.0
    return out


@njit(cache=True)
def _alma_loop(src, length, m, s):
    """Arnaud Legoux Moving Average core loop."""
    n = len(src)
    out = np.empty(n)
    weights = np.empty(length)
    for i in range(length):
        weights[i] = np.exp(-(float(i) - m) ** 2 / (2.0 * s * s))
    for i in range(n):
        start = max(0, i - length + 1)
        wl = i - start + 1
        total = 0.0
        total_w = 0.0
        for j in range(wl):
            wi = length - wl + j
            w = weights[wi]
            total   += src[start + j] * w
            total_w += w
        out[i] = total / total_w if total_w > 1e-12 else src[i]
    return out


@njit(cache=True)
def _kama_loop(src, length, fast_alpha, slow_alpha):
    """Kaufman Adaptive Moving Average core loop."""
    n = len(src)
    out = np.empty(n)
    out[0] = src[0]
    for i in range(1, n):
        if i < length:
            out[i] = src[i]
            continue
        direction  = abs(src[i] - src[i - length])
        volatility = 0.0
        for j in range(i - length + 1, i + 1):
            volatility += abs(src[j] - src[j - 1])
        er = direction / volatility if volatility > 1e-12 else 0.0
        sc = (er * (fast_alpha - slow_alpha) + slow_alpha) ** 2
        out[i] = out[i - 1] + sc * (src[i] - out[i - 1])
    return out


@njit(cache=True)
def _ha_loop(open_, high, low, close):
    """Heikin Ashi candles core loop."""
    n = len(close)
    ha_open  = np.empty(n)
    ha_close = np.empty(n)
    ha_high  = np.empty(n)
    ha_low   = np.empty(n)
    ha_close[0] = (open_[0] + high[0] + low[0] + close[0]) / 4.0
    ha_open[0]  = (open_[0] + close[0]) / 2.0
    ha_high[0]  = max(high[0], max(ha_open[0], ha_close[0]))
    ha_low[0]   = min(low[0],  min(ha_open[0], ha_close[0]))
    for i in range(1, n):
        ha_close[i] = (open_[i] + high[i] + low[i] + close[i]) / 4.0
        ha_open[i]  = (ha_open[i - 1] + ha_close[i - 1]) / 2.0
        ha_high[i]  = max(high[i], max(ha_open[i], ha_close[i]))
        ha_low[i]   = min(low[i],  min(ha_open[i], ha_close[i]))
    return ha_open, ha_high, ha_low, ha_close


@njit(cache=True)
def _supertrend_loop(close, ub_raw, lb_raw):
    n = len(close)
    upper = np.empty(n)
    lower = np.empty(n)
    line  = np.empty(n)
    direction = np.empty(n, dtype=np.int64)
    upper[0] = ub_raw[0]
    lower[0] = lb_raw[0]
    line[0]  = ub_raw[0]
    direction[0] = 1
    for i in range(1, n):
        upper[i] = ub_raw[i] if (ub_raw[i] < upper[i-1] or close[i-1] > upper[i-1]) else upper[i-1]
        lower[i] = lb_raw[i] if (lb_raw[i] > lower[i-1] or close[i-1] < lower[i-1]) else lower[i-1]
        if line[i-1] == upper[i-1]:
            direction[i] = -1 if close[i] > upper[i] else 1
        else:
            direction[i] =  1 if close[i] < lower[i] else -1
        line[i] = lower[i] if direction[i] == -1 else upper[i]
    return line, direction


@njit(cache=True)
def _cci_loop(tp, sma_tp, length):
    n = len(tp)
    out = np.empty(n)
    for i in range(n):
        start    = max(0, i - length + 1)
        wl       = i - start + 1
        mean_val = sma_tp[i]
        mean_dev = 0.0
        for j in range(start, i + 1):
            mean_dev += abs(tp[j] - mean_val)
        mean_dev /= wl
        out[i] = (tp[i] - mean_val) / (0.015 * mean_dev + 1e-12)
    return out


@njit(cache=True)
def _mfi_loop(tp, pos_mf, neg_mf, length):
    n = len(tp)
    out = np.empty(n)
    for i in range(n):
        start   = max(0, i - length + 1)
        pos_sum = 0.0
        neg_sum = 0.0
        for j in range(start, i + 1):
            pos_sum += pos_mf[j]
            neg_sum += neg_mf[j]
        out[i] = 100.0 - 100.0 / (1.0 + pos_sum / (neg_sum + 1e-12))
    return out


@njit(cache=True)
def _percentrank_loop(src, length):
    n = len(src)
    out = np.empty(n)
    for i in range(n):
        start = max(0, i - length + 1)
        wl    = i - start + 1
        count = 0
        for j in range(start, i + 1):
            if src[j] < src[i]:
                count += 1
        out[i] = float(count) / float(wl) * 100.0
    return out


@njit(cache=True)
def _correlation_loop(src1, src2, length):
    n = len(src1)
    out = np.zeros(n)
    for i in range(n):
        start = max(0, i - length + 1)
        wl    = i - start + 1
        if wl < 2:
            continue
        mx = 0.0
        my = 0.0
        for j in range(start, i + 1):
            mx += src1[j]
            my += src2[j]
        mx /= wl
        my /= wl
        num = 0.0
        dx2 = 0.0
        dy2 = 0.0
        for j in range(start, i + 1):
            dx  = src1[j] - mx
            dy  = src2[j] - my
            num += dx * dy
            dx2 += dx * dx
            dy2 += dy * dy
        denom = (dx2 * dy2) ** 0.5
        out[i] = num / denom if denom > 1e-12 else 0.0
    return out


@njit(cache=True)
def _linreg_loop(src, length, offset):
    n = len(src)
    out = np.empty(n)
    for i in range(n):
        start = max(0, i - length + 1)
        wl    = i - start + 1
        if wl < 2:
            out[i] = src[i]
            continue
        mx = 0.0
        my = 0.0
        for j in range(wl):
            mx += float(j)
            my += src[start + j]
        mx /= wl
        my /= wl
        num = 0.0
        den = 0.0
        for j in range(wl):
            dx   = float(j) - mx
            num += dx * (src[start + j] - my)
            den += dx * dx
        slope     = num / den if den > 1e-12 else 0.0
        intercept = my - slope * mx
        out[i]    = slope * float(wl - 1 - offset) + intercept
    return out


@njit(cache=True)
def _barssince_loop(condition):
    n    = len(condition)
    out  = np.full(n, np.nan)
    last = -1
    for i in range(n):
        if condition[i]:
            last = i
        if last != -1:
            out[i] = float(i - last)
    return out


@njit(cache=True)
def _valuewhen_loop(condition, series, occurrence):
    n         = len(series)
    out       = np.full(n, np.nan)
    hits      = np.empty(n)
    hit_count = 0
    for i in range(n):
        if condition[i]:
            hits[hit_count] = series[i]
            hit_count += 1
        if hit_count > occurrence:
            out[i] = hits[hit_count - 1 - occurrence]
    return out


@njit(cache=True)
def _highest_bars_loop(src, length):
    n = len(src)
    out = np.empty(n)
    for i in range(n):
        start    = max(0, i - length + 1)
        best_val = src[start]
        best_pos = start
        for j in range(start + 1, i + 1):
            if src[j] > best_val:
                best_val = src[j]
                best_pos = j
        out[i] = float(i - best_pos)
    return out


@njit(cache=True)
def _lowest_bars_loop(src, length):
    n = len(src)
    out = np.empty(n)
    for i in range(n):
        start    = max(0, i - length + 1)
        best_val = src[start]
        best_pos = start
        for j in range(start + 1, i + 1):
            if src[j] < best_val:
                best_val = src[j]
                best_pos = j
        out[i] = float(i - best_pos)
    return out


@njit(cache=True)
def _rising_loop(src, length):
    n   = len(src)
    out = np.zeros(n, dtype=np.bool_)
    for i in range(length, n):
        ok = True
        for j in range(i - length, i):
            if src[j + 1] <= src[j]:
                ok = False
                break
        out[i] = ok
    return out


@njit(cache=True)
def _falling_loop(src, length):
    n   = len(src)
    out = np.zeros(n, dtype=np.bool_)
    for i in range(length, n):
        ok = True
        for j in range(i - length, i):
            if src[j + 1] >= src[j]:
                ok = False
                break
        out[i] = ok
    return out


@njit(cache=True)
def _pivothigh_loop(src, left_bars, right_bars):
    n   = len(src)
    out = np.full(n, np.nan)
    for i in range(left_bars, n - right_bars):
        candidate = src[i]
        is_pivot  = True
        for j in range(i - left_bars, i + right_bars + 1):
            if j != i and src[j] > candidate:
                is_pivot = False
                break
        if is_pivot:
            out[i + right_bars] = candidate
    return out


@njit(cache=True)
def _pivotlow_loop(src, left_bars, right_bars):
    n   = len(src)
    out = np.full(n, np.nan)
    for i in range(left_bars, n - right_bars):
        candidate = src[i]
        is_pivot  = True
        for j in range(i - left_bars, i + right_bars + 1):
            if j != i and src[j] < candidate:
                is_pivot = False
                break
        if is_pivot:
            out[i + right_bars] = candidate
    return out


# =========================================================
# TA
# =========================================================

class TA:

    # ----- Moving Averages -----

    @staticmethod
    def ema(src, length):
        src = np.asarray(src, dtype=float)
        return _ema_loop(src, 2.0 / (length + 1))

    @staticmethod
    def rma(src, length):
        src = np.asarray(src, dtype=float)
        return _rma_loop(src, 1.0 / length)

    @staticmethod
    def sma(src, length):
        src = np.asarray(src, dtype=float)
        return bn.move_mean(src, window=length, min_count=1)

    @staticmethod
    def wma(src, length):
        src = np.asarray(src, dtype=float)
        return _wma_loop(src, length)

    @staticmethod
    def vwma(src, volume, length):
        src    = np.asarray(src,    dtype=float)
        volume = np.asarray(volume, dtype=float)
        return _vwma_loop(src, volume, length)

    @staticmethod
    def hma(src, length):
        """Hull Moving Average: wma(2*wma(n/2) - wma(n), sqrt(n))."""
        src    = np.asarray(src, dtype=float)
        half   = max(1, length // 2)
        sqrt_n = max(1, round(length ** 0.5))
        return _wma_loop(2.0 * _wma_loop(src, half) - _wma_loop(src, length), sqrt_n)

    @staticmethod
    def dema(src, length):
        """Double EMA: 2*ema - ema(ema)."""
        src = np.asarray(src, dtype=float)
        e   = _ema_loop(src, 2.0 / (length + 1))
        return 2.0 * e - _ema_loop(e, 2.0 / (length + 1))

    @staticmethod
    def tema(src, length):
        """Triple EMA: 3*e1 - 3*e2 + e3."""
        src   = np.asarray(src, dtype=float)
        alpha = 2.0 / (length + 1)
        e1    = _ema_loop(src, alpha)
        e2    = _ema_loop(e1,  alpha)
        e3    = _ema_loop(e2,  alpha)
        return 3.0 * e1 - 3.0 * e2 + e3

    @staticmethod
    def zlma(src, length):
        """Zero-Lag EMA: ema(2*src - src[lag], length)."""
        src  = np.asarray(src, dtype=float)
        lag  = max(1, (length - 1) // 2)
        adj  = np.empty_like(src)
        adj[:lag] = src[:lag]
        adj[lag:] = 2.0 * src[lag:] - src[:-lag]
        return _ema_loop(adj, 2.0 / (length + 1))

    @staticmethod
    def alma(src, length, offset=0.85, sigma=6):
        """Arnaud Legoux Moving Average."""
        src = np.asarray(src, dtype=float)
        m   = offset * (length - 1)
        s   = length / sigma
        return _alma_loop(src, length, m, s)

    @staticmethod
    def kama(src, length=10, fast=2, slow=30):
        """Kaufman Adaptive Moving Average."""
        src = np.asarray(src, dtype=float)
        return _kama_loop(src, length, 2.0 / (fast + 1), 2.0 / (slow + 1))

    # ----- Volatility -----

    @staticmethod
    def stdev(src, length):
        src = np.asarray(src, dtype=float)
        return bn.move_std(src, window=length, min_count=1, ddof=0)

    @staticmethod
    def variance(src, length):
        """Rolling variance (ddof=0)."""
        src = np.asarray(src, dtype=float)
        return bn.move_var(src, window=length, min_count=1, ddof=0)

    @staticmethod
    def tr(high, low, close):
        high       = np.asarray(high,  dtype=float)
        low        = np.asarray(low,   dtype=float)
        close      = np.asarray(close, dtype=float)
        prev_close = np.roll(close, 1)
        prev_close[0] = close[0]
        return np.maximum(high - low,
               np.maximum(np.abs(high - prev_close),
                          np.abs(low  - prev_close)))

    @staticmethod
    def atr(high, low, close, length=14):
        return TA.rma(TA.tr(high, low, close), length)

    @staticmethod
    def natr(high, low, close, length=14):
        """Normalized ATR: atr / close * 100."""
        close = np.asarray(close, dtype=float)
        return TA.atr(high, low, close, length) / (close + 1e-12) * 100.0

    @staticmethod
    def bb(src, length=20, mult=2.0):
        """Bollinger Bands. Returns (upper, middle, lower)."""
        src    = np.asarray(src, dtype=float)
        middle = TA.sma(src, length)
        std    = TA.stdev(src, length)
        return middle + mult * std, middle, middle - mult * std

    @staticmethod
    def bbw(src, length=20, mult=2.0):
        """Bollinger Bands Width = (upper - lower) / middle."""
        upper, middle, lower = TA.bb(src, length, mult)
        return (upper - lower) / np.where(middle != 0, middle, np.nan)

    @staticmethod
    def keltner(high, low, close, length=20, mult=2.0):
        """Keltner Channels. Returns (upper, middle, lower)."""
        middle = TA.ema(close, length)
        band   = TA.atr(high, low, close, length) * mult
        return middle + band, middle, middle - band

    # ----- Oscillators -----

    @staticmethod
    def change(src, length=1):
        src = np.asarray(src, dtype=float)
        out = np.zeros_like(src)
        out[length:] = src[length:] - src[:-length]
        return out

    @staticmethod
    def mom(src, length=10):
        """Momentum: close - close[length]."""
        src = np.asarray(src, dtype=float)
        out = np.zeros_like(src)
        out[length:] = src[length:] - src[:-length]
        return out

    @staticmethod
    def roc(src, length=9):
        """Rate of Change (%). (close - close[length]) / close[length] * 100."""
        src = np.asarray(src, dtype=float)
        out = np.zeros_like(src)
        prev = src[:-length]
        out[length:] = (src[length:] - prev) / (np.abs(prev) + 1e-12) * 100.0
        return out

    @staticmethod
    def rsi(src, length=14):
        delta    = TA.change(src)
        avg_gain = TA.rma(np.maximum(delta,  0), length)
        avg_loss = TA.rma(np.maximum(-delta, 0), length)
        rs       = avg_gain / (avg_loss + 1e-12)
        return 100 - (100 / (1 + rs))

    @staticmethod
    def macd(src, fast=12, slow=26, signal=9):
        """Returns (macd_line, signal_line, histogram)."""
        line = TA.ema(src, fast) - TA.ema(src, slow)
        sig  = TA.ema(line, signal)
        return line, sig, line - sig

    @staticmethod
    def stoch(high, low, close, k=14, d=3, smooth_k=3):
        """Stochastic Oscillator. Returns (smoothed_%K, %D)."""
        high  = np.asarray(high,  dtype=float)
        low   = np.asarray(low,   dtype=float)
        close = np.asarray(close, dtype=float)
        h     = TA.highest(high, k)
        l     = TA.lowest(low,   k)
        raw_k = 100 * (close - l) / np.where(h - l != 0, h - l, 1e-12)
        sk    = TA.sma(raw_k, smooth_k)
        return sk, TA.sma(sk, d)

    @staticmethod
    def cci(high, low, close, length=20):
        """Commodity Channel Index."""
        tp     = (np.asarray(high, dtype=float) + np.asarray(low, dtype=float) + np.asarray(close, dtype=float)) / 3
        sma_tp = TA.sma(tp, length)
        return _cci_loop(tp, sma_tp, length)

    @staticmethod
    def mfi(high, low, close, volume, length=14):
        """Money Flow Index."""
        high   = np.asarray(high,   dtype=float)
        low    = np.asarray(low,    dtype=float)
        close  = np.asarray(close,  dtype=float)
        volume = np.asarray(volume, dtype=float)
        tp      = (high + low + close) / 3
        prev_tp = np.roll(tp, 1); prev_tp[0] = tp[0]
        mf      = tp * volume
        pos_mf  = np.where(tp > prev_tp, mf, 0.0)
        neg_mf  = np.where(tp < prev_tp, mf, 0.0)
        return _mfi_loop(tp, pos_mf, neg_mf, length)

    @staticmethod
    def williamsr(high, low, close, length=14):
        """Williams %R."""
        hh = TA.highest(np.asarray(high,  dtype=float), length)
        ll = TA.lowest( np.asarray(low,   dtype=float), length)
        c  = np.asarray(close, dtype=float)
        return -100.0 * (hh - c) / (hh - ll + 1e-12)

    @staticmethod
    def cmf(high, low, close, volume, length=20):
        """Chaikin Money Flow."""
        high   = np.asarray(high,   dtype=float)
        low    = np.asarray(low,    dtype=float)
        close  = np.asarray(close,  dtype=float)
        volume = np.asarray(volume, dtype=float)
        mfm = ((close - low) - (high - close)) / (high - low + 1e-12)
        mfv = mfm * volume
        return bn.move_sum(mfv, window=length, min_count=1) / (bn.move_sum(volume, window=length, min_count=1) + 1e-12)

    @staticmethod
    def tsi(src, short=13, long=25):
        """True Strength Index. Returns tsi value (-100 to 100)."""
        src    = np.asarray(src, dtype=float)
        pc     = TA.change(src, 1)
        ds     = _ema_loop(_ema_loop(pc,           2.0 / (long  + 1)), 2.0 / (short + 1))
        ds_abs = _ema_loop(_ema_loop(np.abs(pc),   2.0 / (long  + 1)), 2.0 / (short + 1))
        return 100.0 * ds / (ds_abs + 1e-12)

    @staticmethod
    def dpo(src, length=21):
        """Detrended Price Oscillator."""
        src   = np.asarray(src, dtype=float)
        shift = length // 2 + 1
        sma   = TA.sma(src, length)
        out   = np.zeros_like(src)
        out[shift:] = src[shift:] - sma[:-shift]
        return out

    @staticmethod
    def dmi(high, low, close, length=14):
        """Directional Movement Index. Returns (plus_di, minus_di, adx)."""
        high  = np.asarray(high,  dtype=float)
        low   = np.asarray(low,   dtype=float)
        close = np.asarray(close, dtype=float)
        prev_high = np.roll(high, 1); prev_high[0] = high[0]
        prev_low  = np.roll(low,  1); prev_low[0]  = low[0]
        up   = high - prev_high
        down = prev_low - low
        plus_dm  = np.where((up > down)  & (up   > 0), up,   0.0)
        minus_dm = np.where((down > up)  & (down > 0), down, 0.0)
        atr_val  = TA.atr(high, low, close, length)
        plus_di  = 100 * TA.rma(plus_dm,  length) / (atr_val + 1e-12)
        minus_di = 100 * TA.rma(minus_dm, length) / (atr_val + 1e-12)
        dx       = 100 * np.abs(plus_di - minus_di) / (plus_di + minus_di + 1e-12)
        return plus_di, minus_di, TA.rma(dx, length)

    # ----- Volume -----

    @staticmethod
    def obv(close, volume):
        """On-Balance Volume."""
        close  = np.asarray(close,  dtype=float)
        volume = np.asarray(volume, dtype=float)
        direction    = np.sign(TA.change(close))
        direction[0] = 0.0
        return np.cumsum(direction * volume)

    @staticmethod
    def vwap(high, low, close, volume):
        """Cumulative VWAP (no session reset)."""
        high   = np.asarray(high,   dtype=float)
        low    = np.asarray(low,    dtype=float)
        close  = np.asarray(close,  dtype=float)
        volume = np.asarray(volume, dtype=float)
        tp = (high + low + close) / 3
        return np.cumsum(tp * volume) / (np.cumsum(volume) + 1e-12)

    # ----- Channels -----

    @staticmethod
    def donchian(high, low, length=20):
        """Donchian Channels. Returns (upper, middle, lower)."""
        upper  = TA.highest(np.asarray(high, dtype=float), length)
        lower  = TA.lowest( np.asarray(low,  dtype=float), length)
        return upper, (upper + lower) / 2.0, lower

    # ----- Trend -----

    @staticmethod
    def supertrend(high, low, close, length=10, mult=3.0):
        """
        Supertrend. Returns (line, direction).
        direction: -1 = uptrend (buy), 1 = downtrend (sell).
        """
        high  = np.asarray(high,  dtype=float)
        low   = np.asarray(low,   dtype=float)
        close = np.asarray(close, dtype=float)
        atr_val = TA.atr(high, low, close, length)
        hl2     = (high + low) / 2
        return _supertrend_loop(close, hl2 + mult * atr_val, hl2 - mult * atr_val)

    # ----- Pivot Points -----

    @staticmethod
    def pivothigh(src, left_bars, right_bars):
        """Pivot high confirmed right_bars later. NaN elsewhere."""
        return _pivothigh_loop(np.asarray(src, dtype=float), left_bars, right_bars)

    @staticmethod
    def pivotlow(src, left_bars, right_bars):
        """Pivot low confirmed right_bars later. NaN elsewhere."""
        return _pivotlow_loop(np.asarray(src, dtype=float), left_bars, right_bars)

    # ----- Statistics -----

    @staticmethod
    def percentrank(src, length):
        """Percent rank of current value in the last length bars (0–100)."""
        return _percentrank_loop(np.asarray(src, dtype=float), length)

    @staticmethod
    def correlation(src1, src2, length):
        """Rolling Pearson correlation coefficient."""
        return _correlation_loop(np.asarray(src1, dtype=float), np.asarray(src2, dtype=float), length)

    @staticmethod
    def linreg(src, length, offset=0):
        """Linear regression value. offset=0 → last bar, offset=1 → one bar ago."""
        return _linreg_loop(np.asarray(src, dtype=float), length, offset)

    @staticmethod
    def median(src, length):
        """Rolling median."""
        return bn.move_median(np.asarray(src, dtype=float), window=length, min_count=1)

    # ----- Range Helpers -----

    @staticmethod
    def highest(src, length):
        return bn.move_max(np.asarray(src, dtype=float), window=length, min_count=1)

    @staticmethod
    def lowest(src, length):
        return bn.move_min(np.asarray(src, dtype=float), window=length, min_count=1)


ta = TA()


# =========================================================
# SERIES UTILITIES
# =========================================================

def crossover(a, b):
    a, b    = np.asarray(a, dtype=float), np.asarray(b, dtype=float)
    out     = np.zeros(len(a), dtype=bool)
    out[1:] = (a[1:] > b[1:]) & (a[:-1] <= b[:-1])
    return out


def crossunder(a, b):
    a, b    = np.asarray(a, dtype=float), np.asarray(b, dtype=float)
    out     = np.zeros(len(a), dtype=bool)
    out[1:] = (a[1:] < b[1:]) & (a[:-1] >= b[:-1])
    return out


def nz(x, val=0.0):
    """Replace NaN with val (default 0)."""
    return np.where(np.isnan(np.asarray(x, dtype=float)), val, x)


def na(x):
    """True where value is NaN (like na() in PineScript)."""
    return np.isnan(np.asarray(x, dtype=float))


def fixnan(x):
    """Forward-fill NaN with the last valid value (fixnan() in PineScript)."""
    x = np.asarray(x, dtype=float).copy()
    for i in range(1, len(x)):
        if np.isnan(x[i]):
            x[i] = x[i - 1]
    return x


def valuewhen(condition, series, occurrence=0):
    return _valuewhen_loop(np.asarray(condition, dtype=bool), np.asarray(series, dtype=float), occurrence)


def barssince(condition):
    return _barssince_loop(np.asarray(condition, dtype=bool))


def highest_bars(src, length):
    """Bars ago where the highest value occurred within last length bars."""
    return _highest_bars_loop(np.asarray(src, dtype=float), length)


def lowest_bars(src, length):
    """Bars ago where the lowest value occurred within last length bars."""
    return _lowest_bars_loop(np.asarray(src, dtype=float), length)


def rising(src, length):
    """True if src has been strictly rising for length consecutive bars."""
    return _rising_loop(np.asarray(src, dtype=float), length)


def falling(src, length):
    """True if src has been strictly falling for length consecutive bars."""
    return _falling_loop(np.asarray(src, dtype=float), length)


def cum(src):
    """Cumulative sum from the first bar (ta.cum in PineScript)."""
    return np.cumsum(np.asarray(src, dtype=float))


def change_pct(src, length=1):
    """Percent change from length bars ago."""
    src  = np.asarray(src, dtype=float)
    out  = np.zeros_like(src)
    prev = src[:-length]
    out[length:] = (src[length:] - prev) / (np.abs(prev) + 1e-12) * 100.0
    return out


def zscore(src, length):
    """Rolling z-score: (src - sma) / stdev."""
    src  = np.asarray(src, dtype=float)
    mean = bn.move_mean(src, window=length, min_count=1)
    std  = bn.move_std(src,  window=length, min_count=1, ddof=0)
    return (src - mean) / (std + 1e-12)


def bar_index(src):
    """Bar index array (0, 1, 2, ...) — like bar_index in PineScript."""
    return np.arange(len(np.asarray(src)), dtype=float)


def ha(open_, high, low, close):
    """Heikin Ashi candles. Returns (ha_open, ha_high, ha_low, ha_close)."""
    return _ha_loop(
        np.asarray(open_,  dtype=float),
        np.asarray(high,   dtype=float),
        np.asarray(low,    dtype=float),
        np.asarray(close,  dtype=float),
    )


# =========================================================
# EXPORTS
# =========================================================

__all__ = [
    "Series",
    "ta",
    "set_ohlcv",
    "crossover",
    "crossunder",
    "nz",
    "na",
    "fixnan",
    "valuewhen",
    "barssince",
    "highest_bars",
    "lowest_bars",
    "rising",
    "falling",
    "cum",
    "change_pct",
    "zscore",
    "bar_index",
    "ha",
]
