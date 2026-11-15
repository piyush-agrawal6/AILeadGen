"use client";

import { useActionState } from "react";
import { LoaderCircle, ArrowRight } from "lucide-react";

export type GoogleAction = (
  previous: { error: string | null },
  data: FormData
) => Promise<{ error: string | null }>;

function GoogleMark() {
  return (
    <svg width="19" height="19" viewBox="0 0 24 24" aria-hidden="true" className="shrink-0">
      <path
        fill="#4285F4"
        d="M21.6 12.23c0-.71-.06-1.39-.18-2.05H12v3.87h5.38a4.6 4.6 0 0 1-1.99 3.02v2.51h3.23c1.89-1.74 2.98-4.3 2.98-7.35Z"
      />
      <path
        fill="#34A853"
        d="M12 22c2.7 0 4.96-.9 6.62-2.42l-3.23-2.51c-.9.6-2.04.96-3.39.96-2.6 0-4.81-1.76-5.6-4.12H3.06v2.59A10 10 0 0 0 12 22Z"
      />
      <path
        fill="#FBBC05"
        d="M6.4 13.91a6 6 0 0 1 0-3.82V7.5H3.06a10 10 0 0 0 0 9l3.34-2.59Z"
      />
      <path
        fill="#EA4335"
        d="M12 5.97c1.47 0 2.79.51 3.83 1.52l2.87-2.87A9.62 9.62 0 0 0 12 2a10 10 0 0 0-8.94 5.5l3.34 2.59C7.19 7.73 9.4 5.97 12 5.97Z"
      />
    </svg>
  );
}

export function GoogleForm({
  action,
  label = "Continue with Google",
}: {
  action: GoogleAction;
  label?: string;
}) {
  const [state, submit, pending] = useActionState(action, { error: null });

  return (
    <form
      action={submit}
      className="auth-google-form w-full"
      aria-label="Google sign-in"
      aria-busy={pending}
    >
      {state.error && (
        <p className="auth-error pb-auth-alert" role="alert">
          {state.error}
        </p>
      )}
      <button
        type="submit"
        className="auth-google-button pb-auth-google-btn"
        disabled={pending}
      >
        {pending ? (
          <LoaderCircle className="auth-spinner shrink-0 animate-spin" size={19} />
        ) : (
          <GoogleMark />
        )}
        <span>{pending ? "Connecting to Google…" : label}</span>
        {!pending && (
          <ArrowRight
            size={16}
            className="auth-button-arrow ml-auto text-muted-foreground opacity-70 group-hover:opacity-100"
          />
        )}
      </button>
      <p className="auth-sr-only sr-only" aria-live="polite">
        {pending ? "Opening secure Google sign-in." : ""}
      </p>
    </form>
  );
}
