import Link from 'next/link';
import { ArrowLeft } from 'lucide-react';
import { AuthFrame } from './auth-frame';

export function AuthState({
  eyebrow,
  title,
  description,
  children,
  wide = false,
}: {
  eyebrow?: string;
  title: string;
  description: string;
  children?: React.ReactNode;
  wide?: boolean;
}) {
  return (
    <AuthFrame>
      <section className={`auth-form-content auth-state w-full ${wide ? 'max-w-xl' : ''}`}>
        {eyebrow && (
          <p className="text-[11px] font-semibold tracking-wider uppercase text-primary/80 mb-2">
            {eyebrow}
          </p>
        )}
        <h2 className="pb-auth-title">{title}</h2>
        <p className="pb-auth-subtitle">{description}</p>

        <div className="space-y-4 my-5 w-full">{children}</div>

        <div className="pt-4 border-t border-border/60 text-center">
          <Link
            className="auth-back inline-flex items-center justify-center gap-2 text-xs font-medium text-muted-foreground hover:text-foreground transition-colors py-2 px-3 rounded-lg hover:bg-muted/40"
            href="/login"
          >
            <ArrowLeft size={14} />
            <span>Back to sign in</span>
          </Link>
        </div>
      </section>
    </AuthFrame>
  );
}
