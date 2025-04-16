
import sqlite3
from datetime import datetime, timedelta
import secrets
import string

from telegram import ReplyKeyboardMarkup

import logging
logger = logging.getLogger(__name__)

# آی دی ادمین اصلی
ADMIN_ID = 2138687434


# ----------------------
# توابع کمکی
# ----------------------
def generate_referral_code(length=8):
    """تولید کد رفرال تصادفی"""
    chars = string.ascii_uppercase + string.digits
    return ''.join(secrets.choice(chars) for _ in range(length))


# ----------------------
# ایجاد جداول
# ----------------------
def create_tables():
    conn = sqlite3.connect('print3d.db')
    c = conn.cursor()

    c.execute('''CREATE TABLE IF NOT EXISTS files
                 (
                     id INTEGER PRIMARY KEY AUTOINCREMENT,
                     user_id INTEGER,
                     file_name TEXT,
                     mime_type TEXT,
                     file_id TEXT UNIQUE,
                     file_unique_id TEXT,
                     created_at TEXT,
                     quantity INTEGER,
                     description TEXT,
                     status TEXT DEFAULT 'در حال انجام',
                     notes TEXT
                 )''')  # حذف کامنت فارسی از داخل دستور SQL



    # جدول کاربران
    c.execute('''CREATE TABLE IF NOT EXISTS users
                 (
                     id INTEGER PRIMARY KEY,
                     full_name TEXT,
                     phone TEXT UNIQUE,
                     inviter_id INTEGER,
                     remaining_invites INTEGER DEFAULT 5,
                     created_at TEXT,
                     updated_at TEXT
                 )''')

    # جدول رفرال‌ها
    c.execute('''CREATE TABLE IF NOT EXISTS referrals
                 (
                     id INTEGER PRIMARY KEY AUTOINCREMENT,
                     referrer_id INTEGER,
                     referral_code TEXT UNIQUE,
                     used_by INTEGER DEFAULT NULL,
                     created_at TEXT,
                     expires_at TEXT,
                     is_admin BOOLEAN DEFAULT FALSE,
                     FOREIGN KEY(referrer_id) REFERENCES users(id)
                 )''')

    # جدول مدعوین
    c.execute('''CREATE TABLE IF NOT EXISTS invited_users
                 (
                     referrer_id INTEGER,
                     invited_user_id INTEGER PRIMARY KEY,
                     invited_full_name TEXT,
                     invited_phone TEXT,
                     invited_at TEXT,
                     FOREIGN KEY(referrer_id) REFERENCES users(id),
                     FOREIGN KEY(invited_user_id) REFERENCES users(id)
                 )''')

    # جدول کیف پول
    c.execute('''CREATE TABLE IF NOT EXISTS wallets
                 (
                     user_id INTEGER PRIMARY KEY,
                     balance REAL DEFAULT 0,
                     discount REAL DEFAULT 0,
                     FOREIGN KEY(user_id) REFERENCES users(id)
                 )''')

    conn.commit()
    conn.close()


# ----------------------
# توابع کاربران
# ----------------------
def add_user(user_data):
    """اضافه کردن کاربر جدید با مدیریت خطاهای پیشرفته"""
    conn = None
    try:
        conn = sqlite3.connect('print3d.db')
        c = conn.cursor()

        # بررسی وجود شماره تلفن تکراری
        c.execute("SELECT id FROM users WHERE phone = ?", (user_data[2],))
        if c.fetchone():
            raise sqlite3.IntegrityError("شماره تلفن تکراری")

        # درج کاربر جدید
        c.execute('''INSERT INTO users 
                    (id, full_name, phone, inviter_id, created_at, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?)''', user_data)

        # ایجاد رکورد کیف پول
        c.execute('''INSERT INTO wallets (user_id, balance, discount)
                    VALUES (?, 0, 0)''', (user_data[0],))

        conn.commit()
        return True

    except sqlite3.IntegrityError as e:
        print(f"❗خطای یکتایی: {str(e)}")
        raise  # بازگرداندن خطا برای مدیریت در لایه بالاتر
    except Exception as e:
        print(f"🔥 خطای سیستمی در افزودن کاربر: {str(e)}")
        if conn:
            conn.rollback()
        return False
    finally:
        if conn:
            conn.close()


