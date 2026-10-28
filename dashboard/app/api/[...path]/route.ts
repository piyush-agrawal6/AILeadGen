import { serverEnv } from "@/lib/server/env";
import { currentUser } from "@/lib/server/session";
import { NextRequest } from "next/server";
import { sameOrigin } from "@/lib/origin-policy";
import { createHash,createHmac,randomUUID } from "node:crypto";
export const runtime = "nodejs";
export const dynamic = "force-dynamic";
export const maxDuration = 60;
async function forward(request: NextRequest, context: { params: Promise<{ path: string[] }> }) {
  const user = await currentUser();
  if (!user?.email) return Response.json({ detail: "Sign in to continue." }, { status: 401 });
  if (!["GET", "HEAD", "OPTIONS"].includes(request.method) && !sameOrigin(request.headers.get("origin"),request.headers.get("host"),serverEnv().production)) return Response.json({ detail: "Invalid request origin." }, { status: 403 });
  const { path } = await context.params;
  if (path.some(p => !/^[a-zA-Z0-9_.-]+$/.test(p) || p === "." || p === "..")) return Response.json({ detail: "Invalid API path." }, { status: 400 });
  const env = serverEnv();
  const apiPath = `/api/${path.join("/")}${request.nextUrl.search}`;
  if (Number(request.headers.get("content-length") || 0) > 1_048_576) return Response.json({ detail: "Request too large." }, { status: 413 });
  const chunks:Uint8Array[]=[];let length=0;const reader=request.body?.getReader();
  if(reader){for(;;){const next=await reader.read();if(next.done)break;length+=next.value.byteLength;if(length>1_048_576){await reader.cancel();return Response.json({detail:"Request too large."},{status:413});}chunks.push(next.value);}}
  const body=new Uint8Array(length);let offset=0;for(const chunk of chunks){body.set(chunk,offset);offset+=chunk.byteLength;}
  const timestamp = String(Math.floor(Date.now() / 1000)); const nonce = randomUUID(); const actor = user.email.toLowerCase();
  const canonical = [timestamp, nonce, request.method, apiPath, createHash("sha256").update(body).digest("hex"), actor].join("\n");
  const headers: Record<string, string> = { "content-type": request.headers.get("content-type") || "application/json", "x-le-timestamp": timestamp, "x-le-nonce": nonce, "x-le-user": actor, "x-le-signature": createHmac("sha256", env.secret).update(canonical).digest("hex") };
  const lastId = request.headers.get("last-event-id"); if (lastId && /^\d+$/.test(lastId)) headers["last-event-id"] = lastId;
  try {
    const upstream = await fetch(`${env.apiUrl}${apiPath}`, { method: request.method, headers, body: ["GET", "HEAD"].includes(request.method) ? undefined : body, cache: "no-store", redirect: "manual", signal: request.signal });
    const responseHeaders = new Headers({ "cache-control": "no-store", "x-content-type-options": "nosniff" });
    for (const key of ["content-type", "content-disposition", "x-accel-buffering"]) { const value = upstream.headers.get(key); if (value) responseHeaders.set(key, value); }
    if (upstream.headers.get("content-type")?.includes("text/html")) responseHeaders.set("content-security-policy", "sandbox; default-src 'none'; style-src 'unsafe-inline'; img-src data:");
    return new Response(upstream.body, { status: upstream.status, headers: responseHeaders });
  } catch { return Response.json({ detail: "The engine is temporarily unavailable. Please retry." }, { status: 502 }); }
}
export { forward as DELETE,forward as GET,forward as PATCH,forward as POST,forward as PUT };
