import os
import psycopg2
import psycopg2.extras


def get_candles(symbol: str, timeframe: str) -> dict:
    dsn = os.environ["DB_URL"]

    with psycopg2.connect(dsn) as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(
                """
                SELECT open_time, open_price, high_price, low_price, close_price, volume
                FROM crypto_candles
                WHERE symbol = %s AND time_frame = %s
                ORDER BY open_time ASC
                """,
                (symbol, timeframe),
            )
            rows = cur.fetchall()

    if not rows:
        return None

    return {
        "open":   [float(r["open_price"])  for r in rows],
        "high":   [float(r["high_price"])  for r in rows],
        "low":    [float(r["low_price"])   for r in rows],
        "close":  [float(r["close_price"]) for r in rows],
        "volume": [float(r["volume"])      for r in rows],
        "time":   [float(r["open_time"])   for r in rows],
    }
