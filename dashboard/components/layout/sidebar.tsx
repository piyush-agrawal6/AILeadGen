"use client";
import Link from 'next/link';
import { useState } from 'react';
import { usePathname } from 'next/navigation';
import * as Tooltip from '@radix-ui/react-tooltip';
import {
  Activity,
  Bookmark,
  Building2,
  CalendarClock,
  CheckCircle2,
  Gauge,
  Inbox,
  LifeBuoy,
  List,
  ListTodo,
  Network,
  Plug,
  Radar,
  Radio,
  Search,
  Settings2,
  Sparkles,
  Target,
  Users,
  type LucideIcon,
} from 'lucide-react';
import { PlaneByteBrand } from '@/components/auth/brand';
import { brand } from '@/lib/brand';
import { request } from '@/lib/intelligence';
import { useWorkspaceManagement, useWorkspaceCapabilities } from '@/components/workspaces/features';
import { useWorkspace } from '@/components/workspaces/use-workspace';
import { useProducts } from '@/components/workspaces/use-products';
import { isLeadEnginePage } from '@/lib/product-availability';
import { TrialUsageCard } from './TrialUsageCard';

type Item = { href: string; title: string; icon: LucideIcon };

function SidebarSetupShortcut({
  path,
  collapsed,
  mobile,
  onNavigate,
}: {
  path: string;
  collapsed: boolean;
  mobile: boolean;
  onNavigate?: () => void;
}) {
  const workspace = useWorkspace(true);
  const [resumingSetup, setResumingSetup] = useState(false);

  const showSetupShortcut = Boolean(
    workspace.data?.active_organization_id &&
      workspace.data.active_onboarding_status &&
      workspace.data.active_onboarding_status !== 'COMPLETED'
  );
  if (!showSetupShortcut) return null;

  const completedSteps = Math.max(0, Math.min(4, workspace.active?.onboarding_completed_steps ?? 0));
  const totalSteps = workspace.active?.onboarding_total_steps ?? 5;

  async function openSetup() {
    if (resumingSetup) return;
    setResumingSetup(true);
    try {
      if (workspace.data?.active_onboarding_deferred) {
        await request('/organization/onboarding/resume', { method: 'POST', body: '{}' });
      }
    } catch {
      // Navigate to onboarding regardless so saved step loads cleanly
    } finally {
      setResumingSetup(false);
      onNavigate?.();
      window.location.assign('/onboarding');
    }
  }

  const setupButton = (
    <button
      type="button"
      onClick={() => void openSetup()}
      disabled={resumingSetup}
      aria-label={`Workspace setup progress: ${completedSteps} of ${totalSteps}`}
      className={
        'shell-nav-link w-full text-left justify-between ' +
        (path.startsWith('/onboarding') ? 'is-active' : '')
      }
    >
      <span className="flex items-center gap-2.5 min-w-0">
        <CheckCircle2 size={17} className="text-primary shrink-0" />
        <span className="shell-nav-label truncate">Setup</span>
      </span>
      <span className="shell-nav-label rounded-full bg-primary/10 px-2 py-0.5 text-[10px] font-semibold tabular-nums text-primary shrink-0">
        {completedSteps}/{totalSteps}
      </span>
    </button>
  );

  return collapsed && !mobile ? (
    <Tooltip.Root>
      <Tooltip.Trigger asChild>{setupButton}</Tooltip.Trigger>
      <Tooltip.Portal>
        <Tooltip.Content className="nav-tooltip" side="right" sideOffset={12}>
          Setup · {completedSteps}/{totalSteps}
          <Tooltip.Arrow />
        </Tooltip.Content>
      </Tooltip.Portal>
    </Tooltip.Root>
  ) : (
    <div>{setupButton}</div>
  );
}

