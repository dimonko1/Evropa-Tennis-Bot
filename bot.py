import logging
import asyncio
import os
import psycopg2
from psycopg2.extras import DictCursor
from aiogram import Bot, Dispatcher, types
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton
from aiogram.utils.executor import start_webhook
from datetime import datetime

TOKEN = os.getenv("8092903063:AAEUSIAh3DVRs5-sRwih9rZvSUiXKwKT1fY")
DATABASE_URL = os.getenv("postgresql://evropa_tennis_bot_user:diqEKRwZ4LPfWOWvRijYkR7LbCUXS7xN@dpg-cv0b601u0jms73fbpr9g-a/evropa_tennis_bot")
WEBHOOK_HOST = os.getenv("https://evropa-tennis-bot.onrender.com")
WEBHOOK_PATH = f"/webhook/{TOKEN}"
WEBHOOK_URL = f"{WEBHOOK_HOST}{WEBHOOK_PATH}"
WEBAPP_HOST = "0.0.0.0"
WEBAPP_PORT = int(os.getenv("PORT", 10000))

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

# Клавиатура с выбором времени
keyboard = ReplyKeyboardMarkup(resize_keyboard=True)
timeslots = ["08:00–09:00", "09:00–10:00", "10:00–11:00", "11:00–12:00"]
for slot in timeslots:
    keyboard.add(KeyboardButton(slot))

@dp.message_handler(commands=["start"])
async def start(message: types.Message):
    await message.answer("Привет! Выберите время для бронирования:", reply_markup=keyboard)

# Проверка наличия брони
def check_booking(slot, date):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM bookings WHERE slot = %s AND date = %s", (slot, date))
    booking = cursor.fetchone()
    conn.close()
    return booking

# Добавление брони
def add_booking(user_id, user_name, slot, date):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("INSERT INTO bookings (user_id, user_name, slot, date) VALUES (%s, %s, %s, %s)",
                   (user_id, user_name, slot, date))
    conn.commit()
    conn.close()

# Удаление брони
def remove_booking(user_id, slot, date):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM bookings WHERE user_id = %s AND slot = %s AND date = %s",
                   (user_id, slot, date))
    conn.commit()
    conn.close()

@dp.message_handler(lambda message: message.text in timeslots)
async def book_time(message: types.Message):
    slot = message.text
    user_id = message.from_user.id
    user_name = message.from_user.full_name
    date = datetime.now().strftime('%Y-%m-%d')
    
    if check_booking(slot, date):
        await message.answer(f"Время {slot} уже занято. Выберите другое.", reply_markup=keyboard)
    else:
        add_booking(user_id, user_name, slot, date)
        await message.answer(f"Вы забронировали {slot}. Спасибо!", reply_markup=keyboard)

@dp.message_handler(commands=["cancel"])
async def cancel_booking(message: types.Message):
    user_id = message.from_user.id
    date = datetime.now().strftime('%Y-%m-%d')
    remove_booking(user_id, message.text, date)
    await message.answer("Ваша бронь отменена.")

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
