import asyncio
import os
import requests
from aiogram import Bot, Dispatcher, types
from aiogram.filters import CommandStart
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from dotenv import load_dotenv

load_dotenv()

TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
API_URL = "http://localhost:8000"

if not TOKEN:
    print("Ошибка: TELEGRAM_BOT_TOKEN не установлен в .env")
    exit(1)

bot = Bot(token=TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
dp = Dispatcher()

# Временное хранилище активных дел пользователей
# В продакшене лучше использовать Redis или сохранять state в БД
active_cases = {}

@dp.message(CommandStart())
async def send_welcome(message: types.Message):
    # При команде /start сбрасываем текущее активное дело пользователя
    active_cases.pop(message.from_user.id, None)
    await message.answer(
        "Здравствуйте! Я ИИ-ассистент юриста.\n\n"
        "Опишите, пожалуйста, вашу юридическую проблему, и я помогу вам составить заявку для нашего специалиста."
    )

@dp.message()
async def handle_message(message: types.Message):
    user_id = message.from_user.id
    text = message.text

    payload = {
        "user_id": user_id,
        "message": text
    }
    
    # Если у пользователя уже есть активное дело в этой сессии, добавляем case_id
    if user_id in active_cases:
        payload["case_id"] = active_cases[user_id]

    try:
        # Отправляем сообщение на наш FastAPI бэкенд
        response = requests.post(f"{API_URL}/chat", json=payload)
        response.raise_for_status()
        data = response.json()
        
        # Сохраняем case_id для продолжения диалога
        active_cases[user_id] = data["case_id"]
        
        # Отправляем ответ ИИ пользователю
        await message.answer(data["response"])
        
        # Если статус изменился на 'ready', значит заявка сформирована
        if data["status"] == "ready":
            await message.answer("✅ <b>Ваша заявка успешно сформирована и передана юристу! Ожидайте ответа.</b>")
            # Сбрасываем case_id, чтобы следующее сообщение создало новую заявку
            active_cases.pop(user_id, None)

    except Exception as e:
        print(f"Error communicating with backend: {e}")
        await message.answer("Извините, произошла техническая ошибка при связи с сервером. Попробуйте позже.")

async def main():
    print("Запуск Telegram бота-приемщика...")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
