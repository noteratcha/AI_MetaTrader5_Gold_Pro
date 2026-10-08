"""
เปิดปุ่ม Algo Trading ของ MetaTrader 5 ให้อัตโนมัติ (ผู้ใช้สั่ง 8 ต.ค. 2026)
- MT5 Python API อ่านสถานะได้ (terminal_info().trade_allowed) แต่ไม่มีคำสั่งเปิด/ปิดปุ่มนี้
- วิธี: ดึงหน้าต่าง MT5 "ตัวที่ Python เชื่อมอยู่" (exe อยู่ในโฟลเดอร์ terminal_info().path) ขึ้นมา → กดปุ่มลัด Ctrl+E ของ MT5
  → ตรวจผลจาก trade_allowed อีกครั้ง → คืนหน้าต่างเดิม
- Ctrl+E เป็นปุ่มสลับ: ส่งเฉพาะตอนที่ "ปิดอยู่" และส่งครั้งเดียว (ไม่มีทางกลายเป็นปิดปุ่มที่เปิดอยู่)
- ทำเฉพาะตอนเปิดโปรแกรมและตอนกดเริ่มบอท — ถ้าผู้ใช้ปิดเองระหว่างทาง ไม่เปิดคืนให้ (เคารพการตัดสินใจของผู้ใช้)
"""
import ctypes
import os
import time
from ctypes import wintypes

import MetaTrader5 as mt5

MT5_WINDOW_CLASS = "MetaQuotes::MetaTrader::5.00"
_user32 = ctypes.WinDLL("user32", use_last_error=True)
_kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
_WNDENUMPROC = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)
_user32.EnumWindows.argtypes = [_WNDENUMPROC, wintypes.LPARAM]
_user32.GetWindowThreadProcessId.argtypes = [wintypes.HWND, ctypes.POINTER(wintypes.DWORD)]
_user32.GetWindowThreadProcessId.restype = wintypes.DWORD
_user32.GetForegroundWindow.restype = wintypes.HWND
_kernel32.OpenProcess.restype = wintypes.HANDLE
VK_CONTROL, VK_E, KEYEVENTF_KEYUP, SW_RESTORE = 0x11, 0x45, 0x0002, 9


def is_enabled() -> bool:
    t = mt5.terminal_info()
    return bool(t and t.trade_allowed)


def _process_path(pid: int) -> str:
    h = _kernel32.OpenProcess(0x1000, False, pid)   # PROCESS_QUERY_LIMITED_INFORMATION
    if not h:
        return ""
    try:
        buf = ctypes.create_unicode_buffer(1024)
        size = wintypes.DWORD(1024)
        if _kernel32.QueryFullProcessImageNameW(h, 0, buf, ctypes.byref(size)):
            return buf.value
        return ""
    finally:
        _kernel32.CloseHandle(h)


def terminal_windows() -> list:
    """หน้าต่างหลักของ MT5 ตัวที่ Python API เชื่อมอยู่ (เทียบโฟลเดอร์ของ exe กับ terminal_info().path)"""
    info = mt5.terminal_info()
    want = os.path.normcase(os.path.normpath(info.path)) if info and info.path else None
    found = []

    def cb(hwnd, _lp):
        if not _user32.IsWindowVisible(hwnd):
            return True
        cls = ctypes.create_unicode_buffer(256)
        _user32.GetClassNameW(hwnd, cls, 256)
        if cls.value != MT5_WINDOW_CLASS:
            return True
        pid = wintypes.DWORD()
        _user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
        exe = _process_path(pid.value)
        if want is None or (exe and os.path.normcase(os.path.dirname(exe)) == want):
            found.append(hwnd)
        return True

    _user32.EnumWindows(_WNDENUMPROC(cb), 0)
    return found


def _bring_to_front(hwnd) -> bool:
    if not hwnd:
        return False
    if _user32.IsIconic(hwnd):
        _user32.ShowWindow(hwnd, SW_RESTORE)
    fg = _user32.GetForegroundWindow()
    me = _kernel32.GetCurrentThreadId()
    fg_tid = _user32.GetWindowThreadProcessId(fg, None) if fg else 0
    attached = bool(fg_tid and fg_tid != me and _user32.AttachThreadInput(fg_tid, me, True))
    try:
        _user32.BringWindowToTop(hwnd)
        _user32.SetForegroundWindow(hwnd)
    finally:
        if attached:
            _user32.AttachThreadInput(fg_tid, me, False)
    time.sleep(0.25)
    return _user32.GetForegroundWindow() == hwnd


def ensure_enabled(timeout: float = 3.0):
    """เปิด Algo Trading ถ้ายังปิดอยู่ → (สำเร็จ?, ข้อความภาษาไทย)"""
    if mt5.terminal_info() is None and not mt5.initialize():
        return False, "เชื่อมต่อ MT5 ไม่ได้ — เปิดและล็อกอิน MetaTrader 5 ก่อน"
    t = mt5.terminal_info()
    if getattr(t, "tradeapi_disabled", False):
        return False, "MT5 ปิดการเทรดผ่าน Python API ไว้ — เมนู Tools › Options › Expert Advisors เอาติ๊ก 'Disable automatic trading via external Python API' ออก"
    if t.trade_allowed:
        return True, "Algo Trading ใน MT5 เปิดอยู่แล้ว"
    wins = terminal_windows()
    if not wins:
        return False, "หาหน้าต่าง MT5 ไม่พบ — กรุณากดปุ่ม Algo Trading ใน MT5 ให้เป็นสีเขียวเอง"
    prev = _user32.GetForegroundWindow()
    try:
        if not _bring_to_front(wins[0]):
            return False, "ดึงหน้าต่าง MT5 ขึ้นมาไม่ได้ — กรุณากดปุ่ม Algo Trading ใน MT5 ให้เป็นสีเขียวเอง"
        # Ctrl+E = ปุ่มลัดเปิด/ปิด Algo Trading ของ MT5 (ส่งครั้งเดียว เฉพาะตอนที่ปิดอยู่)
        _user32.keybd_event(VK_CONTROL, 0, 0, 0)
        _user32.keybd_event(VK_E, 0, 0, 0)
        _user32.keybd_event(VK_E, 0, KEYEVENTF_KEYUP, 0)
        _user32.keybd_event(VK_CONTROL, 0, KEYEVENTF_KEYUP, 0)
        end = time.time() + timeout
        while time.time() < end:
            time.sleep(0.2)
            if is_enabled():
                return True, "เปิด Algo Trading ใน MT5 ให้อัตโนมัติแล้ว"
        return False, "สั่งเปิด Algo Trading ไม่สำเร็จ — กรุณากดปุ่ม Algo Trading ใน MT5 ให้เป็นสีเขียวเอง"
    finally:
        if prev:
            _bring_to_front(prev)
