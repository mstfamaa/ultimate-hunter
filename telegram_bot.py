import requests
import time

class TelegramBot:
    def __init__(self, token, chat_id):
        self.token = token
        self.chat_id = chat_id
        self.base_url = f"https://api.telegram.org/bot{token}"
    
    def send_message(self, text, parse_mode=None, chat_id=None):
        url = f"{self.base_url}/sendMessage"
        target_chat = chat_id or self.chat_id
        clean_text = text.replace('*', '').replace('_', '').replace('`', '')
        payload = {"chat_id": target_chat, "text": clean_text}
        try:
            response = requests.post(url, json=payload, timeout=15)
            result = response.json()
            if result.get('ok'):
                print(f"✅ تم الإرسال إلى {target_chat}")
                return result
            else:
                print(f"❌ فشل: {result}")
                return None
        except Exception as e:
            print(f"❌ خطأ: {e}")
            return None

TOKEN = "8391034490:AAEJpLAaK3gXg1cglErBH8azmkUSkl3Ip_4"
CHAT_ID = "5796394289"
telegram_bot = TelegramBot(TOKEN, CHAT_ID)
