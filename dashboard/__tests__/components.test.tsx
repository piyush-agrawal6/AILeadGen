import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card,CardContent,CardHeader,CardTitle } from "@/components/ui/card";
import {
formatDuration,
formatNumber,
getScoreColor,
getStatusBadgeClass,
getTierBadgeClass
} from "@/lib/utils";
import { render,screen } from "@testing-library/react";
import { describe,expect,it } from "vitest";

describe("UI Primitives & Formatting Utilities", () => {
  it("renders Button component with variants", () => {
    render(<Button variant="default">Start Scan</Button>);
    const btn = screen.getByRole("button", { name: /Start Scan/i });
    expect(btn).toBeInTheDocument();
  });

  it("renders Badge component with status text", () => {
    render(<Badge variant="success">Active</Badge>);
    expect(screen.getByText("Active")).toBeInTheDocument();
  });

  it("renders Card component with header and title", () => {
    render(
      <Card>
        <CardHeader>
          <CardTitle>Austin Restaurants</CardTitle>
        </CardHeader>
        <CardContent>
          <p>Scored 250 leads</p>
        </CardContent>
      </Card>
    );
    expect(screen.getByText("Austin Restaurants")).toBeInTheDocument();
    expect(screen.getByText("Scored 250 leads")).toBeInTheDocument();
  });

  it("correctly formats numbers", () => {
    expect(formatNumber(12500)).toBe("12,500");
    expect(formatNumber(0)).toBe("0");
  });

  it("correctly formats durations", () => {
    expect(formatDuration(45)).toBe("45s");
    expect(formatDuration(125)).toBe("2m 5s");
    expect(formatDuration(null)).toBe("—");
  });

  it("returns appropriate badge classes for tiers", () => {
    expect(getTierBadgeClass("A+")).toContain("emerald");
    expect(getTierBadgeClass("A")).toContain("sky");
    expect(getTierBadgeClass("B")).toContain("amber");
    expect(getTierBadgeClass("D")).toContain("slate");
  });

  it("returns appropriate badge classes for scan statuses", () => {
    expect(getStatusBadgeClass("COMPLETED")).toContain("emerald");
    expect(getStatusBadgeClass("RUNNING")).toContain("sky");
    expect(getStatusBadgeClass("FAILED")).toContain("rose");
    expect(getStatusBadgeClass("CANCELLED")).toContain("slate");
  });

  it("returns correct score colors based on score value", () => {
    expect(getScoreColor(85)).toBe("text-emerald-400");
    expect(getScoreColor(65)).toBe("text-sky-400");
    expect(getScoreColor(45)).toBe("text-amber-400");
    expect(getScoreColor(20)).toBe("text-slate-400");
  });
});
