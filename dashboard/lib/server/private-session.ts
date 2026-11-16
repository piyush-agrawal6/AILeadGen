import 'server-only';
import {getToken} from 'next-auth/jwt';
import {headers} from 'next/headers';
import {serverEnv} from './env';
/** Backend capability remains inside the encrypted HttpOnly Auth.js JWT. */
export async function privateSession(){
 const token=await getToken({req:{headers:await headers()},secret:process.env.AUTH_SECRET||'',secureCookie:serverEnv().production});
 return typeof token?.planeByteSession==='string'?token.planeByteSession:'';
}
