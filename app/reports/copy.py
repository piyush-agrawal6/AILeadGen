"""Client-safe explanations. No search rankings, traffic or revenue estimates."""
KIND_NAMES={'WEBSITE':'Website experience','SEO':'Search foundations','SECURITY':'Security configuration'}

# title, qualitative impact, recommendation
FINDING_COPY={
 'NO_WEBSITE':('No official website found','People may find it harder to discover a clear, consistent account of your services.','Create a focused website with accurate business details and a simple enquiry path.'),
 'UNREACHABLE_WEBSITE':('Website did not respond successfully','Potential customers may be unable to reach the configured website.','Confirm the domain, hosting and routing with your provider, then restore access before reassessing the site.'),
 'HTTP_ONLY':('An HTTP page was observed','Unencrypted connections can affect visitor confidence and data protection.','Use HTTPS consistently and redirect the HTTP version to the intended secure destination.'),
 'NO_MOBILE_VIEWPORT':('Mobile viewport not observed','Content may be harder to use on smaller screens.','Add an appropriate viewport declaration and verify the main journeys on mobile devices.'),
 'VERY_POOR_PERFORMANCE':('Mobile performance needs attention','A slow experience may make important content and enquiry actions harder to reach.','Review the measured loading bottlenecks and prioritise the largest opportunities first.'),
 'POOR_PERFORMANCE':('Mobile performance can improve','Loading delays can add friction to the visitor journey.','Optimise the measured assets and rendering work, then repeat the same performance check.'),
 'NO_PRIMARY_CTA':('Primary action was not clear in sampled links','Visitors may be unsure how to take the next step.','Make the relevant booking, enquiry or quotation action prominent on key pages.'),
 'POOR_VERTICAL_CONVERSION_FLOW':('Service-specific enquiry path needs review','An unclear route from service information to an enquiry can introduce friction.','Align navigation and calls to action with the business services and customer journey.'),
 'NO_PHONE_CTA':('Click-to-call link not observed','Mobile visitors may need extra steps to use the public phone number.','Provide an accessible click-to-call link where the business phone is displayed.'),
 'NO_CONTACT_FLOW':('Contact route was not observed','Potential customers may struggle to find an appropriate way to enquire.','Provide a clear contact page and an enquiry method suited to the business.'),
 'MISSING_TITLE':('Page title not observed','An absent title can make a page less clear to visitors and search systems.','Write a concise, accurate title for each important page.'),
 'TITLE_LENGTH':('Page title length needs review','A title outside the configured review range may be harder to scan.','Review the title for clarity, relevance and unnecessary repetition.'),
 'MISSING_META_DESCRIPTION':('Meta description not observed','The page has less control over its descriptive search snippet.','Add an accurate, useful description that reflects the page content.'),
 'MISSING_H1':('Primary heading not observed','The main purpose of a page may be less clear to readers and assistive tools.','Use a descriptive primary heading and a coherent heading structure.'),
 'MULTIPLE_H1':('Primary heading structure needs review','Several primary headings can make content hierarchy less clear.','Review the page hierarchy and use headings consistently.'),
 'MISSING_CANONICAL':('Canonical link not observed','Search systems may have less explicit guidance about the preferred page version.','Confirm the preferred URLs and add canonical links where appropriate.'),
 'ROBOTS_NOT_OBSERVED':('Robots configuration was not observed','Crawler instructions could not be confirmed from the sampled response.','Review the robots file and verify that its rules match the intended access policy.'),
 'SITEMAP_NOT_OBSERVED':('Sitemap was not observed','Important public pages may have less explicit discovery guidance.','Publish and maintain a sitemap containing the intended indexable pages.'),
 'MISSING_LOCAL_SCHEMA':('Relevant structured data not observed','Business details may be less explicitly described to machine readers.','Add accurate structured data appropriate to the business and its public services.'),
 'MISSING_SCHEMA':('Structured data not observed','Key information may be less explicitly described to machine readers.','Consider accurate structured data appropriate to the page and business.'),
 'NO_CONTACT_PAGE':('Dedicated contact page not observed','Visitors may have difficulty finding consistent business information.','Provide a clear contact page with accurate public details.'),
 'NO_CITY_REFERENCE':('Location reference not observed in sampled text','Visitors may be less certain about the area served.','Make the business location or service area clear where relevant.'),
 'HOURS_NOT_OBSERVED':('Business hours not observed in sampled text','Visitors may need additional effort to confirm availability.','Publish accurate opening or enquiry hours where appropriate.'),
 'NOINDEX':('A noindex directive was observed','The directive may intentionally keep a page out of search indexes.','Confirm the intended indexing policy before changing the directive.'),
 'LOW_IMAGE_ALT_COVERAGE':('Image descriptions need review','Some visitors and assistive tools may receive less context from images.','Add useful alternative text to meaningful images; leave decorative images appropriately empty.'),
 'SPARSE_INTERNAL_LINKING':('Limited navigation links were observed','People may have fewer obvious routes to relevant service information.','Link related, useful pages with clear and descriptive labels.'),
 'REDIRECT_CHAIN':('Several redirects were observed','Extra redirects can add delay and make destinations less predictable.','Link directly to the intended final URL and simplify unnecessary redirects.'),
 'INTERNAL_REDIRECT_CHAIN':('An internal redirect chain was observed','Extra hops may add friction when moving between pages.','Update internal links to their intended final destinations.'),
 'BROKEN_LINKS':('Some internal links returned errors','Visitors may encounter dead ends during an enquiry journey.','Review the affected links and restore or redirect their intended destinations.'),
 'BROKEN_INTERNAL_LINKS':('Internal page errors were observed','Useful information may be harder to reach.','Correct broken links or provide relevant redirects.'),
 'HTTP_CANONICAL_ON_HTTPS_PAGE':('Canonical URL uses HTTP','The preferred-page signal differs from the secure page version observed.','Review canonical URLs and align them with the intended HTTPS version.'),
 'NAP_PHONE_MISMATCH':('Public phone details differ','Conflicting contact details can create uncertainty for prospective customers.','Confirm the correct number and align the relevant public business details.'),
 'NO_HTTP_TO_HTTPS_REDIRECT':('HTTP did not redirect to HTTPS in the check','Visitors may reach an unencrypted version of the site.','Set an appropriate HTTP-to-HTTPS redirect after confirming the intended secure host.'),
 'CERTIFICATE_VERIFICATION_FAILED':('Certificate verification needs review','Some visitors or automated clients may be unable to establish a trusted connection.','Have the hosting provider verify the certificate chain and configuration.'),
 'NO_HSTS':('HSTS header not observed','The browser was not given an explicit policy to prefer HTTPS on future visits.','Review an appropriate HSTS policy after confirming HTTPS works across the intended hosts.'),
 'NO_CSP':('Content Security Policy not observed','A browser-level policy for permitted content sources could not be confirmed.','Develop and test a Content Security Policy suited to the website before enforcing it.'),
 'NO_NOSNIFF':('Content-type protection header not observed','The browser was not explicitly instructed to avoid content-type guessing.','Send an appropriate X-Content-Type-Options header with correctly typed responses.'),
 'NO_FRAME_PROTECTION':('Frame-embedding protection not observed','A policy restricting who may embed these pages could not be confirmed.','Review frame-ancestors or an appropriate frame protection policy.'),
 'NO_REFERRER_POLICY':('Referrer policy not observed','The browser was not given an explicit policy for referrer information.','Choose and test an appropriate Referrer-Policy for the website.'),
 'NO_PERMISSIONS_POLICY':('Browser permissions policy not observed','Restrictions on optional browser capabilities could not be confirmed.','Review a Permissions-Policy that reflects the capabilities the site needs.'),
 'COOKIE_NO_SECURE':('A cookie lacked the Secure attribute','That cookie may not be restricted to encrypted requests.','Review the cookie purpose and apply Secure where appropriate.'),
 'COOKIE_NO_SAMESITE':('A cookie lacked an explicit SameSite attribute','Cross-site cookie behaviour was not explicitly defined.','Review an appropriate SameSite setting and test essential integrations.'),
 'SESSION_COOKIE_NO_HTTPONLY':('A session-like cookie lacked HttpOnly','Its name suggests a purpose that may benefit from limiting script access.','Confirm the cookie purpose with the owner and apply HttpOnly where appropriate.'),
 'MIXED_ACTIVE_CONTENT':('HTTP resources were referenced by an HTTPS page','Some page resources may not use the same encrypted transport as the page.','Replace the affected active-resource URLs with supported HTTPS destinations.'),
 'INSECURE_FORM_ACTION':('An HTTP form destination was observed','Submitted information may use an unencrypted destination. No form was submitted in this review.','Use an appropriate HTTPS form destination and verify the complete submission flow.'),
 'SERVER_VERSION_DISCLOSURE':('Server version was visible in a response header','The response exposes implementation details that may be unnecessary.','Review and minimise unnecessary version disclosure without obscuring operational monitoring.'),
 'X_POWERED_BY_DISCLOSURE':('Technology was visible in a response header','Some implementation details are publicly disclosed.','Review whether the disclosure is necessary and remove it where appropriate.'),
}


def explanation(kind,item):
    code=item['code']
    if code in FINDING_COPY:title,impact,recommendation=FINDING_COPY[code]
    elif code.startswith('NO_') or code.endswith('_NOT_OBSERVED'):
        title=code.removeprefix('NO_').removesuffix('_NOT_OBSERVED').replace('_',' ').capitalize()+' not observed'
        impact='Visitors may have less context or a less direct route to useful information.'
        recommendation='Review this area on the pages that matter to the customer journey and confirm the intended experience.'
    else:
        title=KIND_NAMES[kind]+' observation'
        impact='The observed configuration may offer an opportunity for improvement.'
        recommendation='Review this evidence with the website provider before making a change.'
    detail=item.get('detail','').replace('Relevant vertical feature not found among sampled navigation links.','A service-specific page or action was not found among the sampled navigation links.').replace('No vertical conversion CTA among observed links.','A clear service enquiry action was not found among the sampled links.').replace('Expected conversion paths:','Relevant customer actions:')
    return {'title':title,'evidence':detail,'impact':impact,'recommendation':recommendation}
