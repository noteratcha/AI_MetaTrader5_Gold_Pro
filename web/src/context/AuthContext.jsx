'use client';

import React, { createContext, useContext, useState, useEffect } from 'react';

const AuthContext = createContext({
  user: null,
  isLoading: true,
  isAuthModalOpen: false,
  authModalTab: 'login',
  openAuthModal: () => {},
  closeAuthModal: () => {},
  login: async () => {},
  register: async () => {},
  logout: () => {},
  refreshUser: async () => {},
  redeemKey: async () => {}
});

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null);
  const [isLoading, setIsLoading] = useState(true);
  const [isAuthModalOpen, setIsAuthModalOpen] = useState(false);
  const [authModalTab, setAuthModalTab] = useState('login'); // 'login' | 'register'

  // โหลดสถานะเข้าสู่ระบบจาก LocalStorage เมื่อเปิดเว็บ
  useEffect(() => {
    try {
      const saved = localStorage.getItem('goldbot_user');
      if (saved) {
        const parsed = JSON.parse(saved);
        setUser(parsed);
        // ดึงชั่วโมงล่าสุดจาก Cloud
        fetchLatestUser(parsed.email);
      }
    } catch (e) {
      console.warn('Failed to parse saved user:', e);
    } finally {
      setIsLoading(false);
    }
  }, []);

  const fetchLatestUser = async (email) => {
    if (!email) return;
    try {
      const res = await fetch(`/api/auth/me?email=${encodeURIComponent(email)}`);
      const data = await res.json();
      if (data.success && data.user) {
        setUser((prev) => {
          const updated = { ...prev, ...data.user };
          localStorage.setItem('goldbot_user', JSON.stringify(updated));
          return updated;
        });
      }
    } catch (e) {
      // offline fallback
    }
  };

  const openAuthModal = (tab = 'login') => {
    setAuthModalTab(tab);
    setIsAuthModalOpen(true);
  };

  const closeAuthModal = () => {
    setIsAuthModalOpen(false);
  };

  const login = async (email, password) => {
    const res = await fetch('/api/auth/login', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ email, password })
    });
    const data = await res.json();
    if (!data.success) {
      throw new Error(data.error || 'เข้าสู่ระบบไม่สำเร็จ');
    }
    setUser(data.user);
    localStorage.setItem('goldbot_user', JSON.stringify(data.user));
    closeAuthModal();
    return data.user;
  };

  const register = async (email, password, displayName) => {
    const res = await fetch('/api/auth/register', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ email, password, displayName })
    });
    const data = await res.json();
    if (!data.success) {
      throw new Error(data.error || 'สมัครสมาชิกไม่สำเร็จ');
    }
    setUser(data.user);
    localStorage.setItem('goldbot_user', JSON.stringify(data.user));
    closeAuthModal();
    return data.user;
  };

  const logout = () => {
    setUser(null);
    localStorage.removeItem('goldbot_user');
  };

  const refreshUser = async () => {
    if (user && user.email) {
      await fetchLatestUser(user.email);
    }
  };

  const redeemKey = async (keyCode) => {
    if (!user || !user.email) {
      throw new Error('กรุณาเข้าสู่ระบบก่อนเติมชั่วโมง');
    }
    const res = await fetch('/api/auth/redeem', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ email: user.email, keyCode })
    });
    const data = await res.json();
    if (!data.success) {
      throw new Error(data.error || 'ไม่สามารถเติมคีย์ได้');
    }
    setUser((prev) => {
      const updated = { ...prev, hoursRemaining: data.hoursRemaining };
      localStorage.setItem('goldbot_user', JSON.stringify(updated));
      return updated;
    });
    return data;
  };

  return (
    <AuthContext.Provider value={{
      user,
      isLoading,
      isAuthModalOpen,
      authModalTab,
      openAuthModal,
      closeAuthModal,
      setAuthModalTab,
      login,
      register,
      logout,
      refreshUser,
      redeemKey
    }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  return useContext(AuthContext);
}
