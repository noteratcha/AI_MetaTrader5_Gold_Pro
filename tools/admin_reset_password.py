"""
GoldBot24 — Admin: รีเซ็ตรหัสผ่านผู้ใช้
สร้างคำสั่ง SQL สำหรับตั้งรหัสผ่านใหม่ (hash แบบ v2 = PBKDF2-HMAC-SHA256 210,000 รอบ เหมือน web/src/lib/server/auth.js)
แล้วคัดลอกลง Clipboard ให้นำไปรันใน Supabase SQL Editor

วิธีใช้:  python tools/admin_reset_password.py           → รีเซ็ตรหัสผ่านผู้ใช้ที่มีอยู่แล้ว
         python tools/admin_reset_password.py --admin   → สร้าง/ซ่อมบัญชีแอดมิน (ตั้งรหัส + role:admin + ปลดระงับ + ปลดล็อกล็อกอินผิด)
รหัสผ่านพิมพ์แบบซ่อนตัวอักษร และไม่ถูกบันทึกลงไฟล์ใด ๆ
"""
import getpass
import hashlib
import os
import re
import subprocess
import sys

ITERATIONS = 210000


def hash_password_v2(password: str) -> str:
    salt = os.urandom(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, ITERATIONS, 32)
    return f"v2${salt.hex()}${digest.hex()}"


def copy_to_clipboard(text: str) -> bool:
    try:
        subprocess.run(
            ["powershell", "-NoProfile", "-Command", "$input | Set-Clipboard"],
            input=text.encode("utf-8"), check=True, capture_output=True,
        )
        return True
    except Exception:
        return False


def admin_upsert_sql(email: str, password_hash: str) -> str:
    """สร้างบัญชีแอดมินถ้ายังไม่มี หรืออัปเดตรหัสผ่าน + tag role:admin ถ้ามีอยู่แล้ว (รันซ้ำได้)"""
    return f"""DO $$
BEGIN
  UPDATE bot_config
  SET mt5_password = '{password_hash}',
      symbols_trading = array_append(
        array_remove(array_remove(array_remove(coalesce(symbols_trading, ARRAY[]::text[]), 'role:user'), 'role:admin'), 'status:disabled'),
        'role:admin'),
      updated_at = NOW()
  WHERE lower(trim(mt5_server)) = '{email}' AND id > 1;

  IF NOT FOUND THEN
    INSERT INTO bot_config (id, mt5_login, mt5_password, mt5_server, is_bot_active, lot_size, symbols_trading)
    VALUES (floor(random() * 90000000 + 10000)::bigint, 0, '{password_hash}', '{email}', true, 9999,
            ARRAY['name:Admin', 'role:admin', 'registered:' || NOW()::text]);
  END IF;

  -- ปลดล็อกการล็อกอินผิดหลายครั้ง (ถ้ามีตาราง user_activity)
  IF to_regclass('public.user_activity') IS NOT NULL THEN
    DELETE FROM user_activity WHERE email = '{email}' AND event = 'login_failed' AND created_at > NOW() - INTERVAL '1 hour';
  END IF;
END $$;

SELECT id, mt5_server, symbols_trading FROM bot_config WHERE lower(trim(mt5_server)) = '{email}';"""


def main():
    admin_mode = "--admin" in sys.argv
    default_email = ""
    prompt = f"อีเมล{'แอดมิน' if admin_mode else 'ผู้ใช้'}{f' [{default_email}]' if default_email else ''}: "
    email = (input(prompt).strip() or default_email).lower()
    if not re.match(r"^[^\s@']+@[^\s@']+\.[^\s@']+$", email):
        sys.exit("อีเมลไม่ถูกต้อง")

    pw1 = getpass.getpass("รหัสผ่านใหม่ (อย่างน้อย 6 ตัว, ไม่แสดงขณะพิมพ์): ")
    pw2 = getpass.getpass("พิมพ์รหัสผ่านใหม่อีกครั้ง: ")
    if pw1 != pw2:
        sys.exit("รหัสผ่านทั้งสองช่องไม่ตรงกัน")
    if len(pw1) < 6:
        sys.exit("รหัสผ่านต้องมีอย่างน้อย 6 ตัวอักษร")

    if admin_mode:
        sql = admin_upsert_sql(email, hash_password_v2(pw1))
        if copy_to_clipboard(sql):
            print("\nคัดลอก SQL ลง Clipboard แล้ว — วางใน Supabase SQL Editor แล้วกด Run")
            print("ผลลัพธ์ควรได้ 1 แถว และ symbols_trading มี role:admin")
        else:
            print("\nคัดลอกลง Clipboard ไม่ได้ — คัดลอกคำสั่งด้านล่างไปรันเอง:\n")
            print(sql)
        return

    sql = (
        "UPDATE bot_config\n"
        f"SET mt5_password = '{hash_password_v2(pw1)}', updated_at = NOW()\n"
        f"WHERE lower(trim(mt5_server)) = '{email}' AND id > 1\n"
        "RETURNING id, mt5_server;"
    )
    if copy_to_clipboard(sql):
        print("\nคัดลอก SQL ลง Clipboard แล้ว — วางใน Supabase SQL Editor แล้วกด Run (ควรได้ผลลัพธ์ 1 แถว)")
    else:
        print("\nคัดลอกลง Clipboard ไม่ได้ — คัดลอกคำสั่งด้านล่างไปรันเอง:\n")
        print(sql)


if __name__ == "__main__":
    main()
