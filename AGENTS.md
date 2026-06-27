# Angry Tests Guide для Yuriy

Правила тестирования по методологии «Злые тесты» (Егор Бугаенко, книга «Angry Tests»).

## Чем злые тесты отличаются от обычных

Обычный тест проверяет: «работает ли код так, как я задумал?»
Злой тест проверяет: «сломает ли кто-то/что-то мой код?»

Код врут. Тесты должны ловить ложь. Если тест можно подделать (пройти с пустой имплементацией) — он бесполезен.

## Принципы (из книги)

### 1. Тесты не должны быть вежливыми (стр. 23)

«Плохой тест — это тот, который никогда не падает.
Хороший тест — тот, который падает при малейшем изменении поведения.»

Мера хорошего теста — **мутационное тестирование**. Мутант (намеренная поломка кода) должен быть убит. Если мутант выжил — ваш тест не проверяет то, что должен.

### 2. Не мокай внешние сервисы — мокай протокол (стр. 45)

Мы используем **respx** — перехват HTTP на уровне транспорта. Никаких ручных `unittest.mock.patch`. Мок воспроизводит поведение сервиса: он может ответить 200, 404, 500, или упасть с таймаутом.

```python
# Правильно: мок на уровне HTTP, сервис "как живой"
respx_mock.get(f"{INTAKE_URL}/case/{CASE_ID}").mock(side_effect=ConnectTimeout)

# Неправильно: мок функции-хелпера
mock_get_case = mocker.patch("main.get_case_from_intake")
```

### 3. Тестируй состояние, а не взаимодействие (стр. 57)

Проверяй `response.status_code`, `response.json()["detail"]` — то, что вернул API. Не проверяй, сколько раз вызвалась функция или с какими аргументами.

```python
# Правильно
resp = client.get(f"/cases/{id}", headers=auth_headers)
assert resp.status_code == 403

# Неправильно
mock_get_case.assert_called_once_with(id)
```

### 4. Данные должны быть грязными (стр. 72)

Скучные данные рождают скучные тесты. Тестируй с:
- UUID вразнобой, не `00000000-0000...`
- Пустыми строками и null
- Битым JSON и невалидными токенами
- Гигантскими payload (10000 символов в имени)
- Строками с Unicode, эмодзи

```python
def test_register_giant_name(self, client):
    resp = client.post("/auth/register", json={
        "email": f"giant_{uuid4().hex[:8]}@test.com",
        "name": "X" * 10000,
        "password": "pass1234"
    })
    assert resp.status_code == 400  # или 413, 422 — система выстояла
```

### 5. Сетевой хаос (стр. 89)

Любой внешний вызов может упасть. Проверяй:
- `ConnectTimeout` — сервис завис навсегда
- `Response(500)` — сервис упал
- `Response(502)` — шлюз upstream не отвечает
- `Response(200, content=b"not json")` — сервис вернул мусор

```python
respx_mock.get(url).mock(side_effect=ConnectTimeout)
res = client.get("/cases", headers=auth_headers)
assert res.status_code == 502
```

### 6. Каждый тест — песочница (стр. 103)

Тесты не должны влиять друг на друга:
- Фикстуры создают данные для конкретного теста
- In-memory SQLite (`:memory:`) с `StaticPool` — каждое подключение видит те же данные
- Мокаем `respx` свежим для каждого теста (`@respx.mock`)
- Два тестовых юзера с фиксированными email — для проверки владения

### 7. Тест должен падать по делу (стр. 118)

Ошибка в тесте должна говорить, что именно сломалось:
```python
assert resp.status_code == 403
assert resp.json()["detail"] == "Access denied"
```

Если тест упадёт с `KeyError: "detail"` вместо `AssertionError` — вы не увидите разницы между «упал код» и «упал тест».

### 8. Идентификаторы — строки, нигде не зашивай числа (стр. 131)

UUID не предсказуемы. Никаких `lawyer_id: 1` в моках — используй константы из теста.

```python
CASE_UUID = "aaaaaaaa-aaaa-4aaa-aaaa-aaaaaaaaaaaa"
FOREIGN_UUID = "bbbbbbbb-bbbb-4bbb-bbbb-bbbbbbbbbbbb"
MISSING_UUID = "cccccccc-cccc-4ccc-cccc-cccccccccccc"
```

## Паттерны проекта

### Базовая структура теста

