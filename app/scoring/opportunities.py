"""Versioned deterministic service opportunities using shared, passive evidence."""
import json
import re
from http.cookies import SimpleCookie
from bs4 import BeautifulSoup
from app.database.prospects import now
from app.config.verticals import get_vertical_manager

SCORING_VERSION = "3.1.0"
ORDER = ["WEBSITE", "SEO", "SECURITY"]


def analyze_opportunities(business, profile=None, lighthouse=None, crawl=None, probe=None, selected=None):
    selected = selected or ORDER
    evidence = {key: [] for key in ORDER}
    def add(kind, code, points, detail):
        evidence[kind].append({"code": code, "points": points, "detail": detail})
    email = bool(business.public_email)
    phone = bool(business.normalized_phone or business.phone or (crawl and crawl.contacts.phones))
    form = bool(crawl and crawl.contacts.contact_forms)
    contactability = "HIGH" if email and phone else "MEDIUM" if email or phone or form else "LOW"
    scores = {key: None for key in ORDER}
    if probe and probe.certificate_valid is False:
        add("SECURITY","CERTIFICATE_VERIFICATION_FAILED",40,"TLS certificate validation failed using the worker trust store; owner verification is required.")
    if not business.website:
        add("WEBSITE", "NO_WEBSITE", 95, "No official website in available public source evidence.")
    elif not profile or not profile.reachable:
        add("WEBSITE", "UNREACHABLE_WEBSITE", 85, "The configured public website did not respond successfully.")
    else:
        html = "\n".join(crawl.all_htmls.values()) if crawl else ""
        soup = BeautifulSoup(html, "html.parser")
        text = soup.get_text(" ", strip=True).casefold()
        links = [a.get_text(" ", strip=True).casefold() + " " + str(a.get("href", "")).casefold() for a in soup.find_all("a")]
        definition = get_vertical_manager().verticals.get(business.vertical)
        ctas = definition.audit_ctas if definition else ["contact", "book", "quote"]
        has_cta = any(cta in value for cta in ctas for value in links)
        if not profile.https_enabled:
            add("WEBSITE", "HTTP_ONLY", 15, "The final website response uses HTTP.")
            add("SECURITY", "HTTP_ONLY", 30, "Traffic to the observed page is unencrypted.")
        if not profile.has_viewport:
            add("WEBSITE", "NO_MOBILE_VIEWPORT", 20, "No viewport declaration in observed HTML.")
            add("SEO", "NO_MOBILE_VIEWPORT", 8, "Mobile viewport signal is absent.")
        if lighthouse and lighthouse.performance_score is not None:
            performance = lighthouse.performance_score
            if performance < 60:
                add("WEBSITE", "VERY_POOR_PERFORMANCE" if performance < 40 else "POOR_PERFORMANCE", 25 if performance < 40 else 15, f"Observed Lighthouse mobile performance: {performance}.")
                add("SEO", "POOR_PERFORMANCE", 8, f"Observed Lighthouse mobile performance: {performance}.")
        if not has_cta:
            add("WEBSITE", "NO_PRIMARY_CTA", 15, "No vertical conversion CTA among observed links.")
        feature_rules = definition.audit_rules if definition else []
        for rule in feature_rules:
            code,keywords,points = rule["code"],rule["keywords"],rule["points"]
            if not any(keyword in value for keyword in keywords for value in links):
                add("WEBSITE",code,points,"Relevant vertical feature not found among sampled navigation links.")
        if phone and not soup.select('a[href^="tel:"]'):
            add("WEBSITE","NO_PHONE_CTA",3,"A public phone exists but no click-to-call link was observed.")
        if not (email or phone or form or profile.has_contact_page):
            add("WEBSITE", "NO_CONTACT_FLOW", 15, "No public contact path observed.")
        if definition and not has_cta:
            add("WEBSITE", "POOR_VERTICAL_CONVERSION_FLOW", 10, f"Expected conversion paths: {', '.join(ctas)}.")
        if soup.select('object[type="application/x-shockwave-flash"], embed[type="application/x-shockwave-flash"]'):
            add("WEBSITE", "LEGACY_IMPLEMENTATION", 15, "Flash content is embedded in observed HTML.")
        if profile.menu_is_pdf and business.vertical == "restaurant":
            add("WEBSITE", "PDF_ONLY_CRITICAL_CONTENT", 8, "The observed menu is a PDF.")
        seo_checks = [
            (not profile.html_title, "MISSING_TITLE", 12, "Homepage title absent."),
            (bool(profile.html_title) and not 10 <= len(profile.html_title) <= 70, "TITLE_LENGTH", 4, "Title length outside the configured 10–70 character range."),
            (not profile.meta_description, "MISSING_META_DESCRIPTION", 10, "Homepage meta description absent."),
            (not profile.has_h1, "MISSING_H1", 8, "No primary heading observed."),
            (profile.h1_count > 1, "MULTIPLE_H1", 3, "Multiple primary headings on the homepage."),
            (not profile.canonical_url, "MISSING_CANONICAL", 5, "No canonical link observed."),
            (not profile.has_robots_txt, "ROBOTS_NOT_OBSERVED", 3, "robots.txt was not successfully observed; this does not establish an indexing error."),
            (not profile.has_sitemap, "SITEMAP_NOT_OBSERVED", 4, "sitemap.xml was not successfully observed."),
            (not profile.has_schema, "NO_STRUCTURED_DATA", 8, "No JSON-LD structured data observed."),
            (bool(definition) and not set(profile.schema_types).intersection(definition.schema_types), "NO_VERTICAL_SCHEMA", 6, "No relevant business schema type observed."),
            (not profile.has_contact_page, "NO_CONTACT_PAGE", 5, "No dedicated contact page observed."),
            (bool(business.city) and business.city.casefold() not in text, "NO_CITY_REFERENCE", 5, "Source city not mentioned in observed page text."),
            (not any(word in text for word in ["opening hours", "business hours", "monday", "mon–fri", "lun", "montag"]), "HOURS_NOT_OBSERVED", 3, "Business hours not observed in sampled HTML."),
        ]
        for condition, code, points, detail in seo_checks:
            if condition:
                add("SEO", code, points, detail)
        robots = " ".join(str(meta.get("content", "")) for meta in soup.find_all("meta", attrs={"name": re.compile("robots", re.I)}))
        headers = {k.lower(): v for k, v in (probe.response_headers if probe else {}).items()}
        if "noindex" in (robots + headers.get("x-robots-tag", "")).lower():
            add("SEO", "NOINDEX", 25, "Explicit noindex directive observed. Intent requires owner confirmation.")
        images = soup.find_all("img")
        if images and sum(bool(image.get("alt")) for image in images) / len(images) < 0.5:
            add("SEO", "LOW_IMAGE_ALT_COVERAGE", 5, "Fewer than half of sampled images have nonempty alt attributes.")
        if len(links) < 3:
            add("SEO", "SPARSE_INTERNAL_LINKING", 3, "Few navigational links in observed HTML.")
        if probe and probe.redirect_count > 2:
            add("SEO", "REDIRECT_CHAIN", 4, f"Observed redirect count: {probe.redirect_count}.")
        if crawl:
            broken=[url for url,status in crawl.page_statuses.items() if status>=400]
            if broken:
                add("WEBSITE","BROKEN_LINKS",min(15,len(broken)*5),f"{len(broken)} fetched internal links returned errors.")
                add("SEO","BROKEN_INTERNAL_LINKS",min(12,len(broken)*4),f"Observed failed internal URLs: {', '.join(broken[:3])}")
            if any(count>2 for count in crawl.redirect_counts.values()):
                add("SEO","INTERNAL_REDIRECT_CHAIN",4,"An observed internal page required more than two redirects.")
        if profile.https_enabled and (profile.canonical_url or "").startswith("http://"):
            add("SEO","HTTP_CANONICAL_ON_HTTPS_PAGE",8,"The observed canonical URL uses HTTP while the page uses HTTPS.")
        if probe and probe.http_redirects_https is False:
            add("SECURITY","NO_HTTP_TO_HTTPS_REDIRECT",8,"The HTTP variant returned a final HTTP response instead of redirecting to HTTPS.")
        source_phone = re.sub(r"\D", "", business.normalized_phone or business.phone or "")
        website_phones = [re.sub(r"\D", "", item[0]) for item in crawl.contacts.phones] if crawl else []
        if len(source_phone) >= 8 and website_phones and not any(value.endswith(source_phone[-10:]) or source_phone.endswith(value[-10:]) for value in website_phones if len(value) >= 8):
            add("SEO", "NAP_PHONE_MISMATCH", 10, "Normalized source and extracted public website phone numbers differ.")
        # Missing security headers are scored only when a successful response supplied headers.
        if probe and probe.response_headers:
            checks = [("strict-transport-security", "NO_HSTS", 8), ("content-security-policy", "NO_CSP", 12), ("x-content-type-options", "NO_NOSNIFF", 5), ("referrer-policy", "NO_REFERRER_POLICY", 4), ("permissions-policy", "NO_PERMISSIONS_POLICY", 3)]
            for header, code, points in checks:
                if not headers.get(header) and (header != "strict-transport-security" or profile.https_enabled):
                    add("SECURITY", code, points, f"{header} absent from the observed response.")
            if "frame-ancestors" not in headers.get("content-security-policy", "") and headers.get("x-frame-options", "").lower() not in ["deny", "sameorigin"]:
                add("SECURITY", "NO_FRAME_PROTECTION", 8, "No frame-ancestors or valid X-Frame-Options observed.")
            if headers.get("x-powered-by"):
                add("SECURITY", "X_POWERED_BY_DISCLOSURE", 2, "Technology disclosed in X-Powered-By.")
            if re.search(r"\d+\.\d+", headers.get("server", "")):
                add("SECURITY", "SERVER_VERSION_DISCLOSURE", 2, "Server version disclosed in response headers.")
            cookies = probe.cookies
            parsed_cookies=[]
            for value in cookies:
                parsed=SimpleCookie()
                try:
                    parsed.load(value);parsed_cookies.extend(parsed.values())
                except Exception:
                    pass
            if any(not cookie["secure"] for cookie in parsed_cookies) and profile.https_enabled:
                add("SECURITY", "COOKIE_NO_SECURE", 5, "A response cookie lacks Secure.")
            if any(not cookie["samesite"] for cookie in parsed_cookies):
                add("SECURITY", "COOKIE_NO_SAMESITE", 3, "A response cookie lacks SameSite.")
            if any(re.search(r"session|auth|token|^sid$", cookie.key, re.I) and not cookie["httponly"] for cookie in parsed_cookies):
                add("SECURITY", "SESSION_COOKIE_NO_HTTPONLY", 5, "A session-like cookie lacks HttpOnly; purpose requires owner confirmation.")
        if profile.https_enabled and soup.select('script[src^="http:"],iframe[src^="http:"],link[rel="stylesheet"][href^="http:"]'):
            add("SECURITY", "MIXED_ACTIVE_CONTENT", 12, "Active content references an HTTP resource on an HTTPS page.")
        if soup.select('form[action^="http:"]'):
            add("SECURITY", "INSECURE_FORM_ACTION", 12, "A form submits to an HTTP destination. No form was submitted.")
        for kind in ["SEO", "SECURITY"]:
            points = min(100, sum(item["points"] for item in evidence[kind]))
            scores[kind] = points if kind != "SECURITY" or (probe and probe.response_headers) or points else None
    scores["WEBSITE"] = min(100, sum(item["points"] for item in evidence["WEBSITE"]))
    if scores["SECURITY"] is None and evidence["SECURITY"]:
        scores["SECURITY"] = min(100,sum(item["points"] for item in evidence["SECURITY"]))
    ranked = sorted((kind for kind in ORDER if kind in selected and scores[kind] is not None and scores[kind] >= 40), key=lambda key: (-scores[key], ORDER.index(key)))
    return {"website_opportunity_score": scores["WEBSITE"], "seo_opportunity_score": scores["SEO"], "security_opportunity_score": scores["SECURITY"],
            "primary_opportunity": ranked[0] if ranked else None, "secondary_opportunity": ranked[1] if len(ranked) > 1 else None,
            "contactability_level": contactability, "scoring_version": SCORING_VERSION, "evidence": evidence}


