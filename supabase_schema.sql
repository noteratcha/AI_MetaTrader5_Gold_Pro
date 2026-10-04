-- ==============================================================================
-- 🚀 AI MetaTrader 5 (FBS) - Supabase Cloud Database Schema
-- สำหรับระบบ Dashboard ดูและตั้งค่า User / Password / Server และควบคุมบอทผ่าน Web
-- ==============================================================================

-- 1. ตารางตั้งค่าบอท และข้อมูลเชื่อมต่อ MT5 (bot_config)
CREATE TABLE IF NOT EXISTS bot_config (
    id INTEGER PRIMARY KEY DEFAULT 1,
    mt5_login BIGINT DEFAULT 0,                 -- เลขที่บัญชี MT5 (User)
    mt5_password TEXT DEFAULT '',               -- รหัสผ่าน MT5 (Password)
    mt5_server TEXT DEFAULT 'FBS-Real',         -- ชื่อเซิร์ฟเวอร์โบรกเกอร์ (เช่น FBS-Real, FBS-Demo)
    is_bot_active BOOLEAN DEFAULT TRUE,         -- สวิตช์เปิด/ปิด การเข้าเทรดของบอท (Master Switch)
    lot_size NUMERIC(6, 2) DEFAULT 0.01,        -- ขนาด Lot เริ่มต้น
    tp_rrr_btc NUMERIC(4, 2) DEFAULT 2.0,       -- Risk to Reward Ratio บิตคอยน์ (1:2.0)
    tp_rrr_xau NUMERIC(4, 2) DEFAULT 2.0,       -- Risk to Reward Ratio ทองคำ (1:2.0)
    cooldown_btc INTEGER DEFAULT 15,            -- ระยะเวลาพัก Cooldown BTC (นาที)
    cooldown_xau INTEGER DEFAULT 10,            -- ระยะเวลาพัก Cooldown XAU (นาที)
    symbols_trading TEXT[] DEFAULT ARRAY['BTCUSD', 'XAUUSD'], -- สินทรัพย์ที่ให้เข้าเทรดอัตโนมัติ
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- ใส่ข้อมูลตั้งต้นแถวแรก (id = 1) หากยังไม่มี
INSERT INTO bot_config (id, mt5_login, mt5_password, mt5_server, is_bot_active, lot_size, tp_rrr_btc, tp_rrr_xau, cooldown_btc, cooldown_xau)
VALUES (1, 0, '', 'FBS-Real', TRUE, 0.01, 2.0, 2.0, 15, 10)
ON CONFLICT (id) DO NOTHING;

-- 2. ตารางประวัติการเทรด (trade_logs)
CREATE TABLE IF NOT EXISTS trade_logs (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    ticket BIGINT,                              -- เลข Order Ticket จาก MT5
    time TIMESTAMPTZ DEFAULT NOW(),             -- เวลาทำรายการ
    symbol TEXT NOT NULL,                       -- คู่สินทรัพย์ (เช่น BTCUSD, XAUUSD)
    action TEXT NOT NULL,                       -- BUY, SELL, หรือ CLOSE
    plan TEXT,                                  -- แผนที่เข้า (เช่น Plan 0 SMC, Plan 1 Bounce, Plan 2 Breakout, AI Reversal)
    price NUMERIC(14, 5) NOT NULL,              -- ราคาที่เข้า หรือราคาที่ปิด
    lot NUMERIC(6, 2) NOT NULL,                 -- ขนาด Lot
    sl NUMERIC(14, 5) DEFAULT 0,                -- Stop Loss
    tp NUMERIC(14, 5) DEFAULT 0,                -- Take Profit
    profit NUMERIC(10, 2) DEFAULT 0,            -- กำไร/ขาดทุนเป็นเงิน USD (สำหรับไม้ที่ปิด)
    comment TEXT,                               -- หมายเหตุเพิ่มเติม
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- สร้าง Index เพื่อให้ดึงประวัติล่าสุดได้รวดเร็ว
CREATE INDEX IF NOT EXISTS idx_trade_logs_time ON trade_logs (time DESC);
CREATE INDEX IF NOT EXISTS idx_trade_logs_symbol ON trade_logs (symbol);

-- 3. ตารางสถานะเรียลไทม์ของบอท (bot_telemetry)
CREATE TABLE IF NOT EXISTS bot_telemetry (
    id INTEGER PRIMARY KEY DEFAULT 1,
    status TEXT DEFAULT 'ONLINE',               -- ONLINE, OFFLINE, PAUSED
    balance NUMERIC(12, 2) DEFAULT 0.0,         -- ยอดเงินในบัญชี (Balance)
    equity NUMERIC(12, 2) DEFAULT 0.0,          -- ทรัพย์สินสุทธิ (Equity)
    floating_profit NUMERIC(10, 2) DEFAULT 0.0, -- กำไร/ขาดทุนของไม้ที่กำลังวิ่งอยู่
    margin_free NUMERIC(12, 2) DEFAULT 0.0,     -- มาร์จิ้นคงเหลือ
    open_positions JSONB DEFAULT '[]'::jsonb,   -- รายการไม้ที่เปิดค้างอยู่แบบละเอียด
    radar_signals JSONB DEFAULT '[]'::jsonb,    -- สัญญาณเรดาร์ล่าสุดจาก AI
    last_heartbeat TIMESTAMPTZ DEFAULT NOW()    -- เวลาอัปเดตล่าสุดจากเครื่องบอท
);

INSERT INTO bot_telemetry (id, status, balance, equity, floating_profit, margin_free, open_positions, radar_signals, last_heartbeat)
VALUES (1, 'OFFLINE', 0.0, 0.0, 0.0, 0.0, '[]'::jsonb, '[]'::jsonb, NOW())
ON CONFLICT (id) DO NOTHING;

-- 4. ตารางบันทึกเหตุการณ์ความเสี่ยง (risk_events)
CREATE TABLE IF NOT EXISTS risk_events (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    time TIMESTAMPTZ DEFAULT NOW(),
    symbol TEXT NOT NULL,
    event_type TEXT NOT NULL,                   -- LOSS_BLOCK, CIRCUIT_BREAKER
    direction TEXT NOT NULL,                    -- BUY, SELL, หรือ N/A
    message TEXT,                               -- รายละเอียดเช่น "ขาดทุนติดต่อกัน 3 ไม้ - หยุด 60 นาที"
    loss_amount NUMERIC(10, 2) DEFAULT 0.0,     -- จำนวนเงินที่เสีย
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- สร้าง Index สำหรับ risk_events
CREATE INDEX IF NOT EXISTS idx_risk_events_time ON risk_events (time DESC);
CREATE INDEX IF NOT EXISTS idx_risk_events_symbol ON risk_events (symbol);

-- 5. ตั้งค่าสิทธิ์ความปลอดภัย (Row Level Security - RLS)
-- เปิดใช้งาน RLS
ALTER TABLE bot_config ENABLE ROW LEVEL SECURITY;
ALTER TABLE trade_logs ENABLE ROW LEVEL SECURITY;
ALTER TABLE bot_telemetry ENABLE ROW LEVEL SECURITY;
ALTER TABLE risk_events ENABLE ROW LEVEL SECURITY;

-- สร้าง Policy อนุญาตให้ Anon Key (จากเว็บ Frontend) และ Service Role อ่าน/เขียนได้
CREATE POLICY "Allow public read bot_config" ON bot_config FOR SELECT USING (true);
CREATE POLICY "Allow public update bot_config" ON bot_config FOR UPDATE USING (true);
CREATE POLICY "Allow public insert bot_config" ON bot_config FOR INSERT WITH CHECK (true);

CREATE POLICY "Allow public read trade_logs" ON trade_logs FOR SELECT USING (true);
CREATE POLICY "Allow public insert trade_logs" ON trade_logs FOR INSERT WITH CHECK (true);

CREATE POLICY "Allow public read bot_telemetry" ON bot_telemetry FOR SELECT USING (true);
CREATE POLICY "Allow public update bot_telemetry" ON bot_telemetry FOR UPDATE USING (true);
CREATE POLICY "Allow public insert bot_telemetry" ON bot_telemetry FOR INSERT WITH CHECK (true);

CREATE POLICY "Allow public read risk_events" ON risk_events FOR SELECT USING (true);
CREATE POLICY "Allow public insert risk_events" ON risk_events FOR INSERT WITH CHECK (true);

-- 5. ตารางบันทึกประวัติสัญญาณสำคัญ (signal_logs)
CREATE TABLE IF NOT EXISTS signal_logs (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    time TIMESTAMPTZ DEFAULT NOW(),
    symbol TEXT NOT NULL,
    signal_type TEXT NOT NULL,                  -- ZONE_ALERT, ENTRY_SIGNAL, H4_FILTERED, RISK_BLOCKED, DIVERGENCE
    plan TEXT,                                  -- SMC-LiquidityHunt, SR-SwingBounce, Trend-Breakout
    direction TEXT,                             -- BUY, SELL, N/A
    price NUMERIC(14, 5) NOT NULL,
    ai_up NUMERIC(5, 2) DEFAULT 0.0,
    ai_down NUMERIC(5, 2) DEFAULT 0.0,
    h4_trend TEXT,
    status TEXT,                                -- ORDER_SENT, WAIT_AI_CONFIRM, H4_BLOCKED, PLAN_BLOCKED, etc.
    detail TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_signal_logs_time ON signal_logs (time DESC);
CREATE INDEX IF NOT EXISTS idx_signal_logs_symbol ON signal_logs (symbol);

ALTER TABLE signal_logs ENABLE ROW LEVEL SECURITY;
CREATE POLICY "Allow public read signal_logs" ON signal_logs FOR SELECT USING (true);
CREATE POLICY "Allow public insert signal_logs" ON signal_logs FOR INSERT WITH CHECK (true);

-- 6. เปิดใช้งาน Realtime สำหรับ Supabase เพื่อให้หน้าเว็บอัปเดตอัตโนมัติทันทีที่มีการเปลี่ยนแปลง
ALTER PUBLICATION supabase_realtime ADD TABLE bot_config;
ALTER PUBLICATION supabase_realtime ADD TABLE trade_logs;
ALTER PUBLICATION supabase_realtime ADD TABLE bot_telemetry;
ALTER PUBLICATION supabase_realtime ADD TABLE risk_events;
ALTER PUBLICATION supabase_realtime ADD TABLE signal_logs;

