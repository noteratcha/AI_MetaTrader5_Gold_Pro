/** @type {import('next').NextConfig} */
const nextConfig = {
  async headers() {
    return [
      {
        // ข้อมูลบัญชี/คีย์ทั้งหมดผ่าน API — ห้าม cache ที่ CDN
        // ยกเว้นข้อมูลสาธารณะที่ cache ได้ (ปฏิทินข่าว / เวอร์ชันโปรแกรม / ข่าวสาร / สถิติสาธารณะ — กันยิง query หนักทุกครั้งที่เปิดหน้า)
        source: '/api/:path((?!calendar$|release$|announcements$|plan-stats$|public-stats$).*)',
        headers: [{ key: 'Cache-Control', value: 'no-store' }],
      },
      {
        source: '/:path*',
        headers: [
          { key: 'X-Frame-Options', value: 'DENY' },
          { key: 'X-Content-Type-Options', value: 'nosniff' },
          { key: 'Referrer-Policy', value: 'strict-origin-when-cross-origin' },
          { key: 'Permissions-Policy', value: 'camera=(), microphone=(), geolocation=(), payment=()' },
        ],
      },
    ];
  },
};

module.exports = nextConfig;
