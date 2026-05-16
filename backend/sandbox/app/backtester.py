import numpy as np
from numba import njit
from datetime import datetime, timezone

from pypine import (
    Series, ta,
    crossover, crossunder,
    nz, na, fixnan, valuewhen, barssince,
    highest_bars, lowest_bars, rising, falling, cum,
    change_pct, zscore, bar_index, ha,
)

_EQUITY_CURVE_POINTS = 300

# exit_reason codes
_EXIT_SIGNAL    = 0
_EXIT_EOD       = 1  # end of data
_EXIT_STOPLOSS  = 2
_EXIT_TAKEPROFIT = 3


@njit(cache=True)
def _run_simulation(close, high, low, time,
                    long_entry, long_exit, short_entry, short_exit,
                    position_size_arr,
                    initial_balance, commission_rate,
                    sl_pct, tp_pct, slippage_rate):
    """
    Core trading simulation. All monetary sizing and price fills happen here.

    position_size_arr : float64 array, values 0.0–1.0 (fraction of balance per trade)
    sl_pct            : stop-loss distance in %, 0 = disabled
    tp_pct            : take-profit distance in %, 0 = disabled
    slippage_rate     : slippage fraction (e.g. 0.001 = 0.1%), 0 = disabled
    """
    n = len(close)

    t_side        = np.empty(n, dtype=np.int8)
    t_entry_bar   = np.empty(n, dtype=np.int64)
    t_exit_bar    = np.empty(n, dtype=np.int64)
    t_entry_time  = np.empty(n, dtype=np.float64)
    t_exit_time   = np.empty(n, dtype=np.float64)
    t_entry_price = np.empty(n, dtype=np.float64)
    t_exit_price  = np.empty(n, dtype=np.float64)
    t_pnl_usdt    = np.empty(n, dtype=np.float64)
    t_pnl_pct     = np.empty(n, dtype=np.float64)
    t_exit_reason = np.zeros(n, dtype=np.int8)
    trade_count   = 0

    equity_curve     = np.empty(n, dtype=np.float64)
    total_commission = 0.0

    balance       = initial_balance
    side          = 0         # 0=flat, 1=long, -1=short
    entry_price   = 0.0
    entry_time_v  = 0.0
    entry_bar_i   = 0
    position_size = 0.0
    sl_price      = 0.0
    tp_price      = 0.0

    for i in range(n):
        price = close[i]

        # ── 1. Check SL / TP ─────────────────────────────────────────
        if side == 1 and (sl_pct > 0.0 or tp_pct > 0.0):
            hit_sl = sl_pct > 0.0 and low[i]  <= sl_price
            hit_tp = tp_pct > 0.0 and high[i] >= tp_price

            if hit_sl or hit_tp:
                reason     = _EXIT_STOPLOSS if hit_sl else _EXIT_TAKEPROFIT
                fill_price = sl_price if hit_sl else tp_price
                fill_price = fill_price * (1.0 - slippage_rate)

                pnl_pct  = (fill_price - entry_price) / entry_price
                pnl_usdt = position_size * pnl_pct
                comm     = position_size * commission_rate
                balance  = balance + pnl_usdt - comm
                total_commission += comm

                t_side[trade_count]        = 1
                t_entry_bar[trade_count]   = entry_bar_i
                t_exit_bar[trade_count]    = i
                t_entry_time[trade_count]  = entry_time_v
                t_exit_time[trade_count]   = time[i]
                t_entry_price[trade_count] = entry_price
                t_exit_price[trade_count]  = fill_price
                t_pnl_usdt[trade_count]    = pnl_usdt
                t_pnl_pct[trade_count]     = pnl_pct * 100.0
                t_exit_reason[trade_count] = reason
                trade_count += 1
                side = 0
                equity_curve[i] = balance
                continue

        elif side == -1 and (sl_pct > 0.0 or tp_pct > 0.0):
            hit_sl = sl_pct > 0.0 and high[i] >= sl_price
            hit_tp = tp_pct > 0.0 and low[i]  <= tp_price

            if hit_sl or hit_tp:
                reason     = _EXIT_STOPLOSS if hit_sl else _EXIT_TAKEPROFIT
                fill_price = sl_price if hit_sl else tp_price
                fill_price = fill_price * (1.0 + slippage_rate)

                pnl_pct  = (entry_price - fill_price) / entry_price
                pnl_usdt = position_size * pnl_pct
                comm     = position_size * commission_rate
                balance  = balance + pnl_usdt - comm
                total_commission += comm

                t_side[trade_count]        = -1
                t_entry_bar[trade_count]   = entry_bar_i
                t_exit_bar[trade_count]    = i
                t_entry_time[trade_count]  = entry_time_v
                t_exit_time[trade_count]   = time[i]
                t_entry_price[trade_count] = entry_price
                t_exit_price[trade_count]  = fill_price
                t_pnl_usdt[trade_count]    = pnl_usdt
                t_pnl_pct[trade_count]     = pnl_pct * 100.0
                t_exit_reason[trade_count] = reason
                trade_count += 1
                side = 0
                equity_curve[i] = balance
                continue

        # ── 2. Entry / Exit signals ───────────────────────────────────
        if side == 0:
            if long_entry[i]:
                entry_price  = price * (1.0 + slippage_rate)
                side         = 1
                entry_time_v = time[i]
                entry_bar_i  = i
                position_size = balance * position_size_arr[i]
                comm          = position_size * commission_rate
                balance      -= comm
                total_commission += comm
                if sl_pct > 0.0:
                    sl_price = entry_price * (1.0 - sl_pct / 100.0)
                if tp_pct > 0.0:
                    tp_price = entry_price * (1.0 + tp_pct / 100.0)

            elif short_entry[i]:
                entry_price  = price * (1.0 - slippage_rate)
                side         = -1
                entry_time_v = time[i]
                entry_bar_i  = i
                position_size = balance * position_size_arr[i]
                comm          = position_size * commission_rate
                balance      -= comm
                total_commission += comm
                if sl_pct > 0.0:
                    sl_price = entry_price * (1.0 + sl_pct / 100.0)
                if tp_pct > 0.0:
                    tp_price = entry_price * (1.0 - tp_pct / 100.0)

        elif side == 1 and long_exit[i]:
            fill  = price * (1.0 - slippage_rate)
            pnl_pct  = (fill - entry_price) / entry_price
            pnl_usdt = position_size * pnl_pct
            comm     = position_size * commission_rate
            balance  = balance + pnl_usdt - comm
            total_commission += comm

            t_side[trade_count]        = 1
            t_entry_bar[trade_count]   = entry_bar_i
            t_exit_bar[trade_count]    = i
            t_entry_time[trade_count]  = entry_time_v
            t_exit_time[trade_count]   = time[i]
            t_entry_price[trade_count] = entry_price
            t_exit_price[trade_count]  = fill
            t_pnl_usdt[trade_count]    = pnl_usdt
            t_pnl_pct[trade_count]     = pnl_pct * 100.0
            t_exit_reason[trade_count] = _EXIT_SIGNAL
            trade_count += 1
            side = 0

        elif side == -1 and short_exit[i]:
            fill  = price * (1.0 + slippage_rate)
            pnl_pct  = (entry_price - fill) / entry_price
            pnl_usdt = position_size * pnl_pct
            comm     = position_size * commission_rate
            balance  = balance + pnl_usdt - comm
            total_commission += comm

            t_side[trade_count]        = -1
            t_entry_bar[trade_count]   = entry_bar_i
            t_exit_bar[trade_count]    = i
            t_entry_time[trade_count]  = entry_time_v
            t_exit_time[trade_count]   = time[i]
            t_entry_price[trade_count] = entry_price
            t_exit_price[trade_count]  = fill
            t_pnl_usdt[trade_count]    = pnl_usdt
            t_pnl_pct[trade_count]     = pnl_pct * 100.0
            t_exit_reason[trade_count] = _EXIT_SIGNAL
            trade_count += 1
            side = 0

        # ── 3. Unrealised equity ──────────────────────────────────────
        if side == 1:
            equity_curve[i] = balance + position_size * ((price - entry_price) / entry_price)
        elif side == -1:
            equity_curve[i] = balance + position_size * ((entry_price - price) / entry_price)
        else:
            equity_curve[i] = balance

    # ── Force-close at last bar ───────────────────────────────────────
    if side != 0:
        if side == 1:
            fill    = close[n - 1] * (1.0 - slippage_rate)
            pnl_pct = (fill - entry_price) / entry_price
        else:
            fill    = close[n - 1] * (1.0 + slippage_rate)
            pnl_pct = (entry_price - fill) / entry_price
        pnl_usdt = position_size * pnl_pct
        comm     = position_size * commission_rate
        balance  = balance + pnl_usdt - comm
        total_commission += comm

        t_side[trade_count]        = side
        t_entry_bar[trade_count]   = entry_bar_i
        t_exit_bar[trade_count]    = n - 1
        t_entry_time[trade_count]  = entry_time_v
        t_exit_time[trade_count]   = time[n - 1]
        t_entry_price[trade_count] = entry_price
        t_exit_price[trade_count]  = fill
        t_pnl_usdt[trade_count]    = pnl_usdt
        t_pnl_pct[trade_count]     = pnl_pct * 100.0
        t_exit_reason[trade_count] = _EXIT_EOD
        trade_count += 1
        equity_curve[n - 1] = balance

    return (
        trade_count,
        t_side[:trade_count],
        t_entry_bar[:trade_count],
        t_exit_bar[:trade_count],
        t_entry_time[:trade_count],
        t_exit_time[:trade_count],
        t_entry_price[:trade_count],
        t_exit_price[:trade_count],
        t_pnl_usdt[:trade_count],
        t_pnl_pct[:trade_count],
        t_exit_reason[:trade_count],
        equity_curve,
        balance,
        total_commission,
    )


