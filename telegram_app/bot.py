
import asyncio, os, io, json, datetime, re, urllib.parse
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from dotenv import load_dotenv

from core.trader_ml import QuantumTradingAIWithML
from telegram_app.keyboards import main_menu, symbols_menu
from telegram_app.visuals import plot_technical_chart

from core.referrals import set_user_referrer, set_referrer_address, stats_summary, build_share_text, load_refs, mark_bonus_sent
BOT_USERNAME = os.getenv("BOT_USERNAME","YourBotUsername")

ADMIN_IDS = set(int(x) for x in os.getenv("ADMIN_IDS","").split(",") if x.strip().isdigit())

def is_admin(uid: int) -> bool:
    return uid in ADMIN_IDS
  # set your bot username in .env for correct share link


load_dotenv()
TOKEN = os.getenv("TELEGRAM_TOKEN", "")
TON_ADDRESS = os.getenv("TON_ADDRESS","UQC3Pro8kBw5LGpD3uxTwrHn6rKP-MMw8sNgFt5IhhDdYZMG")

bot = Bot(token=TOKEN)
dp = Dispatcher()

trader = QuantumTradingAIWithML()
current_symbol = "BTCUSDT"

USERS_FILE = os.getenv("USERS_FILE","data/users.json")
TRIAL_DAYS = int(os.getenv("TRIAL_DAYS","3"))

ASK_COIN_USERS = set()

def load_users():
    if os.path.exists(USERS_FILE):
        with open(USERS_FILE,"r") as f: 
            try: return json.load(f)
            except: return {}
    return {}

def save_users(d):
    os.makedirs(os.path.dirname(USERS_FILE), exist_ok=True)
    with open(USERS_FILE,"w") as f: json.dump(d,f,indent=2,ensure_ascii=False)

def register_user(uid):
    users = load_users()
    if str(uid) not in users:
        now = datetime.datetime.now()
        users[str(uid)] = {"start": now.isoformat(), "plan": "trial"}
        save_users(users)

def plan_status(uid):
    users = load_users()
    u = users.get(str(uid))
    if not u:
        return ("trial", 0, None)
    plan = u.get("plan","trial")
    now = datetime.datetime.now()
    if plan == "trial":
        start = datetime.datetime.fromisoformat(u["start"])
        left = TRIAL_DAYS - (now - start).days
        if left <= 0:
            return ("expired", 0, None)  # trial expired
        return ("trial", left, None)
    elif plan in ("month","year"):
        exp = u.get("expires")
        if not exp:
            return ("expired", 0, None)
        exp_dt = datetime.datetime.fromisoformat(exp)
        left_days = (exp_dt - now).days
        if exp_dt <= now:
            return ("expired", 0, exp_dt.isoformat())
        return (plan, left_days, exp_dt.isoformat())
    return ("expired", 0, None)

def build_payment_links(uid: int):
    # Auto-embed UID in TON payment comment
    comment_m = urllib.parse.quote(f"UID:{uid} Monthly")
    comment_y = urllib.parse.quote(f"UID:{uid} Yearly")
    month_url = f"https://tonhub.com/transfer/{TON_ADDRESS}?text={comment_m}"
    year_url  = f"https://tonhub.com/transfer/{TON_ADDRESS}?text={comment_y}"
    return month_url, year_url

def require_access(uid):
    plan, days_left, _ = plan_status(uid)
    return plan in ("trial","month","year") and (plan!="trial" or days_left>0)

@dp.message(Command("start"))
async def start(message: types.Message):
    user = message.from_user
    register_user(user.id)

    # Parse /start payload for referral "ref<id>"
    parts = (message.text or "").split()
    if len(parts) > 1 and parts[1].startswith("ref"):
        try:
            ref_id = int(parts[1].replace("ref",""))
            if ref_id != user.id:
                set_user_referrer(user.id, ref_id, username=(user.username and "@"+user.username) )

    # also store referrer in users.json for later payment linking
    users = load_users()
    u = users.get(str(user.id), {"start": datetime.datetime.now().isoformat(), "plan":"trial"})
    u["referrer_id"] = ref_id
    if user.username:
        u["username"] = "@"+user.username
    users[str(user.id)] = u
    save_users(users)

        except: pass

    plan, days_left, exp = plan_status(user.id)

    capabilities = (
        "• ИИ-сигналы intraday (LONG/SHORT)\n"
        "• Свечные графики в стиле TradingView\n"
        "• Индикаторы: RSI, MACD, Supertrend\n"
        "• Entry / SL / TP прямо на графике\n"
        "• Самообучение моделей\n"
    )

    if plan == "trial":
        status_line = f"🎁 *Триал активен*. Осталось: *{days_left} дн.*"
    elif plan in ("month","year"):
        status_line = f"✅ *Подписка активна*: {plan}. До: {exp}"
    else:
        status_line = "⛔ *Триал закончился*. Доступ к функциям закрыт до оплаты."

    text = (
        f"👋 Привет, *{user.first_name}*!\n\n"
        "Я — *Quantum AI Trader* 🤖\n"
        f"{capabilities}\n"
        f"🧾 Статус: {status_line}\n\n"
        "Выбери действие ниже 👇"
    )

    await message.answer(text, reply_markup=main_menu(), parse_mode="Markdown")

