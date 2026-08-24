import re
import requests
import telebot
from telebot import types
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

BOT_TOKEN = "8915046634:AAHf96zZTEQ9fUL368Rbfb-MZnuO8LS3aLg"
bot = telebot.TeleBot(BOT_TOKEN, threaded=False)
app = FastAPI()

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
}

# 1. Курсы валют от ЦБ РФ
def get_cbr_rates():
    url = "https://www.cbr-xml-daily.ru/daily_json.js"
    try:
        res = requests.get(url, headers=HEADERS, timeout=6).json()
        return {
            "USD": float(res["Valute"]["USD"]["Value"]),
            "EUR": float(res["Valute"]["EUR"]["Value"]),
            "CNY": float(res["Valute"]["CNY"]["Value"]),
        }
    except Exception as e:
        print(f"CBR error: {e}")
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
    except Exception as e:
        print(f"Crypto error: {e}")
        return None

def main_keyboard():
    keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=3)
    btn_usd = types.KeyboardButton("🇺🇸 USD (Доллар)")
    btn_eur = types.KeyboardButton("🇪🇺 EUR (Евро)")
    btn_cny = types.KeyboardButton("🇨🇳 CNY (Юань)")
    btn_ton = types.KeyboardButton("💎 TON")
    btn_btc = types.KeyboardButton("🪙 BTC")
    btn_usdt = types.KeyboardButton("💵 USDT")
    btn_all = types.KeyboardButton("📊 Все курсы")
    keyboard.add(btn_usd, btn_eur, btn_cny)
    keyboard.add(btn_ton, btn_btc, btn_usdt)
    keyboard.add(btn_all)
    return keyboard

def parse_user_input(text):
    text = text.strip().lower().replace(",", ".")
    pattern = r"^([\d.\s]+)\s*(\$|usd|доллар\w*|€|eur|евро|¥|cny|юан\w*|ton|тон|btc|биткоин\w*|usdt|тезер|юсдт|₽|rub|руб\w*)?$"
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
        elif cur_raw in ["₽", "rub"] or "руб" in cur_raw:
            cur = "RUB"
    return amount, cur

@bot.message_handler(commands=['start', 'help'])
def start_handler(message):
    text = (
        "👋 **Бот-конвертер валют и криптовалют**\n\n"
        "• Нажимайте кнопки на клавиатуре для просмотра курса.\n"
        "• **Валюта в рубли:** `1000$`, `250 eur`, `500 cny`, `20 ton`\n"
        "• **Рубли во всё:** `50000 руб`, `100000₽`"
    )
    bot.send_message(message.chat.id, text, reply_markup=main_keyboard(), parse_mode="Markdown")

