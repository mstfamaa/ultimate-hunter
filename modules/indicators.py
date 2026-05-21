# modules/indicators.py - نسخة مطورة

import pandas as pd
import numpy as np

class TechnicalIndicators:
    
    @staticmethod
    def calculate_rsi(close, period=14):
        delta = close.diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))
        return rsi.iloc[-1] if not pd.isna(rsi.iloc[-1]) else 50
    
    @staticmethod
    def calculate_rsi_array(close, period=14):
        """إرجاع مصفوفة RSI للكشف عن الـ Divergence"""
        delta = close.diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))
        return rsi
    
    @staticmethod
    def calculate_macd(close, fast=12, slow=26, signal=9):
        exp1 = close.ewm(span=fast, adjust=False).mean()
        exp2 = close.ewm(span=slow, adjust=False).mean()
        macd = exp1 - exp2
        signal_line = macd.ewm(span=signal, adjust=False).mean()
        histogram = macd - signal_line
        return macd.iloc[-1], signal_line.iloc[-1], histogram.iloc[-1]
    
    @staticmethod
    def calculate_bollinger_bands(close, period=20, std_dev=2):
        middle = close.rolling(window=period).mean()
        std = close.rolling(window=period).std()
        upper = middle + (std * std_dev)
        lower = middle - (std * std_dev)
        return upper.iloc[-1], middle.iloc[-1], lower.iloc[-1]
    
    @staticmethod
    def calculate_obv(df):
        obv = [0]
        for i in range(1, len(df)):
            if df['close'].iloc[i] > df['close'].iloc[i-1]:
                obv.append(obv[-1] + df['volume'].iloc[i])
            elif df['close'].iloc[i] < df['close'].iloc[i-1]:
                obv.append(obv[-1] - df['volume'].iloc[i])
            else:
                obv.append(obv[-1])
        return obv
    
    @staticmethod
    def calculate_adl(df):
        mfm = ((df['close'] - df['low']) - (df['high'] - df['close'])) / (df['high'] - df['low'])
        mf_volume = mfm * df['volume']
        adl = mf_volume.cumsum()
        return adl.tolist()
    
    @staticmethod
    def calculate_atr(df, period=14):
        high = df['high']
        low = df['low']
        close = df['close']
        tr1 = high - low
        tr2 = abs(high - close.shift())
        tr3 = abs(low - close.shift())
        tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
        atr = tr.rolling(window=period).mean()
        return atr.iloc[-1]
    
    # ========== مؤشرات جديدة ==========
    
    @staticmethod
    def calculate_ichimoku(df):
        """حساب Ichimoku Cloud للكشف عن الاتجاه القوي"""
        high = df['high']
        low = df['low']
        close = df['close']
        
        # Tenkan-sen (Conversion Line): (9-period high + 9-period low)/2
        period9_high = high.rolling(window=9).max()
        period9_low = low.rolling(window=9).min()
        tenkan = (period9_high + period9_low) / 2
        
        # Kijun-sen (Base Line): (26-period high + 26-period low)/2
        period26_high = high.rolling(window=26).max()
        period26_low = low.rolling(window=26).min()
        kijun = (period26_high + period26_low) / 2
        
        # Senkou Span A (Leading Span A): (Tenkan + Kijun)/2
        senkou_a = ((tenkan + kijun) / 2).shift(26)
        
        # Senkou Span B (Leading Span B): (52-period high + 52-period low)/2
        period52_high = high.rolling(window=52).max()
        period52_low = low.rolling(window=52).min()
        senkou_b = ((period52_high + period52_low) / 2).shift(26)
        
        current_price = close.iloc[-1]
        current_senkou_a = senkou_a.iloc[-1] if not pd.isna(senkou_a.iloc[-1]) else 0
        current_senkou_b = senkou_b.iloc[-1] if not pd.isna(senkou_b.iloc[-1]) else 0
        
        # الاتجاه: صاعد إذا كان السعر فوق السحابة و Senkou A > Senkou B
        if current_price > max(current_senkou_a, current_senkou_b) and current_senkou_a > current_senkou_b:
            trend = "STRONG_BULLISH"
        elif current_price > max(current_senkou_a, current_senkou_b):
            trend = "BULLISH"
        elif current_price < min(current_senkou_a, current_senkou_b):
            trend = "BEARISH"
        else:
            trend = "NEUTRAL"
        
        return {"trend": trend, "senkou_a": current_senkou_a, "senkou_b": current_senkou_b}
    
    @staticmethod
    def detect_rsi_divergence(close, rsi_array, lookback=20):
        """الكشف عن الـ Bullish Divergence (قاع أقل، RSI أعلى)"""
        if len(close) < lookback or len(rsi_array) < lookback:
            return False
        
        recent_close = close.tail(lookback)
        recent_rsi = rsi_array.tail(lookback)
        
        # البحث عن القيعان
        close_min_idx = recent_close.idxmin()
        close_min = recent_close.min()
        
        # RSI عند نفس النقطة
        rsi_at_min = recent_rsi.loc[close_min_idx] if close_min_idx in recent_rsi.index else None
        
        # ثاني قاع
        second_lowest_idx = recent_close.nsmallest(2).index[-1]
        second_lowest_close = recent_close.loc[second_lowest_idx]
        rsi_at_second = recent_rsi.loc[second_lowest_idx] if second_lowest_idx in recent_rsi.index else None
        
        if rsi_at_min is not None and rsi_at_second is not None:
            # قاع أقل لكن RSI أعلى -> Bullish Divergence
            if close_min < second_lowest_close and rsi_at_min > rsi_at_second:
                return True
        return False
    
    @staticmethod
    def calculate_vwap(df):
        """حساب Volume Weighted Average Price"""
        typical_price = (df['high'] + df['low'] + df['close']) / 3
        vwap = (typical_price * df['volume']).cumsum() / df['volume'].cumsum()
        return vwap.iloc[-1]
    
    @staticmethod
    def detect_breakout(df, period=20, threshold=1.02):
        """الكشف عن اختراق المقاومة"""
        high = df['high']
        resistance = high.tail(period).max()
        current_price = df['close'].iloc[-1]
        
        if current_price > resistance * threshold:
            return True, resistance
        return False, resistance

    @staticmethod
    def calculate_ichimoku(df):
        """حساب Ichimoku Cloud"""
        high = df['high']
        low = df['low']
        close = df['close']
        
        tenkan = (high.rolling(window=9).max() + low.rolling(window=9).min()) / 2
        kijun = (high.rolling(window=26).max() + low.rolling(window=26).min()) / 2
        senkou_a = ((tenkan + kijun) / 2).shift(26)
        senkou_b = ((high.rolling(window=52).max() + low.rolling(window=52).min()) / 2).shift(26)
        
        current_price = close.iloc[-1]
        if not pd.isna(senkou_a.iloc[-1]) and not pd.isna(senkou_b.iloc[-1]):
            if current_price > max(senkou_a.iloc[-1], senkou_b.iloc[-1]) and senkou_a.iloc[-1] > senkou_b.iloc[-1]:
                trend = "STRONG_BULLISH"
            elif current_price > max(senkou_a.iloc[-1], senkou_b.iloc[-1]):
                trend = "BULLISH"
            else:
                trend = "NEUTRAL"
        else:
            trend = "NEUTRAL"
        return {"trend": trend}

    @staticmethod
    def calculate_ichimoku(df):
        """حساب Ichimoku Cloud"""
        high = df['high']
        low = df['low']
        close = df['close']
        
        tenkan = (high.rolling(window=9).max() + low.rolling(window=9).min()) / 2
        kijun = (high.rolling(window=26).max() + low.rolling(window=26).min()) / 2
        senkou_a = ((tenkan + kijun) / 2).shift(26)
        senkou_b = ((high.rolling(window=52).max() + low.rolling(window=52).min()) / 2).shift(26)
        
        current_price = close.iloc[-1]
        if not pd.isna(senkou_a.iloc[-1]) and not pd.isna(senkou_b.iloc[-1]):
            if current_price > max(senkou_a.iloc[-1], senkou_b.iloc[-1]) and senkou_a.iloc[-1] > senkou_b.iloc[-1]:
                trend = "STRONG_BULLISH"
            elif current_price > max(senkou_a.iloc[-1], senkou_b.iloc[-1]):
                trend = "BULLISH"
            else:
                trend = "NEUTRAL"
        else:
            trend = "NEUTRAL"
        return {"trend": trend}
