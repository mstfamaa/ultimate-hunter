import ccxt
import pandas as pd
import time
from concurrent.futures import ThreadPoolExecutor
from colorama import Fore

class ExchangeHandler:
    def __init__(self, api_key=None, secret_key=None):
        self.exchange = ccxt.bingx({
            'apiKey': api_key,
            'secret': secret_key,
            'options': {'defaultType': 'swap'},
            'enableRateLimit': True,
        })
        self.exchange.set_sandbox_mode(True)
    
    def fetch_ohlcv(self, symbol, timeframe='4h', limit=100):
        try:
            ohlcv = self.exchange.fetch_ohlcv(f"{symbol}-USDT", timeframe=timeframe, limit=limit)
            if not ohlcv or len(ohlcv) < 30:
                return None
            df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
            return df
        except Exception as e:
            if "does not have market symbol" not in str(e):
                print(Fore.RED + f"خطأ في {symbol}: {str(e)[:50]}")
            return None
    
    def fetch_multiple(self, symbols, timeframe='4h', limit=100, max_workers=10):
        """جلب بيانات عدة عملات بشكل متوازي"""
        results = {}
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = {executor.submit(self.fetch_ohlcv, s, timeframe, limit): s for s in symbols}
            for future in futures:
                symbol = futures[future]
                try:
                    df = future.result(timeout=15)
                    if df is not None:
                        results[symbol] = df
                except Exception as e:
                    print(Fore.RED + f"خطأ في {symbol}: {e}")
        return results
