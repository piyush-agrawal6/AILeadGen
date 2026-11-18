"use client";
import Link from 'next/link';
import { useTheme } from 'next-themes';
import { useQuery } from '@tanstack/react-query';
import { signOut } from 'next-auth/react';
import {
  Building2,
  Check,
  ChevronRight,
  CreditCard,
  LifeBuoy,
  LogOut,
  Monitor,
  Moon,
  Sun,
  Users,
} from 'lucide-react';
import { Menu, MenuContent } from '@/components/ui/menu';
import { request } from '@/lib/intelligence';
import { initials, useWorkspace } from '@/components/workspaces/use-workspace';

export type UserIdentity = { name?: string | null; email?: string | null; image?: string | null };

export function AppearanceOptions() {
  const { theme, setTheme } = useTheme();
  return (
    <Menu.RadioGroup value={theme || 'light'} onValueChange={setTheme}>
      {[
        { value: 'light', label: 'Light', icon: Sun },
        { value: 'dark', label: 'Dark', icon: Moon },
        { value: 'system', label: 'Use system setting', icon: Monitor },
      ].map(({ value, label, icon: Icon }) => (
        <Menu.RadioItem value={value} key={value} className="app-menu-item">
          <Icon size={15} />
          {label}
          <Menu.ItemIndicator className="ml-auto">
            <Check size={14} />
          </Menu.ItemIndicator>
        </Menu.RadioItem>
      ))}
    </Menu.RadioGroup>
  );
}

export function AccountMenu({
  user,
  workspaceManagementEnabled,
}: {
  user: UserIdentity;
  workspaceManagementEnabled: boolean;
}) {
  const profile = useQuery({
    queryKey: ['account-profile'],
    queryFn: () => request<{ display_name: string; email: string }>('/profile'),
    enabled: workspaceManagementEnabled,
    retry: false,
  });
  const workspace = useWorkspace(workspaceManagementEnabled);
  const { theme } = useTheme();
  const ThemeIcon = theme === 'dark' ? Moon : theme === 'system' ? Monitor : Sun;

  const name =
    profile.data?.display_name || user.name || user.email?.split('@')[0] || 'Your account';
  const email = profile.data?.email || user.email;
  const activeOrgName = workspace.active?.name;
  const activeRole = workspace.active?.role;

  return (
    <Menu.Root>
      <Menu.Trigger asChild>
        <button className="account-trigger" aria-label="Account menu">
          <span className="account-avatar">{initials(name)}</span>
        </button>
      </Menu.Trigger>
      <MenuContent align="end" className="w-64 min-w-[252px]">
        {/* User Identity Header */}
        <Menu.Label className="app-menu-identity">
          <div className="flex items-center gap-3">
            <span className="account-avatar shrink-0 text-xs font-semibold">
              {initials(name)}
            </span>
            <div className="min-w-0 flex-1">
              <span className="block truncate text-sm font-semibold text-foreground">
                {name}
              </span>
              {email && (
                <span className="block truncate text-xs text-muted-foreground">
                  {email}
                </span>
              )}
              {activeOrgName && (
                <div className="mt-1 flex items-center gap-1.5 text-[11px] text-muted-foreground">
                  <span className="h-1.5 w-1.5 shrink-0 rounded-full bg-emerald-500" />
                  <span className="truncate">{activeOrgName}</span>
                  {activeRole && (
                    <span className="shrink-0 rounded bg-muted px-1.5 py-0.5 text-[10px] font-semibold uppercase tracking-wider text-muted-foreground">
                      {activeRole.toLowerCase()}
                    </span>
                  )}
                </div>
              )}
            </div>
          </div>
        </Menu.Label>

        <Menu.Separator className="app-menu-separator" />

        {/* Workspace & Billing Navigation */}
        {workspaceManagementEnabled && (
          <>
            <Menu.Item asChild className="app-menu-item">
              <Link href="/settings?category=company">
                <Building2 size={15} />
                <span>Workspace settings</span>
              </Link>
            </Menu.Item>
            <Menu.Item asChild className="app-menu-item">
              <Link href="/settings?category=team">
                <Users size={15} />
                <span>Team & members</span>
              </Link>
            </Menu.Item>
          </>
        )}

        <Menu.Item asChild className="app-menu-item">
          <Link href="/settings?category=billing&tab=overview">
            <CreditCard size={15} />
            <span>Billing & usage</span>
          </Link>
        </Menu.Item>

        <Menu.Separator className="app-menu-separator" />

        {/* Appearance & Help */}
        <Menu.Sub>
          <Menu.SubTrigger className="app-menu-item">
            <ThemeIcon size={15} />
            <span>Appearance</span>
            <ChevronRight size={14} className="ml-auto" />
          </Menu.SubTrigger>
          <Menu.Portal>
            <Menu.SubContent sideOffset={5} collisionPadding={12} className="app-menu min-w-48">
              <AppearanceOptions />
            </Menu.SubContent>
          </Menu.Portal>
        </Menu.Sub>

        <Menu.Item asChild className="app-menu-item">
          <Link href="/help">
            <LifeBuoy size={15} />
            <span>Help & support</span>
          </Link>
        </Menu.Item>

        <Menu.Separator className="app-menu-separator" />

        {/* Session Sign out */}
        <Menu.Item
          className="app-menu-item text-red-600 dark:text-red-400 focus:text-red-600 dark:focus:text-red-400"
          onSelect={() => void signOut({ callbackUrl: '/login' })}
        >
          <LogOut size={15} />
          <span>Sign out</span>
        </Menu.Item>
      </MenuContent>
    </Menu.Root>
  );
}
