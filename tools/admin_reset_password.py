"""
GoldBot24 — Admin: รีเซ็ตรหัสผ่านผู้ใช้
สร้างคำสั่ง SQL สำหรับตั้งรหัสผ่านใหม่ (hash แบบ v2 = PBKDF2-HMAC-SHA256 210,000 รอบ เหมือน web/src/lib/server/auth.js)
แล้วคัดลอกลง Clipboard ให้นำไปรันใน Supabase SQL Editor

วิธีใช้:  python tools/admin_reset_password.py
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


def main():
    email = input("อีเมลผู้ใช้: ").strip().lower()
    if not re.match(r"^[^\s@']+@[^\s@']+\.[^\s@']+$", email):
        sys.exit("อีเมลไม่ถูกต้อง")

    pw1 = getpass.getpass("รหัสผ่านใหม่ (อย่างน้อย 6 ตัว, ไม่แสดงขณะพิมพ์): ")
    pw2 = getpass.getpass("พิมพ์รหัสผ่านใหม่อีกครั้ง: ")
    if pw1 != pw2:
        sys.exit("รหัสผ่านทั้งสองช่องไม่ตรงกัน")
    if len(pw1) < 6:
        sys.exit("รหัสผ่านต้องมีอย่างน้อย 6 ตัวอักษร")

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
