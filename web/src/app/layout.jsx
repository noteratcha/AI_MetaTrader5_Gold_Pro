import './globals.css';
import ClientLayoutWrapper from '../components/ClientLayoutWrapper';

export const metadata = {
  title: {
    default: 'Gold Bot 24 · บอทเทรดทองคำ AI',
    template: '%s · GoldBot24',
  },
  applicationName: 'GoldBot24',
  description: 'บอทเทรดทองคำ XAUUSD ด้วย AI เชื่อมต่อ MetaTrader 5 · คิดค่าบริการตามจริง 1 บาท/ชั่วโมง ชำระผ่าน PromptPay',
  icons: { icon: '/favicon.ico', apple: '/app_icon.png' },
  openGraph: {
    title: 'Gold Bot 24 · บอทเทรดทองคำ AI',
    description: 'บอทเทรดทองคำ XAUUSD ด้วย AI · 1 บาท/ชั่วโมง',
    siteName: 'GoldBot24',
  },
};

export const viewport = {
  width: 'device-width',
  initialScale: 1,
  themeColor: '#0a0b0f',
};

export default function RootLayout({ children }) {
  return (
    <html lang="th" suppressHydrationWarning>
      <body suppressHydrationWarning>
        <ClientLayoutWrapper>{children}</ClientLayoutWrapper>
      </body>
    </html>
  );
}