@dp.callback_query(lambda c: c.data == "subscription")
async def subscription(callback: types.CallbackQuery):
    uid = callback.from_user.id
    plan, days_left, exp = plan_status(uid)
    month_url, year_url = build_payment_links(uid)

    if plan == "trial":
        status = f"🎁 Триал активен. Осталось: {days_left} дн."
    elif plan in ("month","year"):
        status = f"✅ Активный план: {plan}. До: {exp}"
    else:
        status = "⛔ Триал истёк. Оплатите подписку, чтобы продолжить."

    kb = types.InlineKeyboardMarkup(inline_keyboard=[
        [types.InlineKeyboardButton(text="💳 Оплатить 5 TON / мес", url=month_url)],
        [types.InlineKeyboardButton(text="💎 Оплатить 40 TON / год", url=year_url)],
        [types.InlineKeyboardButton(text="⬅️ В меню", callback_data="help")]
    ])
    await callback.message.edit_text(
        f"🧾 *Подписка*\n\n{status}\n\n"
        "После оплаты бот активирует доступ автоматически в течение ~10 минут.\n"
        "_Важно: ссылка уже содержит ваш UID — оплачивайте только из этого чата._",
        parse_mode="Markdown", reply_markup=kb, disable_web_page_preview=True
    )

@dp.callback_query(lambda c: c.data == "help")
async def help_cb(callback: types.CallbackQuery):
    text = (
        "⚙️ *Команды*\n\n"
        "• `/chart` — пришлёт график (или просто напишите тикер: `BTC`, `ETHUSDT`)\n"
        "• `/train_ai` — обучить модели ИИ\n"
        "• `/stop` — остановить поток сигналов\n"
        "• Кнопки меню — быстрый доступ к функциям"
    )
    await callback.message.edit_text(text, parse_mode="Markdown", reply_markup=main_menu())

@dp.callback_query(lambda c: c.data == "start_ai")
async def start_ai(callback: types.CallbackQuery):
    uid = callback.from_user.id
    if not require_access(uid):
        await callback.message.answer("⛔ Доступ закрыт. *Триал закончился*. Оформите подписку в «🧾 Подписка / триал».", parse_mode="Markdown")
        return
    await callback.message.answer(f"🧠 Запуск AI режима для {current_symbol}…")
    asyncio.create_task(run_ai_stream(callback.message.chat.id))
    await callback.message.answer("🚀 Поток сигналов запущен. Команда /stop остановит текущую сессию.")

ai_tasks = {}

async def run_ai_stream(chat_id):
    global ai_tasks, current_symbol
    if chat_id in ai_tasks and not ai_tasks[chat_id].done():
        await bot.send_message(chat_id, "ℹ️ Поток уже запущен.")
        return
    async def _runner():
        async for s in trader.run_ai_stream(current_symbol):
            direction = "🟢 LONG" if s["direction"] == "LONG" else "🔴 SHORT"
            await bot.send_message(chat_id,
                f"🎯 *Сигнал:* {direction}\n"
                f"💰 *Цена:* {s['price']:.2f}\n"
                f"🧠 *Уверенность:* {s['confidence']*100:.1f}%",
                parse_mode="Markdown"
            )
    ai_tasks[chat_id] = asyncio.create_task(_runner())

@dp.message(Command("chart"))
async def chart(message: types.Message):
    uid = message.from_user.id
    if not require_access(uid):
        await message.answer("⛔ Доступ закрыт. *Триал закончился*. Оформите подписку в «🧾 Подписка / триал».", parse_mode="Markdown")
        return
    await message.answer("Введите символ монеты, например *BTCUSDT*:", parse_mode="Markdown")
    ASK_COIN_USERS.add(uid)

