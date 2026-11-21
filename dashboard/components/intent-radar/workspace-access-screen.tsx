"use client";

import Link from "next/link";
import { useState } from "react";
import { useRouter,usePathname } from "next/navigation";
import {CustomerIntegrationsCatalog} from './integrations/CustomerIntegrationsCatalog';
import { useQueryClient } from "@tanstack/react-query";
import {
  ArrowRight,
  Building2,
  Clock,
  CreditCard,
  Lock,
  RefreshCw,
  Sparkles,
} from "lucide-react";
import type { ProductAccess } from "@/lib/intent-radar";
import { request } from "@/lib/intelligence";
import { useWorkspace } from "@/components/workspaces/use-workspace";
import { Button } from "@/components/ui/button";

export function WorkspaceAccessScreen({ access }: { access: ProductAccess }) {
  const router = useRouter();
  const path=usePathname();
  const client = useQueryClient();
  const workspace = useWorkspace();
  const [resuming, setResuming] = useState(false);

  const radar = access.intent_radar;
  const state = radar.access_state || (radar.onboarding_status !== "COMPLETED" ? "SETUP_REQUIRED" : "RESTRICTED");
  const orgName = workspace.active?.name || "this workspace";
  const isOwner = workspace.active?.role === "OWNER";
  const account = workspace.active?.billing_account;
  const canActivate = isOwner && (!account || (account.can_manage && !account.shared));
  const completedSteps = workspace.active?.onboarding_completed_steps ?? 0;

  async function continueOnboarding() {
    if (resuming) return;
    setResuming(true);
    try {
      await request("/organization/onboarding/resume", { method: "POST", body: "{}" });
      await client.invalidateQueries({ queryKey: ["account-workspaces"] });
    } catch {
      // Navigate regardless so user lands on saved step
    } finally {
      setResuming(false);
      router.push("/onboarding");
    }
  }

  const copy = (() => {
    switch (state) {
      case "SETUP_REQUIRED":
        return {
          icon: Sparkles,
          badge: `Setup · ${completedSteps}/${workspace.active?.onboarding_total_steps ?? 3} steps`,
          title: `Finish setting up ${orgName}`,
          description:
            "Review your business, choose your ideal customers, and prepare your first discovery.",
          primaryLabel: resuming ? "Opening setup…" : "Continue Onboarding",
          primaryHref: null as string | null,
          onPrimary: continueOnboarding,
          secondaryLabel: "Manage Workspaces",
          secondaryHref: "/settings/workspaces",
        };
      case "TRIAL_AVAILABLE":
        return {
          icon: CreditCard,
          badge: "Trial available",
          title: `Activate Intent Radar for ${orgName}`,
          description:
            "Review trial eligibility and plan options for your billing account.",
          primaryLabel: canActivate ? "Choose a Plan" : "View Billing Status",
          primaryHref: "/settings?category=billing&tab=plans",
          onPrimary: undefined,
          secondaryLabel: "Manage Workspaces",
          secondaryHref: "/settings/workspaces",
        };
      case "SUBSCRIPTION_REQUIRED":
        return {
          icon: CreditCard,
          badge: "Activation required",
          title: `No active coverage for ${orgName}`,
          description:
            `${account?.name || 'Your billing account'} has no active coverage. ${canActivate ? 'Review account billing to activate access.' : 'Ask the billing account administrator to review coverage.'} Your workspace research is saved.`,
          primaryLabel: canActivate ? "Review account billing" : "View Billing",
          primaryHref: "/settings?category=billing&tab=overview",
          onPrimary: undefined,
          secondaryLabel: "Switch Workspace",
          secondaryHref: "/settings/workspaces",
        };
      case "PAYMENT_PENDING":
        return {
          icon: Clock,
          badge: "Verification pending",
          title: `Waiting for payment confirmation`,
          description:
            "Your checkout is awaiting confirmation from Creem. Refresh your billing status to check whether access has been confirmed.",
          primaryLabel: "Check Billing Status",
          primaryHref: "/settings?category=billing&tab=overview",
          onPrimary: undefined,
          secondaryLabel: "Manage Workspaces",
          secondaryHref: "/settings/workspaces",
        };
      case "EXPIRED":
        return {
          icon: RefreshCw,
          badge: "Subscription expired",
          title: `Subscription access has ended for ${orgName}`,
          description:
            "Your saved workspace configuration and historical records remain preserved. Activate or renew a plan to restore Intent Radar access.",
          primaryLabel: isOwner ? "Renew or Change Plan" : "View Billing",
          primaryHref: "/settings?category=billing&tab=plans",
          onPrimary: undefined,
          secondaryLabel: "Switch Workspace",
          secondaryHref: "/settings/workspaces",
        };
      default:
        return {
          icon: Lock,
          badge: "Access unavailable",
          title: `Intent Radar is not active for ${orgName}`,
          description:
            "This workspace does not currently have active Intent Radar access. Review workspace settings, activate a plan, or switch to another workspace.",
          primaryLabel: "Review Workspace Settings",
          primaryHref: "/settings?category=billing&tab=overview",
          onPrimary: undefined,
          secondaryLabel: "Manage Workspaces",
          secondaryHref: "/settings/workspaces",
        };
    }
  })();

  const Icon = copy.icon;

  return (
    <><section
      aria-label="Workspace access status"
      className="mx-auto my-8 max-w-xl rounded-2xl border border-border bg-card p-6 sm:p-7 shadow-sm space-y-5"
    >
      <div className="flex items-start gap-3.5">
        <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-primary/10 text-primary">
          <Icon size={20} aria-hidden="true" />
        </div>
        <div className="min-w-0 space-y-1.5">
          <span className="inline-flex items-center rounded-full border border-primary/20 bg-primary/5 px-2.5 py-0.5 text-[11px] font-semibold text-primary">
            {copy.badge}
          </span>
          <h1 className="text-lg font-bold tracking-tight text-foreground">{copy.title}</h1>
          <p className="text-sm leading-relaxed text-muted-foreground">{copy.description}</p>
        </div>
      </div>

      {!isOwner && (state === "TRIAL_AVAILABLE" || state === "SUBSCRIPTION_REQUIRED" || state === "EXPIRED") && (
        <p className="rounded-xl border border-border bg-muted/30 px-3.5 py-2.5 text-xs text-muted-foreground">
          Only a workspace owner can start or modify subscriptions. Contact your workspace owner or switch to an active workspace.
        </p>
      )}

      <div className="flex flex-wrap items-center gap-2.5 pt-1">
        {copy.onPrimary ? (
          <Button size="sm" disabled={resuming} onClick={() => void copy.onPrimary?.()} className="gap-1.5">
            <span>{copy.primaryLabel}</span>
            <ArrowRight size={14} aria-hidden="true" />
          </Button>
        ) : (
          <Link
            href={copy.primaryHref || "/settings?category=billing&tab=plans"}
            onClick={()=>{if(access.organization_id&&/^\/intent-radar(?:\/[a-z0-9-]+)*$/i.test(path))sessionStorage.setItem('billing-return:'+access.organization_id,path);}}
            className="inline-flex h-8 items-center justify-center gap-1.5 rounded-md bg-primary px-3 text-xs font-medium text-primary-foreground shadow hover:bg-primary/90 transition-colors"
          >
            <span>{copy.primaryLabel}</span>
            <ArrowRight size={14} aria-hidden="true" />
          </Link>
        )}
        <Link
          href={copy.secondaryHref}
          className="inline-flex h-8 items-center justify-center gap-1.5 rounded-md border border-border bg-card px-3 text-xs font-medium text-foreground shadow-sm hover:bg-accent transition-colors"
        >
          <Building2 size={14} aria-hidden="true" />
          <span>{copy.secondaryLabel}</span>
        </Link>
        <Link
          href="/help?article=troubleshooting"
          className="ml-auto text-xs font-medium text-muted-foreground hover:text-primary transition-colors"
        >
          Need help?
        </Link>
      </div>
    </section>{path==='/intent-radar/integrations'&&radar.onboarding_status==='COMPLETED'&&<CustomerIntegrationsCatalog/>}</>
  );
}
