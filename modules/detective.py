import pandas as pd
import numpy as np
from modules.indicators import TechnicalIndicators

class DetectiveConan:
    
    def __init__(self):
        self.indicators = TechnicalIndicators()
        self.threshold = 4
    
    def set_threshold(self, value):
        self.threshold = max(2, min(6, value))
    
    def get_indicator_settings(self, timeframe):
        settings = {
            '5m': {'rsi_period': 14, 'ma_short': 10, 'ma_long': 30, 'bb_period': 20, 'min_candles': 50},
            '15m': {'rsi_period': 14, 'ma_short': 10, 'ma_long': 30, 'bb_period': 20, 'min_candles': 50},
            '1h': {'rsi_period': 14, 'ma_short': 20, 'ma_long': 50, 'bb_period': 20, 'min_candles': 50},
            '4h': {'rsi_period': 14, 'ma_short': 20, 'ma_long': 50, 'bb_period': 20, 'min_candles': 50},
            '1d': {'rsi_period': 21, 'ma_short': 50, 'ma_long': 100, 'bb_period': 20, 'min_candles': 100},
            '1M': {'rsi_period': 28, 'ma_short': 50, 'ma_long': 200, 'bb_period': 20, 'min_candles': 150}
        }
        return settings.get(timeframe, settings['4h'])
    
    def detect_accumulation(self, df, symbol):
        return self.detect_accumulation_with_timeframe(df, symbol, '4h')
    
    def detect_accumulation_with_timeframe(self, df, symbol, timeframe='4h'):
        settings = self.get_indicator_settings(timeframe)
        close = df['close']
        high = df['high']
        low = df['low']
        volume = df['volume']
        
        evidence = []
        score = 0
        strong_signals = 0
        
        rsi = self.indicators.calculate_rsi(close, period=settings['rsi_period'])
        ma_short = close.tail(settings['ma_short']).mean()
        ma_long = close.tail(settings['ma_long']).mean()
        
        recent_high = high.tail(20).max()
        recent_low = low.tail(20).min()
        price_range_percent = ((recent_high - recent_low) / recent_low) * 100
        
        if price_range_percent < 8:
            evidence.append(f"✅ نطاق سعري ضيق ({round(price_range_percent,1)}%)")
            score += 25
            strong_signals += 1
        elif price_range_percent < 15:
            evidence.append(f"⚠️ نطاق سعري متوسط ({round(price_range_percent,1)}%)")
            score += 10
        
        avg_volume = volume.tail(20).mean()
        volume_ratio = volume.iloc[-1] / avg_volume if avg_volume > 0 else 1
        if volume_ratio < 0.7:
            evidence.append(f"✅ حجم منخفض ({round(volume_ratio,1)}x)")
            score += 20
            strong_signals += 1
        elif volume_ratio < 1.0:
            evidence.append(f"⚠️ حجم أقل من المتوسط")
            score += 10
        
        if 30 <= rsi <= 45:
            evidence.append(f"✅ RSI مثالي ({round(rsi,1)})")
            score += 30
            strong_signals += 1
        elif 20 <= rsi < 30:
            evidence.append(f"⚠️ RSI منخفض ({round(rsi,1)})")
            score += 15
        
        macd, signal, hist = self.indicators.calculate_macd(close)
        if hist > 0:
            evidence.append(f"✅ MACD إيجابي")
            score += 25
            strong_signals += 1
        
        lowest_20 = low.tail(20).min()
        current_price = close.iloc[-1]
        distance_from_low = ((current_price - lowest_20) / lowest_20) * 100
        if distance_from_low < 3:
            evidence.append(f"✅ قريب من القاع ({round(distance_from_low,1)}%)")
            score += 25
            strong_signals += 1
        elif distance_from_low < 8:
            evidence.append(f"⚠️ فوق القاع ({round(distance_from_low,1)}%)")
            score += 10
        
        if current_price > ma_short > ma_long:
            evidence.append(f"✅ ترتيب صاعد (MA{settings['ma_short']} > MA{settings['ma_long']})")
            score += 20
            strong_signals += 1
        
        bb_upper, bb_middle, bb_lower = self.indicators.calculate_bollinger_bands(close, period=settings['bb_period'])
        if current_price <= bb_lower * 1.02:
            evidence.append(f"✅ عند Bollinger السفلي")
            score += 20
            strong_signals += 1
        
        obv = self.indicators.calculate_obv(df)
        if len(obv) >= 5 and obv[-1] > obv[-5] and volume_ratio < 0.8:
            evidence.append(f"✅ OBV في صعود")
            score += 20
            strong_signals += 1
        
        adl = self.indicators.calculate_adl(df)
        if len(adl) >= 5 and adl[-1] > adl[-5]:
            evidence.append(f"✅ أموال ذكية تدخل")
            score += 15
        
        atr = self.indicators.calculate_atr(df)
        atr_percent = (atr / current_price) * 100
        if atr_percent < 2:
            evidence.append(f"✅ ATR منخفض ({round(atr_percent,1)}%)")
            score += 15
        
        ichimoku = self.indicators.calculate_ichimoku(df)
        if ichimoku['trend'] == "STRONG_BULLISH":
            evidence.append(f"✅ Ichimoku: سحابة صاعدة قوية")
            score += 20
            strong_signals += 1
        elif ichimoku['trend'] == "BULLISH":
            evidence.append(f"⚠️ Ichimoku: صاعد")
            score += 10
        
        return {
            "score": min(100, score),
            "evidence": evidence[:6],
            "strong_signals": strong_signals,
            "details": {
                "price_range": round(price_range_percent, 2),
                "volume_ratio": round(volume_ratio, 2),
                "rsi": round(rsi, 2),
                "distance_from_low": round(distance_from_low, 2),
                "ma_short": round(ma_short, 5),
                "ma_long": round(ma_long, 5),
                "current_price": round(current_price, 5),
                "atr_percent": round(atr_percent, 2),
                "ichimoku": ichimoku['trend']
            }
        }
    
    def is_ready_for_entry(self, df, timeframe='4h', threshold=None):
        if threshold is None:
            threshold = self.threshold
        settings = self.get_indicator_settings(timeframe)
        close = df['close']
        high = df['high']
        volume = df['volume']
        
        current_price = close.iloc[-1]
        ma_short = close.tail(settings['ma_short']).mean()
        ma_long = close.tail(settings['ma_long']).mean()
        rsi = self.indicators.calculate_rsi(close, period=settings['rsi_period'])
        macd, signal, hist = self.indicators.calculate_macd(close)
        avg_volume = volume.tail(20).mean()
        volume_ratio = volume.iloc[-1] / avg_volume if avg_volume > 0 else 1
        resistance = high.tail(20).max()
        
        conditions = {
            'price_above_ma_short': current_price > ma_short,
            'price_above_ma_long': current_price > ma_long,
            'rsi_ready': 45 <= rsi <= 65,
            'macd_positive': hist > 0,
            'volume_increasing': volume_ratio > 1.1,
            'breakout': current_price > resistance * 0.99
        }
        met = sum(conditions.values())
        is_ready = met >= threshold
        
        return {'is_ready': is_ready, 'met_conditions': met, 'total_conditions': len(conditions)}
    
    def get_status_text(self, score):
        if score >= 80:
            return "🔥 فرصة استثنائية - انطلاق وشيك جداً!"
        elif score >= 70:
            return "🔥 فرصة ذهبية - على وشك الانطلاق!"
        elif score >= 55:
            return "✅ فرصة جيدة - مراقبة عن كثب"
        elif score >= 40:
            return "⚠️ احتمالية متوسطة - متابعة"
        return "📊 ضعيفة - تحت المراقبة"
