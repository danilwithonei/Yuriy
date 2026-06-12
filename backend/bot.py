import asyncio
import os
import aiohttp
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import CommandStart
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.utils.chat_action import ChatActionSender
from dotenv import load_dotenv

load_dotenv()

TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
API_URL = os.getenv("API_URL", "http://localhost:8000")

if not TOKEN:
    print("Ошибка: TELEGRAM_BOT_TOKEN не установлен в .env")
    exit(1)

bot = Bot(token=TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
dp = Dispatcher()

# Временное хранилище активных дел пользователей
active_cases = {}

@dp.message(CommandStart())
async def send_welcome(message: types.Message):
    active_cases.pop(message.from_user.id, None)
    await message.answer(
        "Здравствуйте! Я ИИ-ассистент юриста.\n\n"
        "Опишите, пожалуйста, вашу юридическую проблему, и я помогу вам составить заявку для нашего специалиста."
    )

@dp.callback_query(F.data.startswith("confirm_"))
async def process_confirm(callback: types.CallbackQuery):
    case_id = int(callback.data.split("_")[1])
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(f"{API_URL}/confirm", json={"case_id": case_id}) as response:
                response.raise_for_status()
        
        await callback.message.edit_reply_markup(reply_markup=None) # Убираем кнопку
        await callback.message.answer("✅ <b>Ваша заявка успешно сформирована и передана юристу! Ожидайте ответа.</b>")
        active_cases.pop(callback.from_user.id, None)
        await callback.answer()

    except Exception as e:
        print(f"Error confirming case: {e}")
        await callback.answer("Ошибка при подтверждении.", show_alert=True)

@dp.message()
async def handle_message(message: types.Message):
    user_id = message.from_user.id
    text = message.text

    payload = {"user_id": user_id, "message": text}
    if user_id in active_cases:
        payload["case_id"] = active_cases[user_id]

    try:
        async with ChatActionSender.typing(bot=bot, chat_id=message.chat.id):
            async with aiohttp.ClientSession() as session:
                async with session.post(f"{API_URL}/chat", json=payload) as response:
                    response.raise_for_status()
                    data = await response.json()
        
        active_cases[user_id] = data["case_id"]
        
        ai_response = data["response"]
        
        # Если в ответе ИИ есть призыв к подтверждению, добавляем кнопку
        if "подтвердить отправку" in ai_response.lower():
            builder = InlineKeyboardBuilder()
            builder.row(types.InlineKeyboardButton(
                text="🚀 Подтвердить отправку", 
                callback_data=f"confirm_{data['case_id']}")
            )
            await message.answer(ai_response, reply_markup=builder.as_markup())
        else:
            await message.answer(ai_response)

    except Exception as e:
        print(f"Error communicating with backend: {e}")
        await message.answer("Извините, произошла техническая ошибка.")

async def main():
    print("Запуск Telegram бота-приемщика...")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
