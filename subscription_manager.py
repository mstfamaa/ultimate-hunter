import sqlite3
import time
from datetime import datetime, timedelta

DB_PATH = "subscriptions.db"

def init_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS subscribers (
            user_id INTEGER PRIMARY KEY,
            username TEXT,
            first_name TEXT,
            subscribed_at TEXT,
            expires_at TEXT,
            is_active INTEGER DEFAULT 1,
            added_by INTEGER
        )
    ''')
    c.execute('''
        CREATE TABLE IF NOT EXISTS pending_requests (
            user_id INTEGER PRIMARY KEY,
            username TEXT,
            first_name TEXT,
            requested_at TEXT,
            status TEXT DEFAULT 'pending'
        )
    ''')
    conn.commit()
    conn.close()
    print("✅ قاعدة البيانات جاهزة")

def add_pending_request(user_id, username, first_name):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    now = datetime.now().isoformat()
    c.execute('''
        INSERT OR REPLACE INTO pending_requests (user_id, username, first_name, requested_at, status)
        VALUES (?, ?, ?, ?, 'pending')
    ''', (user_id, username, first_name, now))
    conn.commit()
    conn.close()
    return True

def get_pending_requests():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT user_id, username, first_name, requested_at FROM pending_requests WHERE status = 'pending'")
    rows = c.fetchall()
    conn.close()
    return rows

def remove_pending_request(user_id):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("DELETE FROM pending_requests WHERE user_id = ?", (user_id,))
    conn.commit()
    conn.close()

def approve_request(user_id, days=30, added_by=None):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT username, first_name FROM pending_requests WHERE user_id = ?", (user_id,))
    row = c.fetchone()
    if row:
        username, first_name = row
        now = datetime.now()
        expires = now + timedelta(days=days)
        c.execute('''
            INSERT OR REPLACE INTO subscribers
            (user_id, username, first_name, subscribed_at, expires_at, is_active, added_by)
            VALUES (?, ?, ?, ?, ?, 1, ?)
        ''', (user_id, username, first_name, now.isoformat(), expires.isoformat(), added_by))
        c.execute("DELETE FROM pending_requests WHERE user_id = ?", (user_id,))
        conn.commit()
        conn.close()
        return True, expires
    conn.close()
    return False, None

def add_subscriber(user_id, username, first_name, days=30, added_by=None):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    now = datetime.now()
    expires = now + timedelta(days=days)
    c.execute('''
        INSERT OR REPLACE INTO subscribers
        (user_id, username, first_name, subscribed_at, expires_at, is_active, added_by)
        VALUES (?, ?, ?, ?, ?, 1, ?)
    ''', (user_id, username, first_name, now.isoformat(), expires.isoformat(), added_by))
    conn.commit()
    conn.close()
    return True

def remove_subscriber(user_id):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("DELETE FROM subscribers WHERE user_id = ?", (user_id,))
    conn.commit()
    conn.close()
    return True

def is_subscriber_active(user_id):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT expires_at, is_active FROM subscribers WHERE user_id = ? AND is_active = 1", (user_id,))
    row = c.fetchone()
    conn.close()
    if not row:
        return False
    expires_at = datetime.fromisoformat(row[0])
    return expires_at > datetime.now()

def get_active_subscribers():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    now = datetime.now().isoformat()
    c.execute("SELECT user_id, username, first_name, expires_at FROM subscribers WHERE is_active = 1 AND expires_at > ?", (now,))
    rows = c.fetchall()
    conn.close()
    return rows

def get_subscription_status(user_id):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT expires_at, is_active FROM subscribers WHERE user_id = ?", (user_id,))
    row = c.fetchone()
    conn.close()
    if not row:
        return "❌ غير مشترك"
    expires_at, is_active = row
    exp = datetime.fromisoformat(expires_at)
    if not is_active or exp < datetime.now():
        return "❌ انتهت الصلاحية"
    days = (exp - datetime.now()).days
    return f"✅ نشط - يتبقى {days} يوم"

init_db()

# ============= دوال الإشارات (للتقييم) =============

def save_signal(symbol, score, price, targets):
    """حفظ الإشارة في قاعدة البيانات"""
    import sqlite3
    from datetime import datetime
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS signal_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            symbol TEXT,
            signal_score INTEGER,
            entry_price REAL,
            target_1 REAL,
            target_2 REAL,
            target_3 REAL,
            max_price REAL,
            reached_target INTEGER DEFAULT 0,
            status TEXT DEFAULT 'pending',
            created_at TEXT,
            closed_at TEXT
        )
    ''')
    now = datetime.now().isoformat()
    c.execute('''
        INSERT INTO signal_history (symbol, signal_score, entry_price, target_1, target_2, target_3, status, created_at)
        VALUES (?, ?, ?, ?, ?, ?, 'active', ?)
    ''', (symbol, score, price, targets[0], targets[1], targets[2], now))
    conn.commit()
    conn.close()
    return True

