/** @type {import('next').NextConfig} */
const nextConfig = {
  async headers() {
    return [
      {
        // ข้อมูลบัญชี/คีย์ทั้งหมดผ่าน API — ห้าม cache ที่ CDN
        // ยกเว้นข้อมูลสาธารณะที่ cache ได้ (ปฏิทินข่าว / เวอร์ชันโปรแกรม)
        source: '/api/:path((?!calendar$|release$).*)',
        headers: [{ key: 'Cache-Control', value: 'no-store' }],
      },
      {
        source: '/:path*',
        headers: [
          { key: 'X-Frame-Options', value: 'DENY' },
          { key: 'X-Content-Type-Options', value: 'nosniff' },
          { key: 'Referrer-Policy', value: 'strict-origin-when-cross-origin' },
        ],
      },
    ];
  },
};

module.exports = nextConfig;
