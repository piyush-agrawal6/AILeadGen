"use client";

import React from "react";

function isSafeHref(url: string): boolean {
  const trimmed = url.trim();
  return (
    trimmed.startsWith("/") ||
    trimmed.startsWith("https://") ||
    trimmed.startsWith("http://")
  );
}

export function SafeInlineMarkdown({ text }: { text: string }) {
  // Parse inline links, bold, inline code, and italic without dangerouslySetInnerHTML
  const tokens: React.ReactNode[] = [];
  let remaining = text;
  let key = 0;

  while (remaining.length > 0) {
    const linkMatch = remaining.match(/\[([^\]]+)\]\(([^)\s]+)\)/);
    const boldMatch = remaining.match(/\*\*([^*]+)\*\*/);
    const codeMatch = remaining.match(/`([^`]+)`/);
    const italicMatch = remaining.match(/(?<!\*)\*([^*]+)\*(?!\*)/);

    const candidates = [
      linkMatch ? { type: "link" as const, match: linkMatch } : null,
      boldMatch ? { type: "bold" as const, match: boldMatch } : null,
      codeMatch ? { type: "code" as const, match: codeMatch } : null,
      italicMatch ? { type: "italic" as const, match: italicMatch } : null,
    ]
      .filter((c): c is NonNullable<typeof c> => c !== null && c.match.index !== undefined)
      .sort((a, b) => (a.match.index ?? 0) - (b.match.index ?? 0));

    if (!candidates.length) {
      tokens.push(remaining);
      break;
    }

    const first = candidates[0];
    const idx = first.match.index ?? 0;
    if (idx > 0) {
      tokens.push(remaining.slice(0, idx));
    }

    if (first.type === "link") {
      const label = first.match[1];
      const href = first.match[2];
      if (isSafeHref(href)) {
        const external = href.startsWith("http");
        tokens.push(
          <a
            key={key++}
            href={href}
            target={external ? "_blank" : undefined}
            rel={external ? "noopener noreferrer" : undefined}
            className="font-medium text-primary underline underline-offset-2 hover:opacity-80"
          >
            {label}
          </a>,
        );
      } else {
        tokens.push(label);
      }
    } else if (first.type === "bold") {
      tokens.push(
        <strong key={key++} className="font-semibold text-foreground">
          {first.match[1]}
        </strong>,
      );
    } else if (first.type === "code") {
      tokens.push(
        <code
          key={key++}
          className="rounded bg-muted px-1 py-0.5 font-mono text-[11px] text-foreground"
        >
          {first.match[1]}
        </code>,
      );
    } else {
      tokens.push(
        <em key={key++} className="italic">
          {first.match[1]}
        </em>,
      );
    }

    remaining = remaining.slice(idx + first.match[0].length);
  }

  return <>{tokens}</>;
}

export function SafeMarkdown({
  content,
  compact = false,
}: {
  content: string;
  compact?: boolean;
}) {
  const lines = (content || "").split("\n");
  const blocks: React.ReactNode[] = [];
  let i = 0;

  while (i < lines.length) {
    const line = lines[i];

    if (!line.trim()) {
      i++;
      continue;
    }

    // Fenced code block
    if (line.trim().startsWith("```")) {
      const codeLines: string[] = [];
      i++;
      while (i < lines.length && !lines[i].trim().startsWith("```")) {
        codeLines.push(lines[i]);
        i++;
      }
      i++;
      blocks.push(
        <pre
          key={`code-${i}`}
          className="my-1.5 overflow-x-auto rounded-lg border border-border bg-muted/50 p-2.5 font-mono text-[11px] text-foreground"
        >
          <code>{codeLines.join("\n")}</code>
        </pre>,
      );
      continue;
    }

    // Headings
    if (/^#{1,4}\s+/.test(line)) {
      const text = line.replace(/^#{1,4}\s+/, "");
      blocks.push(
        <h4
          key={`h-${i}`}
          className={`${compact ? "mt-2 mb-1 text-xs" : "mt-3 mb-1.5 text-sm"} font-semibold text-foreground first:mt-0`}
        >
          <SafeInlineMarkdown text={text} />
        </h4>,
      );
      i++;
      continue;
    }

    // Blockquote
    if (line.trim().startsWith(">")) {
      const quoteLines: string[] = [];
      while (i < lines.length && lines[i].trim().startsWith(">")) {
        quoteLines.push(lines[i].trim().replace(/^>\s?/, ""));
        i++;
      }
      blocks.push(
        <blockquote
          key={`bq-${i}`}
          className="my-1.5 border-l-2 border-primary/50 bg-muted/30 px-2.5 py-1 text-[11px] italic text-muted-foreground"
        >
          <SafeInlineMarkdown text={quoteLines.join(" ")} />
        </blockquote>,
      );
      continue;
    }

    // Unordered list
    if (/^\s*[-*•]\s+/.test(line)) {
      const items: string[] = [];
      while (i < lines.length && /^\s*[-*•]\s+/.test(lines[i])) {
        items.push(lines[i].replace(/^\s*[-*•]\s+/, ""));
        i++;
      }
      blocks.push(
        <ul
          key={`ul-${i}`}
          className={`my-1.5 space-y-1 pl-4 list-disc ${compact ? "text-xs" : "text-sm"} text-foreground/90`}
        >
          {items.map((item, idx) => (
            <li key={idx}>
              <SafeInlineMarkdown text={item} />
            </li>
          ))}
        </ul>,
      );
      continue;
    }

    // Ordered list
    if (/^\s*\d+\.\s+/.test(line)) {
      const items: string[] = [];
      while (i < lines.length && /^\s*\d+\.\s+/.test(lines[i])) {
        items.push(lines[i].replace(/^\s*\d+\.\s+/, ""));
        i++;
      }
      blocks.push(
        <ol
          key={`ol-${i}`}
          className={`my-1.5 space-y-1 pl-4 list-decimal ${compact ? "text-xs" : "text-sm"} text-foreground/90`}
        >
          {items.map((item, idx) => (
            <li key={idx}>
              <SafeInlineMarkdown text={item} />
            </li>
          ))}
        </ol>,
      );
      continue;
    }

    // Paragraph
    const paraLines: string[] = [];
    while (
      i < lines.length &&
      lines[i].trim() &&
      !lines[i].trim().startsWith("```") &&
      !/^#{1,4}\s+/.test(lines[i]) &&
      !lines[i].trim().startsWith(">") &&
      !/^\s*[-*•]\s+/.test(lines[i]) &&
      !/^\s*\d+\.\s+/.test(lines[i])
    ) {
      paraLines.push(lines[i]);
      i++;
    }
    blocks.push(
      <p
        key={`p-${i}`}
        className={`my-1 ${compact ? "text-xs leading-relaxed" : "text-sm leading-relaxed"} text-foreground/95 first:mt-0`}
      >
        <SafeInlineMarkdown text={paraLines.join(" ")} />
      </p>,
    );
  }

  return <div className="space-y-1">{blocks}</div>;
}
