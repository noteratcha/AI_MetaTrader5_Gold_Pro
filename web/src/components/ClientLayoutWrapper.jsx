'use client';

import { AuthProvider } from '../context/AuthContext';
import AuthModal from './AuthModal';
import Navbar from './Navbar';
import Footer from './Footer';
import LowHoursBanner from './LowHoursBanner';

export default function ClientLayoutWrapper({ children }) {
  return (
    <AuthProvider>
      <div className="app-shell">
        <Navbar />
        <LowHoursBanner />
        <main style={{ flex: 1, display: 'flex', flexDirection: 'column' }}>{children}</main>
        <Footer />
      </div>
      <AuthModal />
    </AuthProvider>
  );
}
