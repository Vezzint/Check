import re
import requests
import telebot
from telebot import types
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

BOT_TOKEN = "8915046634:AAHf96zZTEQ9fUL368Rbfb-MZnuO8LS3aLg"
bot = telebot.TeleBot(BOT_TOKEN, threaded=False)
app = FastAPI()

HEADERS = {"User-Agent": "Mozilla/5.0"}

# 1. Курсы фиата от ЦБ РФ (включая динамику изменения)
def get_cbr_rates():
    url = "https://www.cbr-xml-daily.ru/daily_json.js"
    try:
        res = requests.get(url, headers=HEADERS, timeout=6).json()
        val = res["Valute"]
        return {
            "USD": {"val": float(val["USD"]["Value"]), "prev": float(val["USD"]["Previous"])},
            "EUR": {"val": float(val["EUR"]["Value"]), "prev": float(val["EUR"]["Previous"])},
            "CNY": {"val": float(val["CNY"]["Value"]), "prev": float(val["CNY"]["Previous"])},
        }
    except Exception:
        return None

# 2. Курсы криптовалют
def get_crypto_rates():
    url = "https://api.coingecko.com/api/v3/simple/price"
    params = {"ids": "the-open-network,bitcoin,tether", "vs_currencies": "rub,usd"}
    try:
        res = requests.get(url, params=params, headers=HEADERS, timeout=6).json()
        return {
            "TON": {"rub": float(res["the-open-network"]["rub"]), "usd": float(res["the-open-network"]["usd"])},
            "BTC": {"rub": float(res["bitcoin"]["rub"]), "usd": float(res["bitcoin"]["usd"])},
            "USDT": {"rub": float(res["tether"]["rub"]), "usd": float(res["tether"]["usd"])},
        }
    except Exception:
        return None

def format_trend(current, previous):
    diff = current - previous
    arrow = "📈 +" if diff >= 0 else "📉 "
    return f"({arrow}{diff:.2f} ₽)"

def main_keyboard():
    keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=3)
    keyboard.add(types.KeyboardButton("🇺🇸 USD"), types.KeyboardButton("🇪🇺 EUR"), types.KeyboardButton("🇨🇳 CNY"))
    keyboard.add(types.KeyboardButton("💎 TON"), types.KeyboardButton("🪙 BTC"), types.KeyboardButton("💵 USDT"))
    keyboard.add(types.KeyboardButton("⭐ Telegram Stars"), types.KeyboardButton("📊 Все курсы"))
    return keyboard

# Извлечение числа и валюты
def parse_user_input(text):
    text = text.strip().lower().replace(",", ".")
    pattern = r"^([\d.\s]+)\s*(\$|usd|доллар\w*|€|eur|евро|¥|cny|юан\w*|ton|тон|btc|биткоин\w*|usdt|тезер|юсдт|⭐|star\w*|звезд\w*|₽|rub|руб\w*)?$"
    match = re.match(pattern, text)
    if not match:
        return None, None

    raw_amount = match.group(1).replace(" ", "")
    try:
        amount = float(raw_amount)
    except ValueError:
        return None, None

    cur_raw = match.group(2)
    cur = "USD"
    if cur_raw:
        if cur_raw in ["$", "usd"] or "доллар" in cur_raw:
            cur = "USD"
        elif cur_raw in ["€", "eur", "евро"]:
            cur = "EUR"
        elif cur_raw in ["¥", "cny"] or "юан" in cur_raw:
            cur = "CNY"
        elif cur_raw in ["ton", "тон"]:
            cur = "TON"
        elif cur_raw in ["btc", "биткоин"]:
            cur = "BTC"
        elif cur_raw in ["usdt", "тезер", "юсдт"]:
            cur = "USDT"
        elif cur_raw in ["⭐", "star", "stars"] or "звезд" in cur_raw:
            cur = "STARS"
        elif cur_raw in ["₽", "rub"] or "руб" in cur_raw:
            cur = "RUB"
    return amount, cur

