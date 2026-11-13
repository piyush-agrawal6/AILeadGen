import 'server-only';
import {createHash,createHmac,randomUUID} from 'node:crypto';
import {currentUser} from './session';
import {serverEnv} from './env';
import type {ProductAccess} from '@/lib/intent-radar';
export async function productAccess():Promise<ProductAccess|null>{
 const user=await currentUser();if(!user?.email)return null;
 const env=serverEnv(),path='/api/organization/products',timestamp=String(Math.floor(Date.now()/1000)),nonce=randomUUID(),actor=user.email.toLowerCase();
 const canonical=[timestamp,nonce,'GET',path,createHash('sha256').update('').digest('hex'),actor].join('\n');
 try{const result=await fetch(env.apiUrl+path,{cache:'no-store',redirect:'error',signal:AbortSignal.timeout(25000),headers:{'x-le-timestamp':timestamp,'x-le-nonce':nonce,'x-le-user':actor,'x-le-signature':createHmac('sha256',env.secret).update(canonical).digest('hex')}});return result.ok?await result.json() as ProductAccess:null;}catch{return null;}
}
