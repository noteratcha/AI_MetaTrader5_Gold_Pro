'use client';

import React, { useState, useEffect } from 'react';
import Link from 'next/link';
import Navbar from '../components/Navbar';
import Footer from '../components/Footer';
import { 
  getSupabase, 
  getSupabaseConfig, 
  saveSupabaseConfig 
} from '../lib/supabase';
import { 
  Bot, 
  Shield, 
  Settings, 
  Key, 
  Server, 
  User, 
  Eye, 
  EyeOff, 
  Play, 
  Pause, 
  TrendingUp, 
  TrendingDown, 
  RefreshCw, 
  Database, 
  CheckCircle2, 
  AlertTriangle, 
  Activity, 
  Clock, 
  Layers, 
  DollarSign, 
  ExternalLink,
  ChevronRight,
  Flame,
  Radio,
  LogIn,
  UserPlus,
  LogOut
} from 'lucide-react';
import { useAuth } from '../context/AuthContext';

export default function Dashboard() {
  const { user, isLoading, openAuthModal } = useAuth();

  // Login Gate: ถ้ายังไม่ได้ Login ให้แสดงหน้าจอเข้าสู่ระบบ
  if (!isLoading && !user) {
    return (
      <div style={{ minHeight: '100vh', display: 'flex', flexDirection: 'column' }}>
        <Navbar />

        <main style={{ maxWidth: '620px', margin: 'auto', padding: '4rem 1.5rem', width: '100%' }}>
          <div style={{
            backgroundColor: 'var(--bg-card)',
            border: '1px solid rgba(251, 191, 36, 0.4)',
            borderRadius: '20px',
            padding: '3rem 2rem',
            textAlign: 'center',
            boxShadow: '0 0 35px rgba(251, 191, 36, 0.15)'
          }}>
            <div style={{
              width: '68px',
              height: '68px',
              borderRadius: '18px',
              backgroundColor: 'rgba(251, 191, 36, 0.12)',
              border: '1.5px solid rgba(251, 191, 36, 0.4)',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              margin: '0 auto 1.5rem auto'
            }}>
              <Bot size={32} color="#fbbf24" />
            </div>

            <h1 style={{ fontSize: '1.8rem', fontWeight: 800, color: '#fff', marginBottom: '0.6rem', letterSpacing: '-0.02em' }}>
              เข้าสู่ระบบเพื่อใช้งานแดชบอร์ด
            </h1>
            <p style={{ color: 'var(--text-secondary)', fontSize: '0.9rem', lineHeight: '1.6', marginBottom: '2rem' }}>
              หน้านี้สำหรับสมาชิก <strong>GoldBot24</strong> ในการดูข้อมูลบอทเรียลไทม์ กรุณาเข้าสู่ระบบหรือสมัครสมาชิกเพื่อเริ่มต้นใช้งาน
            </p>

            <div style={{ display: 'flex', gap: '0.75rem', justifyContent: 'center', flexWrap: 'wrap' }}>
              <button
                onClick={() => openAuthModal('login')}
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  gap: '0.5rem',
                  padding: '12px 26px',
                  borderRadius: '10px',
                  backgroundColor: '#fbbf24',
                  color: '#07090e',
                  fontWeight: 800,
                  fontSize: '0.92rem',
                  border: 'none',
                  cursor: 'pointer',
                  boxShadow: '0 0 20px rgba(251, 191, 36, 0.3)'
                }}
              >
                <LogIn size={16} />
                <span>เข้าสู่ระบบ (Login)</span>
              </button>
              <button
                onClick={() => openAuthModal('register')}
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  gap: '0.5rem',
                  padding: '12px 24px',
                  borderRadius: '10px',
                  backgroundColor: 'rgba(255, 255, 255, 0.08)',
                  color: '#fff',
                  fontWeight: 700,
                  fontSize: '0.92rem',
                  border: '1px solid var(--border-subtle)',
                  cursor: 'pointer'
                }}
              >
                <UserPlus size={16} />
                <span>สมัครสมาชิกใหม่ฟรี (+48 ชม.)</span>
              </button>
            </div>
          </div>
        </main>

        <Footer />
      </div>
    );
  }

  // Config & Credentials State (Gold Only)
  const [botConfig, setBotConfig] = useState({
    mt5_login: '',
    mt5_password: '',
    mt5_server: 'FBS-Real',
    is_bot_active: true,
    lot_size: 0.01,
    tp_rrr_xau: 1.50,
    cooldown_xau: 10,
    symbols_trading: ['XAUUSD']
  });

  // Telemetry & Market State - เริ่มต้นเป็น 0/ว่าง
  const [telemetry, setTelemetry] = useState({
    status: 'OFFLINE',
    balance: 0.0,
    equity: 0.0,
    floating_profit: 0.0,
    margin_free: 0.0,
    last_heartbeat: null,
    open_positions: [],
    radar_signals: [
      { symbol: 'XAUUSD', price: 0, up_prob: 0.50, status: '[WAIT OUTSIDE ZONE]', in_zone: false }
    ]
  });

  // Trade History Logs - เริ่มต้นว่าง
  const [tradeLogs, setTradeLogs] = useState([]);

  // UI States
  const [mounted, setMounted] = useState(false);
  const [isSettingsOpen, setIsSettingsOpen] = useState(false);
  const [isCloudKeysOpen, setIsCloudKeysOpen] = useState(false);
  const [showPassword, setShowPassword] = useState(false);
  const [isSaving, setIsSaving] = useState(false);
  const [saveSuccess, setSaveSuccess] = useState(false);
  const [isConnectedToSupabase, setIsConnectedToSupabase] = useState(false);
  const [lastRefreshed, setLastRefreshed] = useState(null);

  // Cloud keys state
  const [cloudUrl, setCloudUrl] = useState('');
  const [cloudAnonKey, setCloudAnonKey] = useState('');

  // Initial Data Fetch - ดึงข้อมูลเฉพาะตอน Login แล้ว
  useEffect(() => {

    // โหลดข้อมูลล็อกอินที่เคยจำไว้ในเครื่อง (localStorage) ทันที
    if (typeof window !== 'undefined') {
      const savedLogin = localStorage.getItem('remember_mt5_login');
      const savedPass = localStorage.getItem('remember_mt5_password');
      const savedServer = localStorage.getItem('remember_mt5_server');
      if (savedLogin || savedPass || savedServer) {
        setBotConfig(prev => ({
          ...prev,
          mt5_login: savedLogin || prev.mt5_login,
          mt5_password: savedPass || prev.mt5_password,
          mt5_server: savedServer || prev.mt5_server
        }));
      }
    }

    const config = getSupabaseConfig();
    setCloudUrl(config.url || '');
    setCloudAnonKey(config.anonKey || '');
    fetchCloudData();

    // Auto-refresh interval (every 3 seconds fallback)
    const interval = setInterval(() => {
      fetchCloudData();
    }, 3000);

    // Supabase Realtime WebSocket Subscription
    const supabase = getSupabase();
    let channel = null;
    if (supabase) {
      channel = supabase
        .channel('cloud_live_feed')
        .on('postgres_changes', { event: '*', schema: 'public', table: 'bot_telemetry' }, (payload) => {
          if (payload.new) {
            const telemData = payload.new;
            setTelemetry(prev => ({
              ...prev,
              status: telemData.status !== undefined ? telemData.status : prev.status,
              balance: telemData.balance !== undefined ? Number(telemData.balance) : prev.balance,
              equity: telemData.equity !== undefined ? Number(telemData.equity) : prev.equity,
              floating_profit: telemData.floating_profit !== undefined ? Number(telemData.floating_profit) : 0,
              margin_free: telemData.margin_free !== undefined ? Number(telemData.margin_free) : prev.margin_free,
              last_heartbeat: telemData.last_heartbeat || prev.last_heartbeat,
              open_positions: Array.isArray(telemData.open_positions) ? telemData.open_positions : prev.open_positions,
              radar_signals: Array.isArray(telemData.radar_signals) ? telemData.radar_signals : prev.radar_signals,
            }));
            setLastRefreshed(new Date());
          }
        })
        .on('postgres_changes', { event: '*', schema: 'public', table: 'bot_config' }, (payload) => {
          if (payload.new) {
            const configData = payload.new;
            const loginStr = configData.mt5_login ? String(configData.mt5_login) : '';
            const passStr = configData.mt5_password || '';
            const serverStr = configData.mt5_server || 'FBS-Real';

            setBotConfig(prev => ({
              ...prev,
              mt5_login: loginStr || prev.mt5_login,
              mt5_password: passStr || prev.mt5_password,
              mt5_server: serverStr || prev.mt5_server,
              is_bot_active: configData.is_bot_active !== undefined ? configData.is_bot_active : prev.is_bot_active,
              lot_size: Number(configData.lot_size) || prev.lot_size,
              tp_rrr_btc: Number(configData.tp_rrr_btc) || prev.tp_rrr_btc,
              tp_rrr_xau: Number(configData.tp_rrr_xau) || prev.tp_rrr_xau,
              cooldown_btc: Number(configData.cooldown_btc) || prev.cooldown_btc,
              cooldown_xau: Number(configData.cooldown_xau) || prev.cooldown_xau,
            }));

            if (typeof window !== 'undefined') {
              if (loginStr) localStorage.setItem('remember_mt5_login', loginStr);
              if (passStr) localStorage.setItem('remember_mt5_password', passStr);
              if (serverStr) localStorage.setItem('remember_mt5_server', serverStr);
            }
          }
        })
        .on('postgres_changes', { event: '*', schema: 'public', table: 'trade_logs' }, () => {
          fetchCloudData();
        })
        .subscribe();
    }

    return () => {
      clearInterval(interval);
      if (channel && supabase) {
        supabase.removeChannel(channel);
      }
    };
  }, []);

  async function fetchCloudData() {
    const supabase = getSupabase();
    if (!supabase) {
      setIsConnectedToSupabase(false);
      return;
    }

    try {
      // 1. Fetch bot_config
      const { data: configData, error: configError } = await supabase
        .from('bot_config')
        .select('*')
        .eq('id', 1)
        .single();

      if (!configError && configData) {
        const loginStr = configData.mt5_login ? String(configData.mt5_login) : '';
        const passStr = configData.mt5_password || '';
        const serverStr = configData.mt5_server || 'FBS-Real';

        setBotConfig(prev => ({
          ...prev,
          mt5_login: loginStr || prev.mt5_login,
          mt5_password: passStr || prev.mt5_password,
          mt5_server: serverStr || prev.mt5_server,
          is_bot_active: configData.is_bot_active !== undefined ? configData.is_bot_active : prev.is_bot_active,
          lot_size: Number(configData.lot_size) || prev.lot_size,
          tp_rrr_btc: Number(configData.tp_rrr_btc) || prev.tp_rrr_btc,
          tp_rrr_xau: Number(configData.tp_rrr_xau) || prev.tp_rrr_xau,
          cooldown_btc: Number(configData.cooldown_btc) || prev.cooldown_btc,
          cooldown_xau: Number(configData.cooldown_xau) || prev.cooldown_xau,
        }));

        // จดจำลง localStorage อัตโนมัติ เพื่อให้จำได้เสมอแม้รีเฟรชหน้าจอ
        if (typeof window !== 'undefined') {
          if (loginStr) localStorage.setItem('remember_mt5_login', loginStr);
          if (passStr) localStorage.setItem('remember_mt5_password', passStr);
          if (serverStr) localStorage.setItem('remember_mt5_server', serverStr);
        }

        setIsConnectedToSupabase(true);
      }

      // 2. Fetch bot_telemetry
      const { data: telemData, error: telemError } = await supabase
        .from('bot_telemetry')
        .select('*')
        .eq('id', 1)
        .single();

      if (!telemError && telemData) {
        setTelemetry(prev => ({
          ...prev,
          status: telemData.status !== undefined ? telemData.status : prev.status,
          balance: telemData.balance !== undefined ? Number(telemData.balance) : prev.balance,
          equity: telemData.equity !== undefined ? Number(telemData.equity) : prev.equity,
          floating_profit: telemData.floating_profit !== undefined ? Number(telemData.floating_profit) : 0,
          margin_free: telemData.margin_free !== undefined ? Number(telemData.margin_free) : prev.margin_free,
          last_heartbeat: telemData.last_heartbeat || prev.last_heartbeat,
          open_positions: Array.isArray(telemData.open_positions) ? telemData.open_positions : prev.open_positions,
          radar_signals: Array.isArray(telemData.radar_signals) ? telemData.radar_signals : prev.radar_signals,
        }));
      }

      // 3. Fetch trade_logs — เรียงตามเวลาเหตุการณ์จากใหม่ไปเก่า
      const { data: logsData, error: logsError } = await supabase
        .from('trade_logs')
        .select('*')
        .order('time', { ascending: false })
        .limit(50);

      if (!logsError && logsData && logsData.length > 0) {
        // sort อีกครั้งฝั่ง client เพื่อความแน่ใจ (ใหม่สุดขึ้นก่อน)
        const sorted = [...logsData].sort((a, b) => {
          const ta = new Date(String(a.time).replace(' ', 'T').replace(/([^Z+])$/, '$1Z'));
          const tb = new Date(String(b.time).replace(' ', 'T').replace(/([^Z+])$/, '$1Z'));
          return tb - ta;
        });
        setTradeLogs(sorted);
      }

      setLastRefreshed(new Date());
    } catch (err) {
      console.warn('Supabase fetch error:', err);
    }
  }

  // Toggle Bot Master Switch
  async function handleToggleBotActive() {
    const nextStatus = !botConfig.is_bot_active;
    setBotConfig(prev => ({ ...prev, is_bot_active: nextStatus }));

    const supabase = getSupabase();
    if (supabase) {
      await supabase
        .from('bot_config')
        .update({ is_bot_active: nextStatus, updated_at: new Date().toISOString() })
        .eq('id', 1);
    }
  }

  // Save Credentials & Settings to Supabase
  async function handleSaveSettings(e) {
    if (e) e.preventDefault();
    setIsSaving(true);

    // บันทึกจดจำไว้ใน localStorage ของเครื่องผู้ใช้ทันที
    if (typeof window !== 'undefined') {
      if (botConfig.mt5_login) localStorage.setItem('remember_mt5_login', String(botConfig.mt5_login));
      if (botConfig.mt5_password) localStorage.setItem('remember_mt5_password', botConfig.mt5_password);
      if (botConfig.mt5_server) localStorage.setItem('remember_mt5_server', botConfig.mt5_server);
    }

    const supabase = getSupabase();
    if (supabase) {
      try {
        const { error } = await supabase
          .from('bot_config')
          .upsert({
            id: 1,
            mt5_login: botConfig.mt5_login ? Number(botConfig.mt5_login) : 0,
            mt5_password: botConfig.mt5_password,
            mt5_server: botConfig.mt5_server,
            is_bot_active: botConfig.is_bot_active,
            lot_size: Number(botConfig.lot_size),
            tp_rrr_btc: Number(botConfig.tp_rrr_btc),
            tp_rrr_xau: Number(botConfig.tp_rrr_xau),
            cooldown_btc: Number(botConfig.cooldown_btc),
            cooldown_xau: Number(botConfig.cooldown_xau),
            updated_at: new Date().toISOString()
          });

        if (!error) {
          setSaveSuccess(true);
          setTimeout(() => {
            setSaveSuccess(false);
            setIsSettingsOpen(false);
          }, 1500);
        } else {
          alert('เกิดข้อผิดพลาดในการบันทึก: ' + error.message);
        }
      } catch (err) {
        alert('เกิดข้อผิดพลาด: ' + err.message);
      }
    } else {
      // Local fallback
      setSaveSuccess(true);
      setTimeout(() => {
        setSaveSuccess(false);
        setIsSettingsOpen(false);
      }, 1200);
    }
    setIsSaving(false);
  }

  // Save Supabase Keys
  function handleSaveCloudKeys(e) {
    e.preventDefault();
    saveSupabaseConfig(cloudUrl, cloudAnonKey);
    setIsCloudKeysOpen(false);
    fetchCloudData();
  }

  const isStreamingLive = mounted && telemetry.last_heartbeat && 
    (new Date().getTime() - new Date(telemetry.last_heartbeat).getTime() < 90000);

  // แปลงเวลาเป็น timezone ไทย (UTC+7)
  function formatThaiTime(timeStr) {
    if (!timeStr) return '-';
    try {
      // รองรับทั้ง ISO format (2026-09-28T15:10:30+00:00) และ space format (2026-09-28 15:10:30)
      const normalized = timeStr.replace(' ', 'T');
      const date = new Date(normalized.includes('+') || normalized.includes('Z') ? normalized : normalized + 'Z');
      if (isNaN(date.getTime())) return timeStr;
      const datePart = date.toLocaleDateString('th-TH', { timeZone: 'Asia/Bangkok', day: '2-digit', month: '2-digit' });
      const timePart = date.toLocaleTimeString('en-GB', { timeZone: 'Asia/Bangkok', hour: '2-digit', minute: '2-digit', second: '2-digit' });
      return { date: datePart, time: timePart, full: `${datePart} ${timePart}` };
    } catch (e) {
      return { date: '', time: timeStr, full: timeStr };
    }
  }

  return (
    <div style={{ minHeight: '100vh', display: 'flex', flexDirection: 'column' }}>
      <Navbar />

      <main style={{ maxWidth: '1440px', margin: '0 auto', padding: '1.5rem', width: '100%', position: 'relative', zIndex: 1 }}>
        
        {/* Quick Link Navigation Strip */}
        <div style={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          gap: '1rem',
          flexWrap: 'wrap',
          marginBottom: '1.2rem',
          padding: '0.85rem 1.2rem',
          backgroundColor: 'rgba(251, 191, 36, 0.05)',
          border: '1px solid rgba(251, 191, 36, 0.25)',
          borderRadius: '12px'
        }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.6rem' }}>
            <span style={{ fontSize: '1.1rem' }}>👑</span>
            <span style={{ fontSize: '0.85rem', fontWeight: 700, color: '#fbbf24' }}>
              GoldBot24 Ecosystem
            </span>
            <span style={{ fontSize: '0.75rem', color: 'var(--text-secondary)' }}>
              • เรดาร์สัญญาณเทรดทองคำ XAUUSD เชื่อมต่อคลาวด์แบบ Real-time
            </span>
          </div>

          <div style={{ display: 'flex', alignItems: 'center', gap: '0.6rem' }}>
            <Link
              href="/store"
              style={{
                display: 'inline-flex',
                alignItems: 'center',
                gap: '0.4rem',
                padding: '0.4rem 0.85rem',
                borderRadius: '8px',
                backgroundColor: '#fbbf24',
                color: '#07090e',
                fontSize: '0.78rem',
                fontWeight: 700,
                textDecoration: 'none'
              }}
            >
              <span>+ ซื้อชั่วโมง (1 บ./ชม.)</span>
            </Link>

            <Link
              href="/my-keys"
              style={{
                display: 'inline-flex',
                alignItems: 'center',
                gap: '0.4rem',
                padding: '0.4rem 0.85rem',
                borderRadius: '8px',
                backgroundColor: 'rgba(255, 255, 255, 0.06)',
                color: 'var(--text-primary)',
                border: '1px solid var(--border-subtle)',
                fontSize: '0.78rem',
                fontWeight: 600,
                textDecoration: 'none'
              }}
            >
              <span>คลังคีย์ของฉัน</span>
            </Link>

            <Link
              href="/dashboard"
              style={{
                display: 'inline-flex',
                alignItems: 'center',
                gap: '0.4rem',
                padding: '0.4rem 0.85rem',
                borderRadius: '8px',
                backgroundColor: 'rgba(255, 255, 255, 0.06)',
                color: 'var(--text-primary)',
                border: '1px solid var(--border-subtle)',
                fontSize: '0.78rem',
                fontWeight: 600,
                textDecoration: 'none'
              }}
            >
              <span>กระเป๋าเวลา & สถิติ</span>
            </Link>
          </div>
        </div>

        {/* 1. Header Bar */}
        <header style={{ 
          display: 'flex', 
          justifyContent: 'space-between', 
          alignItems: 'center', 
          padding: '16px 24px', 
          marginBottom: '24px',
          flexWrap: 'wrap',
          gap: '16px'
        }} className="glass-panel">
          
          {/* Brand & Status */}
          <div style={{ display: 'flex', alignItems: 'center', gap: '16px' }}>
            <div style={{ 
              width: '46px', 
              height: '46px', 
              borderRadius: '12px', 
              overflow: 'hidden',
              border: '1.5px solid rgba(251, 191, 36, 0.5)',
              boxShadow: '0 0 20px rgba(251, 191, 36, 0.3)',
              background: '#0d131a'
            }}>
              <img src="/app_icon.png" alt="AI Gold Commander Pro" style={{ width: '100%', height: '100%', objectFit: 'cover' }} />
            </div>

            <div>
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px', flexWrap: 'wrap' }}>
                <h1 style={{ fontSize: '22px', fontWeight: '800', letterSpacing: '-0.02em', color: '#fff' }}>
                  <span style={{ color: '#fbbf24' }}>GoldBot24</span> • AI Gold Commander Pro
                </h1>
                <span style={{ 
                  fontSize: '11px', 
                  fontWeight: '700', 
                  padding: '2px 8px', 
                  borderRadius: '6px', 
                  background: 'rgba(251, 191, 36, 0.15)', 
                  color: '#fbbf24',
                  border: '1px solid rgba(251, 191, 36, 0.3)'
                }}>
                  GOLD SPECIALIST v2026.1003.0025
                </span>
              </div>
              <p style={{ fontSize: '13px', color: 'var(--text-secondary)', marginTop: '2px', display: 'flex', alignItems: 'center', gap: '8px' }}>
                <span className={isStreamingLive ? 'live-indicator' : 'offline-indicator'}></span>
                <span>สถานะบอท: <strong style={{ color: isStreamingLive ? 'var(--accent-green)' : '#f59e0b' }}>
                  {isStreamingLive ? 'ONLINE (เรียลไทม์ ⚡)' : 'OFFLINE (รอเปิดบอทในคอม)'}
                </strong></span>
                <span style={{ color: 'var(--border-subtle)' }}>•</span>
                <span style={{ color: 'var(--text-muted)' }}>เซิร์ฟเวอร์: {botConfig.mt5_server || 'FBS-Real'}</span>
                <span style={{ color: 'var(--border-subtle)' }}>•</span>
                <span style={{ color: 'var(--text-muted)' }}>พอร์ต MT5: #{botConfig.mt5_login || '106584946'}</span>
              </p>
            </div>
          </div>

        {/* Action Controls - Authenticated Session & Status */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '10px', flexWrap: 'wrap' }}>
          {user ? (
            <>
              {/* User Account Badge */}
              <Link 
                href="/dashboard"
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  gap: '8px',
                  padding: '8px 14px',
                  borderRadius: 'var(--radius-sm)',
                  backgroundColor: 'rgba(251, 191, 36, 0.1)',
                  border: '1px solid rgba(251, 191, 36, 0.3)',
                  color: '#fbbf24',
                  fontSize: '13px',
                  fontWeight: '700',
                  textDecoration: 'none'
                }}
                title="ไปยังหน้ากระเป๋าเวลา & แดชบอร์ด"
              >
                <User size={15} />
                <span>{user.displayName || user.email.split('@')[0]}</span>
                <span style={{
                  backgroundColor: '#fbbf24',
                  color: '#07090e',
                  padding: '2px 8px',
                  borderRadius: '4px',
                  fontSize: '11px',
                  fontWeight: '800'
                }}>
                  ⏱️ {(user.hoursRemaining || 0).toFixed(2)} ชม.
                </span>
              </Link>

              {/* Store Quick Action */}
              <Link
                href="/store"
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  gap: '6px',
                  padding: '8px 12px',
                  borderRadius: 'var(--radius-sm)',
                  backgroundColor: '#fbbf24',
                  color: '#07090e',
                  fontSize: '12px',
                  fontWeight: '800',
                  textDecoration: 'none',
                  boxShadow: '0 0 12px rgba(251, 191, 36, 0.25)'
                }}
              >
                <span>+ ซื้อชั่วโมง</span>
              </Link>

              {/* Logout Button */}
              <button
                onClick={logout}
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  gap: '6px',
                  padding: '8px 12px',
                  borderRadius: 'var(--radius-sm)',
                  backgroundColor: 'rgba(244, 63, 94, 0.1)',
                  border: '1px solid rgba(244, 63, 94, 0.25)',
                  color: '#f43f5e',
                  fontSize: '12px',
                  fontWeight: '600',
                  cursor: 'pointer'
                }}
                title="ออกจากระบบ"
              >
                <LogOut size={14} />
                <span>ออกจากระบบ</span>
              </button>
            </>
          ) : (
            <>
              {/* Login Button */}
              <button
                onClick={() => openAuthModal('login')}
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  gap: '6px',
                  padding: '8px 14px',
                  borderRadius: 'var(--radius-sm)',
                  backgroundColor: 'transparent',
                  border: '1px solid rgba(251, 191, 36, 0.4)',
                  color: '#fbbf24',
                  fontSize: '13px',
                  fontWeight: '700',
                  cursor: 'pointer'
                }}
              >
                <LogIn size={15} />
                <span>เข้าสู่ระบบ</span>
              </button>

              {/* Register Button */}
              <button
                onClick={() => openAuthModal('register')}
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  gap: '6px',
                  padding: '8px 14px',
                  borderRadius: 'var(--radius-sm)',
                  backgroundColor: '#fbbf24',
                  border: 'none',
                  color: '#07090e',
                  fontSize: '13px',
                  fontWeight: '800',
                  cursor: 'pointer',
                  boxShadow: '0 0 15px rgba(251, 191, 36, 0.3)'
                }}
              >
                <UserPlus size={15} />
                <span>สมัครสมาชิก</span>
              </button>
            </>
          )}

          {/* Manual Refresh */}
          <button 
            onClick={fetchCloudData}
            style={{ 
              padding: '9px', 
              borderRadius: 'var(--radius-sm)',
              background: 'rgba(255, 255, 255, 0.05)',
              color: 'var(--text-secondary)',
              border: '1px solid var(--border-subtle)',
              cursor: 'pointer'
            }}
            title="รีเฟรชข้อมูลเรียลไทม์ล่าสุด"
          >
            <RefreshCw size={15} />
          </button>
        </div>
      </header>

      {/* 2. Account KPI Strip */}
      <div style={{ 
        display: 'grid', 
        gridTemplateColumns: 'repeat(auto-fit, minmax(260px, 1fr))', 
        gap: '16px', 
        marginBottom: '24px' 
      }}>
        
        {/* Card 1: Balance */}
        <div className="glass-panel" style={{ padding: '20px' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', color: 'var(--text-secondary)', fontSize: '13px', fontWeight: '500' }}>
            <span>ยอดบาลานซ์ (Balance)</span>
            <DollarSign size={18} color="var(--accent-cyan)" />
          </div>
          <div className="font-mono" style={{ fontSize: '28px', fontWeight: '800', marginTop: '8px', color: '#fff' }}>
            ${telemetry.balance.toLocaleString('en-US', { minimumFractionDigits: 2 })}
          </div>
          <div style={{ fontSize: '12px', color: 'var(--text-muted)', marginTop: '6px' }}>
            ทุนเริ่มต้น: $1,000.00
          </div>
        </div>

        {/* Card 2: Equity */}
        <div className="glass-panel" style={{ padding: '20px' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', color: 'var(--text-secondary)', fontSize: '13px', fontWeight: '500' }}>
            <span>มูลค่าพอร์ตสุทธิ (Equity)</span>
            <Activity size={18} color="var(--accent-gold)" />
          </div>
          <div className="font-mono" style={{ fontSize: '28px', fontWeight: '800', marginTop: '8px', color: 'var(--accent-gold)' }}>
            ${telemetry.equity.toLocaleString('en-US', { minimumFractionDigits: 2 })}
          </div>
          <div style={{ fontSize: '12px', color: 'var(--accent-green)', marginTop: '6px', display: 'flex', alignItems: 'center', gap: '4px' }}>
            <TrendingUp size={14} />
            <span>เติบโต +{(((telemetry.equity - 1000) / 1000) * 100).toFixed(2)}% สุทธิ</span>
          </div>
        </div>

        {/* Card 3: Floating P&L */}
        <div className="glass-panel" style={{ padding: '20px', borderLeft: telemetry.floating_profit >= 0 ? '4px solid var(--accent-green)' : '4px solid var(--accent-red)' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', color: 'var(--text-secondary)', fontSize: '13px', fontWeight: '500' }}>
            <span>กำไรลอยตัว (Floating P&L)</span>
            {telemetry.floating_profit >= 0 ? <TrendingUp size={18} color="var(--accent-green)" /> : <TrendingDown size={18} color="var(--accent-red)" />}
          </div>
          <div className="font-mono" style={{ 
            fontSize: '28px', 
            fontWeight: '800', 
            marginTop: '8px', 
            color: telemetry.floating_profit >= 0 ? 'var(--accent-green)' : 'var(--accent-red)' 
          }}>
            {telemetry.floating_profit >= 0 ? `+$${telemetry.floating_profit.toFixed(2)}` : `-$${Math.abs(telemetry.floating_profit).toFixed(2)}`}
          </div>
          <div style={{ fontSize: '12px', color: 'var(--text-muted)', marginTop: '6px' }}>
            ถือครอง {telemetry.open_positions.length} ไม้ในตลาด
          </div>
        </div>

        {/* Card 4: Free Margin */}
        <div className="glass-panel" style={{ padding: '20px' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', color: 'var(--text-secondary)', fontSize: '13px', fontWeight: '500' }}>
            <span>มาร์จิ้นคงเหลือ (Free Margin)</span>
            <Shield size={18} color="var(--accent-blue)" />
          </div>
          <div className="font-mono" style={{ fontSize: '28px', fontWeight: '800', marginTop: '8px', color: '#fff' }}>
            ${telemetry.margin_free.toLocaleString('en-US', { minimumFractionDigits: 2 })}
          </div>
          <div style={{ fontSize: '12px', color: 'var(--accent-cyan)', marginTop: '6px' }}>
            ความปลอดภัยสูง (Lot: {botConfig.lot_size})
          </div>
        </div>

      </div>

      {/* 3. AI Market Radar Strip (เรียลไทม์ AI Barometer) */}
      {(() => {
        const activeAlerts = (telemetry.radar_signals || []).filter(s => {
          const isOutside = !s.status || s.status.includes('รอนอกโซน') || s.status.includes('WAIT OUTSIDE ZONE') || s.status.includes('OUT OF ZONE');
          return s.in_zone || !isOutside;
        });
        return (
          <div className="glass-panel" style={{ padding: '20px', marginBottom: '24px' }}>
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '14px' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                <Radio size={18} color="var(--accent-gold)" />
                <h2 style={{ fontSize: '16px', fontWeight: '700' }}>AI Market Radar (ตรวจจับพฤติกรรมเรียลไทม์)</h2>
              </div>
              <span style={{ fontSize: '12px', color: isStreamingLive ? 'var(--accent-green)' : 'var(--text-muted)' }} suppressHydrationWarning>
                {isStreamingLive ? '⚡ สตรีมสด: ' : 'อัปเดตล่าสุด: '}
                {mounted && telemetry.last_heartbeat ? new Date(telemetry.last_heartbeat).toLocaleTimeString('th-TH') : '--:--:--'}
              </span>
            </div>

            {/* แถบสรุปเรดาร์ที่ AI ส่งมา (แจ้งเตือนคู่เงินที่เข้าโซนน่าจับตามอง) */}
            {activeAlerts.length > 0 ? (
              <div style={{
                marginBottom: '16px',
                padding: '12px 16px',
                background: 'linear-gradient(90deg, rgba(245, 158, 11, 0.12), rgba(6, 182, 212, 0.08))',
                border: '1px solid rgba(245, 158, 11, 0.35)',
                borderRadius: 'var(--radius-sm)',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'space-between',
                flexWrap: 'wrap',
                gap: '10px'
              }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                  <Flame size={18} color="var(--accent-gold)" />
                  <span style={{ fontWeight: '700', fontSize: '13px', color: 'var(--accent-gold)' }}>
                    ⭐️ สรุปเรดาร์ AI: สินทรัพย์ที่เข้าโซนเทรด ({activeAlerts.length} รายการ: {activeAlerts.map(a => a.symbol).join(', ')})
                  </span>
                </div>
                <div style={{ display: 'flex', gap: '6px', flexWrap: 'wrap' }}>
                  {activeAlerts.map((a, i) => (
                    <span key={i} style={{ 
                      fontSize: '11px', 
                      fontWeight: '700', 
                      padding: '2px 8px', 
                      borderRadius: '4px',
                      background: a.status.includes('BUY') ? 'rgba(16, 185, 129, 0.2)' : 'rgba(244, 63, 94, 0.2)',
                      color: a.status.includes('BUY') ? 'var(--accent-green)' : 'var(--accent-red)',
                      border: `1px solid ${a.status.includes('BUY') ? 'rgba(16, 185, 129, 0.4)' : 'rgba(244, 63, 94, 0.4)'}`
                    }}>
                      {a.symbol}
                    </span>
                  ))}
                </div>
              </div>
            ) : (
              <div style={{
                marginBottom: '16px',
                padding: '10px 16px',
                background: 'rgba(255, 255, 255, 0.02)',
                border: '1px solid var(--border-subtle)',
                borderRadius: 'var(--radius-sm)',
                fontSize: '12px',
                color: 'var(--text-muted)',
                display: 'flex',
                alignItems: 'center',
                gap: '8px'
              }}>
                <Radio size={14} color="var(--accent-cyan)" />
                <span>ทองคำและบิตคอยน์ยังอยู่นอกโซน — AI กำลังเฝ้าระวังและตรวจจับแท่งเทียนแบบเรียลไทม์...</span>
              </div>
            )}

            {/* การ์ดเรดาร์แต่ละคู่เงิน */}
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(320px, 1fr))', gap: '14px' }}>
              {(telemetry.radar_signals || []).map((signal, idx) => {
                const rawUp = Number(signal.up_prob) || 0.5;
                const upPercent = rawUp > 1 ? rawUp : rawUp * 100;
                const downPercent = 100 - upPercent;
                const isOutside = !signal.status || signal.status.includes('รอนอกโซน') || signal.status.includes('WAIT OUTSIDE ZONE') || signal.status.includes('OUT OF ZONE');
                const isAlert = signal.in_zone || !isOutside;
                
                // แปลงราคาให้เหมาะสมตามประเภทสินทรัพย์
                const priceNum = Number(signal.price) || 0;
                let priceFormatted = '--';
                if (priceNum > 0) {
                  if (priceNum >= 1000) {
                    priceFormatted = `$${priceNum.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
                  } else if (priceNum >= 10) {
                    priceFormatted = `$${priceNum.toFixed(2)}`;
                  } else {
                    priceFormatted = `$${priceNum.toFixed(5)}`;
                  }
                }

                // รูปแบบสีของสถานะ
                let badgeBg = 'rgba(255, 255, 255, 0.05)';
                let badgeColor = 'var(--text-muted)';
                let badgeBorder = 'var(--border-subtle)';

                if (signal.status.includes('BUY') || signal.status.includes('🟢')) {
                  badgeBg = 'rgba(16, 185, 129, 0.15)';
                  badgeColor = 'var(--accent-green)';
                  badgeBorder = 'rgba(16, 185, 129, 0.35)';
                } else if (signal.status.includes('SELL') || signal.status.includes('🔴') || signal.status.includes('🩸')) {
                  badgeBg = 'rgba(244, 63, 94, 0.15)';
                  badgeColor = 'var(--accent-red)';
                  badgeBorder = 'rgba(244, 63, 94, 0.35)';
                } else if (signal.status.includes('Breakout') || signal.status.includes('🚀')) {
                  badgeBg = 'rgba(6, 182, 212, 0.15)';
                  badgeColor = 'var(--accent-cyan)';
                  badgeBorder = 'rgba(6, 182, 212, 0.35)';
                } else if (signal.status.includes('⚠️')) {
                  badgeBg = 'rgba(245, 158, 11, 0.15)';
                  badgeColor = 'var(--accent-gold)';
                  badgeBorder = 'rgba(245, 158, 11, 0.35)';
                }

                return (
                  <div key={idx} style={{ 
                    background: isAlert ? 'linear-gradient(135deg, rgba(255, 255, 255, 0.04), rgba(245, 158, 11, 0.04))' : 'rgba(255, 255, 255, 0.03)', 
                    borderRadius: 'var(--radius-sm)', 
                    padding: '14px 16px',
                    border: isAlert ? '1px solid rgba(245, 158, 11, 0.35)' : '1px solid var(--border-subtle)',
                    display: 'flex',
                    justifyContent: 'space-between',
                    alignItems: 'center',
                    boxShadow: isAlert ? '0 4px 15px rgba(245, 158, 11, 0.08)' : 'none'
                  }}>
                    <div>
                      <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                        <span style={{ 
                          fontWeight: '800', 
                          fontSize: '15px', 
                          color: signal.symbol.includes('BTC') ? 'var(--accent-btc)' : signal.symbol.includes('XAU') ? 'var(--accent-gold)' : '#fff' 
                        }}>
                          {signal.symbol}
                        </span>
                        <span className="font-mono" style={{ fontSize: '13px', color: 'var(--text-muted)' }}>
                          {priceFormatted}
                        </span>
                        {isAlert && (
                          <span style={{
                            fontSize: '10px',
                            fontWeight: '700',
                            color: 'var(--accent-gold)',
                            background: 'rgba(245, 158, 11, 0.2)',
                            padding: '1px 6px',
                            borderRadius: '4px'
                          }}>
                            IN ZONE
                          </span>
                        )}
                      </div>
                      <div style={{ fontSize: '12px', color: 'var(--accent-cyan)', marginTop: '4px' }}>
                        AI คาดการณ์: ขึ้น {upPercent.toFixed(1)}% | ลง {downPercent.toFixed(1)}%
                      </div>
                    </div>

                    <div style={{ 
                      fontSize: '12px', 
                      fontWeight: '600', 
                      padding: '4px 10px', 
                      borderRadius: '6px',
                      background: badgeBg,
                      color: badgeColor,
                      border: `1px solid ${badgeBorder}`,
                      whiteSpace: 'nowrap',
                      marginLeft: '8px'
                    }}>
                      {signal.status}
                    </div>
                  </div>
                );
              })}
            </div>
          </div>
        );
      })()}

      {/* 4. Active Positions & History Tables Grid */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(480px, 1fr))', gap: '24px' }}>
        
        {/* Left: Open Positions Table */}
        <div className="glass-panel" style={{ padding: '20px' }}>
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '16px' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
              <Layers size={18} color="var(--accent-green)" />
              <h2 style={{ fontSize: '16px', fontWeight: '700' }}>ออเดอร์ที่กำลังวิ่งอยู่ (Open Positions)</h2>
            </div>
            <span style={{ 
              fontSize: '11px', 
              fontWeight: '700', 
              padding: '2px 8px', 
              borderRadius: 'var(--radius-full)', 
              background: 'rgba(16, 185, 129, 0.15)', 
              color: 'var(--accent-green)' 
            }}>
              {telemetry.open_positions.length} ไม้
            </span>
          </div>

          {telemetry.open_positions.length === 0 ? (
            <div style={{ padding: '40px', textAlign: 'center', color: 'var(--text-muted)' }}>
              💤 ขณะนี้ไม่มีออเดอร์ค้าง — บอทกำลังเฝ้าระวังโซนเทรดในเบื้องหลัง
            </div>
          ) : (
            <div style={{ overflowX: 'auto' }}>
              <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '13px' }}>
                <thead>
                  <tr style={{ color: 'var(--text-muted)', borderBottom: '1px solid var(--border-subtle)', textAlign: 'left' }}>
                    <th style={{ padding: '10px 8px' }}>คู่เงิน</th>
                    <th style={{ padding: '10px 8px' }}>คำสั่ง</th>
                    <th style={{ padding: '10px 8px' }}>ราคาเข้า</th>
                    <th style={{ padding: '10px 8px' }}>SL / TP</th>
                    <th style={{ padding: '10px 8px', textAlign: 'right' }}>กำไร (USD)</th>
                  </tr>
                </thead>
                <tbody>
                  {telemetry.open_positions.map((pos) => (
                    <tr key={pos.ticket} style={{ borderBottom: '1px solid rgba(255, 255, 255, 0.04)' }}>
                      <td style={{ padding: '12px 8px' }}>
                        <div style={{ fontWeight: '700', color: pos.symbol.includes('BTC') ? 'var(--accent-btc)' : pos.symbol.includes('XAU') ? 'var(--accent-gold)' : '#fff' }}>
                          {pos.symbol}
                        </div>
                        <div style={{ fontSize: '11px', color: 'var(--text-muted)' }}>Lot: {pos.volume}</div>
                      </td>
                      <td style={{ padding: '12px 8px' }}>
                        <span style={{ 
                          fontSize: '11px', 
                          fontWeight: '800', 
                          padding: '3px 8px', 
                          borderRadius: '4px',
                          background: pos.type === 'BUY' ? 'rgba(16, 185, 129, 0.2)' : 'rgba(244, 63, 94, 0.2)',
                          color: pos.type === 'BUY' ? 'var(--accent-green)' : 'var(--accent-red)'
                        }}>
                          {pos.type}
                        </span>
                      </td>
                      <td className="font-mono" style={{ padding: '12px 8px' }}>
                        {pos.price_open.toLocaleString()}
                      </td>
                      <td className="font-mono" style={{ padding: '12px 8px', fontSize: '11px', color: 'var(--text-secondary)' }}>
                        <div>🛡️ SL: {pos.sl.toLocaleString()}</div>
                        <div>🎯 TP: {pos.tp.toLocaleString()}</div>
                      </td>
                      <td className="font-mono" style={{ 
                        padding: '12px 8px', 
                        textAlign: 'right', 
                        fontWeight: '800', 
                        fontSize: '15px',
                        color: pos.profit >= 0 ? 'var(--accent-green)' : 'var(--accent-red)' 
                      }}>
                        {pos.profit >= 0 ? `+$${pos.profit.toFixed(2)}` : `-$${Math.abs(pos.profit).toFixed(2)}`}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>

        {/* Right: Recent Trade Logs */}
        <div className="glass-panel" style={{ padding: '20px' }}>
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '16px' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
              <Clock size={18} color="var(--accent-cyan)" />
              <h2 style={{ fontSize: '16px', fontWeight: '700' }}>ประวัติการเทรดล่าสุด (Trade Logs)</h2>
            </div>
            <span style={{ fontSize: '12px', color: 'var(--text-muted)' }}>บันทึกอัตโนมัติลง Supabase</span>
          </div>

          <div style={{ overflowX: 'auto' }}>
            <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '13px' }}>
              <thead>
                <tr style={{ color: 'var(--text-muted)', borderBottom: '1px solid var(--border-subtle)', textAlign: 'left' }}>
                  <th style={{ padding: '10px 8px' }}>เวลา</th>
                  <th style={{ padding: '10px 8px' }}>คู่เงิน</th>
                  <th style={{ padding: '10px 8px' }}>แผนเทรด</th>
                  <th style={{ padding: '10px 8px', textAlign: 'right' }}>ผลลัพธ์</th>
                </tr>
              </thead>
              <tbody>
                {tradeLogs.map((log) => (
                  <tr key={log.id} style={{ borderBottom: '1px solid rgba(255, 255, 255, 0.04)' }}>
                    <td style={{ padding: '12px 8px', fontSize: '11px', color: 'var(--text-muted)' }}>
                      {(() => {
                        const t = formatThaiTime(log.time);
                        if (typeof t === 'object') {
                          return (
                            <>
                              <div style={{ color: 'var(--text-secondary)', fontWeight: '600' }}>{t.time}</div>
                              <div style={{ fontSize: '10px', color: 'var(--text-muted)', marginTop: '2px' }}>{t.date} 🇹🇭</div>
                            </>
                          );
                        }
                        return t;
                      })()}
                    </td>
                    <td style={{ padding: '12px 8px' }}>
                      <div style={{ fontWeight: '700' }}>{log.symbol}</div>
                      <span style={{ 
                        fontSize: '10px', 
                        fontWeight: '700', 
                        padding: '1px 6px',
                        borderRadius: '4px',
                        background: log.action === 'BUY' ? 'rgba(16, 185, 129, 0.15)' : 
                                    log.action === 'SELL' ? 'rgba(244, 63, 94, 0.15)' : 
                                    log.action.includes('LOCK') || log.action.includes('MODIFY') ? 'rgba(0, 242, 254, 0.15)' : 'rgba(255, 255, 255, 0.08)',
                        color: log.action === 'BUY' ? 'var(--accent-green)' : 
                               log.action === 'SELL' ? 'var(--accent-red)' : 
                               log.action.includes('LOCK') || log.action.includes('MODIFY') ? 'var(--accent-cyan)' : 'var(--text-secondary)' 
                      }}>
                        {log.action}
                      </span>
                    </td>
                    <td style={{ padding: '12px 8px', fontSize: '12px', color: 'var(--text-secondary)' }}>
                      {log.plan}
                    </td>
                    <td className="font-mono" style={{ padding: '12px 8px', textAlign: 'right', fontWeight: '700' }}>
                      {log.status === 'OPEN' ? (
                        <span style={{ color: 'var(--accent-gold)', fontSize: '11px' }}>กำลังวิ่งอยูู่</span>
                      ) : (
                        <span style={{ color: log.profit >= 0 ? 'var(--accent-green)' : 'var(--accent-red)' }}>
                          {log.profit >= 0 ? `+$${log.profit.toFixed(2)}` : `-$${Math.abs(log.profit).toFixed(2)}`}
                        </span>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>

      </div>

      {/* ========================================================================= */}
      {/* 5. Modal: MT5 User / Password / Server Credentials & Strategy Settings     */}
      {/* ========================================================================= */}
      {isSettingsOpen && (
        <div className="modal-backdrop animate-fade-in" onClick={() => setIsSettingsOpen(false)}>
          <div 
            className="glass-panel animate-slide-down" 
            style={{ 
              maxWidth: '560px', 
              width: '100%', 
              background: '#0d131f', 
              border: '1px solid rgba(0, 242, 254, 0.3)',
              boxShadow: '0 20px 50px rgba(0, 0, 0, 0.8), 0 0 30px rgba(0, 242, 254, 0.15)',
              padding: '28px',
              borderRadius: 'var(--radius-md)'
            }}
            onClick={(e) => e.stopPropagation()}
          >
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '20px' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                <Key size={22} color="var(--accent-cyan)" />
                <h3 style={{ fontSize: '18px', fontWeight: '700' }}>ตั้งค่าบัญชี MT5 & พารามิเตอร์เทรด</h3>
              </div>
              <button 
                onClick={() => setIsSettingsOpen(false)}
                style={{ background: 'transparent', color: 'var(--text-muted)', fontSize: '18px', padding: '4px' }}
              >
                ✕
              </button>
            </div>

            <form onSubmit={handleSaveSettings}>
              
              {/* Account Credentials Section */}
              <div style={{ background: 'rgba(255, 255, 255, 0.02)', padding: '16px', borderRadius: 'var(--radius-sm)', border: '1px solid var(--border-subtle)', marginBottom: '18px' }}>
                <h4 style={{ fontSize: '13px', fontWeight: '700', color: 'var(--accent-cyan)', marginBottom: '12px', display: 'flex', alignItems: 'center', gap: '6px' }}>
                  <User size={15} /> ข้อมูลล็อกอิน MetaTrader 5 (FBS)
                </h4>

                {/* MT5 Login (User) */}
                <div style={{ marginBottom: '12px' }}>
                  <label style={{ display: 'block', fontSize: '12px', color: 'var(--text-secondary)', marginBottom: '6px' }}>
                    เลขที่บัญชี MT5 (User / Account Number)
                  </label>
                  <input 
                    type="text" 
                    placeholder="เช่น 78923412" 
                    value={botConfig.mt5_login} 
                    onChange={(e) => setBotConfig({ ...botConfig, mt5_login: e.target.value })}
                    className="font-mono"
                  />
                </div>

                {/* MT5 Password */}
                <div style={{ marginBottom: '12px' }}>
                  <label style={{ display: 'block', fontSize: '12px', color: 'var(--text-secondary)', marginBottom: '6px' }}>
                    รหัสผ่าน MT5 (Trading Password)
                  </label>
                  <div style={{ position: 'relative' }}>
                    <input 
                      type={showPassword ? 'text' : 'password'} 
                      placeholder="ใส่รหัสผ่าน MT5 ของคุณ" 
                      value={botConfig.mt5_password} 
                      onChange={(e) => setBotConfig({ ...botConfig, mt5_password: e.target.value })}
                      style={{ paddingRight: '40px' }}
                    />
                    <button 
                      type="button" 
                      onClick={() => setShowPassword(!showPassword)}
                      style={{ 
                        position: 'absolute', 
                        right: '10px', 
                        top: '50%', 
                        transform: 'translateY(-50%)', 
                        background: 'transparent', 
                        color: 'var(--text-muted)' 
                      }}
                    >
                      {showPassword ? <EyeOff size={16} /> : <Eye size={16} />}
                    </button>
                  </div>
                </div>

                {/* MT5 Server */}
                <div>
                  <label style={{ display: 'block', fontSize: '12px', color: 'var(--text-secondary)', marginBottom: '6px' }}>
                    เซิร์ฟเวอร์โบรกเกอร์ (Broker Server)
                  </label>
                  <input 
                    type="text" 
                    placeholder="เช่น FBS-Real, FBS-Demo" 
                    value={botConfig.mt5_server} 
                    onChange={(e) => setBotConfig({ ...botConfig, mt5_server: e.target.value })}
                  />
                </div>
              </div>

              {/* Trading Strategy & Risk Section */}
              <div style={{ background: 'rgba(255, 255, 255, 0.02)', padding: '16px', borderRadius: 'var(--radius-sm)', border: '1px solid var(--border-subtle)', marginBottom: '20px' }}>
                <h4 style={{ fontSize: '13px', fontWeight: '700', color: 'var(--accent-gold)', marginBottom: '12px', display: 'flex', alignItems: 'center', gap: '6px' }}>
                  <Shield size={15} /> การจัดการความเสี่ยง & พารามิเตอร์เทรด
                </h4>

                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '12px', marginBottom: '12px' }}>
                  <div>
                    <label style={{ display: 'block', fontSize: '12px', color: 'var(--text-secondary)', marginBottom: '6px' }}>
                      Lot Size เริ่มต้น
                    </label>
                    <input 
                      type="number" 
                      step="0.01" 
                      value={botConfig.lot_size} 
                      onChange={(e) => setBotConfig({ ...botConfig, lot_size: e.target.value })}
                      className="font-mono"
                    />
                  </div>

                  <div>
                    <label style={{ display: 'block', fontSize: '12px', color: 'var(--text-secondary)', marginBottom: '6px' }}>
                      บิตคอยน์ Cooldown (นาที)
                    </label>
                    <input 
                      type="number" 
                      value={botConfig.cooldown_btc} 
                      onChange={(e) => setBotConfig({ ...botConfig, cooldown_btc: e.target.value })}
                      className="font-mono"
                    />
                  </div>
                </div>

                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '12px' }}>
                  <div>
                    <label style={{ display: 'block', fontSize: '12px', color: 'var(--text-secondary)', marginBottom: '6px' }}>
                      RRR บิตคอยน์ (BTCUSD)
                    </label>
                    <input 
                      type="number" 
                      step="0.1" 
                      value={botConfig.tp_rrr_btc} 
                      onChange={(e) => setBotConfig({ ...botConfig, tp_rrr_btc: e.target.value })}
                      className="font-mono"
                    />
                  </div>

                  <div>
                    <label style={{ display: 'block', fontSize: '12px', color: 'var(--text-secondary)', marginBottom: '6px' }}>
                      RRR ทองคำ (XAUUSD)
                    </label>
                    <input 
                      type="number" 
                      step="0.1" 
                      value={botConfig.tp_rrr_xau} 
                      onChange={(e) => setBotConfig({ ...botConfig, tp_rrr_xau: e.target.value })}
                      className="font-mono"
                    />
                  </div>
                </div>
              </div>

              {/* Submit Buttons */}
              <div style={{ display: 'flex', gap: '10px', justifyContent: 'flex-end' }}>
                <button 
                  type="button" 
                  onClick={() => setIsSettingsOpen(false)}
                  style={{ 
                    padding: '10px 18px', 
                    borderRadius: 'var(--radius-sm)', 
                    background: 'rgba(255, 255, 255, 0.05)', 
                    color: 'var(--text-secondary)' 
                  }}
                >
                  ยกเลิก
                </button>

                <button 
                  type="submit" 
                  disabled={isSaving}
                  style={{ 
                    padding: '10px 24px', 
                    borderRadius: 'var(--radius-sm)', 
                    background: saveSuccess ? 'var(--accent-green)' : 'linear-gradient(135deg, #00f2fe 0%, #4facfe 100%)', 
                    color: '#07090e',
                    fontWeight: '700',
                    display: 'flex',
                    alignItems: 'center',
                    gap: '8px',
                    boxShadow: 'var(--shadow-neon-cyan)'
                  }}
                >
                  {saveSuccess ? (
                    <>
                      <CheckCircle2 size={16} /> บันทึกลง Supabase สำเร็จ!
                    </>
                  ) : isSaving ? (
                    <>
                      <RefreshCw size={16} className="animate-spin" /> กำลังบันทึก...
                    </>
                  ) : (
                    'บันทึกข้อมูล'
                  )}
                </button>
              </div>

            </form>
          </div>
        </div>
      )}

      {/* ========================================================================= */}
      {/* 6. Modal: Supabase Project URL & Anon Key Settings                        */}
      {/* ========================================================================= */}
      {isCloudKeysOpen && (
        <div className="modal-backdrop animate-fade-in" onClick={() => setIsCloudKeysOpen(false)}>
          <div 
            className="glass-panel animate-slide-down" 
            style={{ 
              maxWidth: '520px', 
              width: '100%', 
              background: '#0d131f', 
              border: '1px solid rgba(0, 242, 254, 0.3)',
              padding: '28px',
              borderRadius: 'var(--radius-md)'
            }}
            onClick={(e) => e.stopPropagation()}
          >
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                <Database size={22} color="var(--accent-cyan)" />
                <h3 style={{ fontSize: '18px', fontWeight: '700' }}>เชื่อมต่อ Supabase Database</h3>
              </div>
              <button 
                onClick={() => setIsCloudKeysOpen(false)}
                style={{ background: 'transparent', color: 'var(--text-muted)', fontSize: '18px' }}
              >
                ✕
              </button>
            </div>

            <p style={{ fontSize: '13px', color: 'var(--text-secondary)', marginBottom: '18px', lineHeight: '1.5' }}>
              นำค่า <strong>Project URL</strong> และ <strong>API anon key</strong> จาก Supabase Dashboard (หน้า Project Settings ➔ API) มาใส่ที่นี่ เพื่อให้ระบบซิงค์ข้อมูลแบบเรียลไทม์:
            </p>

            <form onSubmit={handleSaveCloudKeys}>
              <div style={{ marginBottom: '14px' }}>
                <label style={{ display: 'block', fontSize: '12px', color: 'var(--text-secondary)', marginBottom: '6px' }}>
                  Supabase Project URL
                </label>
                <input 
                  type="text" 
                  placeholder="https://xyzcompany.supabase.co" 
                  value={cloudUrl} 
                  onChange={(e) => setCloudUrl(e.target.value)}
                  className="font-mono"
                  required
                />
              </div>

              <div style={{ marginBottom: '20px' }}>
                <label style={{ display: 'block', fontSize: '12px', color: 'var(--text-secondary)', marginBottom: '6px' }}>
                  Supabase Anon Key (Public)
                </label>
                <input 
                  type="password" 
                  placeholder="eyJhbGciOiJIUzI1NiIsInR5cCI6..." 
                  value={cloudAnonKey} 
                  onChange={(e) => setCloudAnonKey(e.target.value)}
                  className="font-mono"
                  required
                />
              </div>

              <div style={{ display: 'flex', gap: '10px', justifyContent: 'flex-end' }}>
                <button 
                  type="button" 
                  onClick={() => setIsCloudKeysOpen(false)}
                  style={{ 
                    padding: '10px 18px', 
                    borderRadius: 'var(--radius-sm)', 
                    background: 'rgba(255, 255, 255, 0.05)', 
                    color: 'var(--text-secondary)' 
                  }}
                >
                  ปิด
                </button>

                <button 
                  type="submit" 
                  style={{ 
                    padding: '10px 24px', 
                    borderRadius: 'var(--radius-sm)', 
                    background: 'linear-gradient(135deg, #00f2fe 0%, #4facfe 100%)', 
                    color: '#07090e',
                    fontWeight: '700'
                  }}
                >
                  บันทึกการเชื่อมต่อ
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      </main>
      <Footer />
    </div>
  );
}
