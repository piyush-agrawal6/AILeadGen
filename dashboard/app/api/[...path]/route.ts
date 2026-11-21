import {isDeveloperApiPath} from "@/lib/developer-path";
import { serverEnv } from "@/lib/server/env";
import { currentUser } from "@/lib/server/session";
import { NextRequest } from "next/server";
import { sameOrigin } from "@/lib/origin-policy";
import {signedHeaders} from "@/lib/server/account-broker";
import {privateSession} from "@/lib/server/private-session";
export const runtime = "nodejs";
export const dynamic = "force-dynamic";
export const maxDuration = 60;
async function forward(request: NextRequest, context: { params: Promise<{ path: string[] }> }) {
  const started=Date.now();
  const external=process.env.HEYSOW_DEVELOPER_API_ENABLED==='true'&&isDeveloperApiPath(request.nextUrl.pathname);
  const user = external?null:await currentUser();
  if (!external&&!user?.email) return Response.json({ detail: "Sign in to continue." }, { status: 401 });
  if (!external&&!["GET", "HEAD", "OPTIONS"].includes(request.method) && !sameOrigin(request.headers.get("origin"),request.headers.get("host"),serverEnv().production)) return Response.json({ detail: "Invalid request origin." }, { status: 403 });
  const { path } = await context.params;
  if (path.some(p => !/^[a-zA-Z0-9_.@-]+$/.test(p) || p === "." || p === "..")) return Response.json({ detail: "Invalid API path." }, { status: 400 });
  const env = serverEnv();
  if(path[0]==='organization'&&['accounts','admission'].includes(path[1]))return Response.json({detail:'Use the account form to continue.'},{status:404});
  const apiPath = `/api/${path.join("/")}${request.nextUrl.search}`;
  const bodyLimit=path.join("/") === "experiments/catalog" ? 4_000_000 : 1_048_576;
  if (Number(request.headers.get("content-length") || 0) > bodyLimit) return Response.json({ detail: "Request too large." }, { status: 413 });
  const chunks:Uint8Array[]=[];let length=0;const reader=request.body?.getReader();
  if(reader){for(;;){const next=await reader.read();if(next.done)break;length+=next.value.byteLength;if(length>bodyLimit){await reader.cancel();return Response.json({detail:"Request too large."},{status:413});}chunks.push(next.value);}}
  const body=new Uint8Array(length);let offset=0;for(const chunk of chunks){body.set(chunk,offset);offset+=chunk.byteLength;}
  const actor=user?.email?.toLowerCase()||'';
  const headers:Record<string,string>=signedHeaders(request.method,apiPath,body,actor,external?'':await privateSession());
  headers['content-type']=request.headers.get('content-type')||'application/json';
  if(external){
    const token=request.headers.get('authorization')||'';
    if(!/^Bearer pbk_[a-f0-9-]{36}\.[A-Za-z0-9_-]{43}$/.test(token))return Response.json({detail:'A valid scoped API credential is required.'},{status:401,headers:{'WWW-Authenticate':'Bearer','Cache-Control':'no-store'}});
    for(const key of Object.keys(headers))if(key.startsWith('x-le-'))delete headers[key];
    headers.authorization=token;
    const idempotency=request.headers.get('idempotency-key');if(idempotency)headers['idempotency-key']=idempotency;
    const accept=request.headers.get('accept');if(accept)headers.accept=accept;
    const mcpVer=request.headers.get('mcp-protocol-version');if(mcpVer)headers['mcp-protocol-version']=mcpVer;
    const mcpSess=request.headers.get('mcp-session-id');if(mcpSess)headers['mcp-session-id']=mcpSess;
  }
  const lastId = request.headers.get("last-event-id"); if (lastId && /^\d+$/.test(lastId)) headers["last-event-id"] = lastId;
  try {
    const upstream = await fetch(`${env.apiUrl}${apiPath}`, { method: request.method, headers, body: ["GET", "HEAD"].includes(request.method) ? undefined : body, cache: "no-store", redirect: "manual", signal: AbortSignal.any([request.signal, AbortSignal.timeout(55000)]) });
    const responseHeaders = new Headers({ "cache-control": "no-store", "x-content-type-options": "nosniff" });
    for (const key of ["content-type", "content-disposition", "x-accel-buffering", "x-le-cache", "server-timing", "retry-after", "www-authenticate", "mcp-protocol-version", "mcp-session-id", "x-ratelimit-limit", "x-ratelimit-remaining"]) { const value = upstream.headers.get(key); if (value) responseHeaders.set(key, value); }
    if (upstream.headers.get("content-type")?.includes("text/html")) responseHeaders.set("content-security-policy", "sandbox; default-src 'none'; style-src 'unsafe-inline'; img-src data:");
    return new Response(upstream.body, { status: upstream.status, headers: responseHeaders });
  } catch (err) {
    const isTimeout =
      err instanceof Error &&
      (err.name === "TimeoutError" || err.name === "AbortError" || err.message.toLowerCase().includes("timeout"));
    const correlationId=crypto.randomUUID();
    console.error('[api-proxy]',{route:'/api/[...path]',method:request.method,category:isTimeout?'timeout':'upstream_failure',durationMs:Date.now()-started,correlationId});
    const failureHeaders={'x-request-id':correlationId,'cache-control':'private, no-store'};
    if (isTimeout) {
      return Response.json(
        { detail: "Request timed out while waiting for the PlaneByte API. Please retry." },
        { status: 504,headers:failureHeaders },
      );
    }
    return Response.json(
      { detail: "Could not reach the PlaneByte API service. Please retry in a moment." },
      { status: 502,headers:failureHeaders },
    );
  }
}
export { forward as DELETE,forward as GET,forward as PATCH,forward as POST,forward as PUT };
