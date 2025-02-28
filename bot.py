import logging
import asyncio
import os
import psycopg2
from psycopg2.extras import DictCursor
from aiogram import Bot, Dispatcher, types
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.executor import start_webhook
from datetime import datetime, timedelta

TOKEN = "8092903063:AAEUSIAh3DVRs5-sRwih9rZvSUiXKwKT1fY"
DATABASE_URL = "postgresql://evropa_tennis_bot_user:diqEKRwZ4LPfWOWvRijYkR7LbCUXS7xN@dpg-cv0b601u0jms73fbpr9g-a/evropa_tennis_bot"
WEBHOOK_HOST = "https://evropa-tennis-bot.onrender.com"
WEBHOOK_PATH = f"/webhook/{TOKEN}"
WEBHOOK_URL = f"{WEBHOOK_HOST}{WEBHOOK_PATH}"
WEBAPP_HOST = "0.0.0.0"
WEBAPP_PORT = 10000#int(os.getenv("PORT", 10000))

bot = Bot(token=TOKEN)
dp = Dispatcher(bot)

# Подключение к PostgreSQL
def get_db_connection():
    return psycopg2.connect(DATABASE_URL, sslmode='require', cursor_factory=DictCursor)

# Создание таблицы, если её нет
def init_db():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS bookings (
            id SERIAL PRIMARY KEY,
            user_id BIGINT,
            user_name TEXT,
            slot TEXT,
            date DATE
        )
    ''')
    conn.commit()
    conn.close()

# Клавиатура для выбора даты на 30 дней вперёд
def get_date_keyboard():
    keyboard = InlineKeyboardMarkup(row_width=7)
    today = datetime.now()
    for i in range(30):
        date = today + timedelta(days=i)
        date_str = date.strftime('%Y-%m-%d')
        button = InlineKeyboardButton(date.strftime('%d-%m'), callback_data=f"select_date_{date_str}")
        keyboard.add(button)
    return keyboard

# Клавиатура для выбора времени
def get_time_keyboard():
    keyboard = ReplyKeyboardMarkup(resize_keyboard=True)
    timeslots = ["08:00–09:00", "09:00–10:00", "10:00–11:00", "11:00–12:00"]
    for slot in timeslots:
        keyboard.add(KeyboardButton(slot))
    return keyboard

# Словарь для хранения данных о бронированиях пользователя
user_booking_data = {}

@dp.message_handler(commands=["start"])
async def start(message: types.Message):
    await message.answer("Выберите дату для бронирования:", reply_markup=get_date_keyboard())

@dp.callback_query_handler(lambda c: c.data.startswith("select_date_"))
async def choose_date(callback_query: types.CallbackQuery):
    selected_date = callback_query.data.split("_")[2]
    user_id = callback_query.from_user.id
    user_name = callback_query.from_user.full_name
    user_booking_data[user_id] = {"date": selected_date}
    
    await bot.answer_callback_query(callback_query.id, text=f"Вы выбрали {selected_date}. Теперь выберите время:")
    await bot.send_message(callback_query.from_user.id, "Теперь выберите время:", reply_markup=get_time_keyboard())

@dp.message_handler(lambda message: message.text in ["08:00–09:00", "09:00–10:00", "10:00–11:00", "11:00–12:00"])
async def book_time(message: types.Message):
    user_id = message.from_user.id
    user_name = message.from_user.full_name
    if user_id not in user_booking_data or "date" not in user_booking_data[user_id]:
        await message.answer("Пожалуйста, выберите сначала дату.")
        return

    date = user_booking_data[user_id]["date"]
    slot = message.text
    
    if check_booking(slot, date):
        await message.answer(f"Время {slot} на {date} уже занято. Выберите другое.", reply_markup=get_time_keyboard())
    else:
        add_booking(user_id, user_name, slot, date)
        await message.answer(f"Вы забронировали {slot} на {date}. Спасибо!")

@dp.message_handler(commands=["cancel"])
async def cancel_booking(message: types.Message):
    user_id = message.from_user.id
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM bookings WHERE user_id = %s RETURNING slot, date", (user_id,))
    deleted = cursor.fetchall()
    conn.commit()
    conn.close()
    
    if deleted:
        await message.answer(f"Вы отменили бронь на: {', '.join([f'{d[1]} {d[0]}' for d in deleted])}")
    else:
        await message.answer("У вас нет активных броней.")

@dp.message_handler(commands=["mybookings"])
async def my_bookings(message: types.Message):
    user_id = message.from_user.id
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT date, slot FROM bookings WHERE user_id = %s", (user_id,))
    bookings = cursor.fetchall()
    conn.close()
    
    if bookings:
        await message.answer("Ваши бронирования:\n" + "\n".join([f"{b[0]} {b[1]}" for b in bookings]))
    else:
        await message.answer("У вас нет активных броней.")

async def on_startup(dp):
    logging.basicConfig(level=logging.INFO)
    init_db()
    await bot.set_webhook(WEBHOOK_URL)

async def on_shutdown(dp):
    await bot.delete_webhook()

if __name__ == "__main__":
    from aiogram import executor
    executor.start_webhook(
        dispatcher=dp,
        webhook_path=WEBHOOK_PATH,
        on_startup=on_startup,
        on_shutdown=on_shutdown,
        host=WEBAPP_HOST,
        port=WEBAPP_PORT
    )
