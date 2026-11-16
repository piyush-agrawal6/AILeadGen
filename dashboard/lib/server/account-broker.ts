import 'server-only';
import {createHash,createHmac,randomUUID} from 'node:crypto';
import {headers} from 'next/headers';
import {serverEnv} from './env';

export function signedHeaders(method:string,path:string,body:Uint8Array|string,actor:string,session='',client=''){
 const env=serverEnv(),timestamp=String(Math.floor(Date.now()/1000)),nonce=randomUUID();
 const parts=[timestamp,nonce,method,path,createHash('sha256').update(body).digest('hex'),actor];
 if(session)parts.push('session-sha256:'+createHash('sha256').update(session).digest('hex'));
 if(client)parts.push('client:'+client);
 return {'content-type':'application/json','x-le-user':actor,'x-le-timestamp':timestamp,'x-le-nonce':nonce,'x-le-signature':createHmac('sha256',env.secret).update(parts.join('\n')).digest('hex'),...(session?{'x-le-session':session}:{}),...(client?{'x-le-client':client}:{})};
}
export async function clientIdentity(){
 const incoming=await headers();
 const value=[incoming.get('x-vercel-forwarded-for')||incoming.get('x-real-ip')||'unknown',incoming.get('user-agent')||'unknown'].join('|').slice(0,1000);
 return createHmac('sha256',serverEnv().secret).update('account-client:'+value).digest('hex');
}
export type AccountResult={id?:string;authenticated?:boolean;verified?:boolean;accepted?:boolean;reset?:boolean;email?:string;user_id?:string;name?:string;session_token?:string;expires_at?:number;login_ticket?:string;challenge_id?:string;capability?:string;requires_terms?:boolean;terms_version?:string;google_linked?:boolean;password_enabled?:boolean;link_token?:string};
export async function accountRequest(action:string,actor:string,value:unknown={},session=''):Promise<{ok:boolean;status:number;data:AccountResult}>{
 const env=serverEnv();if(!env.accounts||!env.customerAccess||env.secret.length<32)return {ok:false,status:503,data:{}};
 if(!/^[a-z-]+$/.test(action))throw new Error('Unsupported account action');
 const path='/api/organization/accounts/'+action,body=JSON.stringify(value);
 if(Buffer.byteLength(body)>8192)return {ok:false,status:413,data:{}};
 try{
  const result=await fetch(env.apiUrl+path,{method:'POST',body,headers:signedHeaders('POST',path,body,actor,session,await clientIdentity()),cache:'no-store',redirect:'error',signal:AbortSignal.timeout(20000)});
  const data=await result.json();return {ok:result.ok,status:result.status,data:result.ok?data:{}};
 }catch{return {ok:false,status:503,data:{}};}
}
