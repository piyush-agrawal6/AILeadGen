'use client';
import { useActionState, useEffect, useState } from 'react';
import Link from 'next/link';
import { exportAccountDetails, listPrivacyRequests, submitPrivacyRequest } from '@/app/account-security-actions';
import { Button } from '@/components/ui/button';

type RecordedRequest = {
  id: string;
  kind: string;
  status: string;
  created_at: string;
  ordinary_data_due_at?: number | null;
  backup_target_at?: number | null;
};

export function PrivacyControls() {
  const [state, submit, pending] = useActionState(submitPrivacyRequest, { error: null });
  const [message, setMessage] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [history, setHistory] = useState<RecordedRequest[]>([]);

  async function loadHistory() {
    try {
      const items = await listPrivacyRequests();
      setHistory(items as RecordedRequest[]);
    } catch {
      // Keep UI resilient if unauthenticated in test context
    }
  }

  useEffect(() => {
    void loadHistory();
  }, [state.message]);

  async function download() {
    setBusy(true);
    setMessage(null);
    try {
      const value = await exportAccountDetails();
      if (!value) {
        setMessage('Account export could not be loaded. Sign in again or contact support.');
        return;
      }
      const url = URL.createObjectURL(new Blob([JSON.stringify(value, null, 2)], { type: 'application/json' }));
      const link = document.createElement('a');
      link.href = url;
      link.download = 'planebyte-account.json';
      link.click();
      URL.revokeObjectURL(url);
    } catch {
      setMessage('Account export could not be loaded. Please retry.');
    } finally {
      setBusy(false);
    }
  }

  return (
    <section className="rounded-xl border bg-card p-5 space-y-4">
      <div className="space-y-1">
        <h3 className="text-sm font-semibold">Your data, privacy &amp; account deletion</h3>
        <p className="text-xs text-muted-foreground leading-relaxed">
          Download your personal account details in JSON format, submit an audited export/deletion/erasure request, or manage connected integrations.
        </p>
      </div>

      <div className="flex flex-wrap items-center gap-2.5">
        <Button type="button" variant="outline" size="sm" disabled={busy} onClick={() => void download()}>
          Download account details
        </Button>
        <Link href="/settings?category=integrations" className="text-xs text-primary underline underline-offset-2">
          Manage &amp; revoke connected sources
        </Link>
        <Link href="/data-deletion" className="text-xs text-muted-foreground hover:text-foreground underline underline-offset-2">
          Data Deletion Policy
        </Link>
        <Link href="/privacy" className="text-xs text-muted-foreground hover:text-foreground underline underline-offset-2">
          Privacy Policy
        </Link>
      </div>

      {message && <p role="status" className="text-sm">{message}</p>}

      <form action={submit} className="space-y-3 pt-2 border-t border-border/70">
        {state.error && <p role="alert" className="text-sm text-destructive">{state.error}</p>}
        {state.message && <p role="status" className="text-sm text-primary">{state.message}</p>}

        <label className="block text-xs font-medium">
          Data request
          <select name="kind" className="mt-1 block w-full rounded-lg border bg-background p-2 text-sm">
            <option value="EXPORT">Full data export</option>
            <option value="CLOSE_AND_DELETE">Close account &amp; request deletion</option>
            <option value="ERASURE">Review a personal-data erasure request</option>
          </select>
        </label>

        <label className="flex items-start gap-2 text-xs text-muted-foreground leading-relaxed">
          <input type="checkbox" name="confirmed" value="yes" required className="mt-0.5" />
          <span>
            I request a support review. This does not immediately close a workspace, delete data, or issue a refund.
            Other users’ data and legally retained billing, security, or suppression records require separate review.
          </span>
        </label>

        <Button type="submit" variant="outline" size="sm" disabled={pending}>
          {pending ? 'Recording request…' : 'Submit data request'}
        </Button>
      </form>

      {history.length > 0 && (
        <div className="pt-3 border-t border-border/70 space-y-2">
          <h4 className="text-xs font-semibold text-foreground">Recorded privacy requests</h4>
          <ul className="space-y-1.5 text-xs">
            {history.slice(0, 5).map(item => (
              <li key={item.id} className="flex flex-wrap items-center justify-between gap-2 rounded-lg bg-muted/30 px-3 py-2">
                <span className="font-medium text-foreground">{item.kind.replace(/_/g, ' ')}</span>
                <span className="text-muted-foreground font-mono text-[11px]">{item.id.slice(0, 8)}</span>
                <span className="rounded-full bg-primary/10 px-2 py-0.5 text-[11px] font-medium text-primary">
                  {item.status}
                </span>
              </li>
            ))}
          </ul>
        </div>
      )}
    </section>
  );
}