@njit(cache=True)
def _compute_stats(equity_curve, pnl_usdt, pnl_pct, t_entry_bar, t_exit_bar, initial_balance):
    n_trades = len(pnl_usdt)

    winning           = 0
    gross_profit      = 0.0
    gross_loss        = 0.0
    sum_pct           = 0.0
    best_pct          = -1e18
    worst_pct         =  1e18
    max_consec_wins   = 0
    max_consec_losses = 0
    cur_wins          = 0
    cur_losses        = 0
    total_hold_bars   = 0

    for i in range(n_trades):
        p  = pnl_usdt[i]
        pc = pnl_pct[i]
        sum_pct += pc
        total_hold_bars += t_exit_bar[i] - t_entry_bar[i]
        if pc > best_pct:
            best_pct = pc
        if pc < worst_pct:
            worst_pct = pc
        if p > 0:
            winning      += 1
            gross_profit += p
            cur_wins     += 1
            cur_losses    = 0
            if cur_wins > max_consec_wins:
                max_consec_wins = cur_wins
        else:
            gross_loss += abs(p)
            cur_losses += 1
            cur_wins    = 0
            if cur_losses > max_consec_losses:
                max_consec_losses = cur_losses

    avg_pct       = sum_pct / n_trades if n_trades > 0 else 0.0
    avg_hold_bars = float(total_hold_bars) / n_trades if n_trades > 0 else 0.0
    if n_trades == 0:
        best_pct  = 0.0
        worst_pct = 0.0

    # Max drawdown from equity peak
    peak   = initial_balance
    max_dd = 0.0
    for v in equity_curve:
        if v > peak:
            peak = v
        dd = (peak - v) / peak * 100.0
        if dd > max_dd:
            max_dd = dd

    # Sharpe ratio (per-trade returns, no risk-free rate)
    sharpe = 0.0
    if n_trades > 1:
        mean_r = sum_pct / n_trades
        var_r  = 0.0
        for i in range(n_trades):
            d = pnl_pct[i] - mean_r
            var_r += d * d
        var_r /= n_trades
        std_r  = var_r ** 0.5
        sharpe = mean_r / std_r if std_r > 1e-12 else 0.0

    return (
        winning,
        gross_profit,
        gross_loss,
        avg_pct,
        best_pct,
        worst_pct,
        max_dd,
        sharpe,
        max_consec_wins,
        max_consec_losses,
        avg_hold_bars,
    )


