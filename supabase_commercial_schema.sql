-- ==============================================================================
-- 👑 AI MetaTrader 5 (FBS) Gold Pro - Commercial Licensing & Analytics Schema
-- เวอร์ชัน: 2026.1003.0025 | สำหรับรันบน Supabase SQL Editor
-- ==============================================================================

-- 1. ตารางข้อมูลโปรไฟล์และกระเป๋าเวลาผู้ใช้งาน (users_profile)
CREATE TABLE IF NOT EXISTS users_profile (
    id UUID PRIMARY KEY REFERENCES auth.users(id) ON DELETE CASCADE,
    email TEXT UNIQUE NOT NULL,
    username TEXT,
    display_name TEXT,
    hours_remaining NUMERIC(10, 3) DEFAULT 48.000,     -- ชั่วโมงคงเหลือ (เริ่มต้น 48 ชม. ทดลองใช้)
    total_hours_purchased NUMERIC(10, 3) DEFAULT 0.000, -- จำนวนชั่วโมงรวมที่เคยซื้อ
    allow_shared_pool BOOLEAN DEFAULT FALSE,            -- สิทธิ์แชร์เวลาหลายเครื่อง (True = ตัดเวลารวมกัน)
    max_concurrent_sessions INTEGER DEFAULT 1,          -- จำนวนจอสูงสุดที่เปิดได้พร้อมกัน
    is_suspended BOOLEAN DEFAULT FALSE,                 -- สวิตช์ระงับบัญชี (กรณีทุจริต)
    suspend_reason TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_users_profile_email ON users_profile(email);

-- Trigger: สร้าง users_profile อัตโนมัติเมื่อมี User สมัครสมาชิกใหม่ผ่าน Supabase Auth
CREATE OR REPLACE FUNCTION public.handle_new_user()
RETURNS TRIGGER AS $$
BEGIN
    INSERT INTO public.users_profile (id, email, username, display_name, hours_remaining)
    VALUES (
        NEW.id,
        NEW.email,
        COALESCE(NEW.raw_user_meta_data->>'username', split_part(NEW.email, '@', 1)),
        COALESCE(NEW.raw_user_meta_data->>'display_name', split_part(NEW.email, '@', 1)),
        48.000 -- ให้โควต้าเริ่มต้น 48 ชม.
    )
    ON CONFLICT (id) DO NOTHING;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

DROP TRIGGER IF EXISTS on_auth_user_created ON auth.users;
CREATE TRIGGER on_auth_user_created
    AFTER INSERT ON auth.users
    FOR EACH ROW EXECUTE FUNCTION public.handle_new_user();


-- ==============================================================================
-- 2. ตารางบัตรเติมเวลา Product Key (product_keys)
-- รูปแบบรหัส: XXXX-XXXX-XXXX-XXXX-XXXX-XXXX (24 หลัก ตัวพิมพ์ใหญ่)
-- ==============================================================================
CREATE TABLE IF NOT EXISTS product_keys (
    key_code TEXT PRIMARY KEY,
    hours NUMERIC(10, 2) NOT NULL,
    bonus_hours NUMERIC(10, 2) DEFAULT 0.00,
    price_thb NUMERIC(10, 2) DEFAULT 0.00,
    status TEXT DEFAULT 'UNUSED',                      -- 'UNUSED', 'REDEEMED', 'CANCELLED'
    is_used BOOLEAN DEFAULT FALSE,
    purchased_by_user_id UUID REFERENCES users_profile(id),
    order_id TEXT,
    purchased_at TIMESTAMPTZ DEFAULT NOW(),
    redeemed_by_user_id UUID REFERENCES users_profile(id),
    redeemed_at TIMESTAMPTZ DEFAULT NULL
);

CREATE INDEX IF NOT EXISTS idx_product_keys_buyer ON product_keys(purchased_by_user_id);
CREATE INDEX IF NOT EXISTS idx_product_keys_used ON product_keys(is_used);
CREATE INDEX IF NOT EXISTS idx_product_keys_status ON product_keys(status);


-- ==============================================================================
-- 3. ตารางติดตาม Session สดที่กำลังรันอยู่ (license_sessions)
-- ==============================================================================
CREATE TABLE IF NOT EXISTS license_sessions (
    session_id TEXT PRIMARY KEY,                        -- สุ่มประจำจอนั้นๆ
    user_id UUID REFERENCES users_profile(id) ON DELETE CASCADE,
    device_name TEXT DEFAULT 'Windows-PC',              -- ชื่อคอมพิวเตอร์
    mt5_account BIGINT DEFAULT 0,                       -- เลขพอร์ต MT5
    ip_address TEXT,                                    -- IP Address
    started_at TIMESTAMPTZ DEFAULT NOW(),
    last_heartbeat TIMESTAMPTZ DEFAULT NOW()            -- อัปเดตทุกๆ 60 วินาที
);

CREATE INDEX IF NOT EXISTS idx_sessions_user ON license_sessions(user_id);
CREATE INDEX IF NOT EXISTS idx_sessions_hb ON license_sessions(last_heartbeat);


-- ==============================================================================
-- 4. ตารางแพ็กเกจชั่วโมงสำหรับขาย (packages) - อัตรา 1 บาท/ชั่วโมง
-- ==============================================================================
CREATE TABLE IF NOT EXISTS packages (
    id SERIAL PRIMARY KEY,
    name TEXT NOT NULL,
    hours NUMERIC(10, 2) NOT NULL,
    bonus_hours NUMERIC(10, 2) DEFAULT 0.00,
    price_thb NUMERIC(10, 2) NOT NULL,
    badge TEXT DEFAULT NULL,
    description TEXT,
    sort_order INTEGER DEFAULT 1,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

INSERT INTO packages (name, hours, bonus_hours, price_thb, badge, sort_order) VALUES
('Starter 50', 50, 0, 50.00, NULL, 1),
('Popular 100', 100, 0, 100.00, 'ขายดี 🔥', 2),
('Value 300', 300, 20, 300.00, 'แถมฟรี 20 ชม. ✨', 3),
('Marathon 500', 500, 50, 500.00, 'แถมฟรี 50 ชม. 👑', 4)
ON CONFLICT DO NOTHING;


-- ==============================================================================
-- 5. ตารางคำสั่งซื้อและการชำระเงิน (orders)
-- ==============================================================================
CREATE TABLE IF NOT EXISTS orders (
    order_id TEXT PRIMARY KEY,
    user_id UUID REFERENCES users_profile(id),
    package_id INTEGER REFERENCES packages(id),
    amount_thb NUMERIC(10, 2) NOT NULL,
    hours_to_add NUMERIC(10, 2) NOT NULL,
    status TEXT DEFAULT 'PENDING',                      -- 'PENDING', 'PAID', 'EXPIRED', 'FAILED'
    payment_method TEXT DEFAULT 'PROMPTPAY',
    qr_payload TEXT,
    qr_image_url TEXT,
    payment_ref TEXT,
    generated_key_code TEXT,
    paid_at TIMESTAMPTZ DEFAULT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_orders_status ON orders(status);
CREATE INDEX IF NOT EXISTS idx_orders_user ON orders(user_id);


-- ==============================================================================
-- 6. ตารางเวอร์ชันซอฟต์แวร์และการปล่อย Patch อัปเดต (app_releases)
-- ==============================================================================
CREATE TABLE IF NOT EXISTS app_releases (
    version TEXT PRIMARY KEY,                           -- เช่น '2026.1003.0025'
    download_url TEXT NOT NULL,
    checksum_sha256 TEXT NOT NULL,
    mandatory BOOLEAN DEFAULT TRUE,
    changelog TEXT,
    released_at TIMESTAMPTZ DEFAULT NOW()
);


-- ==============================================================================
-- 7. ตารางสถิติการเทรดรายบุคคลและรายแผน (user_plan_stats)
-- ==============================================================================
CREATE TABLE IF NOT EXISTS user_plan_stats (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    user_id UUID REFERENCES users_profile(id) ON DELETE CASCADE,
    email TEXT NOT NULL,
    plan_name TEXT NOT NULL,                            -- Plan 0, 1, 3, 4, 5
    total_trades INTEGER DEFAULT 0,
    win_trades INTEGER DEFAULT 0,
    loss_trades INTEGER DEFAULT 0,
    win_rate_pct NUMERIC(5, 2) DEFAULT 0.0,
    total_profit_usd NUMERIC(12, 2) DEFAULT 0.0,
    gross_profit_usd NUMERIC(12, 2) DEFAULT 0.0,
    gross_loss_usd NUMERIC(12, 2) DEFAULT 0.0,
    profit_factor NUMERIC(6, 2) DEFAULT 0.0,
    last_trade_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    CONSTRAINT uq_user_plan UNIQUE (user_id, plan_name)
);

CREATE INDEX IF NOT EXISTS idx_user_plan_stats_user ON user_plan_stats(user_id);
CREATE INDEX IF NOT EXISTS idx_user_plan_stats_plan ON user_plan_stats(plan_name);


-- ==============================================================================
-- ⚙️ POSTGRESQL RPC STORED FUNCTIONS
-- ==============================================================================

-- 🔹 RPC 1: redeem_product_key (แลก Product Key เป็นชั่วโมงสะสมแบบบวกเพิ่ม)
CREATE OR REPLACE FUNCTION redeem_product_key(p_key_code TEXT, p_user_id UUID DEFAULT NULL)
RETURNS JSONB AS $$
DECLARE
    v_user_id UUID;
    v_key RECORD;
    v_total_hours NUMERIC(10, 2);
    v_new_balance NUMERIC(10, 3);
BEGIN
    v_user_id := COALESCE(p_user_id, auth.uid());
    IF v_user_id IS NULL THEN
        RETURN jsonb_build_object('success', false, 'reason', 'UNAUTHORIZED', 'message', 'กรุณาเข้าสู่ระบบก่อนเติมชั่วโมง');
    END IF;

    -- ล็อกแถว Product Key เพื่อป้องกันการนำไปใช้ซ้ำพร้อมกัน
    SELECT * INTO v_key FROM product_keys WHERE key_code = p_key_code FOR UPDATE;
    
    IF NOT FOUND THEN
        RETURN jsonb_build_object('success', false, 'reason', 'INVALID_KEY', 'message', 'ไม่พบรหัส Product Key นี้ในระบบ');
    END IF;
    
    IF v_key.is_used THEN
        RETURN jsonb_build_object('success', false, 'reason', 'ALREADY_USED', 'message', 'Product Key นี้ถูกใช้งานไปแล้ว');
    END IF;

    v_total_hours := v_key.hours + COALESCE(v_key.bonus_hours, 0);

    -- อัปเดตสถานะคีย์ว่าถูกใช้งานแล้ว
    UPDATE product_keys 
    SET is_used = TRUE,
        status = 'REDEEMED',
        redeemed_by_user_id = v_user_id,
        redeemed_at = NOW()
    WHERE key_code = p_key_code;

    -- บวกเพิ่มชั่วโมงเข้ากระเป๋าของ User (Additive Top-up)
    UPDATE users_profile 
    SET hours_remaining = hours_remaining + v_total_hours,
        total_hours_purchased = total_hours_purchased + v_total_hours,
        updated_at = NOW()
    WHERE id = v_user_id
    RETURNING hours_remaining INTO v_new_balance;

    RETURN jsonb_build_object(
        'success', true, 
        'hours_granted', v_total_hours,
        'hours_remaining', round(v_new_balance::numeric, 2),
        'message', 'เติมชั่วโมงการใช้งานสำเร็จเรียบร้อยแล้ว!'
    );
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;


-- 🔹 RPC 2: start_bot_session (ยืนยันสิทธิ์จอเดี่ยว หรือโหมดแชร์หลายจอ)
CREATE OR REPLACE FUNCTION start_bot_session(
    p_session_id TEXT, 
    p_device_name TEXT DEFAULT 'Windows-PC',
    p_mt5_account BIGINT DEFAULT 0,
    p_user_id UUID DEFAULT NULL
)
RETURNS JSONB AS $$
DECLARE
    v_user_id UUID;
    v_usr RECORD;
    v_active_count INTEGER;
BEGIN
    v_user_id := COALESCE(p_user_id, auth.uid());
    IF v_user_id IS NULL THEN
        RETURN jsonb_build_object('success', false, 'reason', 'UNAUTHORIZED');
    END IF;

    SELECT * INTO v_usr FROM users_profile WHERE id = v_user_id;
    IF NOT FOUND THEN
        RETURN jsonb_build_object('success', false, 'reason', 'USER_NOT_FOUND');
    END IF;

    IF v_usr.is_suspended THEN
        RETURN jsonb_build_object('success', false, 'reason', 'ACCOUNT_SUSPENDED', 'message', v_usr.suspend_reason);
    END IF;

    IF v_usr.hours_remaining <= 0 THEN
        RETURN jsonb_build_object('success', false, 'reason', 'HOURS_EXPIRED', 'hours_left', 0);
    END IF;

    -- ล้าง Session ที่ขาดการส่ง Heartbeat เกิน 90 วินาที
    DELETE FROM license_sessions 
    WHERE last_heartbeat < (NOW() - INTERVAL '90 seconds');

    -- ตรวจสอบโหมด Concurrency
    IF NOT v_usr.allow_shared_pool THEN
        -- โหมดจอเดี่ยว: เตะจอเก่าของ User คนนี้ออกทั้งหมดทันที
        DELETE FROM license_sessions WHERE user_id = v_user_id;
        
        INSERT INTO license_sessions (session_id, user_id, device_name, mt5_account, last_heartbeat)
        VALUES (p_session_id, v_user_id, p_device_name, p_mt5_account, NOW());

        RETURN jsonb_build_object(
            'success', true, 
            'mode', 'SINGLE', 
            'customer', COALESCE(v_usr.display_name, v_usr.email),
            'hours_left', round(v_usr.hours_remaining::numeric, 2)
        );
    ELSE
        -- โหมดแชร์เวลาหลายจอ
        SELECT COUNT(*) INTO v_active_count FROM license_sessions WHERE user_id = v_user_id;
        
        IF v_active_count >= v_usr.max_concurrent_sessions THEN
            RETURN jsonb_build_object(
                'success', false, 
                'reason', 'MAX_SESSIONS_REACHED', 
                'message', 'เปิดใช้งานครบโควต้า ' || v_usr.max_concurrent_sessions || ' จอแล้ว'
            );
        END IF;

        INSERT INTO license_sessions (session_id, user_id, device_name, mt5_account, last_heartbeat)
        VALUES (p_session_id, v_user_id, p_device_name, p_mt5_account, NOW());

        RETURN jsonb_build_object(
            'success', true, 
            'mode', 'SHARED_POOL', 
            'customer', COALESCE(v_usr.display_name, v_usr.email),
            'hours_left', round(v_usr.hours_remaining::numeric, 2),
            'active_screens', v_active_count + 1
        );
    END IF;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;


-- 🔹 RPC 3: heartbeat_session (ตัดเวลาถอยหลัง 60 วิ และตรวจจับสถานะ)
CREATE OR REPLACE FUNCTION heartbeat_session(
    p_session_id TEXT, 
    p_seconds_elapsed INTEGER DEFAULT 60,
    p_user_id UUID DEFAULT NULL
)
RETURNS JSONB AS $$
DECLARE
    v_user_id UUID;
    v_usr RECORD;
    v_new_hours NUMERIC(10, 3);
    v_active_count INTEGER;
BEGIN
    v_user_id := COALESCE(p_user_id, auth.uid());
    IF v_user_id IS NULL THEN
        SELECT user_id INTO v_user_id FROM license_sessions WHERE session_id = p_session_id;
    END IF;

    IF v_user_id IS NULL THEN
        RETURN jsonb_build_object('status', 'KICKED_OUT', 'message', 'เซสชันนี้ถูกปิดหรือหมดอายุแล้ว');
    END IF;

    SELECT * INTO v_usr FROM users_profile WHERE id = v_user_id FOR UPDATE;
    IF NOT FOUND OR v_usr.is_suspended THEN
        DELETE FROM license_sessions WHERE session_id = p_session_id;
        RETURN jsonb_build_object('status', 'SUSPENDED', 'message', 'บัญชีถูกระงับการใช้งาน');
    END IF;

    IF NOT EXISTS (SELECT 1 FROM license_sessions WHERE session_id = p_session_id) THEN
        RETURN jsonb_build_object('status', 'KICKED_OUT', 'message', 'มีการเปิดใช้งานจากอุปกรณ์อื่นในโหมดจอเดี่ยว');
    END IF;

    UPDATE license_sessions SET last_heartbeat = NOW() WHERE session_id = p_session_id;

    -- ตัดเวลาตามจริง (เช่น 60 วินาที / 3600 = 0.0167 ชม.)
    v_new_hours := GREATEST(0.0, v_usr.hours_remaining - (p_seconds_elapsed::numeric / 3600.0));
    UPDATE users_profile SET hours_remaining = v_new_hours, updated_at = NOW() WHERE id = v_user_id;

    IF v_new_hours <= 0 THEN
        DELETE FROM license_sessions WHERE user_id = v_user_id;
        RETURN jsonb_build_object('status', 'HOURS_EXPIRED', 'hours_left', 0);
    END IF;

    SELECT COUNT(*) INTO v_active_count FROM license_sessions WHERE user_id = v_user_id;

    RETURN jsonb_build_object(
        'status', 'OK', 
        'hours_left', round(v_new_hours::numeric, 2),
        'mode', CASE WHEN v_usr.allow_shared_pool THEN 'SHARED_POOL' ELSE 'SINGLE' END,
        'active_screens', v_active_count
    );
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;


-- 🔹 RPC 4: mark_order_paid (ผลิต Product Key อัตโนมัติเมื่อตรวจพบเงินโอนเข้า)
CREATE OR REPLACE FUNCTION mark_order_paid(
    p_order_id TEXT, 
    p_payment_ref TEXT DEFAULT '',
    p_auto_generated_key TEXT DEFAULT ''
)
RETURNS JSONB AS $$
DECLARE
    v_ord RECORD;
    v_pkg RECORD;
    v_key_to_use TEXT;
BEGIN
    SELECT * INTO v_ord FROM orders WHERE order_id = p_order_id;
    IF NOT FOUND THEN
        RETURN jsonb_build_object('success', false, 'reason', 'ORDER_NOT_FOUND');
    END IF;

    IF v_ord.status = 'PAID' THEN
        RETURN jsonb_build_object('success', true, 'message', 'ALREADY_PAID', 'key_code', v_ord.generated_key_code);
    END IF;

    SELECT * INTO v_pkg FROM packages WHERE id = v_ord.package_id;

    v_key_to_use := p_auto_generated_key;

    -- บันทึก Product Key ลงตาราง product_keys พร้อมผูกกับ User ผู้สั่งซื้อ
    INSERT INTO product_keys (
        key_code, hours, bonus_hours, price_thb, status, is_used, 
        purchased_by_user_id, order_id, purchased_at
    )
    VALUES (
        v_key_to_use, v_pkg.hours, COALESCE(v_pkg.bonus_hours, 0), v_ord.amount_thb, 'UNUSED', FALSE, 
        v_ord.user_id, p_order_id, NOW()
    );

    -- อัปเดตสถานะออเดอร์
    UPDATE orders 
    SET status = 'PAID', 
        payment_ref = p_payment_ref, 
        generated_key_code = v_key_to_use,
        paid_at = NOW() 
    WHERE order_id = p_order_id;

    RETURN jsonb_build_object(
        'success', true, 
        'order_id', p_order_id,
        'product_key', v_key_to_use,
        'hours', v_pkg.hours + COALESCE(v_pkg.bonus_hours, 0)
    );
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;
