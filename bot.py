import os
import logging
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.enums import ParseMode
from aiogram.utils.formatting import as_list, as_line, Text
from aiogram import F
from aiogram.utils.chat_action import ChatActionMiddleware
from datetime import datetime, timedelta
import psycopg2

# Настройка логирования
logging.basicConfig(level=logging.INFO)

# Инициализация бота и диспетчера
API_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
bot = Bot(token=API_TOKEN)
dp = Dispatcher(bot)

# Подключение к базе данных
DATABASE_URL = os.getenv('DATABASE_URL')
conn = psycopg2.connect(DATABASE_URL, sslmode='require')
cursor = conn.cursor()

# Команда /start
@dp.message(Command("start"))
async def send_welcome(message: types.Message):
    await message.answer("Привет! Я бот для бронирования теннисного корта. Используй кнопки ниже для бронирования.", reply_markup=main_menu())

# Главное меню
def main_menu():
    builder = InlineKeyboardBuilder()
    builder.add(InlineKeyboardButton(text="Забронировать", callback_data="book"))
    builder.add(InlineKeyboardButton(text="Отменить бронь", callback_data="cancel"))
    builder.adjust(1)
    return builder.as_markup()

# Календарь для выбора даты
def generate_calendar(year=None, month=None):
    now = datetime.now()
    if year is None:
        year = now.year
    if month is None:
        month = now.month

    builder = InlineKeyboardBuilder()
    builder.add(InlineKeyboardButton(text=f"{year}-{month:02d}", callback_data="ignore"))
    builder.add(*[InlineKeyboardButton(text=day, callback_data="ignore") for day in ["Пн", "Вт", "Ср", "Чт", "Пт", "Сб", "Вс"]])
    builder.adjust(7)

    month_start = datetime(year=year, month=month, day=1)
    month_end = (month_start + timedelta(days=32)).replace(day=1) - timedelta(days=1)
    start_offset = month_start.weekday()
    days_in_month = month_end.day

    for day in range(1, days_in_month + 1):
        date = datetime(year=year, month=month, day=day)
        if date < now:
            builder.add(InlineKeyboardButton(text=" ", callback_data="ignore"))
        else:
            builder.add(InlineKeyboardButton(text=str(day), callback_data=f"date_{year}-{month:02d}-{day:02d}"))

    builder.add(InlineKeyboardButton(text="Назад", callback_data="back_to_main"))
    builder.adjust(7)
    return builder.as_markup()

# Выбор времени
def generate_time_slots(date):
    time_slots = ["09:00", "10:00", "11:00", "12:00", "13:00", "14:00", "15:00", "16:00", "17:00", "18:00", "19:00", "20:00"]
    builder = InlineKeyboardBuilder()
    for time_slot in time_slots:
        cursor.execute("SELECT * FROM bookings WHERE booking_date = %s AND booking_time = %s", (date, time_slot))
        if cursor.fetchone():
            builder.add(InlineKeyboardButton(text=f"❌ {time_slot}", callback_data="ignore"))
        else:
            builder.add(InlineKeyboardButton(text=time_slot, callback_data=f"time_{date}_{time_slot}"))
    builder.add(InlineKeyboardButton(text="Назад", callback_data="back_to_calendar"))
    builder.adjust(3)
    return builder.as_markup()

# Обработка callback-запросов
@dp.callback_query(F.data == "book")
async def process_book(callback_query: types.CallbackQuery):
    await callback_query.message.edit_text("Выберите дату:", reply_markup=generate_calendar())

@dp.callback_query(F.data == "cancel"))
async def process_cancel(callback_query: types.CallbackQuery):
    await callback_query.message.edit_text("Функция отмены бронирования пока не реализована.")

@dp.callback_query(F.data.startswith("date_")))
async def process_date(callback_query: types.CallbackQuery):
    date = callback_query.data.split("_")[1]
    await callback_query.message.edit_text(f"Выберите время для {date}:", reply_markup=generate_time_slots(date))

@dp.callback_query(F.data.startswith("time_")))
async def process_time(callback_query: types.CallbackQuery):
    date, time = callback_query.data.split("_")[1], callback_query.data.split("_")[2]
    user_id = callback_query.from_user.id
    cursor.execute("INSERT INTO bookings (user_id, booking_date, booking_time) VALUES (%s, %s, %s)", (user_id, date, time))
    conn.commit()
    await callback_query.message.edit_text(f"Корт успешно забронирован на {date} в {time}.")

@dp.callback_query(F.data == "back_to_main"))
async def process_back_to_main(callback_query: types.CallbackQuery):
    await callback_query.message.edit_text("Главное меню:", reply_markup=main_menu())

@dp.callback_query(F.data == "back_to_calendar"))
async def process_back_to_calendar(callback_query: types.CallbackQuery):
    await callback_query.message.edit_text("Выберите дату:", reply_markup=generate_calendar())

# Запуск бота
if __name__ == '__main__':
    dp.run_polling(bot) callb
