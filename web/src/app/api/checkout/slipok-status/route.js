import { NextResponse } from 'next/server';

const SLIPOK_BRANCH_ID = process.env.SLIPOK_BRANCH_ID || '';
const SLIPOK_API_KEY = process.env.SLIPOK_API_KEY || '';

export async function GET() {
  if (!SLIPOK_BRANCH_ID || !SLIPOK_API_KEY) {
    return NextResponse.json({
      connected: false,
      error: 'SLIPOK_BRANCH_ID or SLIPOK_API_KEY is not set in web/.env.local'
    }, { status: 400 });
  }

  try {
    const res = await fetch(`https://api.slipok.com/api/line/apikey/${SLIPOK_BRANCH_ID}/quota`, {
      method: 'GET',
      headers: {
        'x-authorization': SLIPOK_API_KEY
      }
    });

    const data = await res.json();
    return NextResponse.json({
      connected: res.ok && data.success,
      status_code: res.status,
      branch_id: SLIPOK_BRANCH_ID,
      slipok_response: data
    });
  } catch (error) {
    return NextResponse.json({
      connected: false,
      error: error.message
    }, { status: 500 });
  }
}
