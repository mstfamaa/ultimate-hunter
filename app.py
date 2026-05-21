import json
import time
import threading
from flask import Flask, render_template, request, jsonify
from colorama import init, Fore
from modules.detective import DetectiveConan
from modules.exchange_handler import ExchangeHandler
from config.settings import get_section, SERVER_CONFIG
from telegram_bot import telegram_bot
from trades_manager import TradeManager
from subscription_manager import get_active_subscribers

init(autoreset=True)
app = Flask(__name__)

try:
    with open('my_keys.json', 'r') as f:
        keys = json.load(f)
        API_KEY = keys.get('API_KEY')
        SECRET_KEY = keys.get('SECRET_KEY')
except:
    API_KEY = SECRET_KEY = None

exchange = ExchangeHandler(API_KEY, SECRET_KEY)
detective = DetectiveConan()
trade_manager = TradeManager(detective)
trade_manager.start_monitoring(exchange)

def send_signals_to_users(signals):
    """إرسال الإشارات للمستخدمين - نسخة مبسطة"""
    if not signals:
        return
    
    active_users = get_active_subscribers()
    if not active_users:
        print(Fore.YELLOW + "⚠️ لا يوجد مشتركين")
        return
    
    # ترتيب حسب القوة
    signals = sorted(signals, key=lambda x: x['score'], reverse=True)[:5]
    
    for uid, username, first_name, expires_at, tier in active_users:
        for sig in signals:
            msg = f"""
🤖 ULTIMATE HUNTER V6
━━━━━━━━━━━━━━━━
🔥 {sig['symbol']}/USDT - جاهز للدخول
📊 القوة: {sig['score']}%
💰 السعر: {sig['current_price']}
🎯 الأهداف: {sig['target_1']} / {sig['target_2']} / {sig['target_3']}
📈 RSI: {sig['details']['rsi']}
☁️ Ichimoku: {sig['details'].get('ichimoku', 'N/A')}
⏱️ {time.strftime('%H:%M:%S')}
━━━━━━━━━━━━━━━━
            """
            telegram_bot.send_message(msg, chat_id=uid)
            time.sleep(0.5)
        print(Fore.GREEN + f"📨 تم إرسال {len(signals)} إشارة للمستخدم {uid}")

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/scan', methods=['POST'])
def scan():
    data = request.get_json() or {}
    timeframe = data.get('timeframe', '4h')
    section = data.get('section', 1)
    threshold = data.get('threshold', 4)
    
    symbols = get_section(section)
    detective.set_threshold(threshold)
    
    print(Fore.CYAN + f"📂 تحليل القسم {section} - {len(symbols)} عملة")
    
    all_data = exchange.fetch_multiple(symbols, timeframe=timeframe, max_workers=15)
    ready_signals = []
    all_results = []
    
    for symbol, df in all_data.items():
        if df is None or len(df) < 30:
            continue
        analysis = detective.detect_accumulation(df, symbol)
        price = analysis['details']['current_price']
        score = analysis['score']
        
        if score >= 80:
            targets = (price * 1.07, price * 1.15, price * 1.25)
        elif score >= 70:
            targets = (price * 1.05, price * 1.10, price * 1.20)
        elif score >= 55:
            targets = (price * 1.03, price * 1.06, price * 1.10)
        else:
            targets = (price * 1.02, price * 1.04, price * 1.07)
        
        ready_info = detective.is_ready_for_entry(df, timeframe, threshold)
        
        signal_data = {
            "symbol": symbol,
            "score": score,
            "current_price": price,
            "target_1": round(targets[0], 5),
            "target_2": round(targets[1], 5),
            "target_3": round(targets[2], 5),
            "evidence": analysis['evidence'][:2],
            "details": analysis['details']
        }
        
        all_results.append(signal_data)
        
        if ready_info['is_ready']:
            ready_signals.append(signal_data)
            print(Fore.GREEN + f"   ✅ {symbol}: {score}% - جاهز!")
        else:
            print(Fore.YELLOW + f"   ⏳ {symbol}: {score}% - غير جاهز ({ready_info['met_conditions']}/6)")
    
    if ready_signals:
        send_signals_to_users(ready_signals)
        print(Fore.GREEN + f"📨 تم إرسال {len(ready_signals)} إشارة جاهزة")
    else:
        print(Fore.YELLOW + "⚠️ لا توجد إشارات جاهزة")
    
    all_results.sort(key=lambda x: x['score'], reverse=True)
    return jsonify({"success": True, "results": all_results[:50], "total_analyzed": len(all_results)})

@app.route('/api/trades', methods=['GET'])
def get_trades():
    return jsonify({"trades": trade_manager.trades})

@app.route('/api/open_trade', methods=['POST'])
def open_trade():
    data = request.get_json()
    trade_manager.open_trade(data['symbol'], data['current_price'], data['score'], data.get('details', {}))
    return jsonify({"success": True})

@app.route('/api/close_trade', methods=['POST'])
def close_trade():
    data = request.get_json()
    trade_manager.close_trade(data['trade_id'], data['current_price'], data['score'])
    return jsonify({"success": True})

if __name__ == "__main__":
    from telegram_bot_handlers import run_subscription_bot
    threading.Thread(target=run_subscription_bot, daemon=True).start()
    print(Fore.GREEN + "🚀 ULTIMATE HUNTER V6 - صاعد")
    print(Fore.YELLOW + f"📍 http://localhost:{SERVER_CONFIG['port']}")
    import os
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)
