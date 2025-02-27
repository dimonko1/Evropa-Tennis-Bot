import os
import logging
from aiogram import Bot, Dispatcher, types
from aiogram.contrib.middlewares.logging import LoggingMiddleware
from aiogram.types import ParseMode, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils import executor
import psycopg2
from datetime import datetime, timedelta
from config import TOKEN, DB_URL

# Настройка логирования
logging.basicConfig(level=logging.INFO)

# Инициализация бота и диспетчера
bot = Bot(TOKEN)
dp = Dispatcher(bot)
dp.middleware.setup(LoggingMiddleware())

# Подключение к базе данных
conn = psycopg2.connect(DB_URL, sslmode='require')
cursor = conn.cursor()

# Команда /start
@dp.message_handler(commands=['start'])
async def send_welcome(message: types.Message):
    await message.reply("Привет! Я бот для бронирования теннисного корта. Используй кнопки ниже для бронирования.", reply_markup=main_menu())

# Главное меню
def main_menu():
    keyboard = InlineKeyboardMarkup(row_width=2)
    keyboard.add(InlineKeyboardButton("Забронировать", callback_data="book"))
    keyboard.add(InlineKeyboardButton("Отменить бронь", callback_data="cancel"))
    return keyboard

# Календарь для выбора даты
def generate_calendar(year=None, month=None):
    now = datetime.now()
    if year is None:
        year = now.year
    if month is None:
        month = now.month

    keyboard = InlineKeyboardMarkup(row_width=7)
    keyboard.add(InlineKeyboardButton(f"{year}-{month:02d}", callback_data="ignore"))

    days = ["Пн", "Вт", "Ср", "Чт", "Пт", "Сб", "Вс"]
    keyboard.add(*[InlineKeyboardButton(day, callback_data="ignore") for day in days])

    month_start = datetime(year=year, month=month, day=1)
    month_end = (month_start + timedelta(days=32)).replace(day=1) - timedelta(days=1)
    start_offset = month_start.weekday()
    days_in_month = month_end.day

    buttons = []
    for day in range(1, days_in_month + 1):
        date = datetime(year=year, month=month, day=day)
        if date < now:
            buttons.append(InlineKeyboardButton(" ", callback_data="ignore"))
        else:
            buttons.append(InlineKeyboardButton(str(day), callback_data=f"date_{year}-{month:02d}-{day:02d}"))

    keyboard.add(*id58222140 (*buttons))
    keyboard.add(InlineKeyboardButton("Назад", callback_data="back_to_main"))
    return keyboard

# Выбор времени
def generate_time_slots(date):
    time_slots = ["09:00", "10:00", "11:00", "12:00", "13:00", "14:00", "15:00", "16:00", "17:00", "18:00", "19:00", "20:00"]
    keyboard = InlineKeyboardMarkup(row_width=3)
    for time_slot in time_slots:
        cursor.execute("SELECT * FROM bookings WHERE booking_date = %s AND booking_time = %s", (date, time_slot))
        if cursor.fetchone():
            keyboard.add(InlineKeyboardButton(f"❌ {time_slot}", callback_data="ignore"))
        else:
            keyboard.add(InlineKeyboardButton(time_slot, callback_data=f"time_{date}_{time_slot}"))
    keyboard.add(InlineKeyboardButton("Назад", callback_data="back_to_calendar"))
    return keyboard

# Обработка callback-запросов
@dp.callback_query_handler(lambda c: c.data)
async def process_callback(callback_query: types.CallbackQuery):
    data = callback_query.data
    if data == "book":
        await bot.answer_callback_query(callback_query.id)
        await bot.send_message(callback_query.from_user.id, "Выберите дату:", reply_markup=generate_calendar())
    elif data == "cancel":
        await bot.answer_callback_query(callback_query.id)
        await bot.send_message(callback_query.from_user.id, "Функция отмены бронирования пока не реализована.")
    elif data.startswith("date_"):
        date = data.split("_")[1]
        await bot.answer_callback_query(callback_query.id)
        await bot.send_message(callback_query.from_user.id, f"Выберите время для {date}:", reply_markup=generate_time_slots(date))
    elif data.startswith("time_"):
        date, time = data.split("_")[1], data.split("_")[2]
        user_id = callback_query.from_user.id
        cursor.execute("INSERT INTO bookings (user_id, booking, booking_time) VALUES (%s, %s, %s)", (user_id, date, time))
        conn.commit()
        await bot.answer_callback_query(callback_query.id)
        await bot.send_message(callback_query.from_user.id, f"Корт успешно забронирован на {date} в {time}.")
    elif data == "back_to_main":
        await bot.answer_callback_query(callback_query.id)
        await bot.send_message(callback_query.from_user.id, "Главное меню:", reply_markup=main_menu())
    elif data == "back_to_calendar":
        await bot.answer_callback_query(callback_query.id)
        await bot.send_message(callback_query.from_user.id, "Выберите дату:", reply_markup=generate_calendar())
    else:
        await bot.answer_callback_query(callback_query.id)

# Запуск бота
if __name__ == '__main__':
    executor.start_polling(dp, skip_updates=True)_date
