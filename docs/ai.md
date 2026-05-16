# Модуль AI

## Назначение

`ai` — FastAPI-сервис, предоставляющий LLM-чат ассистента для написания и ревью торговых стратегий.

Функции:
- CRUD для чатов и сообщений пользователя
- Генерация ответов через LLM (Groq / OpenAI / Anthropic)
- Системный промпт содержит полную документацию pypine-библиотеки
- Авто-генерация названий чатов через LLM
- Сохранение пользовательских стратегий

Сервис не делает авторизацию самостоятельно — получает `user_id` через заголовок `X-User-ID`, который инжектит gateway после разрешения JWT.

---

## Архитектура

```
gateway :8000
  └── POST /api/ai/* → ai :9000
                          │  X-User-ID: {id}
                          ├── llm/factory.py   → Groq / OpenAI / Anthropic
                          ├── db.py            → AI PostgreSQL :5433
                          └── context/devtrade_library.md  (контекст pypine)
```

---

## Файлы

| Файл | Роль |
|---|---|
| `main.py` | FastAPI приложение, все эндпоинты |
| `models.py` | Pydantic-схемы запросов |
| `db.py` | Пул соединений к AI PostgreSQL (psycopg3) |
| `config.py` | Настройки из переменных окружения |
| `llm/base.py` | Абстрактный базовый класс `BaseLLMProvider` |
| `llm/factory.py` | `LLMFactory` — создание провайдера по имени |
| `llm/groq_provider.py` | Реализация для Groq |
| `llm/openai_provider.py` | Реализация для OpenAI |
| `llm/anthropic_provider.py` | Реализация для Anthropic |
| `llm/utils.py` | Логгер, `safe_str` |
| `context/devtrade_library.md` | Контекст библиотеки pypine для системного промпта |

---

## API

Все эндпоинты требуют `X-User-ID` в заголовках (проставляется gateway автоматически при наличии валидного JWT).

### `GET /health`

```json
{"status": "ok", "llm_provider": "GroqProvider"}
```

---

### `GET /chats`

Список чатов пользователя, отсортированный по `updated_at DESC` (последние 200).

**Ответ:**
```json
{
  "data": [
    {"chat_id": 1, "chat_name": "RSI стратегия", "created_at": "...", "updated_at": "..."}
  ]
}
```

---

### `POST /chats`

Создать новый чат.

**Тело:**
```json
{"name": "Мой чат"}
```

Если `name` пустой — название `"Новый чат"`. Название автоматически обновится после первого сообщения.

---

### `POST /chats/{chat_id}/rename`

Переименовать чат.

**Тело:**
```json
{"name": "Новое название"}
```

---

### `DELETE /chats/{chat_id}`

Удалить чат со всеми сообщениями (CASCADE).

---

### `GET /chats/{chat_id}/messages`

История сообщений чата (до 2000 сообщений, сортировка по `message_id ASC`).

**Ответ:**
```json
{
  "data": [
    {"message_id": 1, "chat_id": 1, "role": "user", "content": "...", "created_at": "..."},
    {"message_id": 2, "chat_id": 1, "role": "assistant", "content": "...", "created_at": "..."}
  ]
}
```

---

### `POST /chats/{chat_id}/messages`

Отправить сообщение и получить ответ ассистента.

**Тело:**
```json
{"content": "Напиши стратегию на RSI"}
```

**Ответ:**
```json
{
  "user":      {"message_id": 3, "role": "user",      "content": "...", ...},
  "assistant": {"message_id": 4, "role": "assistant", "content": "...", ...}
}
```

Поток выполнения:
1. Сохраняется сообщение пользователя
2. Загружается история чата
3. Формируется системный промпт (pypine-контекст)
4. Вызывается LLM-провайдер
5. Сохраняется ответ ассистента
6. Если чат ещё называется `"Новый чат"` — генерируется название через LLM (2-5 слов)

---

### `POST /strategies/submit`

Сохранить стратегию пользователя в базу.

**Тело:**
```json
{
  "title":    "Моя RSI стратегия",
  "language": "python",
  "code":     "def strategy(open, high, low, close, volume, time): ..."
}
```

---

### `GET /provider/{name}`

Переключить активного LLM-провайдера во время работы сервиса (без перезапуска).

Доступные значения: `groq`, `openai`, `anthropic`.

---

## LLM провайдеры

Все провайдеры реализуют интерфейс `BaseLLMProvider`:

```python
class BaseLLMProvider(ABC):
    def generate(messages, model, temperature, max_tokens) -> str: ...
    def generate_streaming(messages, ...) -> Iterator: ...
    def prepare_messages(messages, system_prompt, max_history=30) -> list: ...
    def get_system_prompt(library_context) -> str: ...
```

Активный провайдер определяется переменной окружения `LLM_PROVIDER` (по умолчанию `groq`).  
История обрезается до последних 30 сообщений перед отправкой в LLM.

---

## Системный промпт

Ассистент представляется как `DevTrade AI` — квантитивный аналитик и разработчик торговых стратегий. Промпт включает:

- Поведенческие правила (отвечать на любые технические вопросы, не уклоняться)
- Полную документацию pypine-библиотеки (из `context/devtrade_library.md`)
- Инструкцию отвечать на языке пользователя (RU/EN)

---

## База данных

Отдельный PostgreSQL-инстанс (`ai_db`). Схема:

```sql
chats    (chat_id, user_id, chat_name, created_at, updated_at)
messages (message_id, chat_id, role, content, created_at)
```

Триггер `messages_touch_chat` автоматически обновляет `chats.updated_at` при добавлении сообщения.

Полная схема: [docs/database.md](database.md)

---

## Docker

```yaml
ai:
  build:
    context: ./backend/ai
    dockerfile: Dockerfile.ai
  ports:
    - "9000:9000"
  depends_on:
    ai_db:
      condition: service_healthy
  environment:
    - DB_URL=${AI_DB_CONNECTION_STRING}
    - LLM_PROVIDER=groq
    - GROQ_API_KEY=...
    - DEFAULT_MODEL=llama-3.3-70b-versatile
    - DEFAULT_MAX_TOKENS=2000
    - DEFAULT_TEMPERATURE=0.7
```