def looks_like_symbol(text):
    return bool(re.fullmatch(r"[A-Za-z]{2,10}([-/]?[A-Za-z]{3,5})?", text.strip()))

@dp.message(Command("help"))

@dp.message(Command("admin"))
async def admin_panel(message: types.Message):
    if not is_admin(message.from_user.id):
        return
    await message.answer(
        "👑 *Админ-панель*\n"
        "• /grant_month <user_id> — выдать месяц\n"
        "• /grant_year <user_id> — выдать год\n"
        "• /block <user_id> — заблокировать доступ\n"
        "• /unblock <user_id> — разблокировать доступ\n"
        "• /referrals — реферальная статистика\n",
        parse_mode="Markdown"
    )

@dp.message(Command("grant_month"))
async def grant_month(message: types.Message):
    if not is_admin(message.from_user.id):
        return
    parts = message.text.split()
    if len(parts)!=2 or not parts[1].isdigit():
        await message.answer("Использование: /grant_month <user_id>"); return
    uid = parts[1]
    from core.subscription_checker import grant_plan
    grant_plan(uid, plan="month", days=30)
    await message.answer(f"✅ Выдан месяц подписки пользователю {uid}")

@dp.message(Command("grant_year"))
async def grant_year(message: types.Message):
    if not is_admin(message.from_user.id):
        return
    parts = message.text.split()
    if len(parts)!=2 or not parts[1].isdigit():
        await message.answer("Использование: /grant_year <user_id>"); return
    uid = parts[1]
    from core.subscription_checker import grant_plan
    grant_plan(uid, plan="year", days=365)
    await message.answer(f"✅ Выдан год подписки пользователю {uid}")

@dp.message(Command("block"))
async def block_user(message: types.Message):
    if not is_admin(message.from_user.id):
        return
    parts = message.text.split()
    if len(parts)!=2 or not parts[1].isdigit():
        await message.answer("Использование: /block <user_id>"); return
    uid = parts[1]
    users = load_users()
    u = users.get(uid, {"start": datetime.datetime.now().isoformat()})
    u["plan"]="blocked"
    u["expires"]=datetime.datetime.now().isoformat()
    users[uid]=u
    save_users(users)
    await message.answer(f"⛔ Пользователь {uid} заблокирован.")

@dp.message(Command("unblock"))
async def unblock_user(message: types.Message):
    if not is_admin(message.from_user.id):
        return
    parts = message.text.split()
    if len(parts)!=2 or not parts[1].isdigit():
        await message.answer("Использование: /unblock <user_id>"); return
    uid = parts[1]
    users = load_users()
    u = users.get(uid, {"start": datetime.datetime.now().isoformat()})
    u["plan"]="trial"
    u.pop("expires", None)
    users[uid]=u
    save_users(users)
    await message.answer(f"✅ Пользователь {uid} разблокирован (переведён на trial).")

async def help_cmd(message: types.Message):
    await message.answer(
        "⚙️ *Команды*\n\n"
        "• `/chart` — пришлёт график (или просто напишите тикер: `BTC`, `ETHUSDT`)\n"
        "• `/train_ai` — обучить модели ИИ\n"
        "• `/stop` — остановить поток сигналов\n"
        "• Кнопки меню — быстрый доступ к функциям",
        parse_mode="Markdown"
    )

@dp.message()
async def handle_text(message: types.Message):
    uid = message.from_user.id
    text = message.text.strip()
    wants_chart = (uid in ASK_COIN_USERS) or looks_like_symbol(text)
    if not wants_chart:
        return
    if not require_access(uid):
        await message.answer("⛔ Доступ закрыт. *Триал закончился*. Оформите подписку в «🧾 Подписка / триал».", parse_mode="Markdown")
        return

    if uid in ASK_COIN_USERS:
        ASK_COIN_USERS.discard(uid)

    symbol = text.upper()
    if not symbol.endswith("USDT"):
        symbol += "USDT"

    data = await trader.fetch_multiple_timeframes(symbol, ["5m"])
    if not data:
        await message.answer("❌ Не удалось получить данные по символу.")
        return
    df = list(data.values())[0]
    df = trader.calculate_all_indicators(df)

    trad = trader.generate_comprehensive_signals(df)
    price = df["close"].iloc[-1]
    atr = df["atr"].iloc[-1] if "atr" in df.columns else price*0.01
    direction = "LONG" if trad.get("final_signal",0) > 0 else "SHORT"
    if direction == "LONG":
        sl = price - 2*atr
        tp = price + 4*atr
    else:
        sl = price + 2*atr
        tp = price - 4*atr

    buf = plot_technical_chart(df, symbol, entry=price, sl=sl, tp=tp)
    await message.answer_photo(
        buf,
        caption=(
            f"📊 *{symbol}*\n"
            f"🎯 Сигнал: *{direction}*\n"
            f"💰 Цена: {price:.2f}\n"
            f"🧠 Уверенность: {trad.get('confidence',0)*100:.1f}%\n"
            f"⛔ SL: {sl:.2f}\n"
            f"🎯 TP: {tp:.2f}\n"
            f"ℹ️ Индикаторы: RSI / MACD / Supertrend"
        ),
        parse_mode="Markdown"
    )