```python
@respx.mock
def test_feature_angry_scenario(client, auth_headers, respx_mock):
    # 1. Имитация катастрофы
    respx_mock.get(f"{INTAKE_URL}/case/{ID}").mock(side_effect=ConnectTimeout)

    # 2. Запрос через шлюз
    resp = client.get(f"/cases/{ID}", headers=auth_headers)

    # 3. Проверка: шлюз выстоял
    assert resp.status_code == 502
    assert "unavailable" in resp.json()["detail"].lower()
```

### Фикстуры (conftest.py)

- `client` — `TestClient(app)` для каждого теста
- `lawyers` — session-scoped, создаёт двух юзеров (A и B) с токенами
- `auth_headers` — `Authorization: Bearer <token>` для юзера A
- `auth_headers_b` — для юзера B (проверка владения)

### WebSocket тесты

```python
def test_ws_foreign_case_forbidden(self, client, auth_headers, respx_mock):
    respx_mock.get(f"{INTAKE_URL}/case/{CASE_UUID}").mock(return_value=Response(200, json={
        "case": {"id": CASE_UUID, "lawyer_id": 999},
        "messages": []
    }))
    token = auth_headers["Authorization"].split(" ")[1]
    with pytest.raises(WebSocketDisconnect) as exc:
        with client.websocket_connect(f"/ws/cases/{CASE_UUID}/chat?token={token}"):
            pass
    assert exc.value.code == 4003
```

## Что обязательно проверять для каждого эндпоинта

| Сценарий | Код | Инструмент |
|----------|-----|------------|
| Happy Path | 200 | — |
| Нет токена | 401 | — |
| Битый токен | 401 | — |
| Просроченный токен | 401 | `_expired_token()` |
| Чужой ресурс | 403 | `auth_headers_b` |
| Ресурс не найден | 404 | `Response(404)` |
| Сервис недоступен | 502 | `ConnectTimeout` или `Response(502)` |
| Битый ответ сервиса | 502 | `Response(200, content=b"not json")` |
| Битая входная дата | 400/422 | garbage/null/гигантский payload |
| Мутационный тест | все убиты | `mutmut run` |

## Мутационное тестирование

Мутант — намеренная поломка: `if a != b` → `if a == b`, `raise` → `pass`, `"Auth error"` → `"XXAuth errorXX"`.

Мутант выжил → тест не заметил поломки → тест бесполезен.

```bash
COMPOSE_PROFILES=testing docker compose run --rm backend-tester mutmut run
```

Смотрим выживших:
```bash
COMPOSE_PROFILES=testing docker compose run --rm backend-tester mutmut results | grep survived
```

Смотрим конкретного мутанта:
```bash
COMPOSE_PROFILES=testing docker compose run --rm backend-tester mutmut show main.x__verify_ownership__mutmut_10
```

Текущие метрики: 103 убито, 64 выжило (в основном logger/boilerplate).

## Сводка: что нельзя делать

- **Нельзя** использовать `unittest.mock` для мока сервисов — только `respx`
- **Нельзя** проверять только статус-код — проверяй `detail`, тип ошибки
- **Нельзя** хардкодить ID как числа — используй UUID-константы
- **Нельзя** писать тесты, которые не убьют мутанта — проверь `mutmut`
- **Нельзя** забывать про `auth_headers` на защищённых эндпоинтах
- **Нельзя** тестировать на «чистых» данных — добавляй Unicode, null, гигантские строки

## Запуск

```bash
# Все тесты
COMPOSE_PROFILES=testing docker compose run --rm backend-tester

# Конкретный файл
COMPOSE_PROFILES=testing docker compose run --rm backend-tester pytest tests/test_auth.py -v

# С coverage
COMPOSE_PROFILES=testing docker compose run --rm backend-tester pytest --cov=. --cov-report=term-missing tests/

# Мутационное тестирование
COMPOSE_PROFILES=testing docker compose run --rm backend-tester mutmut run
```

---

## Миграции БД (Alembic)

Alembic живёт в `packages/shared/`. Миграции запускаются **при старте сервиса** (intake-service, lawyer-service) через `run_migrations()`. Backend НЕ запускает миграции — там `create_db_and_tables()`.

### Структура

```
packages/shared/
  alembic.ini                              # script_location = yuriy_shared:alembic
  yuriy_shared/
    migration.py                           # run_migrations() — точка входа
    alembic/
      env.py                               # импортирует все модели SQLModel
      script.py.mako                       # шаблон новой миграции
      versions/
        0001_initial.py
        0002_add_case_type_title_summary.py
```

### Полный воркфлоу создания миграции

Выполни шаги **строго по порядку**:

**Шаг 1. Убедись, что shared-пакет установлен**
```bash
# С хоста (не Docker):
pip install -e packages/shared
# или (если venv активна):
pip install -e /app/packages/shared
```
Если `yuriy_shared` не установлен, `alembic` не найдёт `script_location`.

