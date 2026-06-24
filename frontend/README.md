# Yuriy Frontend — Личный кабинет юриста

Next.js 16 (App Router) + React 19 + Tailwind CSS v4.

## Стек

- **Next.js 16**, Turbopack (dev)
- **React 19**, `react-markdown` + `remark-gfm`
- **Zustand** — состояние (useAuthStore, useCaseStore)
- **axios** — HTTP с Bearer-перехватчиком
- **Base UI** — компоненты
- **Tailwind CSS v4**, `tailwind-merge`, `class-variance-authority`
- **lucide-react** — иконки

## Структура

```
app/
  login/page.tsx       # Вход (email + password)
  register/page.tsx    # Регистрация
  cases/
    [id]/page.tsx      # Детали дела, чат с ассистентом
components/
  AppSidebar.tsx       # Боковая панель (аватар, имя, выход)
  LayoutShell.tsx      # Общий лэйаут + AuthGuard
  WebSocketProvider.tsx
hooks/
  useCaseChat.ts       # WebSocket чат с ?token=
lib/
  api.ts               # axios инстанс, динамический API URL
store/
  useAuthStore.ts      # Токен, user, login/logout
  useCaseStore.ts      # Список дел, активное дело, WebSocket
```

## API URL

Динамический: `http://<hostname>:8000` из `window.location.hostname` — работает в локальной сети без указания `NEXT_PUBLIC_API_URL`.

## Аутентификация

1. Регистрация `/auth/register` → получает JWT
2. Логин `/auth/login` → получает JWT
3. Токен хранится в Zustand + localStorage
4. axios-перехватчик добавляет `Authorization: Bearer <token>`
5. `AuthGuard` в `LayoutShell` — редирект на `/login` при отсутствии токена
6. WebSocket: `?token=<jwt>` в query params

## Разработка

```bash
npm run dev        # Turbopack на :3000
npm run build      # Продакшен-сборка
npm run lint       # ESLint
```

## Структурные решения

- `allowedDevOrigins: ['bob-rpc-node']` в `next.config.ts` (для разработки на удалённой машине)
- Все ID дел — строки (UUIDv4), не числа
- При 403 (чужое дело) — экран «Нет доступа» внутри LayoutShell
- Поллинг удалён; обновления через WebSocket (CASE_STATUS_UPDATED)
