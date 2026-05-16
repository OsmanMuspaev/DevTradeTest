def strategy(open, high, low, close, volume, time):
    rsi = ta.rsi(close, 14)

    return {
        "long_entry":  rsi < 30,   # oversold  — buy
        "long_exit":   rsi > 60,
        "short_entry": rsi > 70,   # overbought — sell short
        "short_exit":  rsi < 40,
    }
