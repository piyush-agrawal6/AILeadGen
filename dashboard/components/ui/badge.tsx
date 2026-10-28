import { cn } from "@/lib/utils";
import * as React from "react";

export interface BadgeProps extends React.HTMLAttributes<HTMLDivElement> {
  variant?: "default" | "secondary" | "outline" | "destructive" | "success" | "warning";
}

function Badge({ className, variant = "default", ...props }: BadgeProps) {
  const base =
    "inline-flex items-center rounded-full border px-2.5 py-0.5 text-xs font-semibold transition-colors focus:outline-none focus:ring-2 focus:ring-ring focus:ring-offset-2";

  const variants = {
    default: "border-transparent bg-primary text-primary-foreground",
    secondary: "border-transparent bg-secondary text-secondary-foreground",
    outline: "border-border text-foreground",
    destructive: "border-transparent bg-destructive/10 text-destructive border-destructive/20",
    success: "border-transparent bg-emerald-500/10 text-emerald-400 border-emerald-500/20",
    warning: "border-transparent bg-amber-500/10 text-amber-400 border-amber-500/20",
  };

  return <div className={cn(base, variants[variant], className)} {...props} />;
}

export { Badge };
