import { NextResponse, type NextRequest } from 'next/server';
import { validateBasicAuth } from '@/lib/auth';

export async function middleware(request: NextRequest) {
  if (process.env.NODE_ENV === 'test' || process.env.DISABLE_RADAR_AUTH === 'true') {
    return NextResponse.next();
  }

  const isProd = process.env.NODE_ENV === 'production';
  const expectedUser = process.env.RADAR_AUTH_USER || (isProd ? undefined : 'radar_demo');
  const expectedPass =
    process.env.RADAR_AUTH_PASS ||
    process.env.DASHBOARD_ACCESS_KEY ||
    (isProd ? undefined : 'RADAR_DEMO_2026');

  const authHeader = request.headers.get('authorization');
  const authResult = await validateBasicAuth(authHeader, expectedUser, expectedPass);

  if (!authResult.authorized) {
    return new NextResponse('Autenticazione richiesta per Sardegna B2B Radar', {
      status: 401,
      headers: {
        'WWW-Authenticate': 'Basic realm="Sardegna B2B Radar"',
      },
    });
  }

  return NextResponse.next();
}

export const config = {
  matcher: [
    /*
     * Match all request paths except for:
     * - _next/static (static files)
     * - _next/image (image optimization files)
     * - favicon.ico (favicon file)
     * - brand static assets (.svg, .png, etc.)
     */
    '/((?!_next/static|_next/image|favicon.ico|.*\\.(?:svg|png|jpg|jpeg|gif|webp)$).*)',
  ],
};
