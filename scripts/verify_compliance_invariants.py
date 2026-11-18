"""Automated compliance drift & invariant verifier across backend, app, and marketing site."""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def verify() -> list[str]:
    errors: list[str] = []

    registry_path = ROOT / "docs" / "compliance" / "COMPLIANCE_REGISTRY.json"
    if not registry_path.exists():
        return ["Missing docs/compliance/COMPLIANCE_REGISTRY.json"]
    registry = json.loads(registry_path.read_text(encoding="utf-8"))

    # 1. Verify dashboard/lib/legal-policies.json matches registry policy keys & version
    app_policies_path = ROOT / "dashboard" / "lib" / "legal-policies.json"
    app_bundle = json.loads(app_policies_path.read_text(encoding="utf-8"))
    if app_bundle.get("version") != registry.get("policy_version"):
        errors.append(
            f"Policy version mismatch: app={app_bundle.get('version')} vs registry={registry.get('policy_version')}"
        )

    policies = app_bundle.get("policies") or {}
    expected_keys = {p["key"] for p in registry["policies"]}
    missing_keys = expected_keys - set(policies.keys())
    if missing_keys:
        errors.append(f"Missing policies in dashboard/lib/legal-policies.json: {sorted(missing_keys)}")

    # 2. Verify all public routes exist in dashboard/app/ and in isPublicPage()
    auth_exp = (ROOT / "dashboard" / "lib" / "auth-experience.ts").read_text(encoding="utf-8")
    for p in registry["policies"]:
        app_path = p["app_path"].lstrip("/")
        page_file = ROOT / "dashboard" / "app" / app_path / "page.tsx"
        if not page_file.exists():
            errors.append(f"Missing Next.js app legal route: {page_file}")
        if f'"/{app_path}"' not in auth_exp and f"'/{app_path}'" not in auth_exp:
            errors.append(f"Legal route /{app_path} missing from dashboard/lib/auth-experience.ts isPublicPage()")

    # 3. Verify YouTube mandatory disclosures & no legacy contradictions across app policies
    app_json_text = app_policies_path.read_text(encoding="utf-8")
    for required_url in (
        "https://www.youtube.com/t/terms",
        "https://policies.google.com/privacy",
        "https://security.google.com/settings/security/permissions",
    ):
        if required_url not in app_json_text:
            errors.append(f"Missing mandatory YouTube/Google URL in app policies: {required_url}")

    for forbidden in ("Planebyte Studios", "Bangalore, India", "SOC 2 certified", "ISO 27001 certified"):
        if forbidden.lower() in app_json_text.lower():
            errors.append(f"Forbidden contradictory phrase in dashboard/lib/legal-policies.json: {forbidden}")

    # 4. Verify YouTube AI policy gates default to False in app/config/settings.py
    settings_src = (ROOT / "app" / "config" / "settings.py").read_text(encoding="utf-8")
    for flag in ("intent_radar_youtube_ai_analytics_enabled", "intent_radar_youtube_cross_source_analytics_enabled"):
        m = re.search(rf"{flag}\s*:\s*bool\s*=\s*(?:Field\(\s*(?:default\s*=\s*)?)?(True|False)", settings_src)
        if not m or m.group(1) != "False":
            errors.append(f"YouTube AI policy gate {flag} must default to False in app/config/settings.py")

    # 5. Verify pricing invariants match backend commercial catalog ($59 / $149 / $379)
    commercial_src = (ROOT / "app" / "billing" / "commercial.py").read_text(encoding="utf-8")
    for plan in registry["pricing_and_billing"]["plans"]:
        if str(plan["monthly_minor"]) not in commercial_src:
            errors.append(f"Plan {plan['code']} price {plan['monthly_minor']} missing from app/billing/commercial.py")

    # 6. Verify marketing website if present
    mkt = ROOT / "planebyte-website-new"
    if mkt.exists():
        layout_src = (mkt / "src" / "app" / "layout.tsx").read_text(encoding="utf-8")
        if "app.cal.com/embed/embed.js" in layout_src:
            errors.append("planebyte-website-new layout.tsx must not load Cal.com embed script unconditionally")
        footer_src = (mkt / "src" / "partials" / "footer.html").read_text(encoding="utf-8")
        if "Planebyte Studios" in footer_src:
            errors.append("Legacy 'Planebyte Studios' found in marketing footer.html")
        if "data-open-privacy-prefs" not in footer_src:
            errors.append("Missing Privacy Preferences trigger in marketing footer.html")
        for p in registry["policies"]:
            mpath = p["marketing_path"].lstrip("/")
            if not (mkt / "src" / "app" / mpath / "page.tsx").exists():
                errors.append(f"Missing marketing route: planebyte-website-new/src/app/{mpath}/page.tsx")
            html_file = mkt / "src" / "markup" / f"{mpath}.html"
            if html_file.exists():
                txt = html_file.read_text(encoding="utf-8")
                if "Planebyte Studios" in txt or "Bangalore" in txt:
                    errors.append(f"Legacy contradiction found in {html_file}")

    return errors


if __name__ == "__main__":
    issues = verify()
    if issues:
        for item in issues:
            print("COMPLIANCE_FAIL:", item)
        sys.exit(1)
    print("COMPLIANCE_INVARIANTS_OK")
