# Yuriy — ИИ-Юрист (AI Lawyer)

Интеллектуальная система для автоматизации юридического приема и первичного анализа дел. Система опрашивает клиента, проводит автономное исследование законодательства и формирует подробное досье для юриста.

## 🚀 Основные возможности

*   **ИИ-Интервьюер:** Автоматизированный сбор информации о проблеме клиента в формате диалога.
*   **Автономное исследование:** Интеграция с Tavily Search для поиска актуальных законов и прецедентов в реальном времени.
*   **Генерация досье:** Автоматическое составление структурированного Markdown-отчета по делу.
*   **Панель юриста:** Удобный интерфейс на Next.js для управления заявками.
*   **ИИ-Ассистент по делу:** Специализированный чат для юриста, позволяющий задавать вопросы по конкретному делу на основе собранных данных.

## 🛠 Технологический стек

*   **Backend:** Python 3.10+, FastAPI, LangGraph, LangChain, SQLModel (SQLite/PostgreSQL).
*   **LLM:** Qwen (через Aliyun DashScope MaaS).
*   **Frontend:** React, Next.js, TailwindCSS, Lucide Icons.
*   **Search API:** Tavily.

## 📋 Подготовка к запуску

### 1. Клонирование репозитория
```bash
git clone https://github.com/danilwithonei/Yuriy.git
cd Yuriy
```

### 2. Настройка Бэкенда
```bash
cd backend
python -m venv venv
source venv/bin/activate  # Для Windows: .\venv\Scripts\activate
pip install -r requirements.txt
```
*Примечание: Если `requirements.txt` отсутствует, используйте: `pip install fastapi uvicorn langgraph langchain-openai sqlalchemy sqlmodel tavily-python python-dotenv langchain-community dashscope`*

Создайте файл `.env` в папке `backend`:
```env
DASHSCOPE_API_KEY=ваш_ключ_qwen
LLM_MODEL=qwen3.7-plus
TAVILY_API_KEY=ваш_ключ_tavily
```

### 3. Настройка Фронтенда
```bash
cd ../frontend
npm install
```

## 🏃 Запуск приложения

### Запуск Бэкенда
```bash
cd backend
python main.py
```
Сервер будет доступен по адресу: `http://localhost:8000`

### Запуск Фронтенда
```bash
cd frontend
npm run dev
```
Интерфейс будет доступен по адресу: `http://localhost:3000`

## 🧪 Тестирование
Для симуляции подачи заявки клиентом вы можете использовать скрипт:
```bash
python test_app.py
```

## 🔒 Безопасность
Все секретные ключи и база данных исключены из репозитория через `.gitignore`. Никогда не коммитьте файл `.env`!

---
Разработано для автоматизации и повышения эффективности юридической практики.
