"use client";

import { useQuery } from "@tanstack/react-query";
import { Users, MailPlus, ShieldAlert, CheckCircle2 } from "lucide-react";
import { request } from "@/lib/intelligence";
import { useWorkspace, initials } from "@/components/workspaces/use-workspace";
import { InvitationSettings } from "@/components/workspaces/invitations";
import { WorkspaceAccessSettings } from "@/components/workspaces/access-settings";
import { Button } from "@/components/ui/button";

interface Member {
  id: string;
  email: string;
  display_name: string;
  role: "OWNER" | "ADMIN" | "MEMBER" | "VIEWER" | string;
}

export function TeamSection({ activeTab, onSwitchTab }: { activeTab: string; onSwitchTab?: (tab: string) => void }) {
  if (activeTab === "invitations") {
    return (
      <div className="space-y-6">
        <InvitationSettings embedded={true} />
      </div>
    );
  }

  if (activeTab === "roles") {
    return (
      <div className="space-y-6">
        <WorkspaceAccessSettings />
      </div>
    );
  }

  return <WorkspaceMembersTab onSwitchTab={onSwitchTab} />;
}

function WorkspaceMembersTab({ onSwitchTab }: { onSwitchTab?: (tab: string) => void }) {
  const workspace = useWorkspace();
  const query = useQuery({
    queryKey: ["workspace-members"],
    queryFn: () => request<Member[]>("/users"),
    enabled: !!workspace.active,
    retry: false,
  });

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-center justify-between gap-4 border-b pb-4">
        <div>
          <h2 className="text-xl font-semibold tracking-tight">Team Members</h2>
          <p className="mt-1 text-sm text-muted-foreground">
            People with active access to {workspace.active?.name || "this workspace"}.
          </p>
        </div>
        {workspace.canManage && (
          <Button
            size="sm"
            onClick={() => onSwitchTab?.("invitations")}
            className="gap-2"
          >
            <MailPlus size={15} />
            Invite teammate
          </Button>
        )}
      </div>

      {query.isPending ? (
        <p role="status" className="text-sm text-muted-foreground">Loading workspace members…</p>
      ) : query.isError ? (
        <div role="alert" className="rounded-xl border border-destructive/20 bg-destructive/5 p-4 text-sm text-destructive">
          <p>Your team members could not be loaded.</p>
          <Button variant="outline" size="sm" className="mt-3" onClick={() => void query.refetch()}>
            Retry
          </Button>
        </div>
      ) : (
        <div className="space-y-3">
          <div className="flex items-center justify-between text-xs font-medium text-muted-foreground px-1">
            <span>{query.data?.length ?? 0} active member{query.data?.length === 1 ? "" : "s"}</span>
            <span>Role</span>
          </div>

          <div className="divide-y rounded-xl border bg-card overflow-hidden">
            {query.data?.map((person) => {
              const isOwner = person.role === "OWNER";
              const isAdmin = person.role === "ADMIN";
              return (
                <div key={person.id} className="flex items-center justify-between gap-4 p-4 hover:bg-muted/30 transition-colors">
                  <div className="flex items-center gap-3.5 min-w-0">
                    <span className="flex h-10 w-10 shrink-0 items-center justify-center rounded-full bg-primary/10 text-xs font-semibold text-primary">
                      {initials(person.display_name || person.email)}
                    </span>
                    <div className="min-w-0">
                      <p className="truncate text-sm font-medium leading-none">
                        {person.display_name || person.email}
                      </p>
                      <p className="mt-1 truncate text-xs text-muted-foreground">
                        {person.email}
                      </p>
                    </div>
                  </div>

                  <span
                    className={`inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium ${
                      isOwner
                        ? "bg-purple-500/10 text-purple-700 dark:text-purple-300 border border-purple-500/20"
                        : isAdmin
                        ? "bg-blue-500/10 text-blue-700 dark:text-blue-300 border border-blue-500/20"
                        : "bg-muted text-muted-foreground border border-border"
                    }`}
                  >
                    {person.role.toLowerCase()}
                  </span>
                </div>
              );
            })}
          </div>
        </div>
      )}
    </div>
  );
}
