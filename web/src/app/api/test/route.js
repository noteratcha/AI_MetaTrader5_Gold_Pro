export const runtime = 'nodejs';

export async function GET() {
  return Response.json({ message: 'Test API working!', timestamp: new Date().toISOString() });
}

export async function POST(request) {
  const body = await request.json();
  return Response.json({ message: 'Test API POST working!', received: body, timestamp: new Date().toISOString() });
}