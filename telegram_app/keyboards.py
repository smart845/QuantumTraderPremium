
from aiogram.utils.keyboard import InlineKeyboardBuilder

SYMBOLS = ["BTCUSDT","ETHUSDT","BNBUSDT","SOLUSDT","XRPUSDT","TONUSDT"]

def main_menu():
    kb = InlineKeyboardBuilder()
    kb.button(text="🚀 Начать AI-торговлю", callback_data="start_ai")
    kb.button(text="📊 График монеты", callback_data="ask_coin")
    kb.button(text="💰 Обучить ИИ", callback_data="train_ai")
    kb.button(text="⚙️ Команды и помощь", callback_data="help")
    kb.button(text="🧾 Подписка / триал", callback_data="subscription")
    kb.button(text="🤝 Пригласить друга", callback_data="share_ref")
    kb.adjust(2)
    return kb.as_markup()

def symbols_menu():
    kb = InlineKeyboardBuilder()
    for s in SYMBOLS:
        kb.button(text=s, callback_data=f"set_coin:{s}")
    kb.adjust(3)
    return kb.as_markup()
