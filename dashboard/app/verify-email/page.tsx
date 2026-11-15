import type { Metadata } from 'next';
import { ShieldCheck } from 'lucide-react';
import { AuthState } from '@/components/auth/auth-state';
import { GoogleForm } from '@/components/auth/google-form';
import { googleSignIn } from '../login/actions';

export const metadata: Metadata = {
  title: 'Verify your email · PlaneByte',
  description: 'Verified Google OAuth identity verification for PlaneByte.',
};

export default function VerifyEmail() {
  return (
    <AuthState
      eyebrow="EMAIL VERIFICATION"
      title="Verified through Google"
      description="PlaneByte relies on your Google account’s built-in email verification. There are no separate verification codes or unverified email links."
    >
      <div className="rounded-xl border border-border/80 bg-muted/30 p-4 text-left text-xs leading-relaxed space-y-2 mb-4">
        <div className="flex items-center gap-2 font-medium text-foreground">
          <ShieldCheck size={16} className="text-emerald-500 shrink-0" />
          <span>Automatic email verification</span>
        </div>
        <p className="text-muted-foreground">
          When you sign in with Google, Google confirms your verified email address directly with PlaneByte over secure cryptographic tokens.
        </p>
      </div>

      <GoogleForm action={googleSignIn} label="Sign in with verified Google account" />
    </AuthState>
  );
}
