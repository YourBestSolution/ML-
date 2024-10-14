import json
import logging
from aiogram import Bot, Dispatcher, types
from aiogram.utils import executor
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton
from gpt_service import get_response, post_process_response, load_data_from_file, initialize_embedding_collection

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Отключение отладочных сообщений
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("chromadb.telemetry.product.posthog").setLevel(logging.WARNING)
logging.getLogger("aiogram").setLevel(logging.ERROR)
logging.getLogger("aiogram.dispatcher.dispatcher").setLevel(logging.ERROR)

with open('config.json', 'r') as config_file:
    config = json.load(config_file)

TELEGRAM_API_TOKEN = config['TELEGRAM_API_TOKEN']
GREETINGS = ["привет", "здравствуйте", "ку"]
CONTINUATION_PHRASES = ["есть еще информация", "продолжи", "дальше", "еще", "ещё"]

is_active = True

bot = Bot(token=TELEGRAM_API_TOKEN)
dp = Dispatcher(bot)

# Создание клавиатуры
keyboard = ReplyKeyboardMarkup(resize_keyboard=True)
keyboard.add(KeyboardButton("/start"), KeyboardButton("/stop"), KeyboardButton("/help"))


class BotHandler:
    def __init__(self):
        self.is_active = True
        self.last_query = None
        data = load_data_from_file('data.pkl')
        self.embeddings = data["embeddings"]
        initialize_embedding_collection(self.embeddings)

    async def send_welcome(self, message: types.Message):
        self.is_active = True
        await message.reply('Бот активирован. Напиши мне что-нибудь :)', reply_markup=keyboard)

    async def stop_bot(self, message: types.Message):
        self.is_active = False
        await message.reply('Бот деактивирован. Я больше не буду отвечать на сообщения.', reply_markup=keyboard)

    async def send_help(self, message: types.Message):
        help_text = (
            "Доступные команды:\n"
            "/start - Активировать бота\n"
            "/stop - Деактивировать бота\n"
            "/help - Показать это сообщение\n"
            "/status - Проверить статус бота\n"
        )
        await message.reply(help_text, reply_markup=keyboard)

    async def send_status(self, message: types.Message):
        status = "активен" if self.is_active else "неактивен"
        await message.reply(f"Бот сейчас {status}.", reply_markup=keyboard)

    async def handle_text(self, message: types.Message):
        if not self.is_active:
            return

        user_input = message.text.lower().strip()

        if user_input in GREETINGS:
            await message.reply("Привет! Чем могу помочь? Задавайте ваши вопросы.")
            return

        if user_input in CONTINUATION_PHRASES and self.last_query:
            user_input = self.last_query
            continuation_request = True
        else:
            continuation_request = False

        history = []

        history.append({"role": "user", "content": user_input})

        combined_response = await get_response(user_input)

        if combined_response != "Данная информация вне моей компетенции.":
            searching_message = await message.reply("Я уже ищу ответ на твой вопрос...")
            history.append({"role": "assistant", "content": combined_response})
            response = await post_process_response(history)

            if response != "Данная информация вне моей компетенции.":
                history.append({"role": "assistant", "content": response})
                await bot.edit_message_text(chat_id=searching_message.chat.id, message_id=searching_message.message_id, text=response)
                self.last_query = user_input if not continuation_request else self.last_query
            else:
                await bot.edit_message_text(chat_id=searching_message.chat.id, message_id=searching_message.message_id, text="Дополнительная информация отсутствует.")
        else:
            response = combined_response
            history.append({"role": "assistant", "content": response})
            await message.answer(response)

bot_handler = BotHandler()

@dp.message_handler(commands=['start'])
async def send_welcome(message: types.Message):
    await bot_handler.send_welcome(message)

@dp.message_handler(commands=['stop'])
async def stop_bot(message: types.Message):
    await bot_handler.stop_bot(message)

@dp.message_handler(commands=['help'])
async def send_help(message: types.Message):
    await bot_handler.send_help(message)

@dp.message_handler(commands=['status'])
async def send_status(message: types.Message):
    await bot_handler.send_status(message)

@dp.message_handler(content_types=['text'])
async def handle_text(message: types.Message):
    await bot_handler.handle_text(message)

if __name__ == "__main__":
    try:
        logger.info("Запуск бота...")
        executor.start_polling(dp, skip_updates=True)
    except KeyboardInterrupt:
        logger.info("Бот деактивирован...")
        exit()