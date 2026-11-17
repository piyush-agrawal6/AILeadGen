import 'server-only';
import {cache} from 'react';
import {signedHeaders} from './account-broker';
import {privateSession} from './private-session';
import {currentUser} from './session';
import {serverEnv} from './env';
import type {ProductAccess} from '@/lib/intent-radar';
export const productAccess=cache(async function productAccess():Promise<ProductAccess|null>{
 const user=await currentUser();if(!user?.email)return null;
 const env=serverEnv(),path='/api/organization/products',actor=user.email.toLowerCase();
 const headers=signedHeaders('GET',path,'',actor,await privateSession());
 try{const result=await fetch(env.apiUrl+path,{cache:'no-store',redirect:'error',signal:AbortSignal.timeout(45000),headers});return result.ok?await result.json() as ProductAccess:null;}catch{return null;}
});
