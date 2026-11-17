'use client';
import {useActionState,useEffect,useState} from 'react';
import {rememberInvitation} from '@/app/account-actions';
export function InvitationEntry(){
 const [token,setToken]=useState(''),[state,submit,pending]=useActionState(rememberInvitation,{error:null});
 useEffect(()=>{const value=window.location.hash.slice(1);if(/^[A-Za-z0-9_-]{40,100}$/.test(value)){setToken(value);window.history.replaceState(null,'',window.location.pathname)}},[]);
 return <form action={submit} className="space-y-3 text-left">{state.error&&<p role="alert" className="pb-auth-alert">{state.error}</p>}<label className="block text-xs font-medium">Private invitation code<input className="control mt-1 w-full" name="invitation_token" autoComplete="off" minLength={40} maxLength={100} required value={token} onChange={e=>setToken(e.target.value)}/></label><button className="pb-auth-google-btn justify-center w-full" disabled={pending}>{pending?'Preparing…':'Continue with this invitation'}</button></form>;
}
