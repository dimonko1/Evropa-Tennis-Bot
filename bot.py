import logging
import asyncio
import os
import psycopg2
from psycopg2.extras import DictCursor
from aiogram import Bot, Dispatcher, types
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton
from aiogram.utils.executor import start_webhook
from datetime import datetime, timedelta
import locale

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

def get_date_keyboard(action):
    keyboard = ReplyKeyboardMarkup(resize_keyboard=True, row_width=3)
    days = [datetime.now() + timedelta(days=i) for i in range(7)]
    buttons = [KeyboardButton(f"{day.strftime('%Y-%m-%d, %a')}|{action}") for day in days]
    keyboard.add(*buttons, KeyboardButton("🏠 Меню"))
    return keyboard

def get_time_keyboard(date):
    keyboard = ReplyKeyboardMarkup(resize_keyboard=True, row_width=4)
    timeslots = [f"{hour}:00–{hour+1}:00|{date}" for hour in range(7, 21)]
    keyboard.add(*[KeyboardButton(slot) for slot in timeslots], KeyboardButton("🏠 Меню"))
    return keyboard

def get_user_bookings_keyboard(user_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id, date, slot FROM bookings WHERE user_id = %s ORDER BY date, slot", (user_id,))
    bookings = cursor.fetchall()
    conn.close()
    keyboard = ReplyKeyboardMarkup(resize_keyboard=True, row_width=1)
    for booking in bookings:
        keyboard.add(KeyboardButton(f"{booking[0]}: {booking[1]}, {booking[2]}"))
    keyboard.add(KeyboardButton("🏠 Меню"))
    return keyboard if bookings else None

@dp.message_handler(commands=["start"])
async def start(message: types.Message):
    await message.answer("Выберите действие:", reply_markup=main_menu())

@dp.message_handler(lambda message: message.text == "📅 Новая бронь")
async def new_booking(message: types.Message):
    await message.answer("Выберите дату для бронирования:", reply_markup=get_date_keyboard("book"))

@dp.message_handler(lambda message: "|book" in message.text)
async def select_time(message: types.Message):
    date = message.text.split("|")[0]
    await message.answer("Выберите время:", reply_markup=get_time_keyboard(date))

@dp.message_handler(lambda message: "–" in message.text and "|" in message.text)
async def confirm_booking(message: types.Message):
    slot, date = message.text.split("|")
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("INSERT INTO bookings (user_id, user_name, slot, date) VALUES (%s, %s, %s, %s)",
                   (message.from_user.id, message.from_user.full_name, slot, date))
    conn.commit()
    conn.close()
    await message.answer("Бронь подтверждена!", reply_markup=main_menu())

@dp.message_handler(lambda message: message.text == "❌ Отменить бронь")
async def cancel_booking(message: types.Message):
    keyboard = get_user_bookings_keyboard(message.from_user.id)
    if keyboard:
        await message.answer("Выберите бронь для отмены:", reply_markup=keyboard)
    else:
        await message.answer("У вас нет активных бронирований.", reply_markup=main_menu())

@dp.message_handler(lambda message: message.text.startswith("🏠"))
async def go_to_menu(message: types.Message):
    await message.answer("Главное меню:", reply_markup=main_menu())

@dp.message_handler(lambda message: message.text == "📋 Мои бронирования")
async def my_bookings(message: types.Message):
    keyboard = get_user_bookings_keyboard(message.from_user.id)
    if keyboard:
        await message.answer("Ваши бронирования:", reply_markup=keyboard)
    else:
        await message.answer("У вас нет активных бронирований.", reply_markup=main_menu())

@dp.message_handler(lambda message: message.text == "🔍 Посмотреть все бронирования")
async def view_all_bookings(message: types.Message):
    await message.answer("Выберите дату:", reply_markup=get_date_keyboard("view"))

@dp.message_handler(lambda message: "|view" in message.text)
async def show_bookings_for_date(message: types.Message):
    date = message.text.split("|")[0]
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT user_name, slot FROM bookings WHERE date = %s", (date,))
    bookings = cursor.fetchall()
    conn.close()
    if bookings:
        text = f"Бронирования на {date}:\n" + "\n".join([f"{b[0]} - {b[1]}" for b in bookings])
    else:
        text = f"На {date} нет бронирований."
    await message.answer(text, reply_markup=main_menu())

if __name__ == "__main__":
    from aiogram import executor
    executor.start_webhook(
        dispatcher=dp,
        webhook_path=WEBHOOK_PATH,
        on_startup=init_db,
        host=WEBAPP_HOST,
        port=WEBAPP_PORT
    )
