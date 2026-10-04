"""
Sound Manager for AI MetaTrader 5 Trading Bot
ระบบจัดการเสียงแจ้งเตือนอัจฉริยะ:
1. เมื่อเข้าไม้ (Order Entry) -> เสียงดีใจ (Joyful Victory Fanfare 🎺✨)
2. เมื่อชน TP (Take Profit Hit) -> เสียงกระดิ่ง (Crystal Bell / Chimes 🔔)
3. เมื่อชน SL (Stop Loss Hit) -> เสียงอ๊อด (Game/Warning Buzzer 🛑)
4. เมื่ออัปเดตข้อมูล / AI Signal Alert -> ปิดเสียง (Muted)
5. เมื่อมีการขยับ SL (Move SL / Break-Even Lock) -> เสียงนกร้อง (Bird Chirp / จิ๊บๆ 🐦)
"""

import os
import sys
import wave
import struct
import math
import io
import time
import threading
import numpy as np

# ใช้ winsound สำหรับ Windows (Non-blocking & เสียงชัดเจน)
try:
    import winsound
    HAS_WINSOUND = True
except ImportError:
    HAS_WINSOUND = False

# จัดการ encoding สำหรับ Windows Console (CP874) ไม่ให้ error เมื่อ print emoji / ภาษาไทย
if sys.platform == 'win32':
    try:
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace', write_through=True)
    except Exception:
        pass


# กำหนดโฟลเดอร์สำหรับเก็บไฟล์เสียง รองรับทั้งตอนรันสคริปต์ปกติและตอนคอมไพล์เป็น .exe
BASE_DIR = os.path.dirname(sys.executable) if getattr(sys, 'frozen', False) else os.path.dirname(os.path.abspath(__file__))
SOUND_DIR = os.path.join(BASE_DIR, "sounds")
if not os.path.exists(SOUND_DIR) and getattr(sys, 'frozen', False):
    meipass = getattr(sys, '_MEIPASS', '')
    if meipass and os.path.exists(os.path.join(meipass, "sounds")):
        SOUND_DIR = os.path.join(meipass, "sounds")

FILE_JOYFUL     = os.path.join(SOUND_DIR, "joyful_celebration.wav") # 1. เข้าไม้ -> เสียงดีใจ (Fanfare)
FILE_TP_BELL    = os.path.join(SOUND_DIR, "tp_bell.wav")            # 2. ชน TP -> กระดิ่ง
FILE_SL_BUZZER  = os.path.join(SOUND_DIR, "sl_buzzer.wav")          # 3. ชน SL -> อ๊อด
FILE_UPDATE_BELL= os.path.join(SOUND_DIR, "update_bell.wav")        # 4. อัปเดตข้อมูล -> กระดิ่ง
FILE_BIRD       = os.path.join(SOUND_DIR, "move_sl_bird.wav")       # 5. ขยับ SL -> นกร้อง

SAMPLE_RATE = 44100


def _save_wav(filepath, samples):
    """บันทึก numpy array (-1.0 ถึง 1.0) เป็นไฟล์ WAV 16-bit Mono"""
    os.makedirs(os.path.dirname(filepath), exist_ok=True)
    samples = np.clip(samples, -0.98, 0.98)
    int_samples = (samples * 32767).astype(np.int16)
    with wave.open(filepath, 'w') as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(SAMPLE_RATE)
        wf.writeframes(int_samples.tobytes())


def generate_celebration_joy():
    """1. สร้างเสียงดีใจ (Joyful Victory Fanfare 🎺✨) ทำนองเพลงยินดีฉลองเข้าไม้ โด-มี-ซอล-โด๊ววว!"""
    notes = [
        # (start_t, dur, freq)
        (0.00, 0.12, 523.25),  # C5 (โด)
        (0.12, 0.12, 659.25),  # E5 (มี)
        (0.24, 0.14, 783.99),  # G5 (ซอล)
        (0.38, 0.50, 1046.50), # C6 (โด๊ววว ไฮโน้ตยาว ก้องกังวาน)
    ]
    total_duration = 0.95
    total_samples = int(SAMPLE_RATE * total_duration)
    output = np.zeros(total_samples)

    for start_t, dur, freq in notes:
        start_idx = int(SAMPLE_RATE * start_t)
        n_samples = int(SAMPLE_RATE * dur)
        t = np.linspace(0, dur, n_samples, endpoint=False)

        # เสียงฮาร์มอนิกสดใส (Warm Brass / Chime Fanfare)
        wave_note = (
            np.sin(2 * np.pi * freq * t) * 1.0 +
            np.sin(2 * np.pi * (freq * 2) * t) * 0.45 +
            np.sin(2 * np.pi * (freq * 3) * t) * 0.25 +
            np.sin(2 * np.pi * (freq * 4) * t) * 0.10
        )

        # ซองเสียง Attack นุ่ม + Decay เป็นธรรมชาติ
        attack = int(SAMPLE_RATE * 0.008)
        decay_rate = 3.5 if freq > 1000 else 4.5
        decay_env = np.exp(-t * decay_rate)
        if attack > 0 and attack < n_samples:
            decay_env[:attack] *= np.linspace(0, 1, attack)

        note_out = wave_note * decay_env
        end_idx = min(start_idx + n_samples, total_samples)
        length = end_idx - start_idx
        output[start_idx:end_idx] += note_out[:length]

    max_val = np.max(np.abs(output))
    if max_val > 0:
        output = output / max_val * 0.92
    return output



