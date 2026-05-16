# DevTrade

**DevTrade** — algo-trading platform that sits between TradingView and QuantConnect: you write a strategy in pure Python, run a backtest in one request, and get a full performance report with an equity curve. Powerful, but without the complexity barrier.

---

## Table of Contents

- [Architecture](#architecture)
- [Modules](#modules)
- [Quick Start](#quick-start)
- [Configuration](#configuration)
- [Environment Variables](#environment-variables)

---

## Architecture

```
Browser
  │
  ▼
nginx :80
  ├── /           → frontend :80   (React + Vite)
  └── /api/*      → gateway :8000  (FastAPI, reverse proxy)
                        ├── /api/core/*     → core :18080    (C++, live market data)
                        ├── /api/sandbox/*  → sandbox :8010  (Python, backtester)
                        ├── /api/ai/*       → ai :9000       (Python, LLM chat)
                        ├── /api/users/*    → users :8005    (Django, auth)
                        └── /api/health/*   → gateway itself

PostgreSQL (main) :5432   — candles + users + scripts
PostgreSQL (ai)   :5433   — chats + messages
Redis             :6379   — candle cache + session cache
```

All services run inside Docker Compose. The gateway is the only public-facing API — all routing and auth resolution happen there.

---

## Modules

| Module | Tech | Port | Description | Docs |
|---|---|---|---|---|
| **frontend** | React, Vite, Nginx | 80 | Candlestick charts, strategy editor, AI chat | — |
| **gateway** (api) | FastAPI, Python | 8000 | Reverse proxy, auth middleware, Redis cache | [docs/api.md](docs/api.md) |
| **core** | C++17, Crow, IXWebSocket | 18080 | Real-time Binance data, historical sync, PostgreSQL writer | [docs/core.md](docs/core.md) |
| **sandbox** | FastAPI, Python | 8010 | Backtester engine + pypine DSL | [docs/sandbox.md](docs/sandbox.md) |
| **ai** | FastAPI, Python | 9000 | LLM chat assistant (Groq / OpenAI / Anthropic) | [docs/ai.md](docs/ai.md) |
| **users** | Django, Python | 8005 | GitHub OAuth2, JWT auth, user scripts storage | [docs/users.md](docs/users.md) |
| **pypine** | Python library | — | PineScript-style DSL for writing strategies | [docs/pypinelib.md](docs/pypinelib.md) |

### Database schemas

Two independent PostgreSQL instances:

- **Main DB** — `crypto_candles`, `users`, `user_assets`, `user_scripts`
- **AI DB** — `chats`, `messages`

Full schema reference: [docs/database.md](docs/database.md)

---

## Quick Start

**Prerequisites:** Docker, Docker Compose, a GitHub OAuth App.

```bash
# 1. Clone and enter the repo
git clone <repo-url>
cd devtrade

# 2. Create and fill in the environment file
cp .env.example .env
# edit .env (see Environment Variables below)

# 3. Start everything
docker compose up -d --build

# 4. Open the app
open http://localhost
```

To rebuild a single service after changes:
```bash
docker compose up -d --build sandbox
docker compose up -d --build core
```

---

## Configuration

`params.json` in the repo root controls which symbols and timeframes Core tracks, and how many candles to keep per timeframe. It is mounted into both `core` and `frontend` containers.

```json
{
  "crypto_list": ["BTCUSDT", "ETHUSDT", "SOLUSDT", "TONUSDT"],
  "timeframes":  ["1s", "1m", "5m", "15m", "1h", "4h", "1d"],
  "candles_amount": {
    "1d": 1825,
    "4h": 2190,
    "1h": 8760,
    "15m": 672,
    "5m": 2016,
    "1m": 4320,
    "1s": 3600
  }
}
```

To add a new trading pair — add it to `crypto_list` and rebuild `core`.

---

## Environment Variables

Create a `.env` file in the repo root with the following variables:

```dotenv
# ── Main PostgreSQL ──────────────────────────────────
POSTGRES_USER=devtrade
POSTGRES_PASSWORD=secret
POSTGRES_DB=devtrade
DB_CONNECTION_STRING=postgresql://devtrade:secret@db:5432/devtrade

# ── AI PostgreSQL ────────────────────────────────────
AI_POSTGRES_USER=ai
AI_POSTGRES_PASSWORD=secret
AI_POSTGRES_DB=ai
AI_DB_CONNECTION_STRING=postgresql://ai:secret@ai_db:5432/ai

# ── Redis ────────────────────────────────────────────
REDIS_URL=redis://redis:6379

# ── GitHub OAuth ─────────────────────────────────────
GITHUB_CLIENT_ID=your_github_client_id
GITHUB_CLIENT_SECRET=your_github_client_secret

# ── Django ───────────────────────────────────────────
DJANGO_SECRET_KEY=change-me-to-something-random

# ── LLM Provider ─────────────────────────────────────
# Supported: groq | openai | anthropic
LLM_PROVIDER=groq
GROQ_API_KEY=gsk_...
# OPENAI_API_KEY=sk-...
# ANTHROPIC_API_KEY=sk-ant-...
DEFAULT_MODEL=llama-3.3-70b-versatile
DEFAULT_FAST_MODEL=llama-3.1-8b-instant
DEFAULT_TEMPERATURE=0.7
DEFAULT_MAX_TOKENS=2000

# ── Core live data ───────────────────────────────────
LIVE_INTERVAL_MS=1000
```
