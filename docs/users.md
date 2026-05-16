# Модуль Users

## Назначение

`users` — Django-сервис, отвечающий за аутентификацию и хранение пользовательских данных.

Функции:
- GitHub OAuth2 flow (авторизация через аккаунт GitHub)
- Генерация и валидация JWT-токенов
- Профиль пользователя (email, имя, возраст)
- CRUD для пользовательских скриптов (стратегий)

---

## Архитектура

```
Browser
  └── GET /auth/login       → получить URL для GitHub
  └── GET /auth/callback    → обменять code на токен

gateway
  └── ANY /api/users/* → users :8005
                              └── PostgreSQL :5432
                                    ├── users
                                    ├── user_scripts
                                    └── user_assets
```

---

## Файлы

| Файл | Роль |
|---|---|
| `userapp/views.py` | Все вьюхи: auth, me, скрипты, профиль |
| `userapp/models.py` | Django-модели: `User`, `UserScript` |
| `userapp/urls.py` | URL-маршруты |
| `config/settings.py` | Django-настройки, подключение к PostgreSQL |

---

## Аутентификация

### GitHub OAuth2 Flow

```
1. Фронт  →  GET /auth/login
             ← {"url": "https://github.com/login/oauth/authorize?client_id=..."}

2. Фронт  → редирект на GitHub
3. GitHub → редирект обратно на /auth/callback?code=xxx

4. Users  → POST https://github.com/login/oauth/access_token  (обмен code → token)
5. Users  → GET  https://api.github.com/user               (получить профиль)
6. Users  → upsert в таблицу users
7. Users  ← {"token": "<jwt>", "user": {...}}

8. Фронт хранит JWT, прикладывает в Authorization: Bearer <jwt>
```

### JWT

Токены подписаны алгоритмом `HS256`, ключ — `DJANGO_SECRET_KEY`.

Payload:
```json
{
  "user_id": 1,
  "github_id": 123456,
  "github_username": "johndoe"
}
```

Токен не имеет срока истечения (без `exp`). Валидация — проверка подписи + наличие `user_id`.

---

## API

### `GET /auth/login`

Возвращает URL для редиректа на GitHub OAuth.

**Ответ:**
```json
{"url": "https://github.com/login/oauth/authorize?client_id=...&scope=user:email&redirect_uri=..."}
```

---

### `GET /auth/callback?code=`

Обменивает GitHub OAuth code на JWT-токен приложения.

**Ответ:**
```json
{
  "token": "eyJ...",
  "user": {
    "id": 1,
    "github_id": 123456,
    "github_username": "johndoe",
    "full_name": "John Doe"
  }
}
```

---

### `GET /me`

Возвращает профиль текущего пользователя.

**Заголовки:** `Authorization: Bearer <token>`

**Ответ:**
```json
{
  "id": 1,
  "github_id": 123456,
  "github_username": "johndoe",
  "email": "john@example.com",
  "full_name": "John Doe",
  "age": 25
}
```

Используется gateway для разрешения `token → user_id` (с Redis-кэшем).

---

### `PUT /profile/{user_id}`

Обновить поля профиля.

**Тело** (все поля опциональны):
```json
{
  "email": "new@example.com",
  "full_name": "New Name",
  "age": 30
}
```

Разрешённые поля: `email`, `full_name`, `age`. Остальные игнорируются.

---

### `POST /scripts`

Создать скрипт.

**Тело:**
```json
{
  "user_id": 1,
  "code": "def strategy(open, high, low, close, volume, time): ..."
}
```

Название генерируется автоматически: `script_{user_id}_{N}`.

**Ответ:**
```json
{
  "id": 5,
  "title": "script_1_5",
  "code": "...",
  "is_active": true,
  "created_at": "...",
  "updated_at": "..."
}
```

---

### `GET /scripts?user_id=`

Список скриптов пользователя (сортировка по `created_at DESC`).

---

### `PUT /scripts/{script_id}`

Обновить код скрипта.

**Тело:**
```json
{"user_id": 1, "code": "новый код"}
```

---

### `DELETE /scripts/{script_id}`

Удалить скрипт.

**Тело или query-параметр:** `user_id`

---

## Модели

### User

| Поле | Тип | Описание |
|---|---|---|
| `id` | BIGSERIAL PK | Внутренний ID |
| `github_id` | BIGINT UNIQUE | ID аккаунта на GitHub |
| `github_username` | VARCHAR(100) | Логин GitHub |
| `email` | VARCHAR(255) UNIQUE | Email (nullable) |
| `full_name` | VARCHAR(120) | Имя (nullable) |
| `age` | SMALLINT | Возраст 0–120 (nullable) |
| `created_at` | TIMESTAMP | Дата регистрации |
| `updated_at` | TIMESTAMP | Дата последнего обновления |

### UserScript

| Поле | Тип | Описание |
|---|---|---|
| `id` | BIGSERIAL PK | ID скрипта |
| `user_id` | FK → users | Владелец |
| `title` | VARCHAR(100) | Название |
| `code` | TEXT | Код стратегии |
| `is_active` | BOOLEAN | Активен ли скрипт |
| `created_at` | TIMESTAMP | — |
| `updated_at` | TIMESTAMP | — |

---

## Docker

```yaml
users:
  build:
    context: ./backend/users
    dockerfile: Dockerfile.users
  ports:
    - "8005:8005"
  depends_on:
    db:
      condition: service_healthy
  environment:
    POSTGRES_USER: ${POSTGRES_USER}
    POSTGRES_PASSWORD: ${POSTGRES_PASSWORD}
    POSTGRES_DB: ${POSTGRES_DB}
    POSTGRES_HOST: db
    GITHUB_CLIENT_ID: ${GITHUB_CLIENT_ID}
    GITHUB_CLIENT_SECRET: ${GITHUB_CLIENT_SECRET}
    DJANGO_SECRET_KEY: ${DJANGO_SECRET_KEY}
```
