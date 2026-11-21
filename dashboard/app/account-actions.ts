'use server';
import {isWorkEmail,workEmailMessage} from '@/lib/auth-policy';
import {AuthError} from 'next-auth';
import {cookies} from 'next/headers';
import {redirect} from 'next/navigation';
import {randomUUID} from 'node:crypto';
import {signIn} from '@/auth';
import {serverEnv} from '@/lib/server/env';
import {accountRequest} from '@/lib/server/account-broker';
import {verifyChallenge} from '@/lib/server/turnstile';
import {readAccountCookie,saveAccountCookie,verificationCookie} from '@/lib/server/account-cookies';
import {encodeConsent,invitationCookie} from '@/lib/server/admission';
export type AccountState={error:string|null;message?:string};
function value(form:FormData,key:string,max:number){const x=form.get(key);return typeof x==='string'&&x.length<=max?x:'';}
function failure(status:number):AccountState{return {error:status===429?'Too many requests. Wait a little before trying again.':status===503?'Account service is temporarily unavailable. Please try again shortly.':'Check your company email and account details, then try again.'};}
export async function passwordSignIn(_state:AccountState,form:FormData):Promise<AccountState>{
 if(!serverEnv().accounts)return failure(503);
 if(!isWorkEmail(value(form,'email',254)))return {error:workEmailMessage};
 try{await signIn('credentials',{email:value(form,'email',254),password:value(form,'password',128),redirectTo:'/'});}catch(error){if(error instanceof AuthError)return {error:'Email or password is incorrect, or verification is incomplete.'};throw error;}
 return {error:null};
}
export async function createAccount(_state:AccountState,form:FormData):Promise<AccountState>{
 const env=serverEnv();if(!env.accounts||!env.customerAccess||!env.termsVersion)return failure(503);
 if(form.get('accept_terms')!=='accepted')return {error:'Accept the current Terms of Service to continue.'};
 if(value(form,'password',128)!==value(form,'confirm_password',128))return {error:'The passwords do not match. Enter the same password in both fields.'};
 const email=value(form,'email',254).trim().toLowerCase();if(!isWorkEmail(email))return {error:workEmailMessage};
  const invitation=value(form,'invitation_token',100).trim();
  if(!await verifyChallenge(form,'signup'))return {error:'Complete a fresh security check and try again.'};
 const result=await accountRequest('signup',email,{email,password:value(form,'password',128),name:value(form,'name',120),company_name:value(form,'company_name',120),terms_version:env.termsVersion,accepted_terms:true,request_id:value(form,'request_id',36)||randomUUID(),...(invitation?{invitation_token:invitation}:{})});
 if(!result.ok||!result.data.challenge_id||!result.data.capability)return failure(result.status);
 await saveAccountCookie(verificationCookie,{email,...result.data,...(invitation?{invitation}:{})});
 redirect('/verify-email');
}
export async function verifyAccount(_state:AccountState,form:FormData):Promise<AccountState>{
 const pending=await readAccountCookie(verificationCookie);
 if(!pending||typeof pending.email!=='string')return {error:'This verification request expired. Start again from signup.'};
 const result=await accountRequest('verify-email',pending.email,{challenge_id:pending.challenge_id,capability:pending.capability,code:value(form,'code',6)});
 if(!result.ok||!result.data.login_ticket)return {error:'The code is incorrect, expired or already used. Request a new code, or sign in if you have already verified.'};
 const jar=await cookies();jar.delete(verificationCookie);
 if(typeof pending.invitation==='string')await saveInvitation(pending.invitation);
 try{await signIn('credentials',{email:pending.email,ticket:result.data.login_ticket,redirectTo:pending.invitation?'/accept-invitation':'/'});}catch(error){if(error instanceof AuthError)return {error:'Your email was verified. Sign in with your password to continue.'};throw error;}
 return {error:null};
}
async function saveInvitation(invitation:string){const env=serverEnv();(await cookies()).set(invitationCookie,encodeConsent({version:env.termsVersion,accepted_at:Math.floor(Date.now()/1000),nonce:randomUUID(),invitation_token:invitation},env.secret),{httpOnly:true,secure:env.production,sameSite:'lax',path:'/accept-invitation',maxAge:600});}
export async function resendAccountCode():Promise<AccountState>{
 const pending=await readAccountCookie(verificationCookie);
 if(!pending||typeof pending.email!=='string')return {error:'This verification request expired. Start again from signup.'};
 const result=await accountRequest('resend-verification',pending.email,{challenge_id:pending.challenge_id,capability:pending.capability,request_id:randomUUID()});
 if(!result.ok)return failure(result.status);
 await saveAccountCookie(verificationCookie,{...pending,...result.data});
 return {error:null,message:'If your account is eligible, a fresh verification code is on its way. Otherwise, follow the sign-in guidance in your email.'};
}
export async function recoverAccount(_state:AccountState,form:FormData):Promise<AccountState>{
 if(!await verifyChallenge(form,'recovery'))return {error:'Complete a fresh security check and try again.'};
 const email=value(form,'email',254).trim().toLowerCase();const result=await accountRequest('recovery',email,{email,request_id:randomUUID()});
 return result.ok?{error:null,message:'If this account has a PlaneByte password, a reset link will be emailed shortly. For Google-only accounts, use Google Account Recovery.'}:failure(result.status);
}
export async function resetAccountPassword(_state:AccountState,form:FormData):Promise<AccountState>{
 if(value(form,'password',128)!==value(form,'confirm_password',128))return {error:'The passwords do not match. Enter the same password in both fields.'};
 const result=await accountRequest('reset-password','account-request@planebyte.com',{token:value(form,'token',100),password:value(form,'password',128)});
 return result.ok&&result.data.reset?{error:null,message:'Password changed. Sign in again with your new password.'}:{error:'This reset link is invalid or expired, or the password does not meet the requirements. Request a fresh link if needed.'};
}

export async function rememberInvitation(_previous:AccountState,form:FormData):Promise<AccountState>{
 const env=serverEnv(),invitation=value(form,'invitation_token',100);
 if(!env.customerAccess||!(env.invitedRegistration||env.publicRegistration)||!/^[A-Za-z0-9_-]{40,100}$/.test(invitation))return {error:'This invitation cannot be used here. Ask your workspace administrator to check it.'};
 await saveAccountCookie('planebyte-pending-invitation',{invitation,expires_at:Math.floor(Date.now()/1000)+600});
 redirect('/signup');
}
