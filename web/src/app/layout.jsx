import './globals.css';
import ClientLayoutWrapper from '../components/ClientLayoutWrapper';

export const metadata = {
  title: {
    default: 'GoldBot24 | AI Gold Commander Pro (XAUUSD Specialist)',
    template: '%s | GoldBot24',
  },
  applicationName: 'GoldBot24',
  description: 'GoldBot24 - แพลตฟอร์มและระบบบอทเทรดทองคำ AI อัจฉริยะ 100% Pure Gold Specialist (XAUUSD) • บริการเติมชั่วโมง 1 บาท/ชม. ด้วยระบบ SlipOK PromptPay',
  openGraph: {
    title: 'GoldBot24 | AI Gold Commander Pro',
    description: 'GoldBot24 - แพลตฟอร์มระบบบอทเทรดทองคำ AI อัจฉริยะ 100% Pure Gold Specialist (XAUUSD) • ชั่วโมงละ 1 บาท',
    siteName: 'GoldBot24',
  },
};

export default function RootLayout({ children }) {
  return (
    <html lang="th" suppressHydrationWarning>
      <head>
        <meta name="viewport" content="width=device-width, initial-scale=1.0" />
        <link rel="icon" href="/favicon.ico" />
        <link rel="apple-touch-icon" href="/app_icon.png" />
      </head>
      <body suppressHydrationWarning style={{ display: 'flex', flexDirection: 'column', minHeight: '100vh' }}>
        <ClientLayoutWrapper>
          {children}
        </ClientLayoutWrapper>
      </body>
    </html>
  );
}