# ----------------------
# توابع رفرال
# ----------------------
def create_referral(user_id, is_admin=False):
    """ایجاد کد دعوت جدید"""
    conn = None
    try:
        conn = sqlite3.connect('print3d.db')
        c = conn.cursor()

        # بررسی ظرفیت دعوت برای کاربران عادی
        if not is_admin:
            c.execute("SELECT remaining_invites FROM users WHERE id = ?", (user_id,))
            remaining = c.fetchone()[0]
            if remaining <= 0:
                return None, "ظرفیت دعوت شما تکمیل شده است"

        # تولید کد رفرال
        code = generate_referral_code()

        # تنظیم تاریخ انقضا (۱ سال)
        expires = (datetime.now() + timedelta(days=365)).strftime("%Y-%m-%d %H:%M:%S")

        # ذخیره در دیتابیس
        c.execute('''INSERT INTO referrals 
                    (referrer_id, referral_code, created_at, expires_at, is_admin)
                    VALUES (?, ?, ?, ?, ?)''',
                  (user_id, code, datetime.now().strftime("%Y-%m-%d %H:%M:%S"), expires, is_admin))

        conn.commit()
        return code, None

    except sqlite3.IntegrityError:
        return None, "کد دعوت تکراری است. لطفاً مجدد تلاش کنید."
    except Exception as e:
        print(f"🔥 خطا در ایجاد کد دعوت: {str(e)}")
        return None, "خطای سیستمی"
    finally:
        if conn:
            conn.close()


def validate_referral(code):
    try:
        conn = sqlite3.connect('print3d.db')
        c = conn.cursor()

        c.execute('''SELECT referrer_id, expires_at 
                     FROM referrals 
                     WHERE referral_code = ? 
                     AND used_by IS NULL
                     AND expires_at > CURRENT_TIMESTAMP''',
                  (code,))

        result = c.fetchone()
        if not result:
            return False, "کد نامعتبر یا منقضی شده است"

        referrer_id, expires_at = result
        return True, referrer_id

    except Exception as e:
        logger.error(f"خطا در اعتبارسنجی: {str(e)}")
        return False, "خطای سیستمی"
    finally:
        conn.close()


def add_invited_user(referrer_id, user_data):
    try:
        conn = sqlite3.connect('print3d.db')
        c = conn.cursor()
        c.execute('''INSERT INTO invited_users 
                     (referrer_id, invited_user_id, invited_full_name, invited_phone, invited_at)
                     VALUES (?, ?, ?, ?, ?)''',
                  (referrer_id, *user_data))
        conn.commit()
        return True
    except Exception as e:
        print(f"Error adding invited user: {str(e)}")
        return False
    finally:
        conn.close()




def mark_referral_used(code, used_by):
    """علامت‌گذاری کد استفاده شده"""
    conn = sqlite3.connect('print3d.db')
    c = conn.cursor()
    c.execute("UPDATE referrals SET used_by = ? WHERE referral_code = ?", (used_by, code))
    conn.commit()
    conn.close()


# ----------------------
# توابع مدعوین
# ----------------------
def add_invited_user(referrer_id, user_data):
    """ذخیره اطلاعات مدعو"""
    try:
        conn = sqlite3.connect('print3d.db')
        c = conn.cursor()
        c.execute('''INSERT INTO invited_users 
                     (referrer_id, invited_user_id, invited_full_name, invited_phone, invited_at)
                     VALUES (?, ?, ?, ?, ?)''',
                  (referrer_id, *user_data))
        conn.commit()
        return True
    except Exception as e:
        print(f"Error adding invited user: {str(e)}")
        return False
    finally:
        conn.close()


def get_invited_users(referrer_id):
    """دریافت لیست مدعوین"""
    conn = sqlite3.connect('print3d.db')
    c = conn.cursor()
    c.execute('''SELECT invited_full_name, invited_phone, invited_at 
                 FROM invited_users 
                 WHERE referrer_id = ?''', (referrer_id,))
    return c.fetchall()

def decrement_invites(user_id):
    conn = sqlite3.connect('print3d.db')
    c = conn.cursor()
    c.execute("UPDATE users SET remaining_invites = remaining_invites - 1 WHERE id = ?", (user_id,))
    conn.commit()
    conn.close()

def get_user(user_id):
    """دریافت اطلاعات کاربر بر اساس شناسه"""
    conn = sqlite3.connect('print3d.db')
    c = conn.cursor()
    c.execute("SELECT * FROM users WHERE id = ?", (user_id,))
    result = c.fetchone()
    conn.close()
    return result

def get_active_orders(user_id):
    """دریافت سفارشات فعال کاربر"""
    conn = sqlite3.connect('print3d.db')
    c = conn.cursor()
    c.execute("""
        SELECT * FROM files 
        WHERE user_id = ? 
        AND status = 'در حال انجام'
        ORDER BY created_at DESC
    """, (user_id,))
    results = c.fetchall()
    conn.close()
    return results

def get_active_orders_count(user_id):
    """دریافت تعداد سفارشات فعال"""
    conn = sqlite3.connect('print3d.db')
    c = conn.cursor()
    c.execute("""
        SELECT COUNT(*) FROM files 
        WHERE user_id = ? 
        AND status = 'در حال انجام'
    """, (user_id,))
    result = c.fetchone()
    conn.close()
    return result[0] if result else 0


