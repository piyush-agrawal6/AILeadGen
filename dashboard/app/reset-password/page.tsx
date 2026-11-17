import {AccountForm} from '@/components/auth/account-form';
import {resetAccountPassword} from '../account-actions';
import {serverEnv} from '@/lib/server/env';
import type { Metadata } from 'next';
import Link from 'next/link';
import { ArrowRight, ExternalLink, ShieldCheck } from 'lucide-react';
import { AuthState } from '@/components/auth/auth-state';

export const metadata: Metadata = {
  title: 'Password Management · PlaneByte',
  description: 'Recover access to your PlaneByte account securely.',
};

export default async function ResetPassword({searchParams}:{searchParams:Promise<{token?:string}>}) {
 const token=(await searchParams).token;
 if(serverEnv().accounts)return <AuthState eyebrow="ACCOUNT SECURITY" title="Choose a new password" description="This one-time recovery link expires after 20 minutes. Changing your password signs out existing customer sessions.">{typeof token==='string'&&/^[A-Za-z0-9_-]{43}$/.test(token)?<AccountForm action={resetAccountPassword} kind="reset" token={token}/>:<p role="alert">This reset link is invalid. Request a new recovery email.</p>}<Link href="/login" className="pb-auth-google-btn justify-center">Return to sign in</Link></AuthState>;
  return (
    <AuthState
      eyebrow="ACCOUNT SECURITY"
      title="Single sign-on with Google"
      description="PlaneByte uses Google OAuth for secure single sign-on. Your password is never stored or managed by PlaneByte."
    >
      <div className="rounded-xl border border-border/80 bg-muted/30 p-4 text-left text-xs leading-relaxed space-y-2">
        <div className="flex items-center gap-2 font-medium text-foreground">
          <ShieldCheck size={16} className="text-emerald-500 shrink-0" />
          <span>Zero passwords stored</span>
        </div>
        <p className="text-muted-foreground">
          Because authentication is handled entirely through Google, you don’t have a separate PlaneByte password. To reset or recover your Google password, use Google’s secure account settings.
        </p>
      </div>

      <div className="flex flex-col gap-3 pt-2">
        <Link
          href="/login"
          className="pb-auth-google-btn justify-center bg-primary text-primary-foreground hover:bg-primary/90 border-transparent text-center font-medium shadow-sm py-2.5"
        >
          <span>Return to sign in</span>
          <ArrowRight size={15} />
        </Link>
        <a
          href="https://accounts.google.com/signin/recovery"
          target="_blank"
          rel="noopener noreferrer"
          className="pb-auth-google-btn justify-center border-border bg-card text-foreground hover:bg-muted/50 text-center font-medium py-2.5"
        >
          <span>Open Google Account Recovery</span>
          <ExternalLink size={14} className="opacity-70" />
        </a>
      </div>
    </AuthState>
  );
}
