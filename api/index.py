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

# 1. Получение курсов ЦБ РФ
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

# 2. Получение курсов криптовалют
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

# Главная клавиатура
def main_keyboard():
    keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=3)
    keyboard.add(types.KeyboardButton("🇺🇸 USD"), types.KeyboardButton("🇪🇺 EUR"), types.KeyboardButton("🇨🇳 CNY"))
    keyboard.add(types.KeyboardButton("💎 TON"), types.KeyboardButton("🪙 BTC"), types.KeyboardButton("💵 USDT"))
    keyboard.add(types.KeyboardButton("⭐ Telegram Stars"), types.KeyboardButton("📊 Все курсы"))
    return keyboard

# Инлайн-кнопка обновления
def refresh_markup(target):
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("🔄 Обновить", callback_data=f"refresh_{target}"))
    return markup

# Текст отдельного курса для отправки/обновления
def get_single_rate_text(target, cbr, crypto):
    if target == "usd":
        diff = format_trend(cbr['USD']['val'], cbr['USD']['prev'])
        return f"💵 **1 USD** = `{cbr['USD']['val']:.2f}` ₽ {diff}"
    elif target == "eur":
        diff = format_trend(cbr['EUR']['val'], cbr['EUR']['prev'])
        return f"💶 **1 EUR** = `{cbr['EUR']['val']:.2f}` ₽ {diff}"
    elif target == "cny":
        diff = format_trend(cbr['CNY']['val'], cbr['CNY']['prev'])
        return f"💴 **1 CNY** = `{cbr['CNY']['val']:.2f}` ₽ {diff}"
    elif target == "ton":
        return f"💎 **1 TON** = `{crypto['TON']['rub']:,.2f}` ₽ (`${crypto['TON']['usd']:.2f}`)".replace(",", " ")
    elif target == "btc":
        return f"🪙 **1 BTC** = `{crypto['BTC']['rub']:,.0f}` ₽ (`${crypto['BTC']['usd']:,.0f}`)".replace(",", " ")
    elif target == "usdt":
        return f"💵 **1 USDT** = `{crypto['USDT']['rub']:.2f}` ₽ (`${crypto['USDT']['usd']:.2f}`)"
    elif target == "stars":
        star_rub = 0.02 * cbr['USD']['val']
        ton_price_usd = crypto['TON']['usd']
        ton_for_100_stars = (100 * 0.02) / ton_price_usd if ton_price_usd > 0 else 0
        return (
            f"⭐ **Telegram Stars:**\n\n"
            f"• 1 Star = `$0.02` (`{star_rub:.2f}` ₽)\n"
            f"• 100 Stars = `$2.00` (`{star_rub * 100:,.2f}` ₽ ≈ `{ton_for_100_stars:.2f}` TON)\n"
            f"• 500 Stars = `$10.00` (`{star_rub * 500:,.2f}` ₽ ≈ `{ton_for_100_stars * 5:.2f}` TON)\n"
            f"• 1 000 Stars = `$20.00` (`{star_rub * 1000:,.2f}` ₽ ≈ `{ton_for_100_stars * 10:.2f}` TON)"
        ).replace(",", " ")
    elif target == "all":
        star_rub = 0.02 * cbr['USD']['val']
        return (
            f"🏦 **Курсы ЦБ РФ:**\n"
            f"🇺🇸 1 USD = `{cbr['USD']['val']:.2f}` ₽ {format_trend(cbr['USD']['val'], cbr['USD']['prev'])}\n"
            f"🇪🇺 1 EUR = `{cbr['EUR']['val']:.2f}` ₽ {format_trend(cbr['EUR']['val'], cbr['EUR']['prev'])}\n"
            f"🇨🇳 1 CNY = `{cbr['CNY']['val']:.2f}` ₽ {format_trend(cbr['CNY']['val'], cbr['CNY']['prev'])}\n\n"
            f"🚀 **Криптовалюты:**\n"
            f"💎 1 TON = `{crypto['TON']['rub']:,.2f}` ₽ (${crypto['TON']['usd']:.2f})\n"
            f"🪙 1 BTC = `{crypto['BTC']['rub']:,.0f}` ₽ (${crypto['BTC']['usd']:,.0f})\n"
            f"💵 1 USDT = `{crypto['USDT']['rub']:.2f}` ₽\n"
            f"⭐ 100 Stars = `{star_rub * 100:,.2f}` ₽ ($2.00)"
        ).replace(",", " ")
    return "Неизвестный тип"

