"use client";

import React from "react";
import Link from "next/link";
import { AlertTriangle, RefreshCw, Home } from "lucide-react";

interface Props {
  children: React.ReactNode;
}

interface State {
  hasError: boolean;
  message: string;
}

export class WorkspaceErrorBoundary extends React.Component<Props, State> {
  constructor(props: Props) {
    super(props);
    this.state = { hasError: false, message: "" };
  }

  static getDerivedStateFromError(error: Error): State {
    return {
      hasError: true,
      message: error?.message || "An unexpected interface error occurred.",
    };
  }

  componentDidCatch() {
    // Error captured cleanly by boundary; avoid noisy console dumps in production UI.
  }

  render() {
    if (!this.state.hasError) {
      return this.props.children;
    }

    return (
      <div
        role="alert"
        className="mx-auto my-12 max-w-lg rounded-2xl border border-border bg-card p-6 text-center shadow-sm"
      >
        <div className="mx-auto flex h-12 w-12 items-center justify-center rounded-xl bg-destructive/10 text-destructive">
          <AlertTriangle size={22} />
        </div>
        <h2 className="mt-4 text-lg font-semibold text-foreground">
          Something went wrong in this view
        </h2>
        <p className="mt-2 text-sm text-muted-foreground">{this.state.message}</p>
        <div className="mt-5 flex flex-wrap items-center justify-center gap-2.5">
          <button
            type="button"
            onClick={() => this.setState({ hasError: false, message: "" })}
            className="inline-flex items-center gap-1.5 rounded-lg bg-primary px-4 py-2 text-sm font-medium text-primary-foreground hover:opacity-95"
          >
            <RefreshCw size={14} />
            Try again
          </button>
          <Link
            href="/intent-radar"
            className="inline-flex items-center gap-1.5 rounded-lg border border-border bg-background px-4 py-2 text-sm font-medium text-foreground hover:bg-muted"
          >
            <Home size={14} />
            Back to Home
          </Link>
        </div>
      </div>
    );
  }
}
