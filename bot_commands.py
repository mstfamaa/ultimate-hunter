import requests
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes

TOKEN = "8391034490:AAEJpLAaK3gXg1cglErBH8azmkUSkl3Ip_4"
FLASK_API = "http://localhost:5007/api"

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("مرحباً! أرسل /open BTC لفتح صفقة، /status لعرض صفقاتك")

async def open_trade(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("استخدم: /open BTC")
        return
    symbol = context.args[0].upper()
    try:
        r = requests.post(f"{FLASK_API}/scan", json={"timeframe": "4h"})
        data = r.json()
        coin = next((c for c in data.get("results", []) if c["symbol"] == symbol), None)
        if not coin:
            await update.message.reply_text(f"لا توجد بيانات لـ {symbol}")
            return
        price = coin["current_price"]
        score = coin["score"]
        requests.post(f"{FLASK_API}/open_trade", json={"symbol": symbol, "current_price": price, "score": score, "details": {}})
        await update.message.reply_text(f"✅ تم فتح صفقة {symbol} بسعر {price}")
    except Exception as e:
        await update.message.reply_text(f"خطأ: {e}")

async def status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    r = requests.get(f"{FLASK_API}/trades")
    trades = r.json().get("trades", {})
    if not trades:
        await update.message.reply_text("لا توجد صفقات")
        return
    msg = "صفقاتك:\n"
    for tid, t in trades.items():
        msg += f"- {t['symbol']} | دخول: {t['open_price']} | قوة: {t['open_score']}%\n"
    await update.message.reply_text(msg)

async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data
    if data.startswith("open_"):
        symbol = data.split("_")[1]
        context.args = [symbol]
        await open_trade(update, context)
    elif data.startswith("close_"):
        symbol = data.split("_")[1]
        await update.message.reply_text(f"لإغلاق {symbol} استخدم الأمر /close {symbol} (لم يتم تنفيذه تلقائياً)")
    await query.message.delete()

def run_bot():
    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("open", open_trade))
    app.add_handler(CommandHandler("status", status))
    app.add_handler(CallbackQueryHandler(button_callback))
    print("🤖 بوت التليجرام يعمل...")
    app.run_polling()
