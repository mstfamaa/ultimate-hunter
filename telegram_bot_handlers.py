import threading
import time
import asyncio
import requests
import sqlite3
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes
from subscription_manager import (
    add_subscriber, remove_subscriber, get_active_subscribers,
    get_subscription_status, add_pending_request, get_pending_requests,
    approve_request, remove_pending_request, get_user_tier
)
from telegram_bot import telegram_bot

TOKEN = "8391034490:AAEJpLAaK3gXg1cglErBH8azmkUSkl3Ip_4"
ADMIN_IDS = [5796394289]
FLASK_API = "http://localhost:5007/api"
DB_PATH = "subscriptions.db"

def is_admin(user_id):
    return user_id in ADMIN_IDS

def get_main_keyboard(user_id):
    is_admin_user = is_admin(user_id)
    status = get_subscription_status(user_id)
    
    # صف أول: تشغيل وإيقاف التحليل
    row1 = [InlineKeyboardButton("🔍 تشغيل التحليل", callback_data="run_scan"),
            InlineKeyboardButton("⏹️ إيقاف التحليل", callback_data="stop_scan")]
    
    # صف ثاني: اختيار القسم والعتبة والفريم
    row2 = [InlineKeyboardButton("📂 القسم", callback_data="select_section"),
            InlineKeyboardButton("🎯 العتبة", callback_data="select_threshold"),
            InlineKeyboardButton("⏱️ الفريم", callback_data="select_timeframe")]
    
    buttons = [row1, row2]
    
    # أزرار الأدمن
    if is_admin_user:
        buttons.append([InlineKeyboardButton("⚙️ لوحة التحكم", callback_data="admin_panel")])
    
    # أزرار التحليل الرئيسية
    buttons.append([InlineKeyboardButton("📊 تحليل عملة", callback_data="analyze_menu")])
    buttons.append([InlineKeyboardButton("📈 أفضل العملات", callback_data="top_coins")])
    buttons.append([InlineKeyboardButton("📋 صفقاتي", callback_data="my_trades")])
    buttons.append([InlineKeyboardButton("🔔 تنبيهاتي", callback_data="my_alerts")])
    buttons.append([InlineKeyboardButton("ℹ️ معلومات البوت", callback_data="bot_info")])
    
    status_text = f"📊 حالتك: {status}"
    return InlineKeyboardMarkup(buttons), status_text

def get_section_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("📂 القسم 1 (100 عملة)", callback_data="section_1"),
         InlineKeyboardButton("📂 القسم 2 (100 عملة)", callback_data="section_2")],
        [InlineKeyboardButton("📂 القسم 3 (100 عملة)", callback_data="section_3"),
         InlineKeyboardButton("📂 القسم 4 (100 عملة)", callback_data="section_4")],
        [InlineKeyboardButton("📂 القسم 5 (47 عملة)", callback_data="section_5")],
        [InlineKeyboardButton("🔙 رجوع", callback_data="main_menu")],
    ])

def get_threshold_keyboard(current=4):
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("✅ 2 شروط (سهل)" if current==2 else "2 شروط (سهل)", callback_data="threshold_2"),
         InlineKeyboardButton("✅ 3 شروط (متوسط)" if current==3 else "3 شروط (متوسط)", callback_data="threshold_3")],
        [InlineKeyboardButton("✅ 4 شروط (افتراضي)" if current==4 else "4 شروط (افتراضي)", callback_data="threshold_4"),
         InlineKeyboardButton("✅ 5 شروط (صعب)" if current==5 else "5 شروط (صعب)", callback_data="threshold_5")],
        [InlineKeyboardButton("✅ 6 شروط (صارم)" if current==6 else "6 شروط (صارم)", callback_data="threshold_6")],
        [InlineKeyboardButton("🔙 رجوع", callback_data="main_menu")],
    ])

def get_timeframe_keyboard(current="4h"):
    timeframes = ["5m", "15m", "1h", "4h", "1d", "1M"]
    keyboard = []
    row = []
    for tf in timeframes:
        emoji = "✅ " if tf == current else ""
        row.append(InlineKeyboardButton(f"{emoji}{tf}", callback_data=f"timeframe_{tf}"))
        if len(row) == 3:
            keyboard.append(row)
            row = []
    if row:
        keyboard.append(row)
    keyboard.append([InlineKeyboardButton("🔙 رجوع", callback_data="main_menu")])
    return InlineKeyboardMarkup(keyboard)