def generate_tp_bell():
    """2. สร้างเสียงกระดิ่ง (Crystal Bell / Chimes) กริ๊งงงง... ใส ไพเราะเมื่อชน TP ทำกำไร"""
    total_duration = 1.6
    total_samples = int(SAMPLE_RATE * total_duration)
    output = np.zeros(total_samples)
    
    # เคาะกระดิ่ง 2 ครั้งเบาๆ กริ๊ง-กริ๊ง (Strike 1 @ 0.0s, Strike 2 @ 0.22s)
    strikes = [
        (0.00, 1760.0, 0.85), # โน้ต A6 (1760 Hz)
        (0.22, 2093.0, 1.00), # โน้ต C7 (2093 Hz) เสียงสูง กังวานสดใส
    ]
    
    # โอเวอร์โทนของกระดิ่งโลหะ (Inharmonic metal modes)
    modes = [
        (1.00, 1.00, 1.2),   # Fundamental
        (2.01, 0.55, 0.8),   # Harmonic 2
        (3.02, 0.35, 0.5),   # Harmonic 3
        (4.25, 0.20, 0.3),   # Metal overtone 1
        (5.40, 0.12, 0.2),   # Metal overtone 2
    ]
    
    for start_t, base_freq, strike_vol in strikes:
        start_idx = int(SAMPLE_RATE * start_t)
        rem_samples = total_samples - start_idx
        t = np.linspace(0, rem_samples / SAMPLE_RATE, rem_samples, endpoint=False)
        
        strike_wave = np.zeros(rem_samples)
        for mult, amp, decay_rate in modes:
            freq = base_freq * mult
            env = np.exp(-t * (4.0 / decay_rate))
            strike_wave += np.sin(2 * np.pi * freq * t) * (amp * env)
            
        # เติมความใสของหัวไม้เคาะโลหะ (Strike transient click)
        click_len = min(int(SAMPLE_RATE * 0.004), rem_samples)
        strike_wave[:click_len] += np.random.normal(0, 0.4, click_len) * np.exp(-np.linspace(0, 5, click_len))
        
        output[start_idx:] += strike_wave * strike_vol

    max_val = np.max(np.abs(output))
    if max_val > 0:
        output = output / max_val * 0.95
    return output


def generate_sl_buzzer():
    """3. สร้างเสียงอ๊อด (Classic Game/Error Buzzer) อ๊อดดดด! ชัดเจนเมื่อชน SL"""
    duration = 0.45
    total_samples = int(SAMPLE_RATE * duration)
    t = np.linspace(0, duration, total_samples, endpoint=False)
    
    # ความถี่คู่คอร์ดกัดหู (Dissonant harsh low buzz 145 Hz + 185 Hz)
    f1 = 145.0
    f2 = 185.0
    
    # รวม Harmonic คลื่นสี่เหลี่ยม / ฟันเลื่อย (Odd harmonics)
    wave_buzz = np.zeros(total_samples)
    for h in range(1, 16, 2):
        wave_buzz += (1.0 / h) * np.sin(2 * np.pi * (f1 * h) * t)
        wave_buzz += (0.7 / h) * np.sin(2 * np.pi * (f2 * h) * t)
        
    # ซองเสียงแบบ Buzzer: 2 จังหวะ "อ๊อด-อ๊อด!" หรือ 1 จังหวะยาว "อ๊อดดดด!"
    # ทำเป็น 2 ช็อตกระแทกสั้นๆ: 0.16s เสียง - 0.05s หยุด - 0.22s เสียง
    env = np.zeros(total_samples)
    t1_end = int(SAMPLE_RATE * 0.16)
    t2_start = int(SAMPLE_RATE * 0.21)
    
    # ช็อตแรก
    env[:t1_end] = 1.0
    env[:int(SAMPLE_RATE * 0.005)] = np.linspace(0, 1, int(SAMPLE_RATE * 0.005))
    env[t1_end - int(SAMPLE_RATE * 0.01):t1_end] = np.linspace(1, 0, int(SAMPLE_RATE * 0.01))
    
    # ช็อตสอง
    env[t2_start:] = 1.0
    env[t2_start:t2_start + int(SAMPLE_RATE * 0.005)] = np.linspace(0, 1, int(SAMPLE_RATE * 0.005))
    env[-int(SAMPLE_RATE * 0.03):] = np.linspace(1, 0, int(SAMPLE_RATE * 0.03))
    
    output = wave_buzz * env
    max_val = np.max(np.abs(output))
    if max_val > 0:
        output = output / max_val * 0.90
    return output


