import asyncio
import logging
import sqlite3
from aiogram import Bot, Dispatcher, types, F
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton, LabeledPrice
from aiogram.filters import Command

# --- ТОКЕН ТА АДМІН ---
API_TOKEN = '8681771367:AAHqXA1eaQ1UaKxfp1NtidjiUFIAHJiREPI'
ADMIN_ID = 5032697609

logging.basicConfig(level=logging.INFO)
bot = Bot(token=API_TOKEN)
dp = Dispatcher()

# --- БАЗА ДАНИХ ---
conn = sqlite3.connect('chat.db', check_same_thread=False)
cursor = conn.cursor()
cursor.execute('''CREATE TABLE IF NOT EXISTS users 
                  (user_id INTEGER PRIMARY KEY, gender TEXT, status TEXT, partner_id INTEGER, is_vip INTEGER DEFAULT 0)''')
conn.commit()

# --- КЛАВІАТУРИ ---
main_menu = ReplyKeyboardMarkup(keyboard=[
    [KeyboardButton(text="🔍 Пошук"), KeyboardButton(text="💎 VIP")]
], resize_keyboard=True)

stop_menu = ReplyKeyboardMarkup(keyboard=[
    [KeyboardButton(text="❌ Зупинити пошук")]
], resize_keyboard=True)

chat_menu = ReplyKeyboardMarkup(keyboard=[
    [KeyboardButton(text="➡️ Наступний"), KeyboardButton(text="🛑 Стоп")]
], resize_keyboard=True)

# --- ЛОГІКА ---

@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    cursor.execute("SELECT * FROM users WHERE user_id = ?", (message.from_user.id,))
    if not cursor.fetchone():
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="Я хлопець 👦", callback_data="set_male")],
            [InlineKeyboardButton(text="Я дівчина 👧", callback_data="set_female")]
        ])
        await message.answer("Вибери стать:", reply_markup=kb)
    else:
        await message.answer("Ти в меню!", reply_markup=main_menu)

@dp.callback_query(F.data.startswith("set_"))
async def set_gender(call: types.CallbackQuery):
    g = "male" if call.data == "set_male" else "female"
    cursor.execute("INSERT OR REPLACE INTO users (user_id, gender, status) VALUES (?, ?, ?)", (call.from_user.id, g, "idle"))
    conn.commit()
    await call.message.answer(f"Збережено! Твоя стать: {g}", reply_markup=main_menu)
    await call.answer()

@dp.message(F.text == "💎 VIP")
async def buy_vip(message: types.Message):
    await message.answer("VIP статус дозволяє вибирати стать співрозмовника. Оплата зірками (XTR):", reply_markup=main_menu)
    # Тимчасово вимкнув інвойс для тесту пошуку

@dp.message(F.text.in_(["🔍 Пошук", "➡️ Наступний"]))
async def search(message: types.Message):
    uid = message.from_user.id
    
    # 1. Перевіряємо, чи був партнер
    cursor.execute("SELECT partner_id FROM users WHERE user_id = ?", (uid,))
    row = cursor.fetchone()
    old_partner = row[0] if row else None

    if old_partner:
        cursor.execute("UPDATE users SET status='idle', partner_id=NULL WHERE user_id IN (?,?)", (uid, old_partner))
        conn.commit()
        try:
            await bot.send_message(old_partner, "Співрозмовник завершив чат.", reply_markup=main_menu)
        except:
            pass

    # 2. Шукаємо нового
    cursor.execute("SELECT user_id FROM users WHERE status = 'searching' AND user_id != ?", (uid,))
    res = cursor.fetchone()

    if res:
        pid = res[0]
        cursor.execute("UPDATE users SET status='chatting', partner_id=? WHERE user_id=?", (pid, uid))
        cursor.execute("UPDATE users SET status='chatting', partner_id=? WHERE user_id=?", (uid, pid))
        conn.commit()
        await message.answer("Знайшов! Спілкуйтеся 💬", reply_markup=chat_menu)
        await bot.send_message(pid, "Знайшов! Спілкуйтеся 💬", reply_markup=chat_menu)
    else:
        cursor.execute("UPDATE users SET status='searching', partner_id=NULL WHERE user_id=?", (uid,))
        conn.commit()
        await message.answer("Шукаю співрозмовника... 🔍", reply_markup=stop_menu)

@dp.message(F.text.in_(["🛑 Стоп", "❌ Зупинити пошук"]))
async def stop(message: types.Message):
    uid = message.from_user.id
    cursor.execute("SELECT partner_id FROM users WHERE user_id = ?", (uid,))
    row = cursor.fetchone()
    pid = row[0] if row else None

    cursor.execute("UPDATE users SET status='idle', partner_id=NULL WHERE user_id=?", (uid,))
    if pid:
        cursor.execute("UPDATE users SET status='idle', partner_id=NULL WHERE user_id=?", (pid,))
        try:
            await bot.send_message(pid, "Кінець чату. Повернення в меню.", reply_markup=main_menu)
        except:
            pass
    conn.commit()
    await message.answer("Ви зупинили пошук. Повернення в меню.", reply_markup=main_menu)

@dp.message()
async def echo(message: types.Message):
    if message.text:
        cursor.execute("SELECT partner_id, status FROM users WHERE user_id = ?", (message.from_user.id,))
        res = cursor.fetchone()
        if res and res[1] == 'chatting' and res[0]:
            try:
                await bot.send_message(res[0], message.text)
            except:
                await message.answer("Помилка при відправці повідомлення.")
        elif res and res[1] == 'searching':
            await message.answer("Зачекайте, поки я знайду когось... 🔍")

async def main():
    await dp.start_polling(bot)

if __name__ == '__main__':
    asyncio.run(main())