def add_file(file_data):
    """ذخیره اطلاعات فایل در دیتابیس"""
    try:
        conn = sqlite3.connect('print3d.db')
        c = conn.cursor()

        c.execute('''INSERT INTO files 
                    (user_id, file_name, mime_type, file_id, file_unique_id, 
                     created_at, quantity, description, status, notes)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''',
                  file_data)
        conn.commit()
        return True
    except sqlite3.IntegrityError as e:
        print(f"خطای یکتایی: {str(e)}")
        return False
    except Exception as e:
        print(f"خطای عمومی در افزودن فایل: {str(e)}")
        return False
    finally:
        conn.close()

def get_files_by_user(user_id, days=None):
    conn = sqlite3.connect('print3d.db')
    c = conn.cursor()

    query = "SELECT * FROM files WHERE user_id = ?"
    params = [user_id]

    if days:
        date_filter = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d %H:%M:%S")
        query += " AND created_at >= ?"
        params.append(date_filter)

    c.execute(query, params)
    results = c.fetchall()
    conn.close()
    return results


def update_file_description(file_id, description):
    conn = sqlite3.connect('print3d.db')
    c = conn.cursor()
    try:
        c.execute("UPDATE files SET description = ? WHERE file_id = ?",
                 (description, file_id))
        conn.commit()
        return True
    except Exception as e:
        print(f"خطا در آپدیت توضیحات: {str(e)}")
        return False
    finally:
        conn.close()

def get_file_quantity(file_id):
    conn = sqlite3.connect('print3d.db')
    c = conn.cursor()
    c.execute("SELECT quantity FROM files WHERE file_id = ?", (file_id,))
    result = c.fetchone()
    conn.close()
    return result[0] if result else 1

def update_file_quantity(file_id, new_qty):
    print(f"Updated quantity for file {file_id} to {new_qty}")
    try:
        conn = sqlite3.connect('print3d.db')
        c = conn.cursor()
        c.execute("UPDATE files SET quantity = ? WHERE file_id = ?", (new_qty, file_id))
        conn.commit()
        return True
    except Exception as e:
        print(f"خطا در بروزرسانی تعداد: {str(e)}")
        return False
    finally:
        conn.close()

def delete_file(file_id):
    conn = sqlite3.connect('print3d.db')
    c = conn.cursor()
    c.execute("DELETE FROM files WHERE file_id = ?", (file_id,))
    conn.commit()
    conn.close()

def get_remaining_invites(user_id):
    conn = sqlite3.connect('print3d.db')
    c = conn.cursor()
    c.execute("SELECT remaining_invites FROM users WHERE id = ?", (user_id,))
    result = c.fetchone()
    conn.close()
    return result[0] if result else 0


def add_discount(user_id, amount):
    try:
        conn = sqlite3.connect('print3d.db')
        c = conn.cursor()

        c.execute("""
            UPDATE wallets 
            SET discount = discount + ? 
            WHERE user_id = ?
        """, (amount, user_id))

        conn.commit()
        return c.rowcount > 0

    except Exception as e:
        print(f"خطا در افزودن تخفیف: {str(e)}")
        return False
    finally:
        conn.close()


# این تابع را حفظ کرده و اصلاح کنید
def get_customer_kb(user_id):
    """تهیه کیبورد مشتری با نمایش تعداد سفارشات فعال"""
    from keyboards import ReplyKeyboardMarkup  # اضافه کردن ایمپورت

    active_orders = get_active_orders_count(user_id)

    return ReplyKeyboardMarkup(
        keyboard=[
            ["📂 آرشیو", f"🔄 درحال انجام ({active_orders})"],
            ["💳 کیف پول", "📞 پشتیبانی"],
            ["📜 قوانین", "🧾 فاکتور"],
            ["🎁 دریافت هدیه"]
        ],
        resize_keyboard=True,
        is_persistent=True
    )

# در فایل database.py این تابع را اضافه کنید

def meets_gift_conditions(user_id):
    try:
        conn = sqlite3.connect('print3d.db')
        c = conn.cursor()

        # مثال: حداقل ۳ سفارش تکمیل شده
        c.execute("""
            SELECT COUNT(*) FROM files 
            WHERE user_id = ? 
            AND status = 'تکمیل شده'
        """, (user_id,))

        result = c.fetchone()
        return result[0] >= 3 if result else False

    except Exception as e:
        print(f"خطا در بررسی شرایط هدیه: {str(e)}")
        return False
    finally:
        conn.close()

def get_completed_orders(user_id):
    """دریافت سفارشات تکمیل شده"""
    conn = sqlite3.connect('print3d.db')
    c = conn.cursor()
    c.execute("""
        SELECT * FROM files 
        WHERE user_id = ? 
        AND status = 'تکمیل شده'
    """, (user_id,))
    results = c.fetchall()
    conn.close()
    return results