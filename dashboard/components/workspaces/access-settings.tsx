"use client";

import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { request } from "@/lib/intelligence";
import { Table, Pagination, type Paged } from "@/components/operations/ui";

type Audit = {
  id: string;
  actor: string;
  action: string;
  entity: string;
  result: string;
  created_at: string;
};

export function WorkspaceAccessSettings() {
  const [page, setPage] = useState(1);
  const [message, setMessage] = useState("");

  const me = useQuery({
    queryKey: ["my-role"],
    queryFn: () => request<{ role: string }>("/foundation/me"),
  });

  const roles = useQuery({
    queryKey: ["roles"],
    queryFn: () => request<{ email: string; role: string; primary_owner: boolean }[]>("/foundation/roles"),
    enabled: me.data?.role === "OWNER",
  });

  const audit = useQuery({
    queryKey: ["audit", page],
    queryFn: () => request<Paged<Audit>>("/foundation/audit?page=" + page),
    enabled: ["OWNER", "ADMIN"].includes(me.data?.role || ""),
  });

  return (
    <div className="space-y-6">
      <div className="rounded-xl border bg-card p-4">
        <p className="text-sm font-medium">
          Your current workspace role: <strong className="text-primary font-semibold">{me.data?.role || "Loading…"}</strong>
        </p>
      </div>

      {roles.data && (
        <div className="space-y-3">
          <h3 className="text-sm font-semibold">Workspace Role Assignments</h3>
          <Table head={["Account", "Role"]}>
            {roles.data.map((r) => (
              <tr key={r.email}>
                <td>
                  <span className="font-medium text-xs">{r.email}</span>
                  {r.primary_owner && <small className="block text-muted-foreground">Primary workspace owner</small>}
                </td>
                <td>
                  <select
                    className="control text-xs"
                    value={r.role}
                    disabled={r.primary_owner}
                    onChange={async (e) => {
                      try {
                        await request("/foundation/roles", {
                          method: "PUT",
                          body: JSON.stringify({ email: r.email, role: e.target.value }),
                        });
                        await roles.refetch();
                        setMessage("Role saved.");
                      } catch (err) {
                        setMessage(err instanceof Error ? err.message : "Could not save role.");
                      }
                    }}
                  >
                    {["OWNER", "ADMIN", "OPERATOR", "VIEWER"].map((role) => (
                      <option key={role}>{role}</option>
                    ))}
                  </select>
                </td>
              </tr>
            ))}
          </Table>
        </div>
      )}

      <div className="space-y-3">
        <h3 className="text-sm font-semibold">Workspace Security & Audit Operations</h3>
        <Table head={["When", "Actor", "Action", "Entity", "Result"]}>
          {audit.data?.items.map((a) => (
            <tr key={a.id} className="text-xs">
              <td className="whitespace-nowrap">{new Date(a.created_at).toLocaleString()}</td>
              <td className="truncate max-w-[120px]">{a.actor}</td>
              <td className="font-medium">{a.action}</td>
              <td className="max-w-40 break-words font-mono text-[11px]">{a.entity}</td>
              <td>
                <span className={`inline-flex rounded-full px-2 py-0.5 text-[10px] font-medium ${
                  a.result === "SUCCESS" || a.result === "OK" ? "bg-emerald-500/10 text-emerald-600" : "bg-muted text-muted-foreground"
                }`}>
                  {a.result}
                </span>
              </td>
            </tr>
          ))}
        </Table>
        <Pagination page={page} total={audit.data?.total || 0} size={25} onChange={setPage} />
      </div>

      {(message || audit.error) && (
        <p role="status" className="text-xs text-muted-foreground">{message || audit.error?.message}</p>
      )}
    </div>
  );
}
