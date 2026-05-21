import json
import os
import time
import threading
from datetime import datetime
from telegram_bot import telegram_bot

TRADES_FILE = "trades.json"

class TradeManager:
    def __init__(self, detective):
        self.detective = detective
        self.trades = self.load_trades()
        self.monitoring = False
    
    def load_trades(self):
        if os.path.exists(TRADES_FILE):
            try:
                with open(TRADES_FILE, 'r') as f:
                    return json.load(f)
            except:
                return {}
        return {}
    
    def save_trades(self):
        with open(TRADES_FILE, 'w') as f:
            json.dump(self.trades, f, indent=2)
    
    def open_trade(self, symbol, price, score, details):
        tid = f"{symbol}_{int(time.time())}"
        self.trades[tid] = {
            "symbol": symbol,
            "open_price": price,
            "open_score": score,
            "open_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "last_score": score,
            "last_notify": int(time.time())
        }
        self.save_trades()
        
        # إرسال إشعار فتح الصفقة
        msg = f"""
✅ <b>صفقة جديدة مفتوحة</b>
━━━━━━━━━━━━━━━━
<b>{symbol}/USDT</b>
💰 سعر الدخول: {price}
📊 قوة الإشارة: {score}%
⏱️ الوقت: {datetime.now().strftime("%H:%M:%S")}

🕵️ تم تفعيل المراقبة التلقائية.
سيتم إعلامك بأي تغير مهم كل دقيقة.
        """
        telegram_bot.send_message(msg)
        return tid
    
    def close_trade(self, tid, price, score):
        if tid in self.trades:
            t = self.trades[tid]
            profit = ((price - t['open_price']) / t['open_price']) * 100
            msg = f"""
🔒 <b>تم إغلاق الصفقة</b> ({t['symbol']}/USDT)
━━━━━━━━━━━━━━━━
💰 سعر الدخول: {t['open_price']}
💰 سعر الخروج: {price}
📊 تغير السعر: {profit:+.2f}%
📈 النتيجة: {'ربح ✅' if profit > 0 else 'خسارة ❌'}
            """
            telegram_bot.send_message(msg)
            del self.trades[tid]
            self.save_trades()
            return True
        return False
    
    def start_monitoring(self, exchange, timeframe='4h'):
        """بدء مراقبة الصفقات المفتوحة"""
        if self.monitoring:
            return
        self.monitoring = True
        
        def monitor():
            print("🔄 بدء مراقبة الصفقات...")
            while True:
                try:
                    for tid, t in list(self.trades.items()):
                        symbol = t['symbol']
                        print(f"📊 مراقبة {symbol}...")
                        
                        # جلب البيانات وتحليلها
                        df = exchange.fetch_ohlcv(symbol, timeframe=timeframe, limit=50)
                        if df is not None and len(df) >= 30:
                            analysis = self.detective.detect_accumulation(df, symbol)
                            new_score = analysis['score']
                            current_price = analysis['details']['current_price']
                            old_score = t.get('last_score', new_score)
                            now = int(time.time())
                            last_notify = t.get('last_notify', 0)
                            
                            # حساب التغير
                            score_change = new_score - old_score
                            
                            # تحديث دوري كل 60 ثانية (دقيقة)
                            if now - last_notify >= 60:
                                if abs(score_change) < 10:
                                    # الحالة مستقرة
                                    msg = f"""
🔔 <b>تحديث الصفقة</b> ({symbol}/USDT)
━━━━━━━━━━━━━━━━
🟢 <b>الحالة:</b> مستقرة - استمر في التمسك
📊 القوة الحالية: {new_score}% (تغير {score_change:+.1f})
💰 السعر الحالي: {current_price}
💪 قوة الدخول: {t['open_score']}%

✅ لا داعي للقلق، استمر في الصفقة.
⏱️ {datetime.now().strftime("%H:%M:%S")}
                                    """
                                    telegram_bot.send_message(msg)
                                    t['last_notify'] = now
                                
                                elif score_change >= 10:
                                    # زيادة قوية
                                    msg = f"""
📈 <b>تحديث الصفقة</b> ({symbol}/USDT)
━━━━━━━━━━━━━━━━
🟢 <b>الحالة:</b> تزايد القوة - فرصة ممتازة!
📊 القوة الحالية: {new_score}% (زيادة {score_change:+.1f})
💰 السعر الحالي: {current_price}

✅ يمكنك التفكير في زيادة الكمية!
⏱️ {datetime.now().strftime("%H:%M:%S")}
                                    """
                                    telegram_bot.send_message(msg)
                                    t['last_notify'] = now
                                
                                elif score_change <= -10:
                                    # انخفاض خطير
                                    msg = f"""
⚠️ <b>تحديث الصفقة</b> ({symbol}/USDT)
━━━━━━━━━━━━━━━━
🔴 <b>الحالة:</b> انخفاض القوة - يوصى بالخروج!
📊 القوة الحالية: {new_score}% (انخفاض {score_change:+.1f})
💰 السعر الحالي: {current_price}

⚠️ يوصى بإغلاق الصفقة لحماية رأس المال.
⏱️ {datetime.now().strftime("%H:%M:%S")}
                                    """
                                    telegram_bot.send_message(msg)
                                    t['last_notify'] = now
                            
                            # تحديث القوة المسجلة
                            t['last_score'] = new_score
                            self.save_trades()
                    
                    time.sleep(60)  # كل دقيقة
                except Exception as e:
                    print(f"⚠️ خطأ في المراقبة: {e}")
                    time.sleep(60)
        
        # تشغيل المراقبة في خيط منفصل
        monitor_thread = threading.Thread(target=monitor, daemon=True)
        monitor_thread.start()
        print("✅ تم تشغيل مراقبة الصفقات")
