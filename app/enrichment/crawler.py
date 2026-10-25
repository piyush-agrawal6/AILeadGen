import asyncio
import logging
import time
from typing import Dict, List, Optional, Set
from urllib.parse import urljoin, urlparse
from bs4 import BeautifulSoup
import httpx

from app.config.settings import get_settings
from app.enrichment.contacts import ExtractedContacts, extract_contacts_from_html
from app.enrichment.social import extract_social_links
from app.utils.urls import extract_domain, extract_hostname, is_safe_url, sanitize_url

logger = logging.getLogger("leadengine.enrichment.crawler")

PRIORITY_KEYWORDS = [
    "contact", "about", "menu", "reservation", "reserve", "booking", "book", "rooms", "services", "team"
]


class CrawlResult:
    def __init__(self, start_url: str):
        self.start_url = start_url
        self.domain = extract_domain(start_url)
        self.pages_crawled: int = 0
        self.crawl_duration_ms: int = 0
        self.homepage_html: Optional[str] = None
        self.all_htmls: Dict[str, str] = {}
        self.all_links: Set[str] = set()
        self.contacts = ExtractedContacts()
        self.social_links: Dict[str, str] = {}
        self.contact_page_url: Optional[str] = None
        self.booking_url: Optional[str] = None
        self.menu_url: Optional[str] = None
        self.menu_is_pdf: bool = False
        self.has_robots_txt: bool = False
        self.has_sitemap: bool = False


class WebsiteCrawler:
    def __init__(
        self,
        max_pages: int = 6,
        page_timeout: float = 6.0,
        max_duration: float = 30.0,
        max_response_bytes: int = 2_000_000,
    ):
        self.max_pages = max_pages
        self.page_timeout = page_timeout
        self.max_duration = max_duration
        self.max_response_bytes = max_response_bytes

    async def crawl(self, start_url: str, initial_html: Optional[str] = None) -> CrawlResult:
        settings = get_settings()
        clean_start = sanitize_url(start_url)
        result = CrawlResult(start_url=clean_start or start_url)
        if not clean_start or not is_safe_url(clean_start):
            return result

        start_time = time.time()
        start_host = extract_hostname(clean_start)
        base_domain = extract_domain(clean_start)

        visited_urls: Set[str] = set()
        to_visit: List[str] = [clean_start]

        headers = {
            "User-Agent": settings.crawler_user_agent,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9",
        }

        async with httpx.AsyncClient(
            timeout=httpx.Timeout(self.page_timeout, connect=3.0),
            follow_redirects=True,
            verify=False,
        ) as client:
            parsed_base = urlparse(clean_start)
            base_origin = f"{parsed_base.scheme}://{parsed_base.netloc}"

            # Fast robots & sitemap probe with short 2s timeout
            async def check_meta_files():
                try:
                    r_resp = await client.get(urljoin(base_origin, "/robots.txt"), timeout=2.5)
                    if r_resp.status_code == 200 and "user-agent" in r_resp.text.lower():
                        result.has_robots_txt = True
                except Exception:
                    pass
                try:
                    s_resp = await client.get(urljoin(base_origin, "/sitemap.xml"), timeout=2.5)
                    if s_resp.status_code == 200 and ("<urlset" in s_resp.text.lower() or "<sitemapindex" in s_resp.text.lower()):
                        result.has_sitemap = True
                except Exception:
                    pass

            asyncio.create_task(check_meta_files())

            while to_visit and result.pages_crawled < self.max_pages:
                if time.time() - start_time > self.max_duration:
                    break

                current_url = to_visit.pop(0)
                norm_curr = current_url.split("#")[0].rstrip("/")
                if norm_curr in visited_urls:
                    continue
                visited_urls.add(norm_curr)

                html: Optional[str] = None
                # Reuse pre-probed initial HTML for start URL
                if current_url == clean_start and initial_html:
                    html = initial_html
                else:
                    if not is_safe_url(current_url):
                        continue
                    try:
                        resp = await client.get(current_url, headers=headers)
                        if resp.status_code == 200:
                            ct = resp.headers.get("content-type", "").lower()
                            if "text/html" in ct or "application/xhtml" in ct or not ct:
                                html = resp.content[: self.max_response_bytes].decode("utf-8", errors="replace")
                            elif "application/pdf" in ct:
                                if "menu" in current_url.lower():
                                    result.menu_url = current_url
                                    result.menu_is_pdf = True
                    except Exception:
                        continue

                if not html:
                    continue

                result.pages_crawled += 1
                result.all_htmls[current_url] = html
                if current_url == clean_start or result.homepage_html is None:
                    result.homepage_html = html

                # Extract contacts on this page
                page_contacts = extract_contacts_from_html(html, current_url)
                result.contacts.emails.extend(page_contacts.emails)
                result.contacts.phones.extend(page_contacts.phones)
                result.contacts.contact_forms.extend(page_contacts.contact_forms)
                result.contacts.booking_urls.extend(page_contacts.booking_urls)

                if "/contact" in current_url.lower():
                    result.contact_page_url = current_url

                # Discover actual links on this page
                try:
                    soup = BeautifulSoup(html, "lxml")
                    for a in soup.find_all("a", href=True):
                        raw_href = a["href"].strip()
                        full_href = urljoin(current_url, raw_href)
                        result.all_links.add(full_href)

                        lower_href = full_href.lower()
                        link_text = a.get_text().strip().lower()

                        # Menu check
                        if "menu" in lower_href or "menu" in link_text:
                            if not result.menu_url:
                                result.menu_url = full_href
                            if lower_href.endswith(".pdf"):
                                result.menu_is_pdf = True
                                result.menu_url = full_href

                        # Booking check
                        if any(w in lower_href or w in link_text for w in ["reserve", "reservation", "booking", "book now", "opentable", "resy"]):
                            if not result.booking_url:
                                result.booking_url = full_href

                        # Extract internal links matching priority keywords
                        try:
                            parsed_link = urlparse(full_href)
                            link_host = (parsed_link.hostname or "").lower()
                            if link_host == start_host or (base_domain and link_host.endswith("." + base_domain)):
                                link_norm = full_href.split("#")[0].rstrip("/")
                                if (
                                    link_norm not in visited_urls
                                    and link_norm not in to_visit
                                    and len(to_visit) < 15
                                    and not any(link_norm.lower().endswith(ext) for ext in [".jpg", ".png", ".gif", ".zip", ".css", ".js"])
                                ):
                                    if any(kw in link_norm.lower() or kw in link_text for kw in PRIORITY_KEYWORDS):
                                        to_visit.append(link_norm)
                        except Exception:
                            pass
                except Exception:
                    pass

        # Post-process contacts & socials
        result.social_links = extract_social_links(list(result.all_links))
        if not result.booking_url and result.contacts.booking_urls:
            result.booking_url = result.contacts.booking_urls[0]

        result.crawl_duration_ms = int((time.time() - start_time) * 1000)
        return result
