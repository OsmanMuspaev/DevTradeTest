# База данных

В DevTrade используется два независимых PostgreSQL-инстанса:

| Инстанс | Контейнер | Порт | Содержит |
|---|---|---|---|
| **Main DB** | `database` | 5432 | Рыночные данные, пользователи, скрипты |
| **AI DB** | `ai_database` | — (внутренний) | Чаты, сообщения |

---

## Main DB

### `crypto_candles`

Основная таблица рыночных данных. Заполняется модулем Core (C++) в реальном времени.

```sql
CREATE TABLE crypto_candles (
    id          SERIAL PRIMARY KEY,
    symbol      VARCHAR(20)    NOT NULL,  -- "BTCUSDT"
    time_frame  VARCHAR(5)     NOT NULL,  -- "1h"
    open_time   BIGINT         NOT NULL,  -- Unix ms
    open_price  NUMERIC(15, 6) NOT NULL,
    high_price  NUMERIC(15, 6) NOT NULL,
    low_price   NUMERIC(15, 6) NOT NULL,
    close_price NUMERIC(15, 6) NOT NULL,
    volume      NUMERIC(20, 6) NOT NULL,
    is_grow     BOOLEAN        NOT NULL,  -- close > open

    UNIQUE(symbol, time_frame, open_time)
);

CREATE INDEX idx_candles_lookup ON crypto_candles(symbol, time_frame, open_time DESC);
```

**Глубина хранения** (задаётся в `params.json`):

| Таймфрейм | Свечей | Глубина |
|---|---|---|
| `1d` | 1825 | ~5 лет |
| `4h` | 2190 | ~1 год |
| `1h` | 8760 | ~1 год |
| `15m` | 672 | ~7 дней |
| `5m` | 2016 | ~7 дней |
| `1m` | 4320 | ~3 дня |
| `1s` | 3600 | 1 час |

---

### `users`

Пользователи, авторизованные через GitHub OAuth.

```sql
CREATE TABLE users (
    id              BIGSERIAL PRIMARY KEY,
    github_id       BIGINT UNIQUE,
    github_username VARCHAR(100),
    email           VARCHAR(255) UNIQUE,
    full_name       VARCHAR(120),
    age             SMALLINT CHECK (age >= 0 AND age <= 120),
    created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

---

### `user_scripts`

Торговые стратегии пользователей (хранятся как Python-код).

```sql
CREATE TABLE user_scripts (
    id         BIGSERIAL PRIMARY KEY,
    user_id    BIGINT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    title      VARCHAR(100) NOT NULL,
    code       TEXT NOT NULL,
    is_active  BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

---

### `user_assets`

Активы пользователя (задел для будущего live-трейдинга).

```sql
CREATE TABLE user_assets (
    id      BIGSERIAL PRIMARY KEY,
    user_id BIGINT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    symbol  VARCHAR(20) NOT NULL,
    amount  NUMERIC(30, 12) DEFAULT 0,
    UNIQUE(user_id, symbol)
);
```

---

## AI DB

### `chats`

```sql
CREATE TABLE chats (
    chat_id    BIGSERIAL PRIMARY KEY,
    user_id    BIGINT    NOT NULL DEFAULT 1,
    chat_name  TEXT      NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_chats_user_updated ON chats(user_id, updated_at DESC);
```

`updated_at` обновляется автоматически триггером при добавлении нового сообщения.

---

### `messages`

```sql
CREATE TABLE messages (
    message_id BIGSERIAL PRIMARY KEY,
    chat_id    BIGINT NOT NULL REFERENCES chats(chat_id) ON DELETE CASCADE,
    role       TEXT   NOT NULL CHECK (role IN ('system', 'user', 'assistant')),
    content    TEXT   NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_messages_chat_created ON messages(chat_id, created_at);
```

---

## Инициализация

SQL-скрипты инициализации монтируются в PostgreSQL-контейнеры и выполняются при первом старте:

```yaml
volumes:
  - ./database/candle/init.sql:/docker-entrypoint-initdb.d/candle_init.sql
  - ./database/users/init.sql:/docker-entrypoint-initdb.d/users_init.sql
  # для ai_db:
  - ./database/ai/init.sql:/docker-entrypoint-initdb.d/ai_init.sql
```

При повторном запуске уже существующих контейнеров скрипты не перевыполняются (`IF NOT EXISTS`).