def get_admin_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("📋 طلبات الاشتراك", callback_data="pending_requests")],
        [InlineKeyboardButton("👥 المشتركين", callback_data="active_users")],
        [InlineKeyboardButton("🔙 القائمة الرئيسية", callback_data="main_menu")],
    ])

def get_analyze_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🟠 BTC", callback_data="analyze_BTC"),
         InlineKeyboardButton("🟣 ETH", callback_data="analyze_ETH"),
         InlineKeyboardButton("🟢 SOL", callback_data="analyze_SOL")],
        [InlineKeyboardButton("🟡 BNB", callback_data="analyze_BNB"),
         InlineKeyboardButton("🔵 XRP", callback_data="analyze_XRP"),
         InlineKeyboardButton("🐕 DOGE", callback_data="analyze_DOGE")],
        [InlineKeyboardButton("📊 عملة أخرى", callback_data="analyze_custom")],
        [InlineKeyboardButton("🔙 رجوع", callback_data="main_menu")],
    ])

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    username = update.effective_user.username or f"user_{uid}"
    first_name = update.effective_user.first_name or "مستخدم"
    status = get_subscription_status(uid)
    
    if "نشط" in status or "VIP" in status or "BASIC" in status:
        keyboard, status_text = get_main_keyboard(uid)
        welcome_msg = f"👋 مرحباً {first_name}!\n\n{status_text}\n\n📌 استخدم الأزرار أدناه:"
        await update.message.reply_text(welcome_msg, reply_markup=keyboard)
    else:
        add_pending_request(uid, username, first_name)
        for admin_id in ADMIN_IDS:
            keyboard = InlineKeyboardMarkup([[
                InlineKeyboardButton("✅ قبول", callback_data=f"approve_{uid}"),
                InlineKeyboardButton("❌ رفض", callback_data=f"reject_{uid}")
            ]])
            await context.bot.send_message(
                chat_id=admin_id,
                text=f"🆕 طلب اشتراك جديد!\n👤 المستخدم: {first_name}\n🆔 المعرف: {uid}",
                reply_markup=keyboard
            )
        await update.message.reply_text(f"👋 مرحباً {first_name}!\n\n{status}\n\n✅ تم إرسال طلب اشتراكك إلى المشرف.")

