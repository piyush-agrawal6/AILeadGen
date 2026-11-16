'use client';
import {useActionState,useId} from 'react';
import Link from 'next/link';
import type {AccountState} from '@/app/account-actions';
type Action=(previous:AccountState,form:FormData)=>Promise<AccountState>;
const input='mt-1.5 w-full rounded-lg border border-border bg-background px-3 py-2 text-sm text-foreground focus:outline-none focus:ring-2 focus:ring-primary/40';
export function AccountForm({action,kind,requestId,token='',label,initialInvitation='',invitationRequired=false}:{action:Action;kind:'login'|'signup'|'verify'|'recovery'|'reset'|'resend';requestId?:string;token?:string;label?:string;initialInvitation?:string;invitationRequired?:boolean}){
 const [state,submit,pending]=useActionState(action,{error:null}),passwordId=useId();
 return <form action={submit} className="space-y-4 text-left" aria-busy={pending}>
  {state.error&&<p className="pb-auth-alert" role="alert">{state.error}</p>}
  {state.message&&<p className="rounded-lg border border-border bg-muted p-3 text-sm" role="status">{state.message}</p>}
  {requestId&&<input type="hidden" name="request_id" value={requestId}/>}
  {kind==='signup'&&<><label className="block text-xs font-medium">Your name<input className={input} name="name" autoComplete="name" minLength={2} maxLength={120} required/></label><label className="block text-xs font-medium">Company name<input className={input} name="company_name" autoComplete="organization" minLength={2} maxLength={120} required/></label></>}
  {['login','signup','recovery'].includes(kind)&&<label className="block text-xs font-medium">{kind==='signup'?'Company email':'Email'}<input className={input} name="email" type="email" autoComplete="email" maxLength={254} required/></label>}
  {['login','signup','reset'].includes(kind)&&<><label htmlFor={passwordId} className="block text-xs font-medium">{kind==='reset'?'New password':'Password'}</label><input id={passwordId} aria-describedby={kind==='login'?undefined:passwordId+'-help'} className={input} name="password" type="password" autoComplete={kind==='login'?'current-password':'new-password'} minLength={kind==='login'?1:15} maxLength={128} required/>{kind!=='login'&&<span id={passwordId+'-help'} className="mt-1 block text-xs text-muted-foreground">Use a unique passphrase of 15–128 characters.</span>}</>}
  {['signup','reset'].includes(kind)&&<label className="block text-xs font-medium">Confirm password<input className={input} name="confirm_password" type="password" autoComplete="new-password" minLength={15} maxLength={128} required/></label>}
  {kind==='verify'&&<label className="block text-xs font-medium">Verification code<input className={input+' tracking-[0.4em] text-center'} name="code" inputMode="numeric" autoComplete="one-time-code" pattern="[0-9]{6}" minLength={6} maxLength={6} required/></label>}
  {kind==='reset'&&<input type="hidden" name="token" value={token}/>}
  {kind==='signup'&&<><label className="block text-xs font-medium">Invitation code{invitationRequired?'':' (optional)'}<input className={input} name="invitation_token" defaultValue={initialInvitation} required={invitationRequired} autoComplete="off" minLength={40} maxLength={100}/></label><label className="flex items-start gap-2 text-xs text-muted-foreground"><input type="checkbox" name="accept_terms" value="accepted" required className="mt-0.5"/><span>I accept the <Link href="/terms" className="underline">Terms of Service</Link> and have reviewed the <Link href="/privacy" className="underline">Privacy Policy</Link>.</span></label></>}
  <button className="pb-auth-google-btn justify-center w-full" type="submit" disabled={pending}>{pending?'Please wait…':label||({login:'Sign in with email',signup:'Create account with email',verify:'Verify email and continue',recovery:'Send recovery link',reset:'Change password',resend:'Send a new code'}[kind])}</button>
 </form>;
}
