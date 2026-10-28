import {NextRequest} from "next/server";
import {serverEnv} from "@/lib/server/env";
export const runtime="nodejs";
export const dynamic="force-dynamic";
async function tracking(request:NextRequest,context:{params:Promise<{action:string;token:string}>}){
 const {action,token}=await context.params;
 if(!/^[ocu]$/.test(action)||!(/^[A-Za-z0-9_-]{43}(?:\.gif)?$/).test(token))return new Response("Link unavailable",{status:404});
 if(request.method==="POST"&&action!=="u")return new Response(null,{status:405});
 if(Number(request.headers.get("content-length")||0)>1024)return new Response(null,{status:413});
 const chunks:Uint8Array[]=[];let size=0;const reader=request.body?.getReader();
 if(reader){for(;;){const n=await reader.read();if(n.done)break;size+=n.value.length;if(size>1024){await reader.cancel();return new Response(null,{status:413});}chunks.push(n.value);}}
 const body=new Uint8Array(size);let offset=0;for(const chunk of chunks){body.set(chunk,offset);offset+=chunk.length;}
 try{
  const upstream=await fetch(`${serverEnv().apiUrl}/api/tracking/${action}/${token}`,{method:request.method,body:request.method==="POST"?body:undefined,headers:{"content-type":request.headers.get("content-type")||"application/x-www-form-urlencoded","user-agent":request.headers.get("user-agent")||"","sec-fetch-user":request.headers.get("sec-fetch-user")||""},redirect:"manual",cache:"no-store",signal:AbortSignal.timeout(15000)});
  const headers=new Headers({"cache-control":"no-store","referrer-policy":"no-referrer","x-content-type-options":"nosniff","content-security-policy":"default-src 'none'; style-src 'unsafe-inline'; form-action 'self'; frame-ancestors 'none'; base-uri 'none'"});
  for(const key of ["content-type","location"]){const value=upstream.headers.get(key);if(value)headers.set(key,value);}
  return new Response(request.method==="HEAD"?null:upstream.body,{status:upstream.status,headers});
 }catch{return new Response("Temporarily unavailable",{status:503,headers:{"cache-control":"no-store"}});}
}
export {tracking as GET,tracking as POST,tracking as HEAD};