# Распознавание команд кнопок
def detect_button(text):
    t = text.lower().strip()
    if re.search(r"usd|доллар", t) and not re.search(r"\d", t):
        return "usd"
    if re.search(r"eur|евро", t) and not re.search(r"\d", t):
        return "eur"
    if re.search(r"cny|юан", t) and not re.search(r"\d", t):
        return "cny"
    if re.search(r"ton|тон", t) and not re.search(r"\d", t):
        return "ton"
    if re.search(r"btc|биткоин", t) and not re.search(r"\d", t):
        return "btc"
    if re.search(r"usdt|тезер|юсдт", t) and not re.search(r"\d", t):
        return "usdt"
    if re.search(r"star|звезд", t) and not re.search(r"\d", t):
        return "stars"
    if re.search(r"все курс", t):
        return "all"
    return None

# Распознавание сумм
def parse_user_input(text):
    text = text.strip().lower().replace(",", ".")
    # Ищем число (целое или дробное)
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
        "👋 **Бот-конвертер валют, крипты и Telegram Stars**\n\n"
        "• Нажимайте кнопки внизу для моментального курса.\n"
        "• **Суммы:** `500 ton`, `200 usdt`, `1000$`, `540 stars`\n"
        "• **Из рублей:** `50000 руб`, `100000₽`"
    )
    bot.send_message(message.chat.id, text, reply_markup=main_keyboard(), parse_mode="Markdown")

@bot.callback_query_handler(func=lambda call: call.data.startswith("refresh_"))
def callback_refresh(call):
    target = call.data.replace("refresh_", "")
    cbr = get_cbr_rates()
    crypto = get_crypto_rates()
    if not cbr or not crypto:
        bot.answer_callback_query(call.id, "⚠️ Ошибка обновления данных")
        return

    text = get_single_rate_text(target, cbr, crypto)
    try:
        bot.edit_message_text(text, call.message.chat.id, call.message.message_id, reply_markup=refresh_markup(target), parse_mode="Markdown")
        bot.answer_callback_query(call.id, "Курс обновлен! ✅")
    except Exception:
        bot.answer_callback_query(call.id, "Курс уже актуален.")

@bot.message_handler(content_types=['text'])
def message_handler(message):
    txt = message.text.strip()

    # 1. Проверяем, нажата ли кнопка меню (без цифр)
    btn_target = detect_button(txt)
    if btn_target:
        cbr = get_cbr_rates()
        crypto = get_crypto_rates()
        if not cbr or not crypto:
            bot.send_message(message.chat.id, "⚠️ Сервер курсов временно недоступен.")
            return

        text = get_single_rate_text(btn_target, cbr, crypto)
        bot.send_message(message.chat.id, text, reply_markup=refresh_markup(btn_target), parse_mode="Markdown")
        return

    # 2. Обрабатываем числовой ввод (конвертацию)
    amount, cur = parse_user_input(txt)
    if amount is not None:
        cbr = get_cbr_rates()
        crypto = get_crypto_rates()
        if not cbr or not crypto:
            bot.send_message(message.chat.id, "⚠️ Не удалось получить курсы.")
            return

        star_price_usd = 0.02
        star_price_rub = star_price_usd * cbr["USD"]["val"]
        ton_price_usd = crypto["TON"]["usd"]

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
            total = amount * cbr[cur]["val"]
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
            total_ton = total_usd / ton_price_usd if ton_price_usd > 0 else 0
            text = (
                f"⭐ **{int(amount):,} Stars** — это:\n\n"
                f"💵 `${total_usd:,.2f}` USD\n"
                f"🪙 `{total_rub:,.2f}` ₽\n"
                f"💎 `{total_ton:,.2f}` TON"
            ).replace(",", " ")
            bot.send_message(message.chat.id, text, parse_mode="Markdown")
    else:
        bot.send_message(
            message.chat.id,
            "Формат не распознан. Примеры:\n`500 ton`\n`200 usdt`\n`540 stars`\n`50000 руб`",
            parse_mode="Markdown"
        )

# Serverless webhook эндпоинт
@app.post("/")
async def webhook_handler(request: Request):
    json_data = await request.json()
    update = telebot.types.Update.de_json(json_data)
    bot.process_new_updates([update])
    return JSONResponse(status_code=200, content={"status": "ok"})

@app.get("/")
def root():
    return {"status": "Bot is alive and running 24/7"}
