import { LegalDocument } from '@/components/auth/legal-document';

export const metadata = {
  title: 'Terms of Service · PlaneByte',
  description: 'Terms of Service for PlaneByte Intent Radar development release.',
};

export default function Terms() {
  return (
    <LegalDocument
      title="Terms of Service"
      summary="Service information for the current development release. The applicable public service agreement must be approved before launch."
    >
      <section className="pb-legal-section">
        <h2>Workspace access</h2>
        <p>
          Use your permitted verified account. Workspace owners control team membership and roles.
          Public self-service registration is unavailable in this development release. Google sign-in
          does not automatically authorize a connected business mailbox or spreadsheet.
        </p>
      </section>

      <section className="pb-legal-section">
        <h2>Reviewed workflows</h2>
        <p>
          Users review targeting, discovery resource limits and outbound messages before consequential actions.
          Creating or activating a targeting profile does not launch discovery or outreach. Data availability
          varies by provider, geography and category. Fit and verification labels describe available evidence
          and do not guarantee commercial results or message delivery.
        </p>
      </section>

      <section className="pb-legal-section">
        <h2>Responsible use</h2>
        <p>
          Keep account and integration credentials private. Respect recipient opt-outs and workspace suppression
          rules. Product access does not authorize active security testing of third-party websites.
        </p>
      </section>

      <section className="pb-legal-section">
        <h2>Commercial and legal terms pending approval</h2>
        <p>
          The owner must approve the contracting entity, available plans, payment and cancellation terms,
          acceptable-use agreement, liability provisions, dispute process and governing law before public release.
          No subscription pricing, service-level guarantee or compliance certification is asserted by this development copy.
        </p>
      </section>

      <section className="pb-legal-section">
        <h2>Contact</h2>
        <p>
          Ask your workspace administrator or contact{' '}
          <a href="mailto:contact@planebyte.com" className="text-primary underline">
            contact@planebyte.com
          </a>{' '}
          for the applicable agreement and service questions.
        </p>
      </section>
    </LegalDocument>
  );
}