@bot.message_handler(content_types=['text'])
def message_handler(message):
    txt = message.text.lower().strip()

    # 1. Проверка на кнопки валют
    if "usd" in txt or "доллар" in txt:
        cbr = get_cbr_rates()
        if cbr:
            bot.send_message(message.chat.id, f"💵 **1 USD** = `{cbr['USD']:.2f}` ₽", parse_mode="Markdown")
        else:
            bot.send_message(message.chat.id, "⚠️ Ошибка получения курса USD.")
        return

    elif "eur" in txt or "евро" in txt:
        cbr = get_cbr_rates()
        if cbr:
            bot.send_message(message.chat.id, f"💶 **1 EUR** = `{cbr['EUR']:.2f}` ₽", parse_mode="Markdown")
        else:
            bot.send_message(message.chat.id, "⚠️ Ошибка получения курса EUR.")
        return

    elif "cny" in txt or "юань" in txt or "юан" in txt:
        cbr = get_cbr_rates()
        if cbr:
            bot.send_message(message.chat.id, f"💴 **1 CNY** = `{cbr['CNY']:.2f}` ₽", parse_mode="Markdown")
        else:
            bot.send_message(message.chat.id, "⚠️ Ошибка получения курса CNY.")
        return

    elif "ton" in txt or "тон" in txt:
        crypto = get_crypto_rates()
        if crypto:
            bot.send_message(message.chat.id, f"💎 **1 TON** = `{crypto['TON']['rub']:,.2f}` ₽ (${crypto['TON']['usd']:.2f})".replace(",", " "), parse_mode="Markdown")
        else:
            bot.send_message(message.chat.id, "⚠️ Ошибка получения курса TON.")
        return

    elif "btc" in txt or "биткоин" in txt:
        crypto = get_crypto_rates()
        if crypto:
            bot.send_message(message.chat.id, f"🪙 **1 BTC** = `{crypto['BTC']['rub']:,.0f}` ₽ (${crypto['BTC']['usd']:,.0f})".replace(",", " "), parse_mode="Markdown")
        else:
            bot.send_message(message.chat.id, "⚠️ Ошибка получения курса BTC.")
        return

    elif "usdt" in txt or "тезер" in txt:
        crypto = get_crypto_rates()
        if crypto:
            bot.send_message(message.chat.id, f"💵 **1 USDT** = `{crypto['USDT']['rub']:.2f}` ₽ (${crypto['USDT']['usd']:.2f})", parse_mode="Markdown")
        else:
            bot.send_message(message.chat.id, "⚠️ Ошибка получения курса USDT.")
        return

    elif "все курсы" in txt:
        cbr = get_cbr_rates()
        crypto = get_crypto_rates()
        if not cbr or not crypto:
            bot.send_message(message.chat.id, "⚠️ Сервер курсов временно недоступен.")
            return

        text = (
            f"🏦 **Курсы валют ЦБ РФ:**\n"
            f"🇺🇸 1 USD = `{cbr['USD']:.2f}` ₽\n"
            f"🇪🇺 1 EUR = `{cbr['EUR']:.2f}` ₽\n"
            f"🇨🇳 1 CNY = `{cbr['CNY']:.2f}` ₽\n\n"
            f"🚀 **Криптовалюты:**\n"
            f"💎 1 TON = `{crypto['TON']['rub']:,.2f}` ₽ (${crypto['TON']['usd']:.2f})\n"
            f"🪙 1 BTC = `{crypto['BTC']['rub']:,.0f}` ₽ (${crypto['BTC']['usd']:,.0f})\n"
            f"💵 1 USDT = `{crypto['USDT']['rub']:.2f}` ₽"
        ).replace(",", " ")
        bot.send_message(message.chat.id, text, parse_mode="Markdown")
        return

    # 2. Обработка ввода сумм (конвертация)
    amount, cur = parse_user_input(message.text)
    if amount is not None:
        cbr = get_cbr_rates()
        crypto = get_crypto_rates()
        if not cbr or not crypto:
            bot.send_message(message.chat.id, "⚠️ Не удалось получить курсы для конвертации.")
            return

        if cur == "RUB":
            usd_res = amount / cbr["USD"]
            ton_res = amount / crypto["TON"]["rub"]
            btc_res = amount / crypto["BTC"]["rub"]
            usdt_res = amount / crypto["USDT"]["rub"]
            text = (
                f"🪙 **{amount:,.2f} ₽** — это:\n\n"
                f"🇺🇸 `{usd_res:,.2f}` USD\n"
                f"💵 `{usdt_res:,.2f}` USDT\n"
                f"💎 `{ton_res:,.2f}` TON\n"
                f"🪙 `{btc_res:.6f}` BTC"
            ).replace(",", " ")
            bot.send_message(message.chat.id, text, parse_mode="Markdown")
        elif cur in ["USD", "EUR", "CNY"]:
            total = amount * cbr[cur]
            flags = {"USD": "🇺🇸", "EUR": "🇪🇺", "CNY": "🇨🇳"}
            bot.send_message(message.chat.id, f"{flags[cur]} **{amount:g} {cur}** = `{total:,.2f}` ₽".replace(",", " "), parse_mode="Markdown")
        elif cur in ["TON", "BTC", "USDT"]:
            total_rub = amount * crypto[cur]["rub"]
            total_usd = amount * crypto[cur]["usd"]
            icons = {"TON": "💎", "BTC": "🪙", "USDT": "💵"}
            bot.send_message(message.chat.id, f"{icons[cur]} **{amount:g} {cur}** = `{total_rub:,.2f}` ₽ (`${total_usd:,.2f}`)".replace(",", " "), parse_mode="Markdown")
    else:
        bot.send_message(
            message.chat.id,
            "Формат не распознан. Примеры:\n`25 ton`\n`500$`\n`100 000 руб`",
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