def get_signal_stats():
    """إحصائيات دقة الإشارات"""
    import sqlite3
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT COUNT(*) FROM signal_history WHERE status = 'closed'")
    total = c.fetchone()[0]
    c.execute("SELECT COUNT(*) FROM signal_history WHERE reached_target >= 1")
    reached_1 = c.fetchone()[0]
    c.execute("SELECT COUNT(*) FROM signal_history WHERE reached_target >= 2")
    reached_2 = c.fetchone()[0]
    c.execute("SELECT COUNT(*) FROM signal_history WHERE reached_target >= 3")
    reached_3 = c.fetchone()[0]
    conn.close()
    return {
        'total': total,
        'target_1_rate': round(reached_1/total*100, 1) if total > 0 else 0,
        'target_2_rate': round(reached_2/total*100, 1) if total > 0 else 0,
        'target_3_rate': round(reached_3/total*100, 1) if total > 0 else 0
    }

# ============= دوال المستوى والمشتركين =============

def get_user_tier(user_id):
    """الحصول على مستوى المستخدم"""
    import sqlite3
    from datetime import datetime
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    try:
        c.execute("SELECT tier, expires_at FROM subscribers WHERE user_id = ? AND is_active = 1", (user_id,))
        row = c.fetchone()
    except:
        row = None
    conn.close()
    if not row:
        return 'free'
    expires_at = datetime.fromisoformat(row[1])
    if expires_at < datetime.now():
        return 'free'
    return row[0] if row[0] else 'free'

def add_pending_request(user_id, username, first_name):
    """إضافة طلب اشتراك جديد"""
    import sqlite3
    from datetime import datetime
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    now = datetime.now().isoformat()
    c.execute('''
        INSERT OR REPLACE INTO pending_requests (user_id, username, first_name, requested_at, status)
        VALUES (?, ?, ?, ?, 'pending')
    ''', (user_id, username, first_name, now))
    conn.commit()
    conn.close()
    return True

def get_pending_requests():
    """الحصول على طلبات الاشتراك المعلقة"""
    import sqlite3
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT user_id, username, first_name, requested_at FROM pending_requests WHERE status = 'pending'")
    rows = c.fetchall()
    conn.close()
    return rows

def remove_pending_request(user_id):
    """إزالة طلب اشتراك"""
    import sqlite3
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("DELETE FROM pending_requests WHERE user_id = ?", (user_id,))
    conn.commit()
    conn.close()

def approve_request(user_id, days=30, tier='basic', added_by=None):
    """الموافقة على طلب اشتراك"""
    import sqlite3
    from datetime import datetime, timedelta
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT username, first_name FROM pending_requests WHERE user_id = ?", (user_id,))
    row = c.fetchone()
    if row:
        username, first_name = row
        now = datetime.now()
        expires = now + timedelta(days=days)
        c.execute('''
            INSERT OR REPLACE INTO subscribers
            (user_id, username, first_name, subscribed_at, expires_at, tier, is_active, added_by)
            VALUES (?, ?, ?, ?, ?, ?, 1, ?)
        ''', (user_id, username, first_name, now.isoformat(), expires.isoformat(), tier, added_by))
        c.execute("DELETE FROM pending_requests WHERE user_id = ?", (user_id,))
        conn.commit()
        conn.close()
        return True, expires
    conn.close()
    return False, None

def get_active_subscribers():
    """الحصول على المشتركين النشطين"""
    import sqlite3
    from datetime import datetime
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    now = datetime.now().isoformat()
    try:
        c.execute("SELECT user_id, username, first_name, expires_at, tier FROM subscribers WHERE is_active = 1 AND expires_at > ?", (now,))
        rows = c.fetchall()
    except:
        rows = []
    conn.close()
    return rows

def get_subscription_status(user_id):
    """الحالة التفصيلية للاشتراك"""
    import sqlite3
    from datetime import datetime
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    try:
        c.execute("SELECT expires_at, is_active, tier FROM subscribers WHERE user_id = ?", (user_id,))
        row = c.fetchone()
    except:
        row = None
    conn.close()
    if not row:
        return "❌ غير مشترك"
    expires_at, is_active, tier = row
    exp = datetime.fromisoformat(expires_at)
    if not is_active or exp < datetime.now():
        return "❌ انتهت الصلاحية"
    days = (exp - datetime.now()).days
    return f"✅ {tier.upper()} - يتبقى {days} يوم"

def add_subscriber(user_id, username, first_name, days=30, tier='basic', added_by=None):
    """إضافة مشترك جديد مباشرة"""
    import sqlite3
    from datetime import datetime, timedelta
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    now = datetime.now()
    expires = now + timedelta(days=days)
    c.execute('''
        INSERT OR REPLACE INTO subscribers
        (user_id, username, first_name, subscribed_at, expires_at, tier, is_active, added_by)
        VALUES (?, ?, ?, ?, ?, ?, 1, ?)
    ''', (user_id, username, first_name, now.isoformat(), expires.isoformat(), tier, added_by))
    conn.commit()
    conn.close()
    return True

def remove_subscriber(user_id):
    """حذف مشترك"""
    import sqlite3
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("DELETE FROM subscribers WHERE user_id = ?", (user_id,))
    conn.commit()
    conn.close()
    return True
