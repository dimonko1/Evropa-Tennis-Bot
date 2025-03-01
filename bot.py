import logging
import asyncio
import os
import psycopg2
from psycopg2.extras import DictCursor
from aiogram import Bot, Dispatcher, types
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton
from aiogram.utils.executor import start_webhook
from datetime import datetime, timedelta

TOKEN = "8092903063:AAHGdwmtY_4EYG797u5DlLrecFEE2_QabeA"
DATABASE_URL = "postgresql://evropa_tennis_bot_user:diqEKRwZ4LPfWOWvRijYkR7LbCUXS7xN@dpg-cv0b601u0jms73fbpr9g-a/evropa_tennis_bot"
WEBHOOK_HOST = "https://evropa-tennis-bot.onrender.com"
WEBHOOK_PATH = f"/webhook/{TOKEN}"
WEBHOOK_URL = f"{WEBHOOK_HOST}{WEBHOOK_PATH}"
WEBAPP_HOST = "0.0.0.0"
WEBAPP_PORT = int(os.getenv("PORT", 8080))

bot = Bot(token=TOKEN)
dp = Dispatcher(bot)

def get_db_connection():
    return psycopg2.connect(DATABASE_URL, sslmode='require', cursor_factory=DictCursor)

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

def main_menu():
    keyboard = ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    keyboard.add(
        KeyboardButton("📅 Новая бронь"),
        KeyboardButton("❌ Отменить бронь"),
        KeyboardButton("📋 Мои бронирования"),
        KeyboardButton("🔍 Посмотреть все бронирования")
    )
    return keyboard

def get_date_keyboard():
    keyboard = ReplyKeyboardMarkup(resize_keyboard=True, row_width=7)
    days = [datetime.now() + timedelta(days=i) for i in range(31)]
    buttons = [KeyboardButton(day.strftime('%Y-%m-%d, %a')) for day in days]
    keyboard.add(*buttons, KeyboardButton("🔙 Назад"))
    return keyboard

def get_time_keyboard():
    keyboard = ReplyKeyboardMarkup(resize_keyboard=True, row_width=4)
    timeslots = [f"{hour}:00–{hour+1}:00" for hour in range(7, 21)]
    keyboard.add(*[KeyboardButton(slot) for slot in timeslots], KeyboardButton("🔙 Назад"))
    return keyboard

user_booking_data = {}

@dp.message_handler(commands=["start"])
async def start(message: types.Message):
    await message.answer("Выберите действие:", reply_markup=main_menu())

@dp.message_handler(lambda message: message.text == "📅 Новая бронь")
async def new_booking(message: types.Message):
    await message.answer("Выберите дату для бронирования:", reply_markup=get_date_keyboard())

@dp.message_handler(lambda message: message.text == "🔙 Назад")
async def go_back(message: types.Message):
    await message.answer("Главное меню:", reply_markup=main_menu())

@dp.message_handler(lambda message: message.text.startswith("2025"))
async def choose_date(message: types.Message):
    user_booking_data[message.from_user.id] = {"date": message.text.split(",")[0]}
    await message.answer("Теперь выберите время:", reply_markup=get_time_keyboard())

@dp.message_handler(lambda message: message.text in [f"{hour}:00–{hour+1}:00" for hour in range(7, 21)])
async def book_time(message: types.Message):
    user_id = message.from_user.id
    user_name = message.from_user.full_name
    date = user_booking_data.get(user_id, {}).get("date")
    slot = message.text
    if date is None:
        await message.answer("Сначала выберите дату!", reply_markup=get_date_keyboard())
        return
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM bookings WHERE slot = %s AND date = %s", (slot, date))
    if cursor.fetchone()[0] > 0:
        await message.answer(f"Время {slot} на {date} уже занято. Выберите другое.", reply_markup=get_time_keyboard())
    else:
        cursor.execute("INSERT INTO bookings (user_id, user_name, slot, date) VALUES (%s, %s, %s, %s)", (user_id, user_name, slot, date))
        conn.commit()
        await message.answer(f"Вы забронировали {slot} на {date}.", reply_markup=main_menu())
    conn.close()
    user_booking_data.pop(user_id, None)

@dp.message_handler(lambda message: message.text == "📋 Мои бронирования")
async def my_bookings(message: types.Message):
    user_id = message.from_user.id
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT date, slot FROM bookings WHERE user_id = %s ORDER BY date, slot", (user_id,))
    bookings = cursor.fetchall()
    conn.close()
    text = "Ваши бронирования:\n" + "\n".join([f"{b[0]}, {b[1]}" for b in bookings]) if bookings else "У вас нет активных бронирований."
    await message.answer(text, reply_markup=main_menu())

@dp.message_handler(lambda message: message.text == "🔍 Посмотреть все бронирования")
async def view_all_bookings(message: types.Message):
    await message.answer("Выберите дату:", reply_markup=get_date_keyboard())

@dp.message_handler(lambda message: message.text.startswith("2025"))
async def show_bookings_for_date(message: types.Message):
    date = message.text.split(",")[0]
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT user_name FROM bookings WHERE date = %s", (date,))
    bookings = cursor.fetchall()
    conn.close()
    text = f"Бронирования на {date}:\n" + "\n".join([b[0] for b in bookings]) if bookings else f"На {date} нет бронирований."
    await message.answer(text, reply_markup=main_menu())

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