def store_opportunities(conn, business, result):
    columns = ["website_opportunity_score", "seo_opportunity_score", "security_opportunity_score", "primary_opportunity", "secondary_opportunity", "contactability_level", "scoring_version"]
    names = ["business_id", "run_id", *columns, "evidence_json", "created_at"]
    conn.execute(f"INSERT INTO opportunity_scores({','.join(names)}) VALUES({','.join('?' for _ in names)}) ON CONFLICT(business_id) DO UPDATE SET " + ','.join(f'{name}=excluded.{name}' for name in names[1:]), [business.id, business.run_id, *(result[column] for column in columns), json.dumps(result["evidence"]), now()])


def classify_scale(business, location_count=1, city_count=1):
    manager = get_vertical_manager()
    if manager.is_chain_domain(business.domain) or manager.is_chain_name(business.name, business.vertical):
        return "KNOWN_CHAIN", "Known chain name or registered domain", 0.99
    if location_count >= 16 and city_count >= 3 and business.domain:
        return "ENTERPRISE", "Shared domain across at least 16 locations and three cities", 0.85
    if location_count >= 6 and city_count >= 2 and business.domain:
        return "REGIONAL", "Shared domain across at least six locations and multiple cities", 0.8
    if location_count > 1:
        return "SMALL_GROUP", "Multiple observed locations without corroborating enterprise evidence", 0.65
    return "LOCAL", "Single observed location; scale is limited to available evidence", 0.6
