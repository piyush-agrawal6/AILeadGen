import { Suspense } from 'react';
import { notFound } from 'next/navigation';
import { WorkspacesManager } from '@/components/workspaces/workspaces-manager';

export default function WorkspacesPage() {
  if (process.env.HEYSOW_WORKSPACE_MANAGEMENT_ENABLED !== 'true') notFound();
  return (
    <Suspense fallback={<div className="h-44 rounded-2xl border border-border bg-muted/30 animate-pulse" />}>
      <WorkspacesManager />
    </Suspense>
  );
}
