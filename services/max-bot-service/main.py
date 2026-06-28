import asyncio
import os

import aiohttp
from dotenv import load_dotenv
from maxapi import Bot, Dispatcher, F
from maxapi.filters.command import CommandStart
from maxapi.types import BotStarted, CallbackButton, MessageCallback, MessageCreated
from maxapi.utils.inline_keyboard import InlineKeyboardBuilder

from core.logger import logger

load_dotenv()

TOKEN = os.getenv("MAX_BOT_TOKEN")
API_URL = os.getenv("API_URL", "http://intake-agent:8001")

if not TOKEN:
    logger.critical("MAX_BOT_TOKEN not found in .env")
    pass

bot = Bot(token=TOKEN) if TOKEN else None
dp = Dispatcher()

# Временное хранилище активных дел пользователей
active_cases = {}


@dp.bot_started()
async def bot_started(event: BotStarted):
    logger.info("Bot started for a user")
    await bot.send_message(
        chat_id=event.chat_id,
        text="Здравствуйте! Я ИИ-ассистент юриста.\n\n"
        "Опишите, пожалуйста, вашу юридическую проблему, и я помогу вам составить заявку для нашего специалиста.",
    )


@dp.message_created(CommandStart())
async def send_welcome(event: MessageCreated):
    user_id = event.from_user.user_id
    logger.info(f"Command /start received from user_id={user_id}")
    active_cases.pop(user_id, None)
    await event.message.answer(
        "Здравствуйте! Я ИИ-ассистент юриста.\n\n"
        "Опишите, пожалуйста, вашу юридическую проблему, и я помогу вам составить заявку для нашего специалиста."
    )


@dp.message_callback(F.callback.payload.startswith("confirm_"))
async def process_confirm(event: MessageCallback):
    payload_data = event.callback.payload
    case_id = int(payload_data.split("_")[1])
    user_id = event.from_user.user_id
    logger.info(f"Confirmation callback for case_id={case_id} from user_id={user_id}")

    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(f"{API_URL}/confirm", json={"case_id": case_id}) as response:
                response.raise_for_status()
                logger.info(f"Case {case_id} confirmed in Intake Service")

        # В maxapi answer() может обновлять текст сообщения
        await event.answer(new_text="✅ <b>Ваша заявка успешно сформирована и передана юристу! Ожидайте ответа.</b>")
        active_cases.pop(user_id, None)

    except Exception as e:
        logger.error(f"Error confirming case {case_id}: {e}")
        # Здесь мы можем попробовать отправить просто ответ, если answer(new_text) не подходит для уведомлений
        await event.answer(new_text="Ошибка при подтверждении.")


@dp.message_created()
async def handle_message(event: MessageCreated):
    if not event.message.body.text or event.message.body.text.startswith("/"):
        return

    user_id = event.from_user.user_id
    text = event.message.body.text
    logger.info(f"Message from MAX user_id={user_id}: {text[:50]}...")

    payload = {"external_id": str(user_id), "source": "max", "message": text}
    if user_id in active_cases:
        payload["case_id"] = active_cases[user_id]

    try:
        async with aiohttp.ClientSession() as session:
            logger.info(f"Sending request to Intake Service for user_id={user_id}")
            async with session.post(f"{API_URL}/chat", json=payload) as response:
                response.raise_for_status()
                data = await response.json()

        active_cases[user_id] = data["case_id"]
        ai_response = data["response"]
        is_ready = data.get("is_ready")

        logger.info(f"AI response received. is_ready={is_ready}")

        if is_ready:
            builder = InlineKeyboardBuilder()
            builder.row(CallbackButton(text="🚀 Подтвердить отправку", payload=f"confirm_{data['case_id']}"))
            await event.message.answer(text=ai_response, attachments=[builder.as_markup()])
        else:
            await event.message.answer(ai_response)

    except Exception as e:
        logger.error(f"Error communicating with Intake Service: {e}")
        await event.message.answer("Извините, произошла техническая ошибка.")


async def main():
    if not bot:
        logger.error("MAX_BOT_TOKEN is missing. Bot will not start.")
        return
    logger.info("MAX Bot service starting...")
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
