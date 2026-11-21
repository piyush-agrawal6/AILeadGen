import { currentUser } from "@/lib/server/session";
import { NextRequest,NextResponse } from "next/server";
import { isPublicBrandAsset } from "@/lib/auth-policy";
import {isDeveloperApiPath} from "@/lib/developer-path";
import { isPublicPage } from "@/lib/auth-experience";
import {leadEngineEnabled,isLeadEnginePage} from '@/lib/product-availability';
export async function proxy(request: NextRequest) {
  const pathname = request.nextUrl.pathname;
  const developerApi=process.env.HEYSOW_DEVELOPER_API_ENABLED==='true'&&isDeveloperApiPath(pathname);
  const paymentReturn=pathname==='/api/payments/payu-return'&&request.method==='POST';
  const tracking=/^\/t\/[ocu]\/[A-Za-z0-9_-]{43}(?:\.gif)?$/.test(pathname);
  if (!developerApi && !paymentReturn && !tracking && !isPublicBrandAsset(pathname) && !isPublicPage(pathname) && !(pathname==='/api/auth'||pathname.startsWith('/api/auth/')) && !(await currentUser())) {
    const denied=pathname.startsWith('/api/')?NextResponse.json({detail:'Sign in to continue.'},{status:401}):NextResponse.redirect(new URL('/login',request.url));
    denied.headers.set('Cache-Control','private, no-store');denied.headers.append('Vary','Cookie');return denied;
  }
  const nonce = Buffer.from(crypto.randomUUID()).toString("base64"); const dev = process.env.NODE_ENV !== "production";
  const billingCheckout=pathname==='/billing/checkout';
  const paymentConnect=billingCheckout?' https://api.razorpay.com https://lumberjack.razorpay.com':'';
  const paymentFrame=billingCheckout?' https://api.razorpay.com https://checkout.razorpay.com':'';
  const challenge=process.env.TURNSTILE_ENFORCED==='true'&&['/signup','/forgot-password'].includes(pathname)?' https://challenges.cloudflare.com':'';
  const csp = ["default-src 'self'", `script-src 'self' 'nonce-${nonce}' 'strict-dynamic'${dev ? " 'unsafe-eval'" : ""}`, "style-src 'self' 'unsafe-inline'", "img-src 'self' data: https://lh3.googleusercontent.com", "font-src 'self'", `connect-src 'self'${paymentConnect}${challenge}${dev ? " ws: http://localhost:*" : ""}`, `frame-src 'self'${paymentFrame}${challenge}`, "object-src 'none'", "base-uri 'self'", "form-action 'self'", "frame-ancestors 'none'"].join("; ");
  const headers = new Headers(request.headers); headers.set("x-nonce", nonce); headers.set("Content-Security-Policy", csp);
  headers.set('x-heysow-public-page',isPublicPage(pathname)?'1':'0');
  if(!leadEngineEnabled(process.env.LEAD_ENGINE_AVAILABLE)&&isLeadEnginePage(pathname)){
    const response=NextResponse.redirect(new URL('/intent-radar',request.url));
    response.headers.set('Content-Security-Policy',csp);response.headers.set('Cache-Control','no-store');return response;
  }
  // Deny disabled archives before the product shell starts streaming a 200.
  const disabledArchive=(pathname==='/outreach/results'||pathname==='/experiments/nov-2026')&&process.env.HEYSOW_INTERNAL_EXPERIMENTS_ENABLED!=='true';
  const response = disabledArchive?NextResponse.rewrite(new URL('/_not-found',request.url),{status:404,request:{headers}}):NextResponse.next({ request: { headers } }); response.headers.set("Content-Security-Policy", csp); response.headers.set("Cache-Control", "no-store"); return response;
}
export const config = { matcher: ["/((?!_next/static|_next/image|favicon.ico).*)"] };
