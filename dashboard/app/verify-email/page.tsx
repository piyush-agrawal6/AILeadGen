import Link from 'next/link';
import {AuthState} from '@/components/auth/auth-state';
import {AccountForm} from '@/components/auth/account-form';
import {readAccountCookie,verificationCookie} from '@/lib/server/account-cookies';
import {serverEnv} from '@/lib/server/env';
import {verifyAccount,resendAccountCode} from '../account-actions';
export default async function VerifyEmail(){
 const env=serverEnv(),pending=env.accounts?await readAccountCookie(verificationCookie):null;
 return <AuthState eyebrow="VERIFY YOUR EMAIL" title={pending?'Check your company inbox':'Start a new verification'} description={pending?'Enter the six-digit code sent to your company email. If you already have an account, follow the sign-in guidance in that email.':'Your verification request is unavailable or expired.'}>
  {pending?<><AccountForm action={verifyAccount} kind="verify"/><AccountForm action={resendAccountCode} kind="resend"/><p className="text-xs text-muted-foreground">Codes expire after 10 minutes. Wait one minute before requesting another.</p></>:<Link href="/signup" className="pb-auth-google-btn justify-center">Return to signup</Link>}
  <Link href="/login" className="text-xs underline">Already verified? Sign in</Link>
 </AuthState>;
}
