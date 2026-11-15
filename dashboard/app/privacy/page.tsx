import { LegalDocument } from '@/components/auth/legal-document';

export const metadata = {
  title: 'Privacy Policy · PlaneByte',
  description: 'Privacy Policy and data governance for PlaneByte Intent Radar.',
};

export default function Privacy() {
  return (
    <LegalDocument
      title="Privacy Policy"
      summary="How PlaneByte handles account access, workspace information and source-backed research data."
    >
      <section className="pb-legal-section">
        <h2>Account and workspace information</h2>
        <p>
          PlaneByte uses your verified Google identity for sign-in and workspace access.
          Your Google password is not collected by PlaneByte. Current sign-in sessions expire after eight hours.
          Company profiles, team memberships and saved work belong to their selected workspace.
        </p>
      </section>

      <section className="pb-legal-section">
        <h2>Company and professional contact data</h2>
        <p>
          Users may import business information or request discovery from supported public sources.
          Records may include company websites, published business contact information, professional roles,
          source links and collection timestamps. Public source evidence does not independently verify employment or mailbox delivery.
        </p>
      </section>

      <section className="pb-legal-section">
        <h2>AI-assisted features</h2>
        <p>
          When enabled, AI features process the limited company information or instructions needed for the requested task through the configured AI provider.
          Website material is treated as untrusted data. Suggested company details and targeting profiles require review before saving.
          AI generation does not automatically start discovery or outreach.
        </p>
      </section>

      <section className="pb-legal-section">
        <h2>Connected services and messages</h2>
        <p>
          Google sign-in is separate from authorization for customer integrations.
          Owners or administrators explicitly connect supported services with the required permissions.
          Integration credentials remain on the server and are encrypted for supported customer connections.
          Configured outreach may retain message history, replies, unsubscribe choices and delivery or engagement events.
          Open signals are not proof that a person read an email.
        </p>
      </section>

      <section className="pb-legal-section">
        <h2>Access, history and requests</h2>
        <p>
          Workspace roles limit access to organization data. Archiving records can retain campaign, contact and activity history.
          Suppression and contacted-recipient records protect future sending. A complete retention schedule and applicable rights process must be approved before public launch; this development copy does not promise a specific deletion period.
        </p>
      </section>

      <section className="pb-legal-section">
        <h2>Questions and approval</h2>
        <p>
          Contact{' '}
          <a href="mailto:contact@planebyte.com" className="text-primary underline">
            contact@planebyte.com
          </a>{' '}
          with privacy questions. Do not include credentials in your message.
          The owner must approve the controller details, provider disclosures, international processing information, retention policy and applicable rights process before publishing the canonical Privacy Policy.
        </p>
      </section>
    </LegalDocument>
  );
}