def generate_update_bell():
    """4. สร้างเสียงกระดิ่ง (Crystal Bell Ding / Ping) ใสนุ่มนวล สบายหู สำหรับอัปเดตข้อมูล"""
    duration = 0.55
    total_samples = int(SAMPLE_RATE * duration)
    t = np.linspace(0, duration, total_samples, endpoint=False)
    
    # เคาะกระดิ่ง 1 ครั้ง โน้ต A6 (1760 Hz) ใส นุ่ม ละมุน
    base_freq = 1760.0
    modes = [
        (1.00, 0.85, 1.0),
        (2.02, 0.40, 0.7),
        (3.04, 0.22, 0.5),
        (4.28, 0.12, 0.3),
    ]
    bell_wave = np.zeros(total_samples)
    for mult, amp, decay_rate in modes:
        f = base_freq * mult
        env = np.exp(-t * (5.5 / decay_rate))
        bell_wave += np.sin(2 * np.pi * f * t) * (amp * env)
        
    # เติมความใสของหัวไม้เคาะโลหะเบาๆ
    click_len = min(int(SAMPLE_RATE * 0.003), total_samples)
    bell_wave[:click_len] += np.random.normal(0, 0.2, click_len) * np.exp(-np.linspace(0, 6, click_len))
    
    # Attack นุ่มนวล 2ms ไม่กระแทกลำโพง
    attack_samples = int(SAMPLE_RATE * 0.002)
    if attack_samples > 0:
        bell_wave[:attack_samples] *= np.linspace(0, 1, attack_samples)
        
    max_val = np.max(np.abs(bell_wave))
    if max_val > 0:
        output = bell_wave / max_val * 0.65
    return output


def generate_move_sl_bird():
    """5. สร้างเสียงนกร้อง (Bird Chirp / Songbird จิ๊บๆ) ใสธรรมชาติเมื่อมีการขยับ SL"""
    total_duration = 0.55
    total_samples = int(SAMPLE_RATE * total_duration)
    output = np.zeros(total_samples)
    
    # 2 พยางค์ จิ๊บ-จิ๊บ! น่ารักสดใส
    # พยางค์ 1: t = 0.00 - 0.11s (กวาดจาก 3200Hz -> 5400Hz -> 3800Hz)
    # พยางค์ 2: t = 0.17 - 0.32s (กวาดจาก 3500Hz -> 6200Hz -> 4100Hz พร้อมลูกคอ vibrato)
    chirps = [
        (0.00, 0.10, 3200.0, 5200.0, 0.85),
        (0.15, 0.14, 3400.0, 6100.0, 1.00),
        (0.33, 0.08, 4200.0, 5600.0, 0.70)
    ]
    
    for start_t, dur, f_start, f_peak, amp in chirps:
        s_idx = int(SAMPLE_RATE * start_t)
        c_samples = int(SAMPLE_RATE * dur)
        t = np.linspace(0, dur, c_samples, endpoint=False)
        
        # กวาดความถี่แบบพาราโบลาโค้งขึ้นแล้วลง
        f_mid = f_peak
        freq_curve = f_start + 4 * (f_mid - f_start) * (t / dur) * (1.0 - t / dur)
        # เติม vibrato นกร้องเบาๆ
        vibrato = 120.0 * np.sin(2 * np.pi * 50.0 * t)
        inst_freq = freq_curve + vibrato
        
        # Integrate phase
        dt = 1.0 / SAMPLE_RATE
        phase = 2 * np.pi * np.cumsum(inst_freq) * dt
        
        # Sine wave นกเสียงใส พร้อม harmonic บางๆ
        bird_tone = np.sin(phase) + 0.12 * np.sin(phase * 2.0)
        
        # Envelope โค้งมน
        c_env = np.sin(np.pi * t / dur) ** 1.5
        
        end_idx = min(s_idx + c_samples, total_samples)
        length = end_idx - s_idx
        output[s_idx:end_idx] += bird_tone[:length] * c_env[:length] * amp

    max_val = np.max(np.abs(output))
    if max_val > 0:
        output = output / max_val * 0.90
    return output


