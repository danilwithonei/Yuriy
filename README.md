# Yuriy AI — Система автоматизации юридического приема и исследований

«Yuriy» — интеллектуальная система для юридических фирм: автоматизирует первичный сбор данных от клиентов (Telegram/MAX), проводит ИИ-исследование законов и передаёт дело в личный кабинет юриста.

## Структура проекта

```
Yuriy/
├── packages/
│   └── shared/                          # Общий пакет для всех микросервисов
│       ├── pyproject.toml               # зависимости: sqlmodel, langchain-openai, alembic
│       └── yuriy_shared/
│           ├── __init__.py
│           ├── logger.py                # единый setup_logger вместо 5 копий
│           ├── database.py              # create_engine, create_db_and_tables
│           ├── llm.py                   # get_llm с timeout из env
│           ├── sse.py                   # parse_sse_line — один парсер вместо 3
│           ├── migration.py             # run_migrations — Alembic обёртка
│           ├── models/
│           │   ├── lawyer.py            # Lawyer (auth)
│           │   ├── user.py              # User
│           │   ├── case.py              # Case — полный набор полей
│           │   └── message.py           # Message
│           ├── schemas/
│           │   └── case.py              # PatchCasePinRequest, DeleteCaseResponse
│           └── alembic/
│               ├── env.py
│               ├── script.py.mako
│               └── versions/
│                   ├── 0001_initial.py          # все таблицы
│                   └── 0002_add_case_fields.py   # case_type, title, summary для lawyer
│
├── backend/                             # API-шлюз + Auth (порт 8000)
│   ├── main.py                          # FastAPI: auth, case CRUD, WS, прокси
│   ├── auth.py                          # JWT + bcrypt
│   ├── schemas.py                       # RegisterRequest, LoginRequest, LawyerOut
│   ├── ws_manager.py                    # WebSocket ConnectionManager
│   ├── core/logger.py                   # → re-export из yuriy_shared.logger
│   ├── database.py                      # → thin wrapper (AUTH_DATABASE_URL)
│   ├── models.py                        # → re-export Lawyer из shared
│   ├── requirements.txt                 # только backend-специфичные депы
│   └── tests/                           # 54 теста (pytest + respx + mutmut)
│
├── services/
│   ├── intake-service/                  # Intake Agent (порт 8001)
│   │   ├── main.py                      # FastAPI: LangGraph диалог + research
│   │   ├── graph.py                     # LangGraph StateGraph
│   │   ├── core/
│   │   │   ├── agent.py                 # AgentService
│   │   │   ├── state.py                 # AgentState TypedDict
│   │   │   ├── llm.py → shared
│   │   │   └── logger.py → shared
│   │   ├── modules/
│   │   │   ├── intake/ (node.py, prompts.py)
│   │   │   ├── research/ (node.py, prompts.py)
│   │   │   └── compiler/ (node.py, prompts.py)
│   │   ├── models.py → shared
│   │   ├── database.py → shared
│   │   └── tests/
│   │
│   ├── lawyer-service/                  # Lawyer Assistant (порт 8002)
│   │   ├── main.py                      # FastAPI: анализ досье + SSE стрим
│   │   ├── prompts.py
│   │   ├── core/
│   │   │   ├── llm.py → shared
│   │   │   └── logger.py → shared
│   │   ├── models.py → shared
│   │   └── database.py → shared
│   │
│   └── max-bot-service/                 # MAX мессенджер бот
│       ├── main.py
│       └── core/logger.py → shared
│
├── frontend/                            # Next.js 16 (порт 3000)
│   └── src/
│
├── docker-compose.yml                   # 6 сервисов + shared volume
├── AGENTS.md                            # Angry Tests guide
└── test_e2e.py                          # End-to-end интеграционный тест
```

### Сервисы

| Сервис | Роль | Порт | Зависит от shared |
|--------|------|------|:---:|
| **`backend`** | API-шлюз + Auth + WebSocket | `8000` | ✅ |
| **`intake-service`** | LangGraph диалог с клиентом, Tavily-поиск | `8001` | ✅ |
| **`lawyer-service`** | ИИ-ассистент юриста по досье дела | `8002` | ✅ |
| **`max-bot`** | Бот для мессенджера MAX | — | ✅ |
| **`frontend`** | Next.js 16 личный кабинет юриста | `3000` | ❌ |
| **`telegram_bot`** | Telegram-бот (profile: deprecated) | — | ✅ |

