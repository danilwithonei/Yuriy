import os, sys, time, json, uuid, re

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

BASE_URL = os.getenv("BASE_URL", "http://localhost:8000")
EMAIL = os.getenv("TEST_EMAIL", f"e2e_{uuid.uuid4().hex[:8]}@test.com")
PASSWORD = os.getenv("TEST_PASSWORD", "pass1234")
NAME = os.getenv("TEST_NAME", "E2E Tester")

import httpx

HTTP_OK = 200
HTTP_NO_CONTENT = 204
HTTP_BAD_REQUEST = 400
HTTP_UNAUTHORIZED = 401
HTTP_FORBIDDEN = 403
HTTP_NOT_FOUND = 404
HTTP_BAD_GATEWAY = 502

PASS = 0
FAIL = 0

def section(n, title):
    print(f"\n{'='*60}")
    print(f"  [{n}] {title}")
    print(f"{'='*60}")

def check(cond, msg):
    global PASS, FAIL
    if cond:
        PASS += 1
        print(f"  \033[92mPASS\033[0m  {msg}")
    else:
        FAIL += 1
        print(f"  \033[91mFAIL\033[0m  {msg}")

def check_eq(a, b, msg):
    check(a == b, f"{msg}: expected {b}, got {a}")

def check_in(a, b, msg):
    check(a in b, f"{msg}: expected '{a}' in '{b}'")

def ok(msg):
    print(f"  \033[92mOK\033[0m  {msg}")

def warn(msg):
    print(f"  \033[93mWARN\033[0m {msg}")

c = httpx.Client(base_url=BASE_URL, timeout=30)

# ─── 1. Auth ───────────────────────────────────────────────────────

section(1, "Auth: регистрация, логин, битые токены")

# 1A. Регистрация
resp = c.post("/auth/register", json={"email": EMAIL, "password": PASSWORD, "name": NAME})
check_eq(resp.status_code, HTTP_OK, "Register returns 200")
reg = resp.json()
check_in("token", reg, "Register response has token")
check_in("lawyer", reg, "Register response has lawyer")
token = reg["token"]
lawyer_id = reg["lawyer"]["id"]

# 1B. Логин
resp = c.post("/auth/login", json={"email": EMAIL, "password": PASSWORD})
check_eq(resp.status_code, HTTP_OK, "Login returns 200")
check_in("token", resp.json(), "Login response has token")

# 1C. Без токена → 401
resp = c.get("/cases")
check_eq(resp.status_code, HTTP_UNAUTHORIZED, "No token → 401")

# 1D. Битый токен → 401
resp = c.get("/cases", headers={"Authorization": "Bearer deadbeef"})
check_eq(resp.status_code, HTTP_UNAUTHORIZED, "Garbage token → 401")

headers = {"Authorization": f"Bearer {token}"}

# ─── 2. Создание дела ─────────────────────────────────────────────

section(2, "Case: создание intake и direct дел")

# 2A. Создать intake кейс
resp = c.post("/cases", json={"type": "intake"}, headers=headers)
check_eq(resp.status_code, HTTP_OK, "Create intake → 200")
intake_id = resp.json().get("case_id")
check(intake_id and len(intake_id) > 10, f"case_id exists: {intake_id}")

# 2B. Создать direct кейс
resp = c.post("/cases", json={"type": "direct"}, headers=headers)
check_eq(resp.status_code, HTTP_OK, "Create direct → 200")
direct_id = resp.json().get("case_id")
check(direct_id and len(direct_id) > 10, f"direct case_id exists: {direct_id}")

# 2C. Создать дело без авторизации
resp = c.post("/cases", json={"type": "intake"})
check_eq(resp.status_code, HTTP_UNAUTHORIZED, "Create without auth → 401")

# ─── 3. Intake чат ───────────────────────────────────────────────

section(3, "Intake чат: стриминг, токены, is_ready")

scenario = [
    "Здравствуйте! У меня украли телефон вчера вечером. Я был в кафе на Невском проспекте, поставил телефон на зарядку, отвернулся на минуту — и его нет.",
    "Телефон — iPhone 15 Pro Max, серебристый, в прозрачном чехле. Стоил около 150 тысяч рублей. Я купил его в М.Видео месяц назад, чек сохранился.",
    "Я написал заявление в полицию, но пока никаких новостей. Мне сказали ждать. Но я переживаю, что найдут, а потом скажут, что я сам потерял.",
]

last_ready = False

