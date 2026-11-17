import Link from 'next/link';
import {AccountForm} from '@/components/auth/account-form';
import {passwordSignIn} from '../account-actions';
import {serverEnv} from '@/lib/server/env';
import { ShieldCheck, AlertCircle } from 'lucide-react';
import type { Metadata } from 'next';
import { AuthFrame } from '@/components/auth/auth-frame';
import { GoogleForm } from '@/components/auth/google-form';
import { authenticationError } from '@/lib/auth-experience';
import { googleSignIn } from './actions';

export const metadata: Metadata = {
  title: 'Sign in · PlaneByte',
  description: 'Sign in to your PlaneByte workspace securely.',
};

export default async function Login({
  searchParams,
}: {
  searchParams: Promise<{ error?: string | string[] }>;
}) {
  const env=serverEnv();
  const params = await searchParams;
  const rawError = typeof params.error === 'string' ? params.error : undefined;
  const error = authenticationError(rawError);

  return (
    <AuthFrame>
      <div className="w-full">
        <h2 className="pb-auth-title">Welcome back</h2>
        <p className="pb-auth-subtitle">
          {env.accounts?'Sign in with your company email or verified Google account.':'Sign in to your PlaneByte workspace with your verified Google account.'}
        </p>

        {error && (
          <div className="pb-auth-alert auth-error" role="alert">
            <AlertCircle className="w-4 h-4 shrink-0 mt-0.5 text-red-500" />
            <div>
              <p className="font-semibold text-xs">Authentication Notice</p>
              <p className="mt-0.5 text-xs opacity-90">{error}</p>
            </div>
          </div>
        )}

        <GoogleForm action={googleSignIn} />
        {env.accounts&&<><div className="pb-auth-divider"><span>or use email</span></div><AccountForm action={passwordSignIn} kind="login"/></>}

        <div className="pb-auth-security-note auth-signin-note">
          <ShieldCheck size={14} className="text-emerald-500 shrink-0" />
          <span>Secure sign-in. Your Google password stays with Google.</span>
        </div>

        <div className="pb-auth-divider">
          <span>or</span>
        </div>

        <div className="pb-auth-links-row auth-form-links">
          <Link href="/forgot-password" className="text-xs hover:underline">
            Forgot password?
          </Link>
          <span className="text-muted-foreground/40">•</span>
          <Link href="/signup" className="text-xs hover:underline inline-flex items-center gap-0.5">
            <span>{env.accounts?'Create an account':'Request access'}</span>
            <span aria-hidden="true">↗</span>
          </Link>
        </div>

        <p className="pb-auth-fineprint auth-fineprint">
          Before continuing, review our{' '}
          <Link href="/terms">Terms of Service</Link> and{' '}
          <Link href="/privacy">Privacy Policy</Link>.
        </p>
      </div>
    </AuthFrame>
  );
}