## Shared package (`packages/yuriy_shared`)

Единый пакет, устанавливаемый во все Python-сервисы как editable:
```bash
pip install -e /app/packages/shared
```

Устраняет копипасту: logger (5→1), модели User/Case/Message (2→1), llm (2→1), SSE парсер (3→1).

## Миграции (Alembic)

Вместо сырого `ALTER TABLE` в try/except:

```bash
alembic upgrade head
```

Каждый сервис при старте вызывает `run_migrations(DATABASE_URL)`, Alembic автоматически определяет:
- новая БД → создать все таблицы
- существующая БД без alembic_version → stamp как head
- существующая БД с alembic_version → применить pending миграции

## Поток данных

```
Клиент → Intake (LLM + LangGraph) → Confirm → Research (Tavily) → Compiler (досье) → Gateway → WS → Фронтенд
```

1. **Intake**: LLM собирает данные через диалог, стримит токены через SSE на фронтенд
2. **Ready**: LLM помечает последнюю строку `[IS_READY: true/false]` → кнопка «Подтвердить»
3. **Confirm**: юрист нажимает кнопку → `POST /confirm` → фоновая задача research
4. **Research**: `research_node` → Tavily-поиск (или пропуск через `TAVILY_DISABLED`) → `compiler_node`
5. **Compiler**: LLM формирует JSON с `title`, `summary`, `case_file` (Markdown-досье)
6. **Notify**: intake-service → `POST /internal/case-updated` → WS broadcast → фронтенд
7. **Lawyer**: юрист видит дело, читает досье, общается с lawyer-service через WebSocket

## Ключевые изменения

### SSE-стриминг интайка
- `/cases/{id}/intake/chat` возвращает `text/event-stream` с токенами
- Фронтенд показывает токены в реальном времени с мигающим курсором
- `[IS_READY: true/false]` стриппится на backend, `is_ready` приходит в `done`-событии

### Research без graph resumption
- `run_background_research` (**core/agent.py:68**) вызывает `research_node()` и `compiler_node()` напрямую, минуя `ainvoke(None)` — LangGraph 1.2.4 некорректно возобновляет прерванный граф с interrupt_before
- Синхронные вызовы LLM/Tavily блокируют event loop — при `TAVILY_DISABLED` проблема не проявляется

### Компилятор досье
- LLM вызывается без `with_structured_output` — Qwen в thinking-режиме не держит схему
- Ответ парсится вручную: `_parse_json()` в **modules/compiler/node.py**
- Промпт явно указывает ключи `title`, `summary`, `case_file`; парсер принимает и `case_title`/`case_summary`

## Переменные окружения

```env
# Обязательные
DASHSCOPE_API_KEY=sk-...
DASHSCOPE_BASE_HOST=...maas.aliyuncs.com
JWT_SECRET=change-me-in-production

# Опциональные
LLM_MODEL=qwen3.7-plus
LLM_TIMEOUT=300
TAVILY_API_KEY=tvly-...
TAVILY_DISABLED=true                     # отключить Tavily (долгий поиск)
JWT_ALGORITHM=HS256
JWT_EXPIRE_MINUTES=1440

# Базы данных (по умолч. SQLite)
AUTH_DATABASE_URL=sqlite:///./db/auth.db
AGENT_DATABASE_URL=sqlite:///./db/agent_database.db
LAWYER_DATABASE_URL=sqlite:///./db/lawyer_database.db
```

## Тестирование

### Модульные тесты (54 шт.)

```bash
COMPOSE_PROFILES=testing docker compose run --rm backend-tester
```

### E2E-скрипт

```bash
python test_e2e.py
```

Проверяет 7 секций (25+ проверок): auth, case CRUD, intake SSE, confirm, research, direct cases, resilience.

### Мутационное тестирование

```bash
COMPOSE_PROFILES=testing docker compose run --rm backend-tester mutmut run
```

Текущие метрики: 103 убито, 64 выжило (в основном logger/boilerplate).

## Запуск

```bash
docker compose up --build
```

После запуска:
- **Дашборд юриста**: `http://localhost:3000`
- **Gateway API**: `http://localhost:8000`
- **Intake Service**: `http://localhost:8001`
- **Lawyer Service**: `http://localhost:8002`

---

*Разработано для автоматизации и повышения точности юридической работы.*
