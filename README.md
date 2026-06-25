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

### Таймауты
- `LLM_TIMEOUT` (по умолч. 300с) — увеличен с 60с для thinking-режима
- `httpx.Client(timeout=120)` в gateway для intake SSE

### Структурированный вывод на фронтенде

| Поле | Отображается | Где |
|------|:---:|------|
| `title` | ✅ | Хедер страницы (`page.tsx:221`), сайдбар (`AppSidebar.tsx:98`) |
| `summary` | ✅ | Под заголовком в сайдбаре (`AppSidebar.tsx:100-102`) |
| `case_file` | ✅ | Секция «Сформированное досье» (`page.tsx:448-459`) через ReactMarkdown |

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
```

## Тестирование

### E2E-скрипт (Angry Tests)

```bash
python test_e2e.py
```

Проверяет 7 секций (25+ проверок):
1. **Auth**: регистрация, логин, без токена → 401, битый токен → 401
2. **Case**: создание intake/direct, без auth → 401
3. **Intake**: SSE content-type, валидный JSON, токены, done, чужое дело → 403
4. **Confirm**: researching, чужой confirm → 403, fake → 404
5. **Research**: статус ready, title ≤ 60, summary, case_file > 100 chars, Markdown
6. **Direct**: JSON (не SSE), is_ready
7. **Resilience**: несуществующий кейс → 404/502

### Модульные тесты (54 шт.)

```bash
COMPOSE_PROFILES=testing docker compose run --rm backend-tester
```

### Мутационное тестирование

```bash
COMPOSE_PROFILES=testing docker compose run --rm backend-tester mutmut run
```

## Быстрый запуск

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
