CREATE TABLE IF NOT EXISTS crypto_candles (
    id SERIAL PRIMARY KEY,
    symbol VARCHAR(20) NOT NULL,         -- Монета
    time_frame VARCHAR(5) NOT NULL,      -- TF
    open_time BIGINT NOT NULL,           -- Время открытия свечи
    open_price NUMERIC(15, 6) NOT NULL,  -- Цена открытия
    high_price NUMERIC(15, 6) NOT NULL,  -- Максимум
    low_price NUMERIC(15, 6) NOT NULL,   -- Минимум
    close_price NUMERIC(15, 6) NOT NULL, -- Цена закрытия
    volume NUMERIC(20, 6) NOT NULL,      -- Объем торгов
    is_grow BOOLEAN NOT NULL,            -- Выросла ли свеча в цене
    
    UNIQUE(symbol, time_frame, open_time)
);

CREATE INDEX idx_candles_lookup ON crypto_candles(symbol, time_frame, open_time DESC);