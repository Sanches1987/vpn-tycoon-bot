import asyncio
import logging
import sqlite3
import time
from aiogram import Bot, Dispatcher
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton

# ================== НАСТРОЙКИ ==================
TOKEN = "8790885592:AAGNaNCcbjfrio7qeoQMRieVK9PVXpDdNyU"  # ← новый токен
BOT_USERNAME = "vpn_tycoon_bot"                          # ← актуальный username без @
TG_OWNER = "@alexbright8877"                             # ← твой Telegram-ник
# ==============================================

bot = Bot(token=TOKEN)
dp = Dispatcher()

# База данных
conn = sqlite3.connect('vpn_tycoon.db', check_same_thread=False)
c = conn.cursor()
c.execute('''CREATE TABLE IF NOT EXISTS users (
    user_id INTEGER PRIMARY KEY,
    balance REAL DEFAULT 0.0,
    income_per_hour REAL DEFAULT 2.0,
    last_claim INTEGER DEFAULT 0,
    servers INTEGER DEFAULT 1,
    premium INTEGER DEFAULT 0
)''')
conn.commit()

def init_user(user_id):
    now = int(time.time())
    c.execute("SELECT user_id FROM users WHERE user_id=?", (user_id,))
    if not c.fetchone():
        c.execute("INSERT INTO users (user_id, last_claim) VALUES (?, ?)", (user_id, now))
        conn.commit()

def get_user(user_id):
    c.execute("SELECT balance, income_per_hour, last_claim, servers, premium FROM users WHERE user_id=?", (user_id,))
    row = c.fetchone()
    return row if row else (0.0, 2.0, 0, 1, 0)

def calculate_income(user_id):
    balance, income_ph, last_claim, servers, premium = get_user(user_id)
    hours = (int(time.time()) - last_claim) / 3600.0
    return round(hours * income_ph, 2)

# Главная клавиатура
def main_kb():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="💰 Профиль", callback_data="profile")],
        [InlineKeyboardButton(text="🕒 Забрать доход", callback_data="claim")],
        [InlineKeyboardButton(text="📡 Купить сервер (+2$/ч)", callback_data="buy_basic")],
        [InlineKeyboardButton(text="⭐ Купить премиум (+5$/ч)", callback_data="buy_premium")],
        [InlineKeyboardButton(text="👥 Рефералка", callback_data="referral")],
        [InlineKeyboardButton(text="❤️ Донат", callback_data="donate")]
    ])

@dp.message(Command("start"))
async def start_cmd(message: Message):
    user_id = message.from_user.id
    init_user(user_id)

    args = message.text.split()
    if len(args) > 1 and args[1].startswith("ref_"):
        try:
            referrer = int(args[1][4:])
            c.execute("UPDATE users SET balance = balance + 10 WHERE user_id=?", (referrer,))
            conn.commit()
            await message.answer("🎉 Ты пришёл по рефералке! Реферер получил +10$")
        except:
            pass

    await message.answer(
        "🚀 <b>Добро пожаловать в VPN Tycoon!</b>\n\n"
        "Ты — владелец VPN-бизнеса. Зарабатывай даже когда бот закрыт!\n"
        "Нажимай кнопки и строй империю 🔥",
        parse_mode="HTML",
        reply_markup=main_kb()
    )

@dp.callback_query()
async def callback_handler(call: CallbackQuery):
    user_id = call.from_user.id
    init_user(user_id)
    data = call.data

    if data == "claim":
        earned = calculate_income(user_id)
        if earned > 0:
            c.execute("UPDATE users SET balance = balance + ?, last_claim = ? WHERE user_id=?",
                      (earned, int(time.time()), user_id))
            conn.commit()
            await call.message.edit_text(f"✅ <b>Получено {earned}$ оффлайн!</b>\nПриходи снова через пару часов 😉",
                                         parse_mode="HTML", reply_markup=main_kb())
        else:
            await call.answer("Пока нет накопленного дохода 😢", show_alert=True)

    elif data == "profile":
        balance, income, last, servers, premium = get_user(user_id)
        earned_now = calculate_income(user_id)
        text = (f"📊 <b>Твой VPN Tycoon</b>\n\n"
                f"💰 Баланс: <b>{balance + earned_now:.2f}$</b>\n"
                f"📡 Обычных серверов: <b>{servers}</b>\n"
                f"⭐ Премиум: <b>{premium}</b>\n"
                f"💵 Доход в час: <b>{income:.2f}$</b>\n"
                f"📈 Накоплено сейчас: <b>{earned_now}$</b>")
        await call.message.edit_text(text, parse_mode="HTML", reply_markup=main_kb())

    elif data == "buy_basic":
        balance, income, last, servers, premium = get_user(user_id)
        cost = 15 + 5 * servers
        if balance >= cost:
            c.execute("UPDATE users SET balance=balance-?, servers=servers+1, income_per_hour=income_per_hour+2 WHERE user_id=?",
                      (cost, user_id))
            conn.commit()
            await call.answer(f"✅ Куплен сервер за {cost}$ (+2$/ч)")
            await call.message.edit_text("📡 Сервер добавлен! Доход вырос.", reply_markup=main_kb())
        else:
            await call.answer(f"Недостаточно! Нужно {cost}$", show_alert=True)

    elif data == "buy_premium":
        balance, income, last, servers, premium = get_user(user_id)
        cost = 45 + 15 * premium
        if balance >= cost:
            c.execute("UPDATE users SET balance=balance-?, premium=premium+1, income_per_hour=income_per_hour+5 WHERE user_id=?",
                      (cost, user_id))
            conn.commit()
            await call.answer(f"✅ Премиум-сервер за {cost}$ (+5$/ч)")
            await call.message.edit_text("⭐ Премиум добавлен! Доход сильно вырос.", reply_markup=main_kb())
        else:
            await call.answer(f"Недостаточно! Нужно {cost}$", show_alert=True)

    elif data == "referral":
        link = f"https://t.me/{BOT_USERNAME}?start=ref_{user_id}"
        await call.message.edit_text(
            f"🔗 <b>Твоя реферальная ссылка</b>\n\n{link}\n\n"
            f"Приведи друга — получи +10$ сразу! 🔥\n"
            f"Чем больше друзей — тем быстрее миллион 😉",
            parse_mode="HTML",
            reply_markup=main_kb()
        )

    elif data == "donate":
        await call.message.edit_text(
            f"❤️ <b>Поддержи разработчика</b>\n\n"
            f"Хочешь ускорить развитие и получить бонусы?\n"
            f"Напиши мне в личку {TG_OWNER} — обсудим донат / Stars / крипту\n\n"
            f"Спасибо, что помогаешь расти! 🚀",
            parse_mode="HTML",
            reply_markup=main_kb()
        )

async def main():
    logging.basicConfig(level=logging.INFO)
    print("🚀 VPN Tycoon Bot запущен!")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