@bot.message_handler(commands=['start', 'help'])
def start_handler(message):
    text = (
        "👋 **Бот-конвертер валют и криптовалют**\n\n"
        "• Нажимайте кнопки на клавиатуре для быстрого просмотра курса.\n"
        "• **Конвертация валюты/крипты:** `500 ton`, `200 usdt`, `1000$`, `50 eur`, `50 stars`\n"
        "• **Конвертация из рублей:** `50000 руб`, `100000₽`"
    )
    bot.send_message(message.chat.id, text, reply_markup=main_keyboard(), parse_mode="Markdown")

@bot.message_handler(content_types=['text'])
def message_handler(message):
    txt = message.text.strip()

    # Сначала проверяем, не ввел ли пользователь число для конвертации
    amount, cur = parse_user_input(txt)
    
    if amount is not None:
        cbr = get_cbr_rates()
        crypto = get_crypto_rates()
        if not cbr or not crypto:
            bot.send_message(message.chat.id, "⚠️ Ошибка получения курсов. Попробуйте через минуту.")
            return

        star_price_usd = 0.02  # Официальная базовая цена 1 Stars = $0.02
        star_price_rub = star_price_usd * cbr["USD"]["val"]

        if cur == "RUB":
            usd_res = amount / cbr["USD"]["val"]
            eur_res = amount / cbr["EUR"]["val"]
            ton_res = amount / crypto["TON"]["rub"]
            usdt_res = amount / crypto["USDT"]["rub"]
            btc_res = amount / crypto["BTC"]["rub"]
            stars_res = amount / star_price_rub

            text = (
                f"🪙 **{amount:,.2f} ₽** — это:\n\n"
                f"🇺🇸 `{usd_res:,.2f}` USD\n"
                f"💶 `{eur_res:,.2f}` EUR\n"
                f"💵 `{usdt_res:,.2f}` USDT\n"
                f"💎 `{ton_res:,.2f}` TON\n"
                f"⭐ `{int(stars_res):,}` Stars\n"
                f"🪙 `{btc_res:.6f}` BTC"
            ).replace(",", " ")
            bot.send_message(message.chat.id, text, parse_mode="Markdown")

        elif cur in ["USD", "EUR", "CNY"]:
            rate = cbr[cur]["val"]
            total = amount * rate
            flags = {"USD": "🇺🇸", "EUR": "🇪🇺", "CNY": "🇨🇳"}
            bot.send_message(message.chat.id, f"{flags[cur]} **{amount:g} {cur}** = `{total:,.2f}` ₽".replace(",", " "), parse_mode="Markdown")

        elif cur in ["TON", "BTC", "USDT"]:
            total_rub = amount * crypto[cur]["rub"]
            total_usd = amount * crypto[cur]["usd"]
            icons = {"TON": "💎", "BTC": "🪙", "USDT": "💵"}
            bot.send_message(message.chat.id, f"{icons[cur]} **{amount:g} {cur}** = `{total_rub:,.2f}` ₽ (`${total_usd:,.2f}`)".replace(",", " "), parse_mode="Markdown")

        elif cur == "STARS":
            total_rub = amount * star_price_rub
            total_usd = amount * star_price_usd
            bot.send_message(message.chat.id, f"⭐ **{int(amount)} Stars** = `{total_rub:,.2f}` ₽ (`${total_usd:,.2f}`)".replace(",", " "), parse_mode="Markdown")
        return

    # Обработка нажатий кнопок меню
    cbr = get_cbr_rates()
    crypto = get_crypto_rates()

    if txt == "🇺🇸 USD":
        diff = format_trend(cbr['USD']['val'], cbr['USD']['prev'])
        bot.send_message(message.chat.id, f"💵 **1 USD** = `{cbr['USD']['val']:.2f}` ₽ {diff}", parse_mode="Markdown")
    elif txt == "🇪🇺 EUR":
        diff = format_trend(cbr['EUR']['val'], cbr['EUR']['prev'])
        bot.send_message(message.chat.id, f"💶 **1 EUR** = `{cbr['EUR']['val']:.2f}` ₽ {diff}", parse_mode="Markdown")
    elif txt == "🇨🇳 CNY":
        diff = format_trend(cbr['CNY']['val'], cbr['CNY']['prev'])
        bot.send_message(message.chat.id, f"💴 **1 CNY** = `{cbr['CNY']['val']:.2f}` ₽ {diff}", parse_mode="Markdown")
    elif txt == "💎 TON":
        bot.send_message(message.chat.id, f"💎 **1 TON** = `{crypto['TON']['rub']:,.2f}` ₽ (${crypto['TON']['usd']:.2f})".replace(",", " "), parse_mode="Markdown")
    elif txt == "🪙 BTC":
        bot.send_message(message.chat.id, f"🪙 **1 BTC** = `{crypto['BTC']['rub']:,.0f}` ₽ (${crypto['BTC']['usd']:,.0f})".replace(",", " "), parse_mode="Markdown")
    elif txt == "💵 USDT":
        bot.send_message(message.chat.id, f"💵 **1 USDT** = `{crypto['USDT']['rub']:.2f}` ₽ (${crypto['USDT']['usd']:.2f})", parse_mode="Markdown")
    elif txt == "⭐ Telegram Stars":
        star_rub = 0.02 * cbr['USD']['val']
        text = (
            f"⭐ **Telegram Stars (Звёзды):**\n\n"
            f"• 1 Star = `$0.02` (`{star_rub:.2f}` ₽)\n"
            f"• 50 Stars = `$1.00` (`{star_rub * 50:,.2f}` ₽)\n"
            f"• 100 Stars = `$2.00` (`{star_rub * 100:,.2f}` ₽)\n"
            f"• 500 Stars = `$10.00` (`{star_rub * 500:,.2f}` ₽)"
        ).replace(",", " ")
        bot.send_message(message.chat.id, text, parse_mode="Markdown")
    elif txt == "📊 Все курсы":
        text = (
            f"🏦 **Курсы ЦБ РФ:**\n"
            f"🇺🇸 1 USD = `{cbr['USD']['val']:.2f}` ₽ {format_trend(cbr['USD']['val'], cbr['USD']['prev'])}\n"
            f"🇪🇺 1 EUR = `{cbr['EUR']['val']:.2f}` ₽ {format_trend(cbr['EUR']['val'], cbr['EUR']['prev'])}\n"
            f"🇨🇳 1 CNY = `{cbr['CNY']['val']:.2f}` ₽ {format_trend(cbr['CNY']['val'], cbr['CNY']['prev'])}\n\n"
            f"🚀 **Криптовалюты:**\n"
            f"💎 1 TON = `{crypto['TON']['rub']:,.2f}` ₽ (${crypto['TON']['usd']:.2f})\n"
            f"🪙 1 BTC = `{crypto['BTC']['rub']:,.0f}` ₽ (${crypto['BTC']['usd']:,.0f})\n"
            f"💵 1 USDT = `{crypto['USDT']['rub']:.2f}` ₽\n"
            f"⭐ 50 Stars = `${50 * 0.02:.2f}` (`{50 * 0.02 * cbr['USD']['val']:.2f}` ₽)"
        ).replace(",", " ")
        bot.send_message(message.chat.id, text, parse_mode="Markdown")
    else:
        bot.send_message(
            message.chat.id,
            "Формат не распознан. Примеры:\n`500 ton`\n`200 usdt`\n`50 stars`\n`100 000 руб`",
            parse_mode="Markdown"
        )

@app.post("/")
async def webhook_handler(request: Request):
    json_data = await request.json()
    update = telebot.types.Update.de_json(json_data)
    bot.process_new_updates([update])
    return JSONResponse(status_code=200, content={"status": "ok"})

@app.get("/")
def root():
    return {"status": "Bot webhook is active"}