def ensure_all_sound_files():
    """ตรวจสอบและสร้างไฟล์เสียงทั้ง 5 แบบอัตโนมัติหากยังไม่มี"""
    os.makedirs(SOUND_DIR, exist_ok=True)
    
    creators = [
        (FILE_JOYFUL, generate_celebration_joy, "1. เสียงดีใจ (เข้าไม้)"),
        (FILE_TP_BELL, generate_tp_bell, "2. เสียงกระดิ่ง (ชน TP)"),
        (FILE_SL_BUZZER, generate_sl_buzzer, "3. เสียงอ๊อด (ชน SL)"),
        (FILE_UPDATE_BELL, generate_update_bell, "4. เสียงกระดิ่งนุ่มนวล (อัปเดตข้อมูล)"),
        (FILE_BIRD, generate_move_sl_bird, "5. เสียงนกร้อง (ขยับ SL)"),
    ]
    
    for filepath, func, label in creators:
        if not os.path.exists(filepath):
            try:
                samples = func()
                _save_wav(filepath, samples)
                # print(f"[AUDIO] Created {label} -> {os.path.basename(filepath)}")
            except Exception as e:
                print(f"[AUDIO ERROR] Failed to create {label}: {e}")


def _play_wav_async(filepath, fallback_beep=None):
    """เล่นไฟล์เสียง WAV ในพื้นหลังแบบไม่สะดุดการทำงานของบอท"""
    if not os.path.exists(filepath):
        ensure_all_sound_files()
        
    if HAS_WINSOUND and os.path.exists(filepath):
        try:
            # SND_FILENAME | SND_ASYNC (เล่นทันที ไม่บล็อก Thread / Terminal ไม่ค้าง)
            winsound.PlaySound(filepath, winsound.SND_FILENAME | winsound.SND_ASYNC)
            return
        except Exception:
            pass
            
    # กรณีฉุกเฉิน: Fallback ด้วย winsound.Beep
    if HAS_WINSOUND and fallback_beep:
        def _beep():
            for freq, dur in fallback_beep:
                try:
                    winsound.Beep(freq, dur)
                except Exception:
                    pass
        threading.Thread(target=_beep, daemon=True).start()


# ==============================================================================
# ฟังก์ชันเรียกใช้งานเสียงทั้ง 5 เหตุการณ์ (นำไปใช้ในบอทได้ทันที)
# ==============================================================================

def play_order_entry():
    """1. เมื่อเข้าไม้ -> เล่นเสียงดีใจ (Joyful Victory Fanfare 🎺✨ โด-มี-ซอล-โด๊ววว!)"""
    fallback = [(523, 120), (659, 120), (784, 120), (1046, 380)]
    _play_wav_async(FILE_JOYFUL, fallback_beep=fallback)


def play_tp_hit():
    """2. เมื่อชน TP -> เล่นเสียงกระดิ่ง (Crystal Bell / Chimes 🔔)"""
    fallback = [(1760, 180), (2093, 350)]
    _play_wav_async(FILE_TP_BELL, fallback_beep=fallback)


def play_sl_hit():
    """3. เมื่อชน SL -> เล่นเสียงอ๊อด (Game/Warning Buzzer 🛑)"""
    fallback = [(150, 200), (150, 300)]
    _play_wav_async(FILE_SL_BUZZER, fallback_beep=fallback)


def play_data_update():
    """4. เมื่ออัปเดตข้อมูล / AI Signal Alert -> ปิดเสียง (Muted ตามความต้องการ)"""
    pass


def play_sl_moved():
    """5. เมื่อมีการขยับ SL -> เล่นเสียงนกร้อง (Bird Chirp / จิ๊บๆ 🐦)"""
    fallback = [(3500, 80), (4500, 120)]
    _play_wav_async(FILE_BIRD, fallback_beep=fallback)


# สร้างไฟล์เสียงทันทีเมื่อ import โมดูล
ensure_all_sound_files()


if __name__ == "__main__":
    print("=" * 60)
    print("🔊 ทดสอบระบบเสียงทั้ง 5 แบบสำหรับ AI MetaTrader 5 Bot")
    print("=" * 60)
    
    print("\n1. 🎺 กำลังเล่น: เสียงดีใจ (เมื่อเข้าไม้)...")
    play_order_entry()
    time.sleep(2.0)
    
    print("2. 🔔 กำลังเล่น: เสียงกระดิ่ง (เมื่อชน TP)...")
    play_tp_hit()
    time.sleep(2.0)
    
    print("3. 🚨 กำลังเล่น: เสียงอ๊อด (เมื่อชน SL)...")
    play_sl_hit()
    time.sleep(1.5)
    
    print("4. 🔔 กำลังเล่น: เสียงกระดิ่งนุ่มนวล (เมื่ออัปเดตข้อมูล)...")
    play_data_update()
    time.sleep(1.5)
    
    print("5. 🐦 กำลังเล่น: เสียงนกร้อง (เมื่อมีการขยับ SL)...")
    play_sl_moved()
    time.sleep(1.5)
    
    print("\n✅ ทดสอบครบทั้ง 5 เสียงเรียบร้อยแล้ว!")