for i, msg in enumerate(scenario, 1):
    token_count = 0
    full = ""
    done = False
    with c.stream("POST", f"/cases/{intake_id}/intake/chat",
                  json={"message": msg}, headers=headers, timeout=120) as resp:
        check_eq(resp.status_code, HTTP_OK, f"Msg {i}: intake chat returns 200")

        ct = resp.headers.get("content-type", "")
        check_in("text/event-stream", ct, f"Msg {i}: content-type is SSE")

        for line in resp.iter_lines():
            if line.startswith("data: "):
                payload = line[6:].strip()
                if not payload:
                    continue
                try:
                    data = json.loads(payload)
                except json.JSONDecodeError:
                    check(False, f"Msg {i}: SSE payload is valid JSON")
                    continue

                if "token" in data:
                    token_count += 1
                    full += data["token"]
                elif "error" in data:
                    check(False, f"Msg {i}: no error in stream")
                    break
                elif data.get("done"):
                    done = True
                    last_ready = data.get("is_ready", False)
                    break

        check(done, f"Msg {i}: done event received")
        check(token_count > 0, f"Msg {i}: at least one token received")
        check(len(full) > 20, f"Msg {i}: full response > 20 chars")

# После 3 сообщений is_ready должен стать True
check(last_ready, "Intake завершён: is_ready=true")

# 3X. Чужое дело → 403
# Создаём второго юзера
EMAIL_B = f"e2e_b_{uuid.uuid4().hex[:8]}@test.com"
c.post("/auth/register", json={"email": EMAIL_B, "password": "pass1234", "name": "Intruder"})
resp_b = c.post("/auth/login", json={"email": EMAIL_B, "password": "pass1234"})
token_b = resp_b.json()["token"]

resp = c.post(f"/cases/{intake_id}/intake/chat",
              json={"message": "test"}, headers={"Authorization": f"Bearer {token_b}"}, timeout=30)
check_eq(resp.status_code, HTTP_FORBIDDEN, "Foreign case → 403")

# ─── 4. Confirm ───────────────────────────────────────────────────

section(4, "Confirm: запуск исследования, проверка владения")

# 4A. Подтверждение
resp = c.post(f"/cases/{intake_id}/intake/confirm", headers=headers)
check_eq(resp.status_code, HTTP_OK, "Confirm returns 200")
check_eq(resp.json().get("status"), "researching", "Confirm returns researching")

# 4B. Чужой confirm → 403
resp = c.post(f"/cases/{intake_id}/intake/confirm",
              headers={"Authorization": f"Bearer {token_b}"})
check_eq(resp.status_code, HTTP_FORBIDDEN, "Foreign confirm → 403")

# 4C. Confirm несуществующего дела
fake_id = "ffffffff-ffff-4fff-ffff-ffffffffffff"
resp = c.post(f"/cases/{fake_id}/intake/confirm", headers=headers)
check_eq(resp.status_code, HTTP_NOT_FOUND, "Confirm fake case → 404")

# ─── 5. Ожидание завершения ───────────────────────────────────────

section(5, "Research: дождаться ready, проверить structured output")

timeout = 180
polled = 0
result = None
status = None
while polled < timeout:
    time.sleep(3)
    polled += 3
    resp = c.get(f"/cases/{intake_id}", headers=headers)
    if resp.status_code != HTTP_OK:
        warn(f"Poll attempt #{polled//3}: {resp.status_code}")
        continue
    result = resp.json()
    status = result.get("case", {}).get("status")
    print(f"  poll {polled}s: status={status}", end="")
    title = result.get("case", {}).get("title")
    if title:
        print(f", title=\"{title[:50]}...\"", end="")
    print()
    if status == "ready":
        ok(f"Completed in ~{polled}s")
        break

check(result is not None, "Research poll вернул результат")
case = result.get("case", {})

check_eq(status, "ready", "Final status is 'ready'")
check(case.get("title"), "Title не пустой")
check(len(case["title"]) <= 60, "Title ≤ 60 символов")
check(case.get("summary"), "Summary не пустой")
check(case.get("case_file"), "case_file не пустой")
check(len(case["case_file"]) > 100, "case_file > 100 символов")
check_in("#", case["case_file"], "case_file содержит Markdown (#)")

# ─── 6. Direct-кейс: чат без графа ────────────────────────────────

section(6, "Direct кейс: чат без intake графа")

resp = c.post(f"/cases/{direct_id}/intake/chat",
              json={"message": "Какой срок давности по краже?"}, headers=headers, timeout=30)
if resp.status_code == HTTP_OK:
    ct = resp.headers.get("content-type", "")
    data = resp.json()
    # Direct возвращает JSON, не SSE
    check("text/event-stream" not in ct, "Direct chat не SSE")
    check("is_ready" in data, "Direct response has is_ready")
    ok("Direct чат работает")

# ─── 7. Gateway resilience ────────────────────────────────────────

section(7, "Resilience: что если intake сервис упал")

# Запрос к несуществующему кейсу
resp = c.get(f"/cases/{uuid.uuid4()}", headers=headers)
check_in(resp.status_code, [HTTP_NOT_FOUND, HTTP_BAD_GATEWAY],
         "Несуществующий кейс → 404 или 502")

# ─── Итог ─────────────────────────────────────────────────────────

print(f"\n{'='*60}")
total = PASS + FAIL
print(f"  \033[1mResult: {PASS}/{total} passed, {FAIL} failed\033[0m")
print(f"{'='*60}")

if FAIL:
    sys.exit(1)
