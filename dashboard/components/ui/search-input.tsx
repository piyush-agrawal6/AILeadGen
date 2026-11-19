"use client";

import * as React from "react";
import { Search, X } from "lucide-react";
import { cn } from "@/lib/utils";

export interface SearchInputProps
  extends Omit<React.InputHTMLAttributes<HTMLInputElement>, "type"> {
  onClear?: () => void;
  wrapperClassName?: string;
  iconSize?: number;
}

export const SearchInput = React.forwardRef<HTMLInputElement, SearchInputProps>(
  (
    {
      className,
      wrapperClassName,
      value,
      onChange,
      onClear,
      placeholder = "Search…",
      disabled,
      iconSize = 13,
      ...props
    },
    ref
  ) => {
    const hasValue = value !== undefined && value !== null && String(value).length > 0;

    return (
      <div className={cn("relative flex items-center w-full min-w-0", wrapperClassName)}>
        <Search
          size={iconSize}
          className="absolute left-2.5 top-1/2 -translate-y-1/2 text-muted-foreground pointer-events-none shrink-0"
          aria-hidden="true"
        />
        <input
          ref={ref}
          type="text"
          value={value}
          onChange={onChange}
          placeholder={placeholder}
          disabled={disabled}
          className={cn(
            "flex h-8 w-full rounded-lg border border-border bg-card pl-9 pr-7 py-1 text-xs text-foreground placeholder:text-muted-foreground transition-colors focus:border-primary focus:outline-none focus:ring-1 focus:ring-primary disabled:cursor-not-allowed disabled:opacity-50",
            className
          )}
          style={{ paddingLeft: "2.25rem" }}
          {...props}
        />
        {hasValue && onClear && (
          <button
            type="button"
            onClick={onClear}
            disabled={disabled}
            aria-label="Clear search"
            className="absolute right-2 top-1/2 -translate-y-1/2 p-0.5 rounded text-muted-foreground hover:text-foreground focus:outline-none focus:ring-1 focus:ring-primary cursor-pointer transition-colors"
          >
            <X size={12} aria-hidden="true" />
          </button>
        )}
      </div>
    );
  }
);

SearchInput.displayName = "SearchInput";
