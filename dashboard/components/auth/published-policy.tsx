import React from 'react';
import Link from 'next/link';
import legalBundle from '@/lib/legal-policies.json';
import { LegalDocument } from './legal-document';

export type PolicyKey = keyof typeof legalBundle.policies;

type PolicyBlock =
  | { text: string }
  | { list: string[] }
  | { table: string[][] }
  | { callout: { title: string; text: string } };

type PolicySection = {
  id: string;
  title: string;
  blocks: PolicyBlock[];
};

type PolicyDoc = {
  title: string;
  kicker: string;
  subtitle: string;
  canonical_path: string;
  sections: PolicySection[];
};

const POLICY_NAV: { key: PolicyKey; href: string; label: string }[] = [
  { key: 'privacy', href: '/privacy', label: 'Privacy Policy' },
  { key: 'terms', href: '/terms', label: 'Terms of Service' },
  { key: 'cookies', href: '/cookies', label: 'Cookie Policy' },
  { key: 'cancellation', href: '/cancellation', label: 'Cancellation' },
  { key: 'refund', href: '/refund', label: 'Refunds' },
  { key: 'delivery-policy', href: '/delivery-policy', label: 'Digital Delivery' },
  { key: 'acceptable-use', href: '/acceptable-use', label: 'Acceptable Use' },
  { key: 'sources-policy', href: '/sources-policy', label: 'Third-Party Sources' },
  { key: 'data-deletion', href: '/data-deletion', label: 'Data Deletion' },
  { key: 'subprocessors', href: '/subprocessors', label: 'Subprocessors' },
  { key: 'dpa', href: '/dpa', label: 'DPA (Draft)' }
];

// Trusted static policy text rendered strictly as React elements (never dangerouslySetInnerHTML).
function PolicyInline({ text }: { text: string }) {
  const tokenRegex = /(\[[^\]]+\]\([^)]+\)|\*\*[^*]+\*\*|`[^`]+`)/g;
  const parts = text.split(tokenRegex);
  return (
    <>
      {parts.map((part, idx) => {
        const linkMatch = part.match(/^\[([^\]]+)\]\(([^)]+)\)$/);
        if (linkMatch) {
          const [, label, href] = linkMatch;
          if (href.startsWith('https://') || href.startsWith('http://') || href.startsWith('mailto:')) {
            return (
              <a
                key={idx}
                href={href}
                target={href.startsWith('mailto:') ? undefined : '_blank'}
                rel={href.startsWith('mailto:') ? undefined : 'noopener noreferrer'}
                className="text-primary underline underline-offset-2 hover:opacity-80"
              >
                {label}
              </a>
            );
          }
          const appHref = href === '/cancellation-refund-policy' ? '/cancellation' : href;
          return (
            <Link key={idx} href={appHref} className="text-primary underline underline-offset-2 hover:opacity-80">
              {label}
            </Link>
          );
        }
        if (part.startsWith('**') && part.endsWith('**')) {
          return <strong key={idx} className="font-semibold text-foreground">{part.slice(2, -2)}</strong>;
        }
        if (part.startsWith('`') && part.endsWith('`')) {
          return (
            <code key={idx} className="rounded bg-muted px-1 py-0.5 text-[0.85em] font-mono text-foreground">
              {part.slice(1, -1)}
            </code>
          );
        }
        return <React.Fragment key={idx}>{part}</React.Fragment>;
      })}
    </>
  );
}

export function PublishedPolicy({ policy }: { policy: PolicyKey }) {
  const doc = legalBundle.policies[policy] as unknown as PolicyDoc;

  return (
    <LegalDocument
      title={doc.title}
      activeTab={policy === 'terms' || policy === 'privacy' || policy === 'refund' || policy === 'cancellation' ? policy : 'privacy'}
      eyebrow={doc.kicker}
      publishedVersion={`${legalBundle.version} · Effective ${legalBundle.effective_date}`}
      summary={legalBundle.summary}
    >
      {/* Related Policies Navigation */}
      <nav aria-label="PlaneByte Legal Policies" className="flex flex-wrap gap-x-3.5 gap-y-2 text-xs mb-6 pb-4 border-b border-border">
        {POLICY_NAV.map(item => (
          <Link
            key={item.key}
            href={item.href}
            aria-current={policy === item.key ? 'page' : undefined}
            className={
              policy === item.key
                ? 'font-semibold text-primary underline underline-offset-4'
                : 'text-muted-foreground hover:text-foreground underline underline-offset-4'
            }
          >
            {item.label}
          </Link>
        ))}
      </nav>

      {/* Table of Contents for longer policies */}
      {doc.sections.length >= 3 && (
        <nav aria-label="On this page" className="mb-8 rounded-xl border border-border/80 bg-muted/20 p-4">
          <p className="text-[11px] font-semibold uppercase tracking-wider text-muted-foreground mb-2">
            On this page
          </p>
          <ol className="grid grid-cols-1 sm:grid-cols-2 gap-1.5 text-xs">
            {doc.sections.map(sec => (
              <li key={sec.id}>
                <a href={`#${sec.id}`} className="text-foreground/90 hover:text-primary underline-offset-2 hover:underline">
                  {sec.title}
                </a>
              </li>
            ))}
          </ol>
        </nav>
      )}

      {/* Policy Sections */}
      {doc.sections.map(section => (
        <section key={section.id} id={section.id} className="pb-legal-section scroll-mt-24">
          <h2>{section.title}</h2>
          {section.blocks.map((block, index) => {
            if ('callout' in block) {
              return (
                <div
                  key={index}
                  className="my-4 rounded-xl border border-primary/30 bg-primary/5 p-4 text-sm space-y-1.5"
                >
                  <strong className="block text-foreground font-semibold">{block.callout.title}</strong>
                  <p className="m-0 text-muted-foreground leading-relaxed">
                    <PolicyInline text={block.callout.text} />
                  </p>
                </div>
              );
            }
            if ('table' in block) {
              return (
                <div key={index} className="my-4 overflow-x-auto rounded-xl border border-border">
                  <table className="w-full text-left text-xs sm:text-sm border-collapse">
                    <thead className="bg-muted/40">
                      <tr>
                        {block.table[0].map((cell, cIdx) => (
                          <th key={cIdx} className="p-3 font-semibold text-foreground border-b border-border">
                            <PolicyInline text={cell} />
                          </th>
                        ))}
                      </tr>
                    </thead>
                    <tbody>
                      {block.table.slice(1).map((row, rIdx) => (
                        <tr key={rIdx} className="border-b border-border/70 last:border-b-0">
                          {row.map((cell, cIdx) => (
                            <td key={cIdx} className="p-3 align-top text-muted-foreground leading-relaxed">
                              <PolicyInline text={cell} />
                            </td>
                          ))}
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              );
            }
            if ('list' in block) {
              return (
                <ul key={index} className="list-disc pl-5 space-y-2 my-3 text-sm text-muted-foreground leading-relaxed">
                  {block.list.map((item, lIdx) => (
                    <li key={lIdx}>
                      <PolicyInline text={item} />
                    </li>
                  ))}
                </ul>
              );
            }
            return (
              <p key={index} className="leading-relaxed">
                <PolicyInline text={block.text} />
              </p>
            );
          })}
        </section>
      ))}
    </LegalDocument>
  );
}