export function Sidebar({
  collapsed = false,
  onNavigate,
  mobile = false,
}: {
  collapsed?: boolean;
  onNavigate?: () => void;
  mobile?: boolean;
}) {
  const path = usePathname();
  const management = useWorkspaceManagement();
  const capabilities = useWorkspaceCapabilities();
  const products = useProducts();

  const leadAvailable = capabilities.leadEngineAvailable !== false;
  const isLeadPage = leadAvailable && (path === '/' || isLeadEnginePage(path));
  const radar = !isLeadPage;

  const groups: { name: string; items: Item[] }[] = [
    {
      name: 'Prospecting',
      items: [
        { href: '/lead-engine', title: 'Overview', icon: Gauge },
        { href: '/find-leads', title: 'Find Leads', icon: Search },
        { href: '/leads', title: 'Companies', icon: Building2 },
        { href: '/contacts', title: 'Contacts', icon: Users },
        { href: '/enrichment', title: 'Enrichment', icon: Sparkles },
        ...(management ? [{ href: '/settings/icp', title: 'Ideal customers', icon: Target }] : []),
      ],
    },
    {
      name: 'Sales',
      items: [
        { href: '/lists', title: 'Lists', icon: List },
        { href: '/tasks', title: 'Tasks', icon: ListTodo },
        { href: '/campaigns', title: 'Campaigns', icon: Radar },
        { href: '/outreach', title: 'Outreach', icon: Inbox },
        { href: '/schedules', title: 'Schedules', icon: CalendarClock },
      ],
    },
    ...(management
      ? [
          {
            name: 'Intelligence',
            items: [
              { href: '/recommendations', title: 'Recommendations', icon: Sparkles },
              ...(capabilities.leadAssistant ? [{ href: '/assistant', title: 'AI Assistant', icon: Sparkles }] : []),
            ],
          },
        ]
      : []),
    ...(capabilities.customerIntegrations
      ? [{ name: 'Tools', items: [{ href: '/settings/integrations', title: 'Connections', icon: Plug }] }]
      : []),
  ];

  const radarGroups: { name: string; items: Item[] }[] = [
    {
      name: 'Workspace',
      items: [
        { href: '/intent-radar', title: 'Home', icon: Gauge },
        { href: '/intent-radar/discover', title: 'Discover', icon: Search },
        { href: '/intent-radar/signals', title: 'Signals', icon: Activity },
        { href: '/intent-radar/opportunities', title: 'Opportunities', icon: Target },
        { href: '/intent-radar/monitors', title: 'Monitoring', icon: Radio },
      ],
    },
    {
      name: 'Intelligence',
      items: [
        { href: '/intent-radar/ideal-customers', title: 'Ideal Customers', icon: Users },
        ...(products.data?.intent_radar?.growth_enabled === false
          ? []
          : [{ href: '/intent-radar/growth', title: 'Growth Intelligence', icon: Sparkles }]),
        { href: '/intent-radar/saved', title: 'Research Library', icon: Bookmark },
        { href: '/intent-radar/integrations', title: 'Integrations', icon: Plug },
      ],
    },
  ];

  function active(href: string) {
    if (path === href) return true;
    if (href === '/intent-radar') return path === '/intent-radar';
    if (href === '/') return path === '/';
    if (href === '/settings') {
      return path.startsWith('/settings') || path.startsWith('/account') || path.startsWith('/billing');
    }
    if (href === '/help') {
      return path.startsWith('/help');
    }
    if (href === '/campaigns') {
      return /^\/(?:scans|discovery)\/\d+/.test(path);
    }
    return path.startsWith(href + '/');
  }

  function item({ href, title, icon: Icon }: Item) {
    const link = (
      <Link
        href={href}
        onClick={onNavigate}
        aria-label={title}
        aria-current={active(href) ? 'page' : undefined}
        className={'shell-nav-link ' + (active(href) ? 'is-active' : '')}
      >
        <Icon size={18} />
        <span className="shell-nav-label">{title}</span>
      </Link>
    );
    return collapsed && !mobile ? (
      <Tooltip.Root key={href}>
        <Tooltip.Trigger asChild>{link}</Tooltip.Trigger>
        <Tooltip.Portal>
          <Tooltip.Content className="nav-tooltip" side="right" sideOffset={12}>
            {title}
            <Tooltip.Arrow />
          </Tooltip.Content>
        </Tooltip.Portal>
      </Tooltip.Root>
    ) : (
      <div key={href}>{link}</div>
    );
  }

  return (
    <aside
      className={
        'shell-sidebar ' +
        (collapsed && !mobile ? 'is-collapsed' : '') +
        (mobile ? ' is-mobile' : '')
      }
      aria-label="Product navigation"
    >
      <Link href="/intent-radar" className="shell-brand" onClick={onNavigate} aria-label="PlaneByte Intent Radar">
        <PlaneByteBrand compact />
        <span className="shell-nav-label font-semibold">{brand.name}</span>
      </Link>

      <nav aria-label="Main navigation" className="shell-nav">
        {(radar
          ? products.data && products.data.intent_radar.enabled === false
            ? []
            : radarGroups
          : products.data && products.data.lead_engine === false
            ? []
            : groups
        ).map((group) => (
            <section key={group.name} className="shell-nav-group">
              <p className="shell-nav-heading">{group.name}</p>
              {group.items.map(item)}
            </section>
          )
        )}
      </nav>

      {/* Trial & Real Usage Card */}
      <TrialUsageCard collapsed={collapsed} mobile={mobile} />

      <nav aria-label="Workspace settings" className="shell-nav shell-nav-bottom">
        {management && (
          <SidebarSetupShortcut
            path={path}
            collapsed={collapsed}
            mobile={mobile}
            onNavigate={onNavigate}
          />
        )}
        {[
          { href: '/settings', title: 'Settings', icon: Settings2 },
          { href: '/help', title: 'Help & support', icon: LifeBuoy },
        ].map(item)}
      </nav>
    </aside>
  );
}
