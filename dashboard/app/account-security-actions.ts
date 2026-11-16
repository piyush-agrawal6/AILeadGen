'use server';
import {currentUser} from '@/lib/server/session';
import {privateSession} from '@/lib/server/private-session';
import {accountRequest} from '@/lib/server/account-broker';
import {serverEnv} from '@/lib/server/env';
import {saveAccountCookie,verificationCookie,linkCookie} from '@/lib/server/account-cookies';
import {signIn} from '@/auth';
import {randomUUID} from 'node:crypto';
import {redirect} from 'next/navigation';
import type {AccountState} from './account-actions';
export async function accountSecurity(){
 const user=await currentUser(),env=serverEnv();if(!user?.email)return null;
 const token=await privateSession();
 if(!env.accounts||!token)return {google_linked:true,password_enabled:false,requires_terms:false,managed:false};
 const result=await accountRequest('session',user.email,{},token);
 return result.ok?{google_linked:!!result.data.google_linked,password_enabled:!!result.data.password_enabled,requires_terms:!!result.data.requires_terms,managed:true}:null;
}
export async function linkGoogle(){
 const user=await currentUser();if(!user?.email)redirect('/login');
 const result=await accountRequest('link-google',user.email,{},await privateSession());
 if(!result.ok||!result.data.link_token)redirect('/settings/account?tab=security&error=link_unavailable');
 await saveAccountCookie(linkCookie,{email:user.email,link_token:result.data.link_token,expires_at:result.data.expires_at});
 await signIn('google',{redirectTo:'/settings/account?tab=security'});
}
export async function addPassword(_previous:AccountState,form:FormData):Promise<AccountState>{
 const user=await currentUser(),password=form.get('password');if(!user?.email||typeof password!=='string'||password.length>128)return {error:'Sign in with Google again, then enter a new password.'};
 const result=await accountRequest('set-password',user.email,{password,request_id:randomUUID()},await privateSession());
 if(!result.ok)return {error:'A password could not be added. Sign in with Google again and use a unique passphrase of at least 15 characters.'};
 await saveAccountCookie(verificationCookie,{email:user.email,...result.data});redirect('/verify-email');
}
export async function acceptAccountTerms(_previous:AccountState,form:FormData):Promise<AccountState>{
 const user=await currentUser();if(!user?.email||form.get('accepted')!=='yes')return {error:'Review and accept the current account terms.'};
 const result=await accountRequest('terms',user.email,{terms_version:serverEnv().termsVersion,accepted:true,request_id:randomUUID()},await privateSession());
 if(!result.ok)return {error:'The account terms could not be updated. Sign in again and retry.'};
 redirect('/');
}
