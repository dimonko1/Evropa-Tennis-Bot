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
    keyboard = ReplyKeyboardMarkup(resize_keyboard=True, row_width=3)
    buttons = [KeyboardButton((datetime.now() + timedelta(days=i)).strftime('%Y-%m-%d')) for i in range(31)]
    keyboard.add(*buttons)
    return keyboard

def get_time_keyboard():
    keyboard = ReplyKeyboardMarkup(resize_keyboard=True, row_width=4)
    timeslots = [f"{hour}:00–{hour+1}:00" for hour in range(7, 21)]
    buttons = [KeyboardButton(slot) for slot in timeslots]
    keyboard.add(*buttons)
    return keyboard

user_booking_data = {}

def check_booking(slot, date):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM bookings WHERE slot = %s AND date = %s", (slot, date))
    count = cursor.fetchone()[0]
    conn.close()
    return count > 0

def add_booking(user_id, user_name, slot, date):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("INSERT INTO bookings (user_id, user_name, slot, date) VALUES (%s, %s, %s, %s)",
                   (user_id, user_name, slot, date))
    conn.commit()
    conn.close()
    
@dp.message_handler(commands=["start"])
async def start(message: types.Message):
    await message.answer("Выберите действие:", reply_markup=main_menu())

@dp.message_handler(lambda message: message.text == "📅 Новая бронь")
async def new_booking(message: types.Message):
    await message.answer("Выберите дату для бронирования:", reply_markup=get_date_keyboard())

@dp.message_handler(lambda message: message.text.count("-") == 2)
async def choose_date(message: types.Message):
    user_booking_data[message.from_user.id] = {"date": message.text}
    await message.answer("Теперь выберите время:", reply_markup=get_time_keyboard())

@dp.message_handler(lambda message: any(message.text.startswith(f"{hour}:00") for hour in range(7, 21)))
async def book_time(message: types.Message):
    user_id = message.from_user.id
    user_name = message.from_user.full_name
    
    if user_id not in user_booking_data:
        await message.answer("Сначала выберите дату!", reply_markup=get_date_keyboard())
        return
    
    date = user_booking_data[user_id]["date"]
    slot = message.text
    
    if check_booking(slot, date):
        await message.answer(f"Время {slot} на {date} уже занято. Выберите другое.", reply_markup=get_time_keyboard())
    else:
        add_booking(user_id, user_name, slot, date)
        await message.answer(f"Вы забронировали {slot} на {date}. Спасибо!", reply_markup=main_menu())
        del user_booking_data[user_id]

@dp.message_handler(lambda message: message.text == "❌ Отменить бронь")
async def cancel_booking(message: types.Message):
    user_id = message.from_user.id
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT slot, date FROM bookings WHERE user_id = %s", (user_id,))
    bookings = cursor.fetchall()
    conn.close()
    
    if bookings:
        keyboard = ReplyKeyboardMarkup(resize_keyboard=True, row_width=1)
        buttons = [KeyboardButton(f"{b[1]} {b[0]}") for b in bookings]
        keyboard.add(*buttons)
        await message.answer("Выберите бронь для отмены:", reply_markup=keyboard)
    else:
        await message.answer("У вас нет активных броней.", reply_markup=main_menu())

@dp.message_handler(lambda message: message.text == "🔍 Посмотреть все бронирования")
async def view_all_bookings(message: types.Message):
    await message.answer("Выберите дату для просмотра:", reply_markup=get_date_keyboard())

@dp.message_handler(lambda message: message.text in [b.text for b in get_date_keyboard().keyboard[0]])
async def show_bookings_for_date(message: types.Message):
    date = message.text
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT slot, user_name FROM bookings WHERE date = %s ORDER BY slot", (date,))
    bookings = cursor.fetchall()
    conn.close()
    
    if bookings:
        text = f"Бронирования на {date}:\n" + "\n".join([f"{b[0]} - {b[1]}" for b in bookings])
    else:
        text = "На эту дату нет бронирований."
    
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
