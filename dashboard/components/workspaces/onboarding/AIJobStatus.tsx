'use client';
import React, { useState } from 'react';
import { AlertCircle, CheckCircle2, RefreshCw, Sparkles } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { deriveJobStatus, reviewFailure, type Review } from './types';

export function AIJobStatus({
  kind,
  query,
  onControl,
  onFreshRun
}: {
  kind: 'company' | 'icp';
  query: { data?: Review; error: Error | null; refetch: () => Promise<unknown> };
  onControl: (action: 'CANCEL' | 'RETRY') => Promise<void>;
  onFreshRun?: () => Promise<void>;
}) {
  const [busy, setBusy] = useState(false);
  const [ctrlErr, setCtrlErr] = useState('');
  const review = query.data;

  async function handleControl(action: 'CANCEL' | 'RETRY') {
    setBusy(true);
    setCtrlErr('');
    try {
      await onControl(action);
    } catch (e) {
      setCtrlErr((e as Error).message);
    } finally {
      setBusy(false);
    }
  }

  if (!review && !query.error) return null;

  const derived = deriveJobStatus(review, kind);
  const isFailed = derived.isFailed;
  const isRunning = derived.isBusy;
  const isReady = derived.isSuccess;

  return (
    <div
      className={`pb-progress-card ${isRunning ? 'is-busy' : isFailed ? 'is-failed' : isReady ? 'is-ready' : ''}`}
      role={isFailed ? 'alert' : 'status'}
      aria-live="polite"
    >
      <div className="flex items-start justify-between gap-3">
        <div className="flex items-start gap-2.5 min-w-0">
          {isFailed ? (
            <AlertCircle size={16} className="text-destructive flex-shrink-0 mt-0.5" aria-hidden="true" />
          ) : isReady ? (
            <CheckCircle2 size={16} className="text-primary flex-shrink-0 mt-0.5" aria-hidden="true" />
          ) : (
            <Sparkles size={16} className="pb-spin-gentle text-[#6b56a6] dark:text-[#c4b5fd] flex-shrink-0 mt-0.5" aria-hidden="true" />
          )}
          <div className="min-w-0">
            <strong className="text-xs font-semibold text-foreground block">
              {query.error ? 'Could not refresh status' : derived.stageName}
            </strong>
            <p className="text-xs text-muted-foreground mt-0.5 leading-relaxed">
              {isFailed
                ? reviewFailure(review?.error_code)
                : isRunning
                  ? 'Progress is saved automatically. You can stay on this page or return later.'
                  : kind === 'icp'
                    ? 'Review the 5 tailored customer segments below and choose your primary ICP.'
                    : 'Extracted from your public website. Edit any field below before saving.'}
            </p>
          </div>
        </div>

        <div className="flex items-center gap-1.5 flex-shrink-0">
          {review?.can_retry && (
            <Button size="sm" variant="outline" disabled={busy} onClick={() => void handleControl('RETRY')}>
              Retry
            </Button>
          )}
          {isFailed && !review?.can_retry && onFreshRun && (
            <Button
              size="sm"
              variant="outline"
              disabled={busy}
              onClick={async () => {
                setBusy(true);
                setCtrlErr('');
                try {
                  await onFreshRun();
                } catch (e) {
                  setCtrlErr((e as Error).message);
                } finally {
                  setBusy(false);
                }
              }}
            >
              Retry with fresh run
            </Button>
          )}
          {isRunning && (
            <Button size="sm" variant="ghost" disabled={busy} onClick={() => void handleControl('CANCEL')}>
              Cancel
            </Button>
          )}
          <button
            type="button"
            className="text-muted-foreground hover:text-foreground p-1.5 rounded-lg"
            onClick={() => void query.refetch()}
            aria-label="Refresh status"
          >
            <RefreshCw size={13} />
          </button>
        </div>
      </div>

      {isRunning && (
        <div className="pb-progress-bar" aria-hidden="true">
          <div className="pb-progress-bar-fill" />
        </div>
      )}

      {ctrlErr && <p className="text-xs text-destructive mt-2">{ctrlErr}</p>}
    </div>
  );
}