async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data
    uid = query.from_user.id
    
    # تشغيل التحليل
    if data == "run_scan":
        await query.edit_message_text("🔍 جاري تشغيل التحليل...")
        try:
            response = requests.post(f"{FLASK_API}/scan", json={"timeframe": "4h", "section": 1, "threshold": 4}, timeout=5)
            if response.status_code == 200:
                await query.edit_message_text("✅ تم تشغيل التحليل بنجاح")
            else:
                await query.edit_message_text("❌ فشل تشغيل التحليل")
        except:
            await query.edit_message_text("⚠️ لا يمكن الاتصال بالخادم")
        return
    
    # إيقاف التحليل
    if data == "stop_scan":
        await query.edit_message_text("⏹️ تم إيقاف التحليل")
        return
    
    # اختيار القسم
    if data == "select_section":
        await query.edit_message_text("📂 اختر قسم العملات:", reply_markup=get_section_keyboard())
        return
    
    if data.startswith("section_"):
        section_num = data.split("_")[1]
        await query.edit_message_text(f"✅ تم اختيار القسم {section_num}")
        return
    
    # اختيار العتبة
    if data == "select_threshold":
        current = context.user_data.get("threshold", 4)
        await query.edit_message_text("🎯 اختر عدد الشروط المطلوبة:", reply_markup=get_threshold_keyboard(current))
        return
    
    if data.startswith("threshold_"):
        value = int(data.split("_")[1])
        context.user_data["threshold"] = value
        await query.edit_message_text(f"✅ تم تغيير العتبة إلى {value} من 6 شروط")
        return
    
    # اختيار الفريم
    if data == "select_timeframe":
        current = context.user_data.get("timeframe", "4h")
        await query.edit_message_text("⏱️ اختر الإطار الزمني:", reply_markup=get_timeframe_keyboard(current))
        return
    
    if data.startswith("timeframe_"):
        tf = data.split("_")[1]
        context.user_data["timeframe"] = tf
        await query.edit_message_text(f"✅ تم تغيير الإطار الزمني إلى {tf}")
        return
    
    # القائمة الرئيسية
    if data == "main_menu":
        keyboard, status_text = get_main_keyboard(uid)
        await query.edit_message_text(f"📌 القائمة الرئيسية\n\n{status_text}", reply_markup=keyboard)
        return
    
    # لوحة تحكم الأدمن
    if data == "admin_panel":
        if not is_admin(uid):
            await query.edit_message_text("❌ غير مصرح")
            return
        await query.edit_message_text("⚙️ لوحة تحكم الأدمن", reply_markup=get_admin_keyboard())
        return
    
    if data == "pending_requests":
        if not is_admin(uid):
            await query.edit_message_text("❌ غير مصرح")
            return
        reqs = get_pending_requests()
        if not reqs:
            await query.edit_message_text("📭 لا توجد طلبات")
            return
        msg = "📋 الطلبات المعلقة:\n"
        for uid_r, uname, fname, req_at in reqs:
            msg += f"• {fname} - {uid_r}\n"
        await query.edit_message_text(msg)
        return
    
    if data == "active_users":
        if not is_admin(uid):
            await query.edit_message_text("❌ غير مصرح")
            return
        users = get_active_subscribers()
        if not users:
            await query.edit_message_text("📭 لا يوجد مشتركين")
            return
        msg = "👥 المشتركين:\n"
        for uid_u, uname, fname, exp, tier in users:
            msg += f"• {fname} - ينتهي: {exp.split('T')[0]}\n"
        await query.edit_message_text(msg)
        return
    
    # قوائم التحليل
    if data == "analyze_menu":
        await query.edit_message_text("📊 اختر العملة:", reply_markup=get_analyze_keyboard())
        return
    
    if data == "top_coins":
        await query.edit_message_text("🏆 أفضل العملات\nقيد التطوير...")
        return
    
    if data == "my_trades":
        await query.edit_message_text("📋 صفقاتك\nقيد التطوير...")
        return
    
    if data == "my_alerts":
        await query.edit_message_text("🔔 تنبيهاتك\nقيد التطوير...")
        return
    
    if data == "bot_info":
        await query.edit_message_text("ℹ️ بوت ULTIMATE HUNTER V6\nلإشارات التداول\nبإشراف: مصطفى الجالدي")
        return
    
    # تحليل عملة
    if data.startswith("analyze_"):
        symbol = data.split("_")[1]
        if symbol == "custom":
            await query.edit_message_text("📝 أرسل اسم العملة")
            context.user_data["waiting_for_symbol"] = True
            return
        await query.edit_message_text(f"📊 جاري تحليل {symbol}...")
        return
    
    # قبول/رفض الطلبات
    if data.startswith("approve_"):
        if not is_admin(uid):
            await query.edit_message_text("❌ غير مصرح")
            return
        uid_req = int(data.split("_")[1])
        success, expires = approve_request(uid_req, days=30, tier='basic', added_by=uid)
        if success:
            await query.edit_message_text(f"✅ تم قبول طلب المستخدم {uid_req}")
            await context.bot.send_message(chat_id=uid_req, text=f"✅ تم قبول اشتراكك!\n📅 ينتهي: {expires.strftime('%Y-%m-%d')}")
        else:
            await query.edit_message_text(f"❌ فشل قبول الطلب")
        return
    
    if data.startswith("reject_"):
        if not is_admin(uid):
            await query.edit_message_text("❌ غير مصرح")
            return
        uid_req = int(data.split("_")[1])
        remove_pending_request(uid_req)
        await query.edit_message_text(f"❌ تم رفض طلب المستخدم {uid_req}")
        await context.bot.send_message(chat_id=uid_req, text="❌ عذراً، تم رفض اشتراكك.")
        return

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if context.user_data.get("waiting_for_symbol"):
        symbol = update.message.text.strip().upper()
        context.user_data["waiting_for_symbol"] = False
        await update.message.reply_text(f"📊 جاري تحليل {symbol}...")

def run_subscription_bot():
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    application = Application.builder().token(TOKEN).build()
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CallbackQueryHandler(button_callback))
    application.add_handler(CommandHandler("analyze", handle_message))
    print("🤖 بوت التليجرام يعمل - الأزرار محدثة (عتبة وفريم)")
    loop.run_until_complete(application.initialize())
    loop.run_until_complete(application.start())
    loop.run_until_complete(application.updater.start_polling())
    loop.run_forever()
