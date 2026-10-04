'use client';

import React from 'react';
import { AuthProvider } from '../context/AuthContext';
import AuthModal from './AuthModal';

export default function ClientLayoutWrapper({ children }) {
  return (
    <AuthProvider>
      {children}
      <AuthModal />
    </AuthProvider>
  );
}
