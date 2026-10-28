import { currentUser } from "@/lib/server/session";
import { NextRequest,NextResponse } from "next/server";
import { isPublicBrandAsset } from "@/lib/auth-policy";
export async function proxy(request: NextRequest) {
  const pathname = request.nextUrl.pathname;
  const tracking=/^\/t\/[ocu]\/[A-Za-z0-9_-]{43}(?:\.gif)?$/.test(pathname);
  if (!tracking && !isPublicBrandAsset(pathname) && pathname !== "/login" && !pathname.startsWith("/api/auth") && !(await currentUser())) {
    if (pathname.startsWith("/api/")) return NextResponse.json({ detail: "Sign in to continue." }, { status: 401 });
    return NextResponse.redirect(new URL("/login", request.url));
  }
  const nonce = Buffer.from(crypto.randomUUID()).toString("base64"); const dev = process.env.NODE_ENV !== "production";
  const csp = ["default-src 'self'", `script-src 'self' 'nonce-${nonce}' 'strict-dynamic'${dev ? " 'unsafe-eval'" : ""}`, "style-src 'self' 'unsafe-inline'", "img-src 'self' data: https://lh3.googleusercontent.com", "font-src 'self'", `connect-src 'self'${dev ? " ws: http://localhost:*" : ""}`, "frame-src 'none'", "object-src 'none'", "base-uri 'self'", "form-action 'self'", "frame-ancestors 'none'"].join("; ");
  const headers = new Headers(request.headers); headers.set("x-nonce", nonce); headers.set("Content-Security-Policy", csp);
  const response = NextResponse.next({ request: { headers } }); response.headers.set("Content-Security-Policy", csp); response.headers.set("Cache-Control", "no-store"); return response;
}
export const config = { matcher: ["/((?!_next/static|_next/image|favicon.ico).*)"] };
