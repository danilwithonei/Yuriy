# Yuriy AI — Система автоматизации юридического приема и исследований

«Yuriy» — интеллектуальная система для юридических фирм: автоматизирует первичный сбор данных от клиентов (Telegram/MAX), проводит ИИ-исследование законов и передаёт дело в личный кабинет юриста.

## Архитектура

| Сервис | Роль | Порт |
|--------|------|------|
| **`backend`** | API-шлюз + Auth | `8000` |
| **`intake-service`** | LangGraph-диалог с клиентом, Tavily-поиск | `8001` |
| **`lawyer-service`** | ИИ-ассистент юриста по досье дела | `8002` |
| **`frontend`** | Next.js 16 личный кабинет юриста | `3000` |
| **`max-bot`** | Бот для мессенджера MAX | — |
| **`bot-service`** | Telegram-бот (отключён) | — |

### Backend (API Gateway + Auth)

- **Auth**: регистрация/логин email+password, JWT (passlib + python-jose), отдельная SQLite-БД `Lawyer`
- **Middleware**: JWT-защита на `/cases/*` и `/ws/*`
- **UUID**: идентификаторы дел — UUIDv4 (строка), не автоинкремент
- **WebSocket ownership**: при подключении к `/ws/cases/{id}/chat` проверяется владение делом через `_verify_ownership`
  - `4001` — нет/битый/просроченный токен
  - `4002` — Intake Service недоступен
  - `4003` — чужое дело
  - `4004` — дело не найдено
- **WS push**: intake-service после исследования шлёт `POST /internal/case-updated`, gateway рассылает `CASE_STATUS_UPDATED` всем дашбордам. Поллинг удалён.
- **`_verify_ownership`**: принимает опциональный `client: httpx.AsyncClient` — реюз HTTP-клиента в WebSocket-цикле. Возвращает `case_data`, исключая дублирующийся HTTP-запрос в POST `/assist`.

### Frontend (Next.js 16)

- **Стек**: Next.js 16 App Router, React 19, Zustand, Tailwind CSS v4, Base UI
- **Auth**: страницы `/login` и `/register`, `useAuthStore`, `AuthGuard` в `LayoutShell`, axios Bearer-перехватчик
- **API URL**: динамический (`http://<hostname>:8000`) из `window.location.hostname` — не требует `NEXT_PUBLIC_API_URL`
- **WebSocket**: соединение с `?token=` JWT, `useCaseChat` хук
- **403**: при попытке открыть чужое дело — экран «Нет доступа», не консоль

### Intake Service

- LangGraph State Machine с Human-in-the-loop
- Structured Output (Pydantic) для определения готовности данных
- Tavily API для юридического поиска
- Изолированная SQLite на дело

### Lawyer Service

- ИИ-ассистент по досье дела
- Отдельная SQLite для истории диалогов юриста с ИИ
- Модель `Case.id` — UUID, `Message.case_id` — UUID

## Технологии ИИ

- **LLM**: DashScope MaaS — `qwen3.6-flash`
- **Workflow**: LangGraph
- **Search**: Tavily SDK
- **Patterns**: Human-in-the-loop, Structured Output

## Быстрый запуск

### 1. Настройка окружения

```env
# backend/.env
DASHSCOPE_API_KEY=sk-...
DASHSCOPE_BASE_HOST=...maas.aliyuncs.com
TAVILY_API_KEY=tvly-...
LLM_MODEL=qwen3.6-flash
TELEGRAM_BOT_TOKEN=...
MAX_BOT_TOKEN=...
JWT_SECRET=change-me-in-production
JWT_ALGORITHM=HS256
JWT_EXPIRE_MINUTES=1440
```

### 2. Запуск

```bash
docker compose up --build
```

После запуска:
- **Дашборд юриста**: `http://localhost:3000`
- **Gateway API**: `http://localhost:8000`
- **Intake Service**: `http://localhost:8001`
- **Lawyer Service**: `http://localhost:8002`

## Поток данных

1. **Intake**: Клиент → Telegram/MAX → `intake-service`
2. **Logic**: LangGraph анализирует, ставит `interrupt` при нехватке данных
3. **Ready**: ИИ выставляет `is_ready` → кнопка «Подтвердить»
4. **Research**: Граф «размораживается», Tavily-поиск → Markdown-досье
5. **Notify**: `intake-service` → `POST /internal/case-updated` → WS broadcast → фронтенд
6. **Lawyer**: Юрист видит дело, читает досье, общается с `lawyer-service` через WebSocket

## Многоканальность

- **`external_id`**: ID пользователя во внешней системе (строка)
- **`source`**: `telegram` | `max` | `frontend` | `system`

## Тестирование

### Набор

- 54 теста (pytest + respx + asyncio)
- Auth: регистрация, логин, /me, истечение токена, удалённый юзер
- Auth unit: hash/verify password, decode_token, get_current_lawyer
- Access control: владение делом (GET/POST), 404/502/403
- List cases: пустой список, таймаут, 500, битый JSON
- WebSocket: чат, изоляция каналов, сервис недоступен, битый JSON
- WebSocket auth: нет токена, битой, просрочен, чужое/своё дело

### Запуск

```bash
# pytest + coverage
COMPOSE_PROFILES=testing docker compose run --rm backend-tester

# mutmut
COMPOSE_PROFILES=testing docker compose run --rm backend-tester mutmut run
```

### Мутационное тестирование

- Всего мутантов: 1173
- Убито (killed): **103**
- Выжило (survived): **64** (в основном logger/database/ws_manager boilerplate + мутации строк деталей)
- Критические выжившие (auth + verify_ownership): **10** — мутации detail/status_code, убывающая отдача

### Правила «злого» тестирования

1. Не писать тесты только на Happy Path
2. Всегда тестировать таймаут (`ConnectTimeout`) и 502
3. Подавать битые данные (невалидный JSON, null ID)
4. Проверять мутационное тестирование — если мутант выжил, тест недостаточно строгий

---
*Разработано для автоматизации и повышения точности юридической работы.*
