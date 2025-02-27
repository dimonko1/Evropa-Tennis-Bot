import logging
import asyncio
import asyncpg
from aiogram import Bot, Dispatcher, types
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from datetime import datetime, timedelta
from config import TOKEN, DB_URL

# Настройки бота
bot = Bot(token=TOKEN)
dp = Dispatcher()

# Подключение к базе PostgreSQL
async def init_db():
    conn = await asyncpg.connect(DB_URL)
    await conn.execute('''CREATE TABLE IF NOT EXISTS bookings (
                            id SERIAL PRIMARY KEY,
                            user_id BIGINT,
                            user_name TEXT,
                            slot TEXT,
                            date TIMESTAMP
                          );''')
    await conn.close()

# Получение списка доступных дат (следующие 7 дней)
def get_dates():
    today = datetime.now().date()
    return [today + timedelta(days=i) for i in range(7)]

# Получение клавиатуры для выбора даты
def get_date_keyboard():
    keyboard = InlineKeyboardMarkup(row_width=3)
    dates = get_dates()
    buttons = [
        InlineKeyboardButton(date.strftime('%d-%m-%Y'), callback_data=f"date_{date}")
        for date in dates
    ]
    keyboard.add(*buttons)
    return keyboard

# Получение клавиатуры для выбора времени
def get_time_keyboard(date):
    keyboard = InlineKeyboardMarkup(row_width=2)
    timeslots = ["08:00–09:00", "09:00–10:00", "10:00–11:00", "11:00–12:00"]
    buttons = [
        InlineKeyboardButton(slot, callback_data=f"time_{date}_{slot}")
        for slot in timeslots
    ]
    keyboard.add(*buttons)
    return keyboard

# Обработка команды /start
@dp.message_handler(commands=["start"])
async def start(message: types.Message):
    await message.answer("Выберите день для бронирования:", reply_markup=get_date_keyboard())

# Обработка выбора даты
@dp.callback_query_handler(lambda c: c.data.startswith('date_'))
async def handle_date_selection(callback_query: types.CallbackQuery):
    selected_date = callback_query.data.split("_")[1]
    selected_date = datetime.strptime(selected_date, '%Y-%m-%d').date()
    await bot.answer_callback_query(callback_query.id)
    await bot.send_message(
        callback_query.from_user.id,
        f"Вы выбрали {selected_date}. Теперь выберите время:",
        reply_markup=get_time_keyboard(selected_date)
    )

# Обработка выбора времени
@dp.callback_query_handler(lambda c: c.data.startswith('time_'))
async def handle_time_selection(callback_query: types.CallbackQuery):
    date_str, slot = callback_query.data.split("_")[1], callback_query.data.split("_")[2]
    selected_date = datetime.strptime(date_str, '%Y-%m-%d').date()
    user_id = callback_query.from_user.id
    user_name = callback_query.from_user.full_name

    # Проверка на наличие бронирования
    conn = await asyncpg.connect(DB_URL)
    existing_booking = await conn.fetchrow("SELECT * FROM bookings WHERE slot=$1 AND date=$2", slot, selected_date)

    if existing_booking:
        await bot.answer_callback_query(callback_query.id, text=f"Время {slot} уже занято.")
        await bot.send_message(callback_query.from_user.id, "Выберите другое время:", reply_markup=get_time_keyboard(selected_date))
    else:
        await conn.execute("INSERT INTO bookings (user_id, user_name, slot, date) VALUES ($1, $2, $3, $4)",
                           user_id, user_name, slot, selected_date)
        await bot.answer_callback_query(callback_query.id, text=f"Вы забронировали {slot} на {selected_date}.")
        await bot.send_message(callback_query.from_user.id, f"Спасибо, вы успешно забронировали {slot} на {selected_date}.", reply_markup=get_date_keyboard())
    await conn.close()

# Запуск бота
async def main():
    logging.basicConfig(level=logging.INFO)
    await init_db()
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
