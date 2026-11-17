import 'server-only';
import {createCipheriv,createDecipheriv,createHash,randomBytes} from 'node:crypto';
import {cookies} from 'next/headers';
import {serverEnv} from './env';
export const verificationCookie='planebyte-email-verification';
export const linkCookie='planebyte-google-link';
function key(){if(serverEnv().secret.length<32)throw new Error('Account cookies unavailable');return createHash('sha256').update('planebyte:account-cookies:v1:'+serverEnv().secret).digest();}
export function sealAccountCookie(value:Record<string,unknown>){const iv=randomBytes(12),cipher=createCipheriv('aes-256-gcm',key(),iv);return Buffer.concat([iv,cipher.update(JSON.stringify(value)),cipher.final(),cipher.getAuthTag()]).toString('base64url');}
export function openAccountCookie(raw:string):Record<string,unknown>|null{
 try{if(raw.length>4000)return null;const data=Buffer.from(raw,'base64url');if(data.length<29)return null;const cipher=createDecipheriv('aes-256-gcm',key(),data.subarray(0,12));cipher.setAuthTag(data.subarray(-16));const result=JSON.parse(Buffer.concat([cipher.update(data.subarray(12,-16)),cipher.final()]).toString());if(typeof result.expires_at!=='number'||result.expires_at<=Date.now()/1000)return null;return result;}catch{return null;}
}
export async function saveAccountCookie(name:string,value:Record<string,unknown>,seconds=600){(await cookies()).set(name,sealAccountCookie(value),{httpOnly:true,secure:serverEnv().production,sameSite:'lax',path:'/',maxAge:seconds});}
export async function readAccountCookie(name:string){return openAccountCookie((await cookies()).get(name)?.value||'');}