def _sample_with_times(values: np.ndarray, times: np.ndarray, n: int):
    length = len(values)
    if length <= n:
        return values.tolist(), times.tolist()
    idx = np.round(np.linspace(0, length - 1, n)).astype(int)
    return values[idx].tolist(), times[idx].tolist()


def _compute_monthly_returns(equity_curve: np.ndarray, time_arr: np.ndarray) -> list:
    """Group equity by calendar month. Skipped if timestamps look sequential/fake."""
    if len(equity_curve) == 0 or time_arr[0] < 1_000_000_000:
        return []
    monthly_open  = {}
    monthly_close = {}
    for val, ts in zip(equity_curve, time_arr):
        ts_s = ts / 1000.0 if ts > 1e12 else ts
        try:
            dt  = datetime.fromtimestamp(ts_s, tz=timezone.utc)
        except (ValueError, OSError):
            continue
        key = (dt.year, dt.month)
        if key not in monthly_open:
            monthly_open[key] = val
        monthly_close[key] = val
    result = []
    for key in sorted(monthly_open):
        year, month = key
        o   = monthly_open[key]
        c   = monthly_close[key]
        pct = (c - o) / o * 100.0 if o > 0 else 0.0
        result.append({"year": year, "month": month, "return_percent": round(pct, 2)})
    return result


