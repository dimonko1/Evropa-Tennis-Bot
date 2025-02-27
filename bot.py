import logging
import asyncio
import asyncpg
from aiogram import Bot, Dispatcher, types
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton
from datetime import datetime
from config import TOKEN, DB_URL

# Настройки бота
bot = Bot(token=TOKEN)
dp = Dispatcher(bot)

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

# Клавиатура с выбором времени
keyboard = ReplyKeyboardMarkup(resize_keyboard=True)
timeslots = ["08:00–09:00", "09:00–10:00", "10:00–11:00", "11:00–12:00"]
for slot in timeslots:
    keyboard.add(KeyboardButton(slot))

# Команда /start
@dp.message_handler(commands=["start"])
async def start(message: types.Message):
    await message.answer("Привет! Выберите время для бронирования:", reply_markup=keyboard)

# Обработка выбора времени
@dp.message_handler(lambda message: message.text in timeslots)
async def book_time(message: types.Message):
    slot = message.text
    user_id = message.from_user.id
    user_name = message.from_user.full_name
    date = datetime.now().date()

    conn = await asyncpg.connect(DB_URL)
    existing_booking = await conn.fetchrow("SELECT * FROM bookings WHERE slot=$1 AND date=$2", slot, date)
    
    if existing_booking:
        await message.answer(f"Время {slot} уже занято. Выберите другое.", reply_markup=keyboard)
    else:
        await conn.execute("INSERT INTO bookings (user_id, user_name, slot, date) VALUES ($1, $2, $3, $4)",
                           user_id, user_name, slot, date)
        await message.answer(f"Вы забронировали {slot}. Спасибо!", reply_markup=keyboard)
    
    await conn.close()

# Запуск бота
async def main():
    logging.basicConfig(level=logging.INFO)
    await init_db()
    await dp.start_polling()

if __name__ == "__main__":
    asyncio.run(main())
