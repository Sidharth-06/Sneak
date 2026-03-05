"""
OSINT Photon — deep website crawler for competitive intelligence.
Inspired by the Photon OSINT tool but built as a lightweight async service.

Discovers:
- Social media profiles across all major platforms
- Technology stack (from HTML headers, scripts, meta tags)
- Documents & files (PDFs, whitepapers, decks)
- External service integrations (analytics, CDN, SaaS tools)
- Site structure mapping
"""

import asyncio
import httpx
from bs4 import BeautifulSoup
import re
import json
import logging
from urllib.parse import urljoin, urlparse
from collections import Counter

logger = logging.getLogger(__name__)

# Social media detection patterns
_SOCIAL_PATTERNS = {
    "LinkedIn": re.compile(r'https?://(?:www\.)?linkedin\.com/(?:company|in)/[\w-]+', re.I),
    "Twitter/X": re.compile(r'https?://(?:www\.)?(?:twitter\.com|x\.com)/[\w]+', re.I),
    "GitHub": re.compile(r'https?://(?:www\.)?github\.com/[\w-]+', re.I),
    "YouTube": re.compile(r'https?://(?:www\.)?youtube\.com/(?:@|channel/|c/)[\w-]+', re.I),
    "Facebook": re.compile(r'https?://(?:www\.)?facebook\.com/[\w.-]+', re.I),
    "Instagram": re.compile(r'https?://(?:www\.)?instagram\.com/[\w.]+', re.I),
    "TikTok": re.compile(r'https?://(?:www\.)?tiktok\.com/@[\w.]+', re.I),
    "Medium": re.compile(r'https?://(?:[\w]+\.)?medium\.com(?:/[\w-]+)?', re.I),
    "Discord": re.compile(r'https?://discord\.(?:gg|com)/[\w]+', re.I),
    "Slack": re.compile(r'https?://[\w-]+\.slack\.com', re.I),
    "Reddit": re.compile(r'https?://(?:www\.)?reddit\.com/r/[\w]+', re.I),
}

# Tech stack fingerprints — detected from scripts, meta tags, headers
_TECH_FINGERPRINTS = {
    # JavaScript Frameworks
    "React": ["react", "react-dom", "_next/static", "__NEXT_DATA__"],
    "Next.js": ["_next/", "__NEXT_DATA__", "next/dist"],
    "Vue.js": ["vue.js", "vue.min.js", "__vue__", "nuxt"],
    "Angular": ["angular", "ng-version", "ng-app"],
    "Svelte": ["svelte", "__svelte"],

    # Analytics & Marketing
    "Google Analytics": ["google-analytics.com", "gtag", "googletagmanager", "UA-", "G-"],
    "Google Tag Manager": ["googletagmanager.com/gtm"],
    "Segment": ["segment.com/analytics", "cdn.segment.com"],
    "Hotjar": ["hotjar.com", "hj("],
    "Mixpanel": ["mixpanel.com", "mixpanel"],
    "Amplitude": ["amplitude.com", "amplitude"],
    "HubSpot": ["hubspot.com", "hs-scripts", "hbspt"],
    "Intercom": ["intercom.io", "intercom", "intercomSettings"],
    "Drift": ["drift.com", "driftt"],
    "Zendesk": ["zendesk.com", "zdassets"],

    # CDN & Hosting
    "Cloudflare": ["cloudflare", "cf-ray", "__cfruid"],
    "AWS CloudFront": ["cloudfront.net"],
    "Vercel": ["vercel", "v0.dev"],
    "Netlify": ["netlify"],
    "Fastly": ["fastly"],
    "Akamai": ["akamai"],

    # CMS & Platforms
    "WordPress": ["wp-content", "wp-includes", "wordpress"],
    "Shopify": ["shopify.com", "myshopify", "cdn.shopify"],
    "Webflow": ["webflow.com", "wf-"],
    "Squarespace": ["squarespace.com", "sqsp"],
    "Ghost": ["ghost.io", "ghost.org"],

    # Auth & Identity
    "Auth0": ["auth0.com"],
    "Okta": ["okta.com"],
    "Firebase": ["firebase", "firebaseapp.com"],

    # Payment
    "Stripe": ["stripe.com", "js.stripe.com"],
    "PayPal": ["paypal.com", "paypalobjects.com"],

    # Error Tracking
    "Sentry": ["sentry.io", "sentry-cdn"],
    "Datadog": ["datadoghq.com", "dd-rum"],
    "New Relic": ["newrelic.com", "nr-data"],
    "LogRocket": ["logrocket.com"],

    # Chat & Support
    "Crisp": ["crisp.chat"],
    "LiveChat": ["livechatinc.com"],
    "Freshdesk": ["freshdesk.com"],
}

