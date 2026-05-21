#!/bin/bash

# التأكد من تثبيت أداة jq للتعامل مع مخرجات JSON
if ! command -v jq &> /dev/null; then
    echo "السكربت يتطلب أداة jq لفلترة النتائج."
    echo "يرجى تثبيتها أولاً باستخدام: sudo apt install jq"
    exit 1
fi

# محاولة قراءة مفتاح API من ملف my_keys.json
# (ملاحظة: طلب جلب الأسواق هو طلب عام Public لا يتطلب مفتاح API إجبارياً، لكن سيتم استخدامه بناءً على طلبك)
if [ -f "my_keys.json" ]; then
    # يبحث عن المفتاح تحت اسم apiKey أو api_key أو API_KEY
    API_KEY=$(jq -r '.apiKey // .api_key // .API_KEY' my_keys.json 2>/dev/null)
else
    API_KEY=""
fi

# رابط BingX API لجلب العقود الآجلة الدائمة (USDT-M)
ENDPOINT="https://open-api.bingx.com/openApi/swap/v2/quote/contracts"

echo "====================================================="
echo "جاري جلب أسماء العملات (العقود الآجلة) من منصة BingX..."
echo "====================================================="

# إرسال طلب Curl واستخراج أسماء العقود
# سيتم استخدام sed 's/-//g' لإزالة الشرطة (لتصبح BTCUSDT بدلاً من BTC-USDT كما تظهر في التطبيق)
if [ -n "$API_KEY" ] && [ "$API_KEY" != "null" ]; then
    curl -s -X GET "$ENDPOINT" -H "X-BX-APIKEY: $API_KEY" | jq -r '.data[].symbol' | sed 's/-//g'
else
    curl -s -X GET "$ENDPOINT" | jq -r '.data[].symbol' | sed 's/-//g'
fi

echo ""
echo "====================================================="
echo "تم الجلب بنجاح!"