**Шаг 2. Проверь `env.py`**

Прочитай `packages/shared/yuriy_shared/alembic/env.py`.
**Если миграция затрагивает новую модель — добавь её импорт в `env.py`.**

Сейчас там импортированы:
```python
import yuriy_shared.models.lawyer
import yuriy_shared.models.user
import yuriy_shared.models.case
import yuriy_shared.models.message
```

Если добавил новую модель `yuriy_shared/models/foo.py` — добавь:
```python
import yuriy_shared.models.foo  # noqa: E402, F401
```
Без этого импорта `SQLModel.metadata` не увидит модель, и `--autogenerate` ничего не сгенерирует.

**Шаг 3. Сгенерируй миграцию**
```bash
cd packages/shared
alembic -c alembic.ini revision --autogenerate -m "add_field_x_to_table_y"
```
Эта команда:
- Сравнит `SQLModel.metadata` (из импортированных моделей) с текущей БД
- Создаст файл в `versions/` с автоматическими `upgrade()` и `downgrade()`

**Шаг 4. Проверь сгенерированный файл**

Прочитай созданный файл в `packages/shared/yuriy_shared/alembic/versions/`.
Проверь:
- `upgrade()` — правильные ли операции? Не удаляет ли лишнего?
- `downgrade()` — корректно ли откатывает?
- `down_revision` — правильный ли ID предыдущей миграции?
- Для ALTER TABLE (добавление/удаление колонок) — обёрнуто ли в `with op.batch_alter_table()`?
- Для SQLite `CREATE TABLE`/`DROP TABLE` — `batch_alter_table` **не нужен**, только для ALTER

**Шаг 5. Если autogenerate не угадал — исправь вручную**

Autogenerate может ошибиться. Типичные правки:
- Заменить `op.alter_column()` на `with op.batch_alter_table()`
- Добавить проверку `inspect()` для idempotency (см. 0002 как пример)
- Убрать лишние изменения (например, `sa.DateTime()` → `sa.DateTime(timezone=True)`)

**Шаг 6. Протестируй**
```bash
docker compose --profile testing run --rm backend-tester
```

Если тесты падают — исправь миграцию и повтори шаг 4-6.

### Правила

1. **Idempotency** — проверять существование колонок через `inspect()` (как в 0002). Миграция должна безопасно применяться повторно.
2. **SQLite-safe** — всегда `with op.batch_alter_table()` для ALTER TABLE. Без этого SQLite упадёт с ошибкой.
3. **Downgrade** — обязателен, тоже idempotent. Должен откатывать только то, что создал upgrade.
4. **Revises** — цепочка: `0001` → `0002` → `0003` → ... Каждая новая миграция ссылается на предыдущую.
5. **Не менять существующие миграции** — только новая revision. Если что-то не так в старой миграции — создай новую, которая это фиксит.
6. **Тестировать** — всегда запускать `docker compose --profile testing run --rm backend-tester` после создания миграции.

### Как применяются

`run_migrations(database_url)` в `migration.py`:

```python
# Логика:
# - есть alembic_version → upgrade head
# - есть таблицы без alembic_version → stamp head (легаси)
# - нет таблиц → upgrade head
```

Порядок в сервисах:
```python
create_db_and_tables()    # SQLModel metadata.create_all
run_migrations(DATABASE_URL)  # Alembic upgrade head
```

Такой порядок безопасен: `create_all` идемпотентен, `upgrade` применяет только новые миграции.

### Ручное управление (из Docker)

```bash
# Откатить последнюю
docker compose exec intake-agent alembic -c /app/packages/shared/alembic.ini downgrade -1

# Текущая версия
docker compose exec intake-agent alembic -c /app/packages/shared/alembic.ini current

# История
docker compose exec intake-agent alembic -c /app/packages/shared/alembic.ini history
```

**Важно:** `script_location = yuriy_shared:alembic` — package-relative, работает только при `pip install -e /app/packages/shared`. В Docker так и есть — `COPY packages/shared /app/packages/shared && pip install -e /app/packages/shared`.

### Чего нельзя

- **Не редактировать существующие миграции** — создавай новую
- **Не использовать `ALTER TABLE` без `batch_alter_table`** — упадёт на SQLite
- **Не забывать downgrade** — без него не откатить
- **Не удалять импорты из `env.py`** — без них autogenerate не увидит модели
- **Не менять `alembic_version` руками** — сломаешь цепочку revises
- **Не пропускать шаг 4** (проверку сгенерированного файла) — autogenerate часто ошибается
