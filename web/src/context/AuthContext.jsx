'use client';

import { createContext, useCallback, useContext, useEffect, useMemo, useRef, useState } from 'react';

const SESSION_KEY = 'goldbot_session';
// แอดมินเลือกดูเว็บแบบ 'admin' (มีเมนูจัดการ) หรือ 'user' (เห็นเหมือนลูกค้าทั่วไป)
const VIEW_MODE_KEY = 'goldbot_view_mode';
const LEGACY_KEYS = ['goldbot_user', 'remember_mt5_login', 'remember_mt5_password', 'remember_mt5_server', 'supabase_url', 'supabase_anon_key'];

const AuthContext = createContext(null);

function readSession() {
  try {
    const raw = localStorage.getItem(SESSION_KEY);
    if (!raw) return null;
    const parsed = JSON.parse(raw);
    return parsed?.token && parsed?.user ? parsed : null;
  } catch {
    return null;
  }
}

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null);
  const [isLoading, setIsLoading] = useState(true);
  const [isAuthModalOpen, setIsAuthModalOpen] = useState(false);
  const [authModalTab, setAuthModalTab] = useState('login');
  const [viewMode, setViewModeState] = useState('admin');
  const tokenRef = useRef(null);

  const persist = useCallback((token, nextUser) => {
    tokenRef.current = token;
    setUser(nextUser);
    try {
      if (token && nextUser) localStorage.setItem(SESSION_KEY, JSON.stringify({ token, user: nextUser }));
      else localStorage.removeItem(SESSION_KEY);
    } catch {
      /* storage ใช้ไม่ได้ (private mode) — ยังทำงานต่อได้ในหน่วยความจำ */
    }
  }, []);

  const logout = useCallback(() => persist(null, null), [persist]);

  useEffect(() => {
    try {
      if (localStorage.getItem(VIEW_MODE_KEY) === 'user') setViewModeState('user');
    } catch {
      /* storage ใช้ไม่ได้ — ใช้ค่าเริ่มต้น */
    }
  }, []);

  const setViewMode = useCallback((mode) => {
    const next = mode === 'user' ? 'user' : 'admin';
    setViewModeState(next);
    try {
      localStorage.setItem(VIEW_MODE_KEY, next);
    } catch {
      /* ignore */
    }
  }, []);

  /** fetch ที่แนบ Token อัตโนมัติ และออกจากระบบเมื่อ Token หมดอายุ (401) */
  const apiFetch = useCallback(
    async (path, options = {}) => {
      const headers = { ...(options.headers || {}) };
      if (options.body && !headers['Content-Type']) headers['Content-Type'] = 'application/json';
      if (tokenRef.current) headers.Authorization = `Bearer ${tokenRef.current}`;
      const res = await fetch(path, { ...options, headers });
      let data = {};
      try {
        data = await res.json();
      } catch {
        data = { success: false, error: 'การตอบกลับจากเซิร์ฟเวอร์ไม่ถูกต้อง' };
      }
      if (res.status === 401 && tokenRef.current) logout();
      if (!res.ok || data.success === false) {
        const err = new Error(data.error || `เกิดข้อผิดพลาด (HTTP ${res.status})`);
        err.status = res.status;
        err.data = data;
        throw err;
      }
      return data;
    },
    [logout]
  );

  const refreshUser = useCallback(async () => {
    if (!tokenRef.current) return;
    try {
      const data = await apiFetch('/api/auth/me');
      // weakPassword ได้มาตอนล็อกอินเท่านั้น — เก็บไว้จนกว่าจะเปลี่ยนรหัสผ่าน
      const saved = readSession();
      persist(tokenRef.current, { ...data.user, weakPassword: saved?.user?.weakPassword || undefined });
    } catch {
      /* ออฟไลน์ — ใช้ข้อมูลเดิมไปก่อน */
    }
  }, [apiFetch, persist]);

  useEffect(() => {
    try {
      LEGACY_KEYS.forEach((k) => localStorage.removeItem(k)); // session รุ่นเก่า (token ไม่มีลายเซ็น / รหัส MT5)
    } catch {
      /* ignore */
    }
    const saved = readSession();
    if (saved) {
      tokenRef.current = saved.token;
      setUser(saved.user);
      refreshUser();
    }
    setIsLoading(false);
  }, [refreshUser]);

  // ดึงชั่วโมงคงเหลือใหม่ทุก 60 วินาที (เฉพาะตอนแท็บเปิดอยู่) ให้ตรงกับโปรแกรม AI Gold Commander Pro ที่กำลังหักเวลา
  useEffect(() => {
    if (!user) return undefined;
    const id = setInterval(() => {
      if (typeof document === 'undefined' || document.visibilityState === 'visible') refreshUser();
    }, 60000);
    return () => clearInterval(id);
  }, [user?.id, refreshUser]); // eslint-disable-line react-hooks/exhaustive-deps

  const login = useCallback(
    async (email, password) => {
      const data = await apiFetch('/api/auth/login', { method: 'POST', body: JSON.stringify({ email, password }) });
      persist(data.token, data.user);
      setIsAuthModalOpen(false);
      return data.user;
    },
    [apiFetch, persist]
  );

  const register = useCallback(
    async (email, password, displayName, code = '') => {
      const data = await apiFetch('/api/auth/register', { method: 'POST', body: JSON.stringify({ email, password, displayName, code }) });
      // ขั้นแรก: เซิร์ฟเวอร์ส่งรหัสยืนยันไปที่อีเมล ยังไม่สร้างบัญชี
      if (data.step === 'verify') return { step: 'verify', message: data.message };
      persist(data.token, data.user);
      setIsAuthModalOpen(false);
      return data.user;
    },
    [apiFetch, persist]
  );

  const redeemKey = useCallback(
    async (keyCode) => {
      const data = await apiFetch('/api/auth/redeem', { method: 'POST', body: JSON.stringify({ keyCode }) });
      if (user) persist(tokenRef.current, { ...user, hoursRemaining: data.hoursRemaining });
      return data;
    },
    [apiFetch, persist, user]
  );

  const changePassword = useCallback(
    async (currentPassword, newPassword) => {
      const data = await apiFetch('/api/auth/change-password', { method: 'POST', body: JSON.stringify({ currentPassword, newPassword }) });
      if (user) persist(tokenRef.current, { ...user, weakPassword: undefined });
      return data;
    },
    [apiFetch, persist, user]
  );

  /** เข้าสู่ระบบด้วย token ที่ได้จาก API อื่น (เช่น ตั้งรหัสผ่านใหม่สำเร็จ) */
  const completeLogin = useCallback((token, nextUser) => persist(token, nextUser), [persist]);

  const value = useMemo(
    () => ({
      user,
      isLoading,
      isAdmin: Boolean(user?.isAdmin),
      // แสดงเมนู/ลิงก์แอดมินเฉพาะตอนเป็นแอดมินและอยู่ในโหมดแอดมิน (สิทธิ์จริงตรวจที่ Server เสมอ)
      isAdminView: Boolean(user?.isAdmin) && viewMode === 'admin',
      viewMode,
      setViewMode,
      isAuthModalOpen,
      authModalTab,
      setAuthModalTab,
      openAuthModal: (tab = 'login') => {
        setAuthModalTab(tab);
        setIsAuthModalOpen(true);
      },
      closeAuthModal: () => setIsAuthModalOpen(false),
      login,
      register,
      logout,
      refreshUser,
      redeemKey,
      changePassword,
      completeLogin,
      apiFetch,
    }),
    [user, isLoading, viewMode, setViewMode, isAuthModalOpen, authModalTab, login, register, logout, refreshUser, redeemKey, changePassword, completeLogin, apiFetch]
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error('useAuth must be used inside <AuthProvider>');
  return ctx;
}
