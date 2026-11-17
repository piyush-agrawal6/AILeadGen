import Link from 'next/link';
import policies from '@/lib/legal-policies.json';
import { LegalDocument } from './legal-document';

// Owner-approved static text, rendered as React text nodes. Never interpret
// customer content or policy text as HTML.
function PolicyText({ text }: { text: string }) {
  return <>{text.split(/(\*\*[^*]+\*\*)/g).map((part, index) =>
    part.startsWith('**') ? <strong key={index}>{part.slice(2, -2)}</strong> : part
  )}</>;
}

export function PublishedPolicy({ policy }: { policy: keyof typeof policies }) {
  const document = policies[policy];
  return <LegalDocument title={document.title} activeTab={policy} publishedVersion="planebyte-creem-global-2026-11-17-v3"
    summary="Effective 17 November 2026. Planebyte is an individually operated business owned by Piyush Agrawal. Legal notices: House No. 1005, Attabira, Bargarh, Odisha 768027, India. Support and privacy: contact@planebyte.com.">
    <nav aria-label="Policies" className="flex flex-wrap gap-x-4 gap-y-2 text-sm mb-8">
      {Object.entries(policies).map(([key, value]) => <Link key={key} href={`/${key}`} className="underline" aria-current={policy === key ? 'page' : undefined}>{value.title}</Link>)}
    </nav>
    {document.sections.map(section => <section key={section.title} className="pb-legal-section">
      <h2>{section.title}</h2>
      {section.blocks.map((block, index) => 'table' in block && block.table ?
        <div key={index} className="overflow-x-auto"><table className="w-full text-left text-sm">
          <thead><tr>{block.table[0].map(cell => <th key={cell} className="p-3 border border-border">{cell}</th>)}</tr></thead>
          <tbody>{block.table.slice(1).map((row, rowIndex) => <tr key={rowIndex}>{row.map((cell, column) => <td key={column} className="p-3 align-top border border-border"><PolicyText text={cell}/></td>)}</tr>)}</tbody>
        </table></div> : 'text' in block ? <p key={index}><PolicyText text={block.text}/></p> : null)}
    </section>)}
  </LegalDocument>;
}
