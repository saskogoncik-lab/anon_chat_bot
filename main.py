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
    await call.message.answer("Збережено!", reply_markup=main_menu)
    await call.answer()

@dp.message(F.text == "💎 VIP")
async def buy_vip(message: types.Message):
    await bot.send_invoice(
        message.chat.id,
        title="VIP Статус",
        description="Пошук за статтю!",
        provider_token="",
        currency="XTR",
        prices=[LabeledPrice(label="VIP", amount=100)],
        payload="vip"
    )

@dp.message(F.text.in_(["🔍 Пошук", "➡️ Наступний"]))
async def search(message: types.Message):
    uid = message.from_user.id
    cursor.execute("SELECT partner_id FROM users WHERE user_id = ?", (uid,))
    old = cursor.fetchone()[0]
    if old:
        cursor.execute("UPDATE users SET status='idle', partner_id=NULL WHERE user_id IN (?,?)", (uid, old))
        conn.commit()
        try: await bot.send_message(old, "Співрозмовник вийшов.", reply_markup=main_menu)
        except: pass

    cursor.execute("SELECT user_id FROM users WHERE status = 'searching' AND user_id != ?", (uid,))
    res = cursor.fetchone()
    if res:
        pid = res[0]
        cursor.execute("UPDATE users SET status='chatting', partner_id=? WHERE user_id=?", (pid, uid))
        cursor.execute("UPDATE users SET status='chatting', partner_id=? WHERE user_id=?", (uid, pid))
        conn.commit()
        await message.answer("Знайшов!", reply_markup=chat_menu)
        await bot.send_message(pid, "Знайшов!", reply_markup=chat_menu)
    else:
        cursor.execute("UPDATE users SET status='searching' WHERE user_id=?", (uid,))
        conn.commit()
        await message.answer("Шукаю...", reply_markup=stop_menu)

@dp.message(F.text.in_(["🛑 Стоп", "❌ Зупинити пошук"]))
async def stop(message: types.Message):
    uid = message.from_user.id
    cursor.execute("SELECT partner_id FROM users WHERE user_id = ?", (uid,))
    pid = cursor.fetchone()[0]
    cursor.execute("UPDATE users SET status='idle', partner_id=NULL WHERE user_id=?", (uid,))
    if pid:
        cursor.execute("UPDATE users SET status='idle', partner_id=NULL WHERE user_id=?", (pid,))
        await bot.send_message(pid, "Кінець чату.", reply_markup=main_menu)
    conn.commit()
    await message.answer("Головне меню.", reply_markup=main_menu)

@dp.message()
async def echo(message: types.Message):
    if message.text:
        cursor.execute("SELECT partner_id FROM users WHERE user_id = ?", (message.from_user.id,))
        res = cursor.fetchone()
        if res and res[0]:
            try: await bot.send_message(res[0], message.text)
            except: pass

async def main():
    await dp.start_polling(bot)

if __name__ == '__main__':
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
