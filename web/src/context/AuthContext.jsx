'use client';

import { createContext, useCallback, useContext, useEffect, useMemo, useRef, useState } from 'react';

const SESSION_KEY = 'goldbot_session';
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
    async (email, password, displayName) => {
      const data = await apiFetch('/api/auth/register', { method: 'POST', body: JSON.stringify({ email, password, displayName }) });
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

  const value = useMemo(
    () => ({
      user,
      isLoading,
      isAdmin: Boolean(user?.isAdmin),
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
      apiFetch,
    }),
    [user, isLoading, isAuthModalOpen, authModalTab, login, register, logout, refreshUser, redeemKey, changePassword, apiFetch]
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error('useAuth must be used inside <AuthProvider>');
  return ctx;
}
