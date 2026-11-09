import Link from 'next/link';
import {ShieldCheck} from 'lucide-react';
import type {Metadata} from 'next';
import {AuthFrame} from '@/components/auth/auth-frame';
import {GoogleForm} from '@/components/auth/google-form';
import {authenticationError} from '@/lib/auth-experience';
import {googleSignIn} from './actions';
export const metadata:Metadata={title:'Sign in · PlaneByte'};
export default async function Login({searchParams}:{searchParams:Promise<{error?:string|string[]}>}){
 const params=await searchParams;const error=authenticationError(typeof params.error==='string'?params.error:undefined);
 return <AuthFrame><div className="auth-form-content"><p className="auth-form-eyebrow">YOUR WORKSPACE, CONNECTED</p><h2>Welcome back</h2><p className="auth-form-subtitle">Sign in to your PlaneByte workspace.</p>{error&&<p className="auth-error" role="alert">{error}</p>}<GoogleForm action={googleSignIn}/><div className="auth-signin-note"><ShieldCheck size={16}/><span>Secure sign-in. Your Google password stays with Google.</span></div><div className="auth-form-links"><Link href="/forgot-password">Trouble signing in?</Link></div><p className="auth-new-account">New to PlaneByte? <Link href="/signup">Request access <span aria-hidden="true">↗</span></Link></p><div className="auth-fineprint">Before continuing, review our <Link href="/terms">Terms of Service</Link> and <Link href="/privacy">Privacy Policy</Link>.</div></div></AuthFrame>;
}
