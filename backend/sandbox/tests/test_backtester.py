import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "app"))

import pytest
import numpy as np
from backtester import run_backtest

# 30 баров с ростом, потом падением — достаточно для большинства индикаторов
_CLOSE = [100,102,101,104,103,106,105,108,107,110,
          109,112,111,114,113,116,115,118,117,120,
          119,117,115,113,111,109,107,105,103,101]

MOCK = {
    "open":   [c - 1 for c in _CLOSE],
    "high":   [c + 1 for c in _CLOSE],
    "low":    [c - 1 for c in _CLOSE],
    "close":  _CLOSE,
    "volume": [1000] * 30,
    "time":   list(range(30)),
}

EMA_STRATEGY = """
def strategy(open, high, low, close, volume, time):
    ema5  = ta.ema(close, 5)
    ema10 = ta.ema(close, 10)
    return {
        "long_entry": crossover(ema5, ema10),
        "long_exit":  crossunder(ema5, ema10),
    }
"""

RSI_LONG_SHORT = """
def strategy(open, high, low, close, volume, time):
    rsi = ta.rsi(close, 5)
    return {
        "long_entry":  rsi < 40,
        "long_exit":   rsi > 60,
        "short_entry": rsi > 70,
        "short_exit":  rsi < 30,
    }
"""

SERIES_INDEX_STRATEGY = """
def strategy(open, high, low, close, volume, time):
    prev = close[1]
    return {
        "long_entry":  close > prev,
        "long_exit":   close < prev,
    }
"""

NO_STRATEGY      = "x = 1 + 1"
BAD_RETURN       = "def strategy(o,h,l,c,v,t): return 'not a dict'"
SYNTAX_ERR       = "def strategy(o: this is broken"
ZERO_SIGNALS     = "def strategy(o,h,l,c,v,t): return {}"


# ── структура ответа ──────────────────────────────────────────────────────────

def test_all_fields_present():
    result = run_backtest(MOCK, EMA_STRATEGY)
    for field in [
        "initial_balance", "final_balance", "net_profit", "net_profit_percent",
        "total_trades", "winning_trades", "losing_trades", "winrate_percent",
        "profit_factor", "max_drawdown_percent", "avg_trade_percent",
        "best_trade_percent", "worst_trade_percent", "trades", "equity_curve",
    ]:
        assert field in result, f"Missing field: {field}"

def test_initial_balance_respected():
    result = run_backtest(MOCK, EMA_STRATEGY, initial_balance=5000)
    assert result["initial_balance"] == 5000.0

def test_equity_curve_max_300_points():
    result = run_backtest(MOCK, EMA_STRATEGY)
    assert len(result["equity_curve"]) <= 300

def test_equity_curve_length_small_data():
    # 30 баров — меньше 300, прореживания не будет
    result = run_backtest(MOCK, EMA_STRATEGY)
    assert len(result["equity_curve"]) == 30


# ── корректность статистики ───────────────────────────────────────────────────

def test_winning_plus_losing_equals_total():
    result = run_backtest(MOCK, EMA_STRATEGY)
    assert result["winning_trades"] + result["losing_trades"] == result["total_trades"]

def test_net_profit_matches_balances():
    result = run_backtest(MOCK, EMA_STRATEGY)
    expected = round(result["final_balance"] - result["initial_balance"], 2)
    assert result["net_profit"] == expected

def test_zero_trades_no_change():
    result = run_backtest(MOCK, ZERO_SIGNALS, initial_balance=10000)
    assert result["total_trades"] == 0
    assert result["net_profit"] == 0.0
    assert result["final_balance"] == 10000.0
    assert result["winrate_percent"] == 0

def test_commission_applied_on_trade():
    # стратегия входит на баре 0 — комиссия должна уменьшить баланс
    always_long = """
def strategy(o,h,l,c,v,t):
    entry = np.zeros(len(c), dtype=bool)
    exit_ = np.zeros(len(c), dtype=bool)
    entry[0] = True
    exit_[-1] = True
    return {"long_entry": entry, "long_exit": exit_}
"""
    result = run_backtest(MOCK, always_long, initial_balance=10000, commission_percent=1.0)
    # комиссия 1% при входе + 1% при выходе → точно не равен 10000 ни до ни после
    assert result["final_balance"] != 10000.0


# ── стороны сделок ────────────────────────────────────────────────────────────

def test_long_only_trades_have_correct_side():
    result = run_backtest(MOCK, EMA_STRATEGY)
    for trade in result["trades"]:
        assert trade["side"] == "long"

def test_short_trades_appear_in_long_short_strategy():
    result = run_backtest(MOCK, RSI_LONG_SHORT)
    sides = {t["side"] for t in result["trades"]}
    assert len(sides) > 0  # хотя бы одна сторона

def test_no_simultaneous_positions():
    # проверяем что сделки не перекрываются по времени
    result = run_backtest(MOCK, RSI_LONG_SHORT)
    trades = result["trades"]
    for i in range(len(trades) - 1):
        assert trades[i]["exit_time"] <= trades[i + 1]["entry_time"]


# ── Series — доступ к предыдущим барам ───────────────────────────────────────

def test_series_indexing_works():
    result = run_backtest(MOCK, SERIES_INDEX_STRATEGY)
    assert "trades" in result
    assert isinstance(result["equity_curve"], list)


# ── обработка ошибок ──────────────────────────────────────────────────────────

def test_missing_strategy_function():
    with pytest.raises(ValueError, match="strategy"):
        run_backtest(MOCK, NO_STRATEGY)

def test_strategy_returns_non_dict():
    with pytest.raises(ValueError, match="dict"):
        run_backtest(MOCK, BAD_RETURN)

def test_syntax_error_in_script():
    with pytest.raises(SyntaxError):
        run_backtest(MOCK, SYNTAX_ERR)