# Document file extensions to look for
_DOC_EXTENSIONS = {".pdf", ".doc", ".docx", ".ppt", ".pptx", ".xls", ".xlsx", ".csv"}


class OSINTPhotonService:
    """Deep website crawler for competitive intelligence."""

    async def crawl(self, homepage_url: str, company_name: str, max_pages: int = 10) -> dict:
        """
        Crawl a company's website and extract intelligence.
        Returns {social_profiles{}, tech_stack[], documents[], integrations[], raw_content str}.
        """
        result = {
            "social_profiles": {},
            "tech_stack": [],
            "documents": [],
            "integrations": [],
            "external_services": [],
            "site_structure": [],
            "raw_content": "",
        }

        if not homepage_url:
            return result

        parsed = urlparse(homepage_url)
        base_domain = parsed.hostname or ""

        # Discover pages to crawl
        pages_to_crawl = [homepage_url]
        discovery_paths = [
            "/", "/about", "/about-us", "/company", "/team",
            "/products", "/solutions", "/features", "/pricing",
            "/blog", "/resources", "/press", "/newsroom",
            "/careers", "/jobs", "/contact", "/partners",
            "/developers", "/docs", "/api", "/integrations",
            "/customers", "/case-studies", "/security", "/privacy",
        ]
        for path in discovery_paths:
            pages_to_crawl.append(urljoin(homepage_url, path))

        # Crawl pages in parallel
        sem = asyncio.Semaphore(8)
        all_html: list[str] = []
        all_links: set[str] = set()
        headers_collected: list[dict] = []

        async with httpx.AsyncClient(
            timeout=8.0,
            follow_redirects=True,
            limits=httpx.Limits(max_connections=10),
            headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"},
        ) as client:

            async def _fetch(url: str):
                async with sem:
                    try:
                        resp = await client.get(url)
                        if resp.status_code == 200 and "html" in resp.headers.get("content-type", ""):
                            all_html.append(resp.text)
                            headers_collected.append(dict(resp.headers))
                            # Collect all links from the page
                            soup = BeautifulSoup(resp.text, "html.parser")
                            for a in soup.find_all("a", href=True):
                                href = a["href"]
                                if href.startswith("http"):
                                    all_links.add(href)
                                elif href.startswith("/"):
                                    all_links.add(urljoin(homepage_url, href))
                            result["site_structure"].append({
                                "url": url,
                                "title": (soup.find("title").get_text(strip=True) if soup.find("title") else ""),
                            })
                    except Exception:
                        pass

            await asyncio.gather(*[_fetch(url) for url in pages_to_crawl[:max_pages]])

        # Combine all HTML for analysis
        combined_html = "\n".join(all_html)

        # ── 1. Social Media Discovery ──
        for platform, pattern in _SOCIAL_PATTERNS.items():
            matches = pattern.findall(combined_html)
            if matches:
                # Deduplicate and pick the most likely official account
                unique = list(set(matches))
                result["social_profiles"][platform] = unique[0]

        # Also check links
        for link in all_links:
            for platform, pattern in _SOCIAL_PATTERNS.items():
                if platform not in result["social_profiles"] and pattern.match(link):
                    result["social_profiles"][platform] = link

        # ── 2. Technology Stack Detection ──
        tech_found: dict[str, int] = {}
        for tech, signatures in _TECH_FINGERPRINTS.items():
            count = sum(1 for sig in signatures if sig.lower() in combined_html.lower())
            if count > 0:
                tech_found[tech] = count

        # Also check response headers
        for headers in headers_collected:
            server = headers.get("server", "").lower()
            if "nginx" in server:
                tech_found["Nginx"] = tech_found.get("Nginx", 0) + 1
            elif "apache" in server:
                tech_found["Apache"] = tech_found.get("Apache", 0) + 1
            if "cloudflare" in str(headers):
                tech_found["Cloudflare"] = tech_found.get("Cloudflare", 0) + 1
            powered_by = headers.get("x-powered-by", "").lower()
            if "express" in powered_by:
                tech_found["Express.js"] = tech_found.get("Express.js", 0) + 1
            if "php" in powered_by:
                tech_found["PHP"] = tech_found.get("PHP", 0) + 1

        result["tech_stack"] = sorted(tech_found.keys())

        # Categorize tech for strategic analysis
        tech_categories: dict[str, list[str]] = {}
        for tech in result["tech_stack"]:
            cat = "Other"
            if tech in ["React", "Next.js", "Vue.js", "Angular", "Svelte"]:
                cat = "Frontend Framework"
            elif tech in ["Google Analytics", "Google Tag Manager", "Segment", "Hotjar",
                          "Mixpanel", "Amplitude", "HubSpot"]:
                cat = "Analytics & Marketing"
            elif tech in ["Cloudflare", "AWS CloudFront", "Vercel", "Netlify", "Fastly", "Akamai"]:
                cat = "CDN & Hosting"
            elif tech in ["Stripe", "PayPal"]:
                cat = "Payments"
            elif tech in ["Sentry", "Datadog", "New Relic", "LogRocket"]:
                cat = "Monitoring & Error Tracking"
            elif tech in ["Intercom", "Drift", "Zendesk", "Crisp", "LiveChat", "Freshdesk"]:
                cat = "Customer Support"
            elif tech in ["Auth0", "Okta", "Firebase"]:
                cat = "Authentication"
            elif tech in ["WordPress", "Shopify", "Webflow", "Squarespace", "Ghost"]:
                cat = "CMS/Platform"
            tech_categories.setdefault(cat, []).append(tech)

        result["integrations"] = [
            {"category": cat, "tools": tools}
            for cat, tools in tech_categories.items()
        ]

        # ── 3. Document Discovery ──
        for link in all_links:
            parsed_link = urlparse(link)
            path = parsed_link.path.lower()
            if any(path.endswith(ext) for ext in _DOC_EXTENSIONS):
                doc_name = path.split("/")[-1]
                result["documents"].append({
                    "name": doc_name,
                    "url": link,
                    "type": path.split(".")[-1].upper(),
                })

        # ── 4. Build raw content for AI ──
        content_parts = [
            f"OSINT DEEP CRAWL RESULTS FOR: {homepage_url}",
            f"Company: {company_name}",
            f"Pages successfully crawled: {len(result['site_structure'])}",
        ]

        if result["social_profiles"]:
            content_parts.append(
                "Social media profiles detected:\n" +
                "\n".join(f"  • {platform}: {url}" for platform, url in result["social_profiles"].items())
            )

        if result["tech_stack"]:
            content_parts.append(
                f"Technology stack detected ({len(result['tech_stack'])} technologies):\n" +
                "\n".join(
                    f"  [{cat}]: {', '.join(tools)}"
                    for cat, tools in tech_categories.items()
                )
            )

        if result["documents"]:
            content_parts.append(
                f"Documents found ({len(result['documents'])}):\n" +
                "\n".join(f"  • {d['name']} ({d['type']}): {d['url']}" for d in result["documents"][:15])
            )

        if result["site_structure"]:
            content_parts.append(
                f"Site structure ({len(result['site_structure'])} pages):\n" +
                "\n".join(f"  • {p['title'] or p['url']}" for p in result["site_structure"][:20])
            )

        result["raw_content"] = "\n\n".join(content_parts)
        logger.info(
            f"[Photon] Crawl complete: {len(result['social_profiles'])} socials, "
            f"{len(result['tech_stack'])} techs, {len(result['documents'])} docs"
        )
        return result