@dp.callback_query(lambda c: c.data == "train_ai")
async def train_ai(callback: types.CallbackQuery):
    uid = callback.from_user.id
    if not require_access(uid):
        await callback.message.answer("⛔ Доступ к обучению — только при активной подписке.")
        return
    await callback.message.answer("🧠 Обучение AI…")
    data = await trader.fetch_multiple_timeframes(current_symbol, ["5m"])
    if not data:
        await callback.message.answer("❌ Нет данных для обучения.")
        return
    df = list(data.values())[0]
    df = trader.calculate_all_indicators(df)
    trader.ai_engine.train_models(df)
    trader.ai_engine.save_models()
    await callback.message.answer("✅ Модели обучены и сохранены.")

@dp.message(Command("train_ai"))
async def train_ai_cmd(message: types.Message):
    # reuse callback logic minimally
    await train_ai(types.CallbackQuery(id="0", from_user=message.from_user, message=message, data="train_ai"))



@dp.callback_query(lambda c: c.data == "share_ref")
async def share_ref(callback: types.CallbackQuery):
    uid = callback.from_user.id
    text = build_share_text(BOT_USERNAME, uid)
    kb = types.InlineKeyboardMarkup(inline_keyboard=[
        [types.InlineKeyboardButton(text="📤 Поделиться", switch_inline_query=text)]
    ])
    await callback.message.answer(
        f"🤝 *Реферальная программа*\n\n"
        f"Бонус: *1 TON* за каждую годовую подписку друга.\n"
        f"Твоя ссылка:\nhttps://t.me/{BOT_USERNAME}?start=ref{uid}\n\n"
        "Отправь её друзьям и получай бонусы!",
        parse_mode="Markdown"
    )

@dp.message(Command("set_ton_address"))
async def set_ton_address(message: types.Message):
    parts = message.text.split(maxsplit=1)
    if len(parts) < 2:
        await message.answer("Укажи адрес TON: `/set_ton_address EQC...`", parse_mode="Markdown")
        return
    addr = parts[1].strip()
    set_referrer_address(message.from_user.id, addr)
    await message.answer(f"✅ Адрес сохранён: `{addr}`", parse_mode="Markdown")

@dp.message(Command("referrals"))
async def referrals_cmd(message: types.Message):
    # Basic summary
    summary = stats_summary()
    await message.answer(summary)

@dp.message(Command("mark_paid"))
async def mark_paid_cmd(message: types.Message):
    # admin marks a specific referral bonus as paid, format: /mark_paid <referrer_id> <user_id>
    parts = message.text.split()
    if len(parts) != 3:
        await message.answer("Использование: `/mark_paid <referrer_id> <user_id>`", parse_mode="Markdown")
        return
    try:
        referrer_id = int(parts[1]); user_id = int(parts[2])
        mark_bonus_sent(referrer_id, user_id)
        await message.answer("✅ Бонус помечен как выплаченный.")
    except:
        await message.answer("❌ Не удалось пометить. Проверьте параметры.")

@dp.message(Command("stop"))
async def stop(message: types.Message):
    t = ai_tasks.get(message.chat.id)
    if t:
        t.cancel()
        await message.answer("🛑 Поток сигналов остановлен для этой сессии.")
    else:
        await message.answer("ℹ️ Активных потоков не найдено.")

async def main():
    if not TOKEN:
        print("❌ TELEGRAM_TOKEN не задан. Добавьте его в .env")
        return
    print("🤖 Quantum Telegram Bot (Premium v2) started")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())


@dp.message(Command("dashboard"))
async def dashboard_link(message: types.Message):
    url = os.getenv("BOT_DASHBOARD_URL","http://localhost:8090")
    await message.answer(f"🔐 Админ-дашборд: {url}")
