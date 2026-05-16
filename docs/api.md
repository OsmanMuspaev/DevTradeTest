# Модуль API (Gateway)

## Назначение

`gateway` — единственная точка входа для всех API-запросов с фронтенда. Принимает все `/api/*` запросы от nginx и проксирует их в нужный внутренний сервис.

Дополнительные задачи:
- Разрешение JWT-токена в `user_id` (через Users сервис + Redis-кэш)
- Проброс `X-User-ID` заголовка в AI-сервис
- Кэширование свечных данных в Redis

---

## Архитектура

```
nginx :80
  └── /api/* → gateway :8000 (FastAPI)
                  ├── /api/core/*     → core :18080
                  ├── /api/sandbox/*  → sandbox :8010
                  ├── /api/ai/*       → ai :9000       (+ X-User-ID инъекция)
                  ├── /api/users/*    → users :8005
                  └── /api/health/*   → gateway (локально)
```

---

## Файлы

| Файл | Роль |
|---|---|
| `main.py` | FastAPI app, подключение роутера |
| `router.py` | Регистрация всех эндпоинтов |
| `endpoints/core.py` | Проксирование + Redis-кэш свечей |
| `endpoints/ai.py` | Проксирование + инъекция X-User-ID |
| `endpoints/users.py` | Прозрачное проксирование на users |
| `endpoints/sandbox.py` | Прозрачное проксирование на sandbox |
| `endpoints/health.py` | Проверка доступности gateway |
| `utils/auth.py` | Разрешение JWT → user_id через Redis |
| `utils/cache.py` | Redis-кэш для свечных данных |

---

## Маршруты

### `GET /api/health`

Проверка доступности gateway.

---

### `GET /api/core/coin/{symbol}?tf=&offset=`

Получение исторических свечей. Проксируется в `core :18080`.

**Кэширование:** запросы с `offset > 0` кэшируются в Redis на 60 секунд.  
Запросы с `offset = 0` (актуальные данные) кэш не используют — всегда идут в core напрямую.

| Параметр | Тип | По умолчанию | Описание |
|---|---|---|---|
| `symbol` | string | — | Символ (BTCUSDT, ETHUSDT, ...) |
| `tf` | string | `1m` | Таймфрейм |
| `offset` | int | `0` | Смещение в свечах от конца |

**Ответ:** передаётся как есть из core, с добавлением поля `"source": "cache"` если данные из Redis.

---

### `POST /api/ai/*`

Все AI-запросы. Перед проксированием:
1. Извлекает `Authorization: Bearer <token>` из заголовков
2. Разрешает токен в `user_id` через `GET /users/me` (с Redis-кэшем на 5 минут)
3. Добавляет заголовок `X-User-ID: <id>` к запросу в AI-сервис

Если токен отсутствует или невалиден — запрос всё равно проксируется, но без `X-User-ID`.  
AI-сервис сам отдаёт 401, если заголовок отсутствует.

---

### `ANY /api/users/*`

Прозрачный прокси на `users :8005`. Поддерживает GET, POST, PUT, DELETE.

---

### `ANY /api/sandbox/*`

Прозрачный прокси на `sandbox :8010`. Поддерживает GET, POST, PUT, DELETE.

---

## Кэш свечей (Redis)

```
Ключ:   candles:{symbol}:{tf}:{offset}
TTL:    60 секунд
Формат: JSON-сериализованный список свечей
```

Кэш отключён для `offset = 0` — актуальная свеча обновляется в реальном времени.

---

## Кэш сессий (Redis)

```
Ключ:   session:{jwt_token}
TTL:    300 секунд (5 минут), сбрасывается при каждом hit
Формат: user_id (строка)
```

При обращении к AI-эндпоинту gateway делает `GET /users/me` с токеном, получает `user_id`, кэширует. При следующих запросах — идёт сразу в Redis, обходя Users сервис.

---

## Коды ошибок

| Код | Причина |
|---|---|
| `502` | Downstream-сервис недоступен (core, sandbox, ai, users) |
| `401` | Передан невалидный токен (возвращает users/ai) |

---

## Docker

```yaml
gateway:
  build:
    context: ./backend/api
    dockerfile: Dockerfile.api
  ports:
    - "8000:8000"
  environment:
    - REDIS_URL=redis://redis:6379
    - USERS_URL=http://users:8005
    - CORE_URL=http://core:18080
```
