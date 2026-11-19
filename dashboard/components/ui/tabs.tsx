"use client";

import React from "react";
import Link from "next/link";
import { cn } from "@/lib/utils";

/* =========================================================================
   1. PRIMARY PAGE TABS
   Horizontal tabs with subtle active bottom border / underline and
   PlaneByte blue accent. Used for major views across modules.
   ========================================================================= */

export interface PrimaryTabItem {
  id: string;
  label: string;
  href?: string;
  count?: number | string;
  icon?: React.ComponentType<{ size?: number; className?: string }>;
  disabled?: boolean;
}

export function PrimaryTabs({
  items,
  activeId,
  onChange,
  className,
  ariaLabel = "Page navigation",
  tabRole = "button",
}: {
  items: PrimaryTabItem[];
  activeId: string;
  onChange?: (id: string) => void;
  className?: string;
  ariaLabel?: string;
  tabRole?: "tab" | "button";
}) {
  return (
    <nav
      role={tabRole === "tab" ? "tablist" : undefined}
      aria-label={ariaLabel}
      className={cn(
        "flex items-center gap-1 border-b border-border overflow-x-auto no-scrollbar",
        className
      )}
    >
      {items.map((tab) => {
        const Icon = tab.icon;
        const isActive = activeId === tab.id;

        const content = (
          <>
            {Icon && <Icon size={14} className={isActive ? "text-primary" : "text-muted-foreground"} />}
            <span>{tab.label}</span>
            {tab.count !== undefined && (
              <span
                className={cn(
                  "rounded-full px-1.5 py-0.2 text-[10px] font-semibold tabular-nums transition-colors",
                  isActive
                    ? "bg-primary/10 text-primary dark:bg-primary/20"
                    : "bg-muted text-muted-foreground"
                )}
              >
                {tab.count}
              </span>
            )}
          </>
        );

        const tabClasses = cn(
          "inline-flex items-center gap-2 px-3.5 py-2.5 text-xs font-medium border-b-2 transition-all whitespace-nowrap cursor-pointer select-none",
          isActive
            ? "border-primary text-foreground font-semibold"
            : "border-transparent text-muted-foreground hover:text-foreground hover:border-border/80",
          tab.disabled && "opacity-50 pointer-events-none cursor-not-allowed"
        );

        if (tab.href) {
          return (
            <Link
              key={tab.id}
              href={tab.href}
              aria-current={isActive ? "page" : undefined}
              className={tabClasses}
              onClick={() => onChange?.(tab.id)}
            >
              {content}
            </Link>
          );
        }

        return (
          <button
            key={tab.id}
            type="button"
            role={tabRole === "tab" ? "tab" : undefined}
            aria-selected={tabRole === "tab" ? isActive : undefined}
            disabled={tab.disabled}
            className={tabClasses}
            onClick={() => onChange?.(tab.id)}
          >
            {content}
          </button>
        );
      })}
    </nav>
  );
}

/* =========================================================================
   2. SECONDARY TABS / SEGMENTED CONTROL
   Compact rounded segmented control for local view switching
   (e.g., AI Discovery / Advanced Search, Table / Cards, Overview / Run History).
   ========================================================================= */

export interface SegmentItem {
  id: string;
  label: string;
  icon?: React.ComponentType<{ size?: number; className?: string }>;
  count?: number | string;
  disabled?: boolean;
}

export function SegmentedControl({
  items,
  activeId,
  onChange,
  className,
  size = "md",
  ariaLabel = "View switcher",
}: {
  items: SegmentItem[];
  activeId: string;
  onChange: (id: string) => void;
  className?: string;
  size?: "sm" | "md";
  ariaLabel?: string;
}) {
  return (
    <div
      role="tablist"
      aria-label={ariaLabel}
      className={cn(
        "inline-flex items-center rounded-lg border border-border/80 bg-muted/40 p-0.5 select-none",
        className
      )}
    >
      {items.map((item) => {
        const Icon = item.icon;
        const isActive = activeId === item.id;

        return (
          <button
            key={item.id}
            type="button"
            role="tab"
            aria-selected={isActive}
            disabled={item.disabled}
            onClick={() => onChange(item.id)}
            className={cn(
              "inline-flex items-center gap-1.5 rounded-md font-medium transition-all cursor-pointer",
              size === "sm" ? "px-2 py-0.5 text-[11px]" : "px-2.5 py-1 text-xs",
              isActive
                ? "bg-card text-foreground font-semibold shadow-xs border border-border/50"
                : "text-muted-foreground hover:text-foreground border border-transparent",
              item.disabled && "opacity-50 pointer-events-none"
            )}
          >
            {Icon && <Icon size={size === "sm" ? 12 : 13} />}
            <span>{item.label}</span>
            {item.count !== undefined && (
              <span
                className={cn(
                  "rounded-full px-1.5 py-0.2 text-[10px] tabular-nums",
                  isActive ? "bg-muted text-foreground" : "bg-muted/60 text-muted-foreground"
                )}
              >
                {item.count}
              </span>
            )}
          </button>
        );
      })}
    </div>
  );
}

/* =========================================================================
   3. STATUS FILTER TABS
   Used specifically for filtering list views and tables by status.
   Pill buttons with real counts and distinct inactive/active states.
   ========================================================================= */

export interface StatusFilterItem {
  id: string;
  label: string;
  count?: number;
}

export function StatusFilterTabs({
  items,
  activeId,
  onChange,
  className,
  ariaLabel = "Filter by status",
}: {
  items: StatusFilterItem[];
  activeId: string;
  onChange: (id: string) => void;
  className?: string;
  ariaLabel?: string;
}) {
  return (
    <div
      role="tablist"
      aria-label={ariaLabel}
      className={cn("flex flex-wrap items-center gap-1", className)}
    >
      {items.map((item) => {
        const isActive = activeId === item.id;

        return (
          <button
            key={item.id}
            type="button"
            aria-label={`${item.label}${typeof item.count === "number" ? ` (${item.count})` : ""}`}
            aria-pressed={isActive}
            onClick={() => onChange(item.id)}
            className={cn(
              "inline-flex items-center gap-1.5 rounded-lg px-2.5 py-1 text-xs font-medium transition-colors cursor-pointer border",
              isActive
                ? "border-primary/40 bg-primary/10 text-primary font-semibold dark:bg-primary/20"
                : "border-border/70 bg-card text-muted-foreground hover:border-border hover:text-foreground"
            )}
          >
            <span>{item.label}</span>
            {typeof item.count === "number" && (
              <span
                className={cn(
                  "rounded-full px-1.5 py-0.2 text-[10px] tabular-nums",
                  isActive
                    ? "bg-primary/20 text-primary dark:bg-primary/30"
                    : "bg-muted text-muted-foreground"
                )}
              >
                {item.count}
              </span>
            )}
          </button>
        );
      })}
    </div>
  );
}
