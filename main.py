from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, CallbackQueryHandler, ContextTypes
import yfinance as yf
import pandas as pd
import logging

logging.basicConfig(format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO)

TOKEN = "8199814346:AAE3y0kpOswMDDG3R4ayv33nbs7IPV2LLDM"

SYMBOLS = {
    "EUR/USD": "EURUSD=X",
    "GBP/USD": "GBPUSD=X",
    "USD/JPY": "USDJPY=X",
    "USD/CHF": "USDCHF=X",
    "AUD/USD": "AUDUSD=X"
}

DURATIONS = ['5s', '15s', '30s', '1m', '2m']

user_selections = {}

async def analyze(symbol):
    data = yf.download(symbol, period='1d', interval='1m')
    if data.empty:
        return "لا توجد بيانات حالياً للتحليل."

    df = data.tail(50)
    df['MA'] = df['Close'].rolling(window=10).mean()
    df['STD'] = df['Close'].rolling(window=10).std()
    df['Upper'] = df['MA'] + (2 * df['STD'])
    df['Lower'] = df['MA'] - (2 * df['STD'])
    delta = df['Close'].diff()
    gain = delta.where(delta > 0, 0.0)
    loss = -delta.where(delta < 0, 0.0)
    avg_gain = gain.rolling(window=14).mean()
    avg_loss = loss.rolling(window=14).mean()
    rs = avg_gain / avg_loss
    df['RSI'] = 100 - (100 / (1 + rs))

    last = df.iloc[-1]
    rsi = round(last['RSI'], 2)
    close = last['Close']
    upper = last['Upper']
    lower = last['Lower']
    ma = round(last['MA'], 2)

    signal = "BUY" if rsi < 30 and close < lower else "SELL" if rsi > 70 and close > upper else "NEUTRAL"

    analysis = f"RSI: {rsi}\nMA: {ma}\nBB Upper: {round(upper,2)}\nBB Lower: {round(lower,2)}\nSignal: {signal}"
    return analysis

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [[InlineKeyboardButton(symbol, callback_data=f'symbol_{symbol}')] for symbol in SYMBOLS.keys()]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text("اختر الزوج (العملة):", reply_markup=reply_markup)

async def handle_symbol(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    symbol = query.data.split('_', 1)[1]
    user_id = query.from_user.id
    user_selections[user_id] = {"symbol": symbol}

    keyboard = [[InlineKeyboardButton(duration, callback_data=f'duration_{duration}')] for duration in DURATIONS]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text(f"اختر المدة الزمنية للتحليل ({symbol}):", reply_markup=reply_markup)

async def handle_duration(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    duration = query.data.split('_', 1)[1]
    user_id = query.from_user.id

    if user_id not in user_selections or "symbol" not in user_selections[user_id]:
        await query.edit_message_text("يرجى اختيار الزوج أولاً باستخدام /start.")
        return

    symbol = user_selections[user_id]["symbol"]
    user_selections[user_id]["duration"] = duration
    analysis = await analyze(SYMBOLS[symbol])

    keyboard = [
        [InlineKeyboardButton("تغيير الزوج", callback_data="change_pair")],
        [InlineKeyboardButton("إعادة التحليل", callback_data="reanalyze")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await query.edit_message_text(f"التحليل ({symbol}, {duration}):\n\n{analysis}", reply_markup=reply_markup)

async def change_pair(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    user_selections.pop(user_id, None)

    keyboard = [[InlineKeyboardButton(symbol, callback_data=f'symbol_{symbol}')] for symbol in SYMBOLS.keys()]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text("اختر الزوج (العملة):", reply_markup=reply_markup)

async def reanalyze(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    data = user_selections.get(user_id)

    if not data or "symbol" not in data or "duration" not in data:
        await query.edit_message_text("لا توجد معلومات محفوظة. أرسل /start.")
        return

    symbol = data["symbol"]
    duration = data["duration"]
    analysis = await analyze(SYMBOLS[symbol])

    keyboard = [
        [InlineKeyboardButton("تغيير الزوج", callback_data="change_pair")],
        [InlineKeyboardButton("إعادة التحليل", callback_data="reanalyze")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text(f"التحليل ({symbol}, {duration}):\n\n{analysis}", reply_markup=reply_markup)

def main():
    app = ApplicationBuilder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(handle_symbol, pattern='^symbol_'))
    app.add_handler(CallbackQueryHandler(handle_duration, pattern='^duration_'))
    app.add_handler(CallbackQueryHandler(change_pair, pattern='^change_pair$'))
    app.add_handler(CallbackQueryHandler(reanalyze, pattern='^reanalyze$'))
    print("البوت يعمل الآن...")
    app.run_polling()

if __name__ == '__main__':
    main()
