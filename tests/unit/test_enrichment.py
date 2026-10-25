import pytest
from app.enrichment.contacts import extract_contacts_from_html, is_valid_business_email
from app.enrichment.dns import validate_email_syntax
from app.enrichment.social import extract_social_links
from app.enrichment.technology import detect_analytics, detect_technologies


SAMPLE_HTML = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Bella Roma Bistro - Italian Restaurant Austin</title>
    <meta name="description" content="Authentic handmade pasta and woodfired pizza in downtown Austin.">
    <link rel="canonical" href="https://bellaromabistro.com/">
    <script src="https://www.googletagmanager.com/gtm.js?id=GTM-TEST"></script>
</head>
<body class="wp-block-group elementor-default">
    <header>
        <h1>Bella Roma Bistro</h1>
        <a href="mailto:info@bellaromabistro.com">Email Us</a>
        <a href="tel:512-555-0144">(512) 555-0144</a>
        <a href="https://www.opentable.com/restref/client/?rid=1234">Reserve Table</a>
    </header>
    <main>
        <p>Contact our reservations team at reservations@bellaromabistro.com or call our manager directly.</p>
        <p>Ignore test@example.com or user@domain.com or photo@2x.png</p>
        <form action="/contact-us" method="POST">
            <input type="text" name="name" required />
            <input type="email" name="email" required />
            <textarea name="message"></textarea>
            <button type="submit">Send Message</button>
        </form>
    </main>
    <footer>
        <a href="https://www.instagram.com/bellaromabistro/">Instagram</a>
        <a href="https://www.facebook.com/bellaromabistro/">Facebook</a>
        <a href="https://twitter.com/bellaromabistro">Twitter</a>
        <a href="/menu.pdf">Download Menu (PDF)</a>
    </footer>
    <script src="/wp-content/themes/theme/assets/js/jquery.min.js"></script>
</body>
</html>
"""


def test_contact_extraction():
    contacts = extract_contacts_from_html(SAMPLE_HTML, "https://bellaromabistro.com")

    # Emails extracted and sorted by priority (info@, reservations@)
    extracted_addrs = [e[0] for e in contacts.emails]
    assert "info@bellaromabistro.com" in extracted_addrs
    assert "reservations@bellaromabistro.com" in extracted_addrs
    # Ensure garbage was excluded
    assert "test@example.com" not in extracted_addrs
    assert "user@domain.com" not in extracted_addrs
    assert "photo@2x.png" not in extracted_addrs

    # Priority ordering: info@ should precede reservations@
    assert extracted_addrs[0] == "info@bellaromabistro.com"

    # Phone extracted
    extracted_phones = [p[0] for p in contacts.phones]
    assert "+15125550144" in extracted_phones

    # Form extracted
    assert len(contacts.contact_forms) > 0
    assert "contact-us" in contacts.contact_forms[0]

    # Booking URL detected
    assert len(contacts.booking_urls) > 0
    assert "opentable.com" in contacts.booking_urls[0]


def test_social_link_extraction():
    raw_urls = [
        "https://www.instagram.com/bellaromabistro/",
        "https://facebook.com/bellaromabistro",
        "https://x.com/bellaromabistro",
        "https://www.linkedin.com/company/bella-roma-group/",
        "https://instagram.com/p/Cxyz123/",  # post, not business handle
        "https://facebook.com/terms",       # generic policy
    ]
    socials = extract_social_links(raw_urls)
    assert socials["instagram"] == "https://www.instagram.com/bellaromabistro"
    assert socials["facebook"] == "https://www.facebook.com/bellaromabistro"
    assert socials["x_url"] == "https://x.com/bellaromabistro"
    assert socials["linkedin"] == "https://www.linkedin.com/company/bella-roma-group"


def test_tech_detection():
    techs = detect_technologies(SAMPLE_HTML)
    assert "WordPress" in techs
    assert "Elementor" in techs
    assert "jQuery" in techs


def test_analytics_detection():
    analytics = detect_analytics(SAMPLE_HTML)
    assert "Google Tag Manager" in analytics


def test_email_validation_syntax():
    assert validate_email_syntax("hello@company.com") is True
    assert validate_email_syntax("info.austin@sub.domain.org") is True
    assert validate_email_syntax("invalid-email-no-at") is False
    assert validate_email_syntax("@no-user.com") is False
    assert is_valid_business_email("test@example.com") is False
    assert is_valid_business_email("noreply@company.com") is False
