"use client";

import { useTheme } from "next-themes";
import { useSyncExternalStore } from "react";
import { signOut } from "next-auth/react";
import { Sun, Moon, Monitor, ShieldCheck, ExternalLink, LogOut, Lock } from "lucide-react";
import { AccountProfileSettings } from "@/components/workspaces/account-profile";
import { Button } from "@/components/ui/button";

const subscribe = () => () => {};

export function AccountSection({ activeTab }: { activeTab: string }) {
  if (activeTab === "security") {
    return <AccountSecurityTab />;
  }
  if (activeTab === "appearance") {
    return <AccountAppearanceTab />;
  }
  return <AccountProfileTab />;
}

function AccountProfileTab() {
  return (
    <div className="space-y-6">
      <div className="rounded-xl border bg-muted/20 p-4">
        <div className="flex items-start gap-3">
          <div className="rounded-lg bg-primary/10 p-2 text-primary">
            <Lock size={18} />
          </div>
          <div>
            <h3 className="text-sm font-semibold">Verified Sign-in Identity</h3>
            <p className="mt-1 text-xs text-muted-foreground leading-relaxed">
              Your sign-in email and primary authentication are secured and verified by Google OAuth.
              Editable profile information below personalizes your team presence and notifications across workspaces.
            </p>
          </div>
        </div>
      </div>
      <AccountProfileSettings embedded={true} />
    </div>
  );
}

function AccountSecurityTab() {
  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-lg font-semibold tracking-tight">Sign-in & Security</h2>
        <p className="mt-1 text-xs sm:text-sm text-muted-foreground">
          Your PlaneByte session is protected by your verified Google account.
        </p>
      </div>

      <div className="grid gap-4 sm:grid-cols-2">
        <div className="rounded-xl border bg-card p-5 space-y-4">
          <div className="flex items-start gap-3">
            <div className="rounded-lg bg-emerald-500/10 p-2 text-emerald-600 dark:text-emerald-400">
              <ShieldCheck size={20} />
            </div>
            <div className="space-y-1">
              <h3 className="text-sm font-semibold">Google Authentication Active</h3>
              <p className="text-xs text-muted-foreground leading-relaxed">
                Two-factor verification, device trust, and password security are managed directly through Google Security. PlaneByte does not store your Google password.
              </p>
            </div>
          </div>

          <div className="pt-2">
            <a
              className="inline-flex items-center gap-1.5 text-xs font-medium text-primary hover:underline"
              href="https://myaccount.google.com/security"
              target="_blank"
              rel="noopener noreferrer"
            >
              Manage Google account security <ExternalLink size={13} />
            </a>
          </div>
        </div>

        <div className="rounded-xl border bg-card p-5 space-y-3 flex flex-col justify-between">
          <div>
            <h3 className="text-sm font-semibold">Current Browser Session</h3>
            <p className="mt-1 text-xs text-muted-foreground leading-relaxed">
              Sessions stay active for up to 8 hours of inactivity before requiring re-authentication.
            </p>
          </div>
          <div className="pt-2">
            <Button
              variant="outline"
              size="sm"
              className="gap-2 text-destructive hover:bg-destructive/10"
              onClick={() => void signOut({ callbackUrl: "/login" })}
            >
              <LogOut size={14} />
              Sign out
            </Button>
          </div>
        </div>
      </div>
    </div>
  );
}

function AccountAppearanceTab() {
  const { theme, setTheme } = useTheme();
  const mounted = useSyncExternalStore(subscribe, () => true, () => false);

  const options = [
    { value: "light", title: "Light", description: "Crisp neutral surfaces for bright environments", icon: Sun },
    { value: "dark", title: "Dark", description: "Low-glare dark surfaces for focused research", icon: Moon },
    { value: "system", title: "System", description: "Automatically match your operating system theme", icon: Monitor },
  ];

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-lg font-semibold tracking-tight">Appearance Preferences</h2>
        <p className="mt-1 text-xs sm:text-sm text-muted-foreground">
          Customize how PlaneByte looks on this browser. Workspace data and shared team settings remain unaffected.
        </p>
      </div>

      <div className="grid gap-4 sm:grid-cols-3">
        {options.map(({ value, title, description, icon: Icon }) => {
          const isSelected = mounted && theme === value;
          return (
            <button
              key={value}
              type="button"
              onClick={() => setTheme(value)}
              className={`flex flex-col items-start rounded-xl border p-4 text-left transition-all ${
                isSelected
                  ? "border-primary bg-primary/5 ring-1 ring-primary shadow-sm"
                  : "border-border bg-card hover:border-muted-foreground/30"
              }`}
            >
              <div className={`rounded-lg p-2 ${isSelected ? "bg-primary text-primary-foreground" : "bg-muted text-muted-foreground"}`}>
                <Icon size={18} />
              </div>
              <strong className="mt-3 text-sm font-medium">{title}</strong>
              <p className="mt-1 text-xs text-muted-foreground leading-relaxed">{description}</p>
            </button>
          );
        })}
      </div>

      <p className="text-xs text-muted-foreground">
        Sidebar expansion is preserved separately per device using local browser preferences.
      </p>
    </div>
  );
}
