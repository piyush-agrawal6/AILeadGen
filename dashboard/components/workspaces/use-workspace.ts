"use client";
import { useQuery } from '@tanstack/react-query';
import { request } from '@/lib/intelligence';
import type { WorkspaceAccessState } from '@/lib/intent-radar';

export type Membership = {
  id?: string;
  organization_id: string;
  name: string;
  slug?: string;
  role: 'OWNER' | 'ADMIN' | 'MEMBER' | 'VIEWER';
  status?: string;
  created_at?: string;
  plan_label?: string | null;
  plan_status?: string | null;
  access_state?: WorkspaceAccessState | null;
  onboarding_status?: string | null;
  onboarding_completed_steps?: number | null;
  onboarding_total_steps?: number | null;
  next_setup_step?: string | null;
  member_count?: number | null;
};

export type WorkspaceSummary = {
  items: Membership[];
  active_organization_id: string | null;
  active_onboarding_status: string | null;
  active_onboarding_deferred?: boolean;
  active_is_internal?: boolean;
};

export function useWorkspace(enabled = true) {
  const query = useQuery({
    queryKey: ['account-workspaces'],
    queryFn: () => request<WorkspaceSummary>('/organization/workspaces'),
    enabled,
    retry: false,
  });
  const items = Array.isArray(query.data?.items) ? query.data.items : [];
  const active = items.find(
    (item) => item.organization_id === query.data?.active_organization_id
  );
  return {
    ...query,
    active,
    canManage: active?.role === 'OWNER' || active?.role === 'ADMIN',
    isInternal: query.data?.active_is_internal === true,
  };
}

export function clearWorkspaceSessionState() {
  if (typeof window === 'undefined') return;
  try {
    const keysToClear = [
      'pb_ai_assistant_draft',
      'planebyte:discovery-history-return',
      'planebyte:discovery-preload',
      'planebyte:signals-return',
    ];
    for (const k of keysToClear) {
      window.sessionStorage.removeItem(k);
    }
  } catch {
    // Ignore storage unavailability
  }
}

export function initials(name: string) {
  return (
    name
      .trim()
      .split(/\s+/)
      .filter(Boolean)
      .slice(0, 2)
      .map((word) => word.replace(/[^\p{L}\p{N}]/gu, '').slice(0, 1))
      .join('')
      .toUpperCase() || 'W'
  );
}