def run_backtest(data: dict, user_code: str,
                 initial_balance=10000,
                 commission_percent=0.1,
                 slippage_percent=0.0):
    open_ = np.asarray(data["open"],   dtype=float)
    high  = np.asarray(data["high"],   dtype=float)
    low   = np.asarray(data["low"],    dtype=float)
    close = np.asarray(data["close"],  dtype=float)
    volume = np.asarray(data["volume"], dtype=float)
    time  = np.asarray(data["time"],   dtype=float)

    namespace = {
        "__builtins__": __builtins__,
        "np":           np,
        "ta":           ta,
        "crossover":    crossover,
        "crossunder":   crossunder,
        "nz":           nz,
        "na":           na,
        "fixnan":       fixnan,
        "valuewhen":    valuewhen,
        "barssince":    barssince,
        "highest_bars": highest_bars,
        "lowest_bars":  lowest_bars,
        "rising":       rising,
        "falling":      falling,
        "cum":          cum,
        "change_pct":   change_pct,
        "zscore":       zscore,
        "bar_index":    bar_index,
        "ha":           ha,
    }

    exec(user_code, namespace)

    if "strategy" not in namespace:
        raise ValueError("User script must define strategy(...) function")

    signals = namespace["strategy"](
        Series(open_), Series(high), Series(low),
        Series(close), Series(volume), Series(time),
    )

    if not isinstance(signals, dict):
        raise ValueError("strategy() must return a dict with signal arrays")

    long_entry  = np.asarray(signals.get("long_entry",  np.zeros(len(close), dtype=bool)), dtype=bool)
    long_exit   = np.asarray(signals.get("long_exit",   np.zeros(len(close), dtype=bool)), dtype=bool)
    short_entry = np.asarray(signals.get("short_entry", np.zeros(len(close), dtype=bool)), dtype=bool)
    short_exit  = np.asarray(signals.get("short_exit",  np.zeros(len(close), dtype=bool)), dtype=bool)

    # Optional strategy-level parameters
    sl_pct = float(signals.get("sl_percent", 0.0) or 0.0)
    tp_pct = float(signals.get("tp_percent", 0.0) or 0.0)

    raw_ps = signals.get("position_size", None)
    if raw_ps is None:
        position_size_arr = np.ones(len(close), dtype=float)
    elif isinstance(raw_ps, (int, float)):
        position_size_arr = np.full(len(close), float(raw_ps), dtype=float)
    else:
        position_size_arr = np.clip(np.asarray(raw_ps, dtype=float), 0.0, 1.0)

    (
        trade_count,
        t_side,
        t_entry_bar,
        t_exit_bar,
        t_entry_time,
        t_exit_time,
        t_entry_price,
        t_exit_price,
        t_pnl_usdt,
        t_pnl_pct,
        t_exit_reason,
        equity_curve,
        final_balance,
        total_commission,
    ) = _run_simulation(
        close, high, low, time,
        long_entry, long_exit, short_entry, short_exit,
        position_size_arr,
        float(initial_balance),
        commission_percent / 100.0,
        sl_pct,
        tp_pct,
        slippage_percent / 100.0,
    )

    start_balance = float(initial_balance)
    net_profit    = final_balance - start_balance

    (
        winning,
        gross_profit,
        gross_loss,
        avg_pct,
        best_pct,
        worst_pct,
        max_dd,
        sharpe,
        max_consec_wins,
        max_consec_losses,
        avg_hold_bars,
    ) = _compute_stats(equity_curve, t_pnl_usdt, t_pnl_pct, t_entry_bar, t_exit_bar, start_balance)

    bah = (close[-1] - close[0]) / close[0] * 100.0 if len(close) > 1 else 0.0

    _exit_reason_labels = {
        _EXIT_SIGNAL:     "signal",
        _EXIT_EOD:        "end_of_backtest",
        _EXIT_STOPLOSS:   "stop_loss",
        _EXIT_TAKEPROFIT: "take_profit",
    }

    trades = []
    for i in range(trade_count):
        t = {
            "side":        "long" if t_side[i] == 1 else "short",
            "entry_time":  float(t_entry_time[i]),
            "exit_time":   float(t_exit_time[i]),
            "entry_price": float(t_entry_price[i]),
            "exit_price":  float(t_exit_price[i]),
            "pnl_usdt":    float(t_pnl_usdt[i]),
            "pnl_percent": float(t_pnl_pct[i]),
            "exit_reason": _exit_reason_labels.get(int(t_exit_reason[i]), "signal"),
        }
        trades.append(t)

    monthly_returns = _compute_monthly_returns(equity_curve, time)
    eq_values, eq_times = _sample_with_times(equity_curve, time, _EQUITY_CURVE_POINTS)

    return {
        "initial_balance":        round(start_balance, 2),
        "final_balance":          round(final_balance, 2),
        "net_profit":             round(net_profit, 2),
        "net_profit_percent":     round(net_profit / start_balance * 100, 2),
        "buy_and_hold_percent":   round(bah, 2),
        "total_trades":           trade_count,
        "winning_trades":         int(winning),
        "losing_trades":          int(trade_count - winning),
        "winrate_percent":        round(winning / trade_count * 100 if trade_count else 0, 2),
        "profit_factor":          round(gross_profit / gross_loss if gross_loss else 0, 2),
        "sharpe_ratio":           round(float(sharpe), 3),
        "max_drawdown_percent":   round(float(max_dd), 2),
        "avg_trade_percent":      round(float(avg_pct), 2),
        "best_trade_percent":     round(float(best_pct), 2),
        "worst_trade_percent":    round(float(worst_pct), 2),
        "max_consecutive_wins":   int(max_consec_wins),
        "max_consecutive_losses": int(max_consec_losses),
        "avg_hold_bars":          round(float(avg_hold_bars), 1),
        "total_commission_paid":  round(float(total_commission), 2),
        "monthly_returns":        monthly_returns,
        "trades":                 trades,
        "equity_curve":           eq_values,
        "equity_times":           eq_times,
    }
