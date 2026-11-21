"use client";
import Link from 'next/link';
import { useState } from 'react';
import { useQueryClient } from '@tanstack/react-query';
import { Check, ChevronsUpDown, Plus, Building2, Settings2 } from 'lucide-react';
import { Menu, MenuContent } from '@/components/ui/menu';
import { request } from '@/lib/intelligence';
import {
  useWorkspace,
  initials,
  clearWorkspaceSessionState,
} from './use-workspace';

export function WorkspaceSwitcher({
  onSelected,
}: {
  onSelected: (id: string) => void;
}) {
  const client = useQueryClient();
  const list = useWorkspace();
  const [pending, setPending] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [open, setOpen] = useState(false);

  async function select(id: string) {
    if (!id || pending || id === list.data?.active_organization_id) return;
    setPending(true);
    setError(null);
    try {
      // Cancel all in-flight queries belonging to the previous workspace before switching
      await client.cancelQueries();
      await request('/organization/active', {
        method: 'PUT',
        body: JSON.stringify({ organization_id: id }),
      });
      clearWorkspaceSessionState();
      client.clear();
      onSelected(id);
    } catch {
      setError('Workspace could not be changed. Please retry.');
    } finally {
      setPending(false);
    }
  }

  if (list.isPending) {
    return (
      <div className="workspace-trigger opacity-70 animate-pulse pointer-events-none" aria-busy="true">
        <span className="workspace-avatar">
          <Building2 size={13} className="text-muted-foreground" />
        </span>
        <span className="workspace-trigger-text text-xs text-muted-foreground">
          Loading…
        </span>
      </div>
    );
  }
  if (list.isError) {
    return (
      <button
        type="button"
        className="workspace-trigger hover:border-primary/40 cursor-pointer"
        onClick={() => void list.refetch()}
        title="Workspace connection failed. Click to retry."
        aria-label="Retry loading workspace"
      >
        <span className="workspace-avatar text-amber-500 bg-amber-500/10">
          <Building2 size={13} />
        </span>
        <span className="workspace-trigger-text text-xs text-muted-foreground">
          Offline · Retry
        </span>
      </button>
    );
  }

  const name = list.active?.name || 'Choose workspace';
  return (
    <div className="relative min-w-0">
      <Menu.Root open={open} onOpenChange={setOpen}>
        <Menu.Trigger asChild>
          <button
            className="workspace-trigger"
            aria-label={'Workspace: ' + name}
            disabled={pending}
            aria-describedby={error ? 'workspace-switch-error' : undefined}
          >
            <span className="workspace-avatar">
              {list.active ? initials(name) : <Building2 size={15} />}
            </span>
            <span className="workspace-trigger-text">
              <strong>{name}</strong>
              <small>
                {pending
                  ? 'Switching workspace…'
                  : list.active?.plan_label || 'Company workspace'}
              </small>
            </span>
            <ChevronsUpDown size={14} className="shrink-0 text-muted-foreground" />
          </button>
        </Menu.Trigger>
        <MenuContent align="end" className="w-80 max-w-[calc(100vw-24px)]">
          <Menu.Label className="px-3 py-2 text-[11px] font-semibold uppercase tracking-wider text-muted-foreground">
            Your workspaces
          </Menu.Label>
          <Menu.RadioGroup
            value={list.data?.active_organization_id || ''}
            onValueChange={(id) => void select(id)}
          >
            {list.data?.items.map((item) => {
              const needsSetup = item.access_state === 'SETUP_REQUIRED';
              return (
                <Menu.RadioItem
                  key={item.organization_id}
                  value={item.organization_id}
                  aria-label={item.name}
                  disabled={pending}
                  className="app-menu-item workspace-option"
                >
                  <span className="workspace-avatar">{initials(item.name)}</span>
                  <span className="min-w-0 flex-1">
                    <strong className="block truncate font-medium">{item.name}</strong>
                    <small className="flex items-center gap-1.5 text-[11px] text-muted-foreground">
                      <span className="capitalize">{item.role.toLowerCase()}</span>
                      <span>·</span>
                      <span>
                        {needsSetup
                          ? `Setup ${item.onboarding_completed_steps ?? 0}/${item.onboarding_total_steps ?? 3}`
                          : item.plan_label || 'Workspace'}
                      </span>
                    </small>
                  </span>
                  <Menu.ItemIndicator>
                    <Check size={15} />
                  </Menu.ItemIndicator>
                </Menu.RadioItem>
              );
            })}
          </Menu.RadioGroup>
          {!list.data?.items.length && (
            <p className="px-3 py-2 text-sm text-muted-foreground">
              Create a workspace for your company or accept a team invitation.
            </p>
          )}
          <Menu.Separator className="app-menu-separator" />
          <Menu.Item asChild className="app-menu-item">
            <Link href="/settings/workspaces">
              <Settings2 size={15} />
              <span>Manage workspaces</span>
            </Link>
          </Menu.Item>
          <Menu.Item asChild className="app-menu-item">
            <Link href="/settings/workspaces?create=1">
              <Plus size={15} />
              <span>Create workspace</span>
            </Link>
          </Menu.Item>
        </MenuContent>
      </Menu.Root>
      {error && (
        <p id="workspace-switch-error" role="alert" className="workspace-error">
          {error}
        </p>
      )}
    </div>
  );
}
