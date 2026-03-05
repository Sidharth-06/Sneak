"""
Company Website Direct Scraper — discovers and scrapes the company's own site
for deep intel: press releases, blog posts, careers/hiring signals, leadership,
and structured metadata (JSON-LD, OpenGraph).
"""

import httpx
from bs4 import BeautifulSoup
import asyncio
import json
import re
import logging
from urllib.parse import urljoin, urlparse

logger = logging.getLogger(__name__)

# Common subpages to discover
_TARGET_PATHS = [
    "/about", "/about-us", "/company",
    "/press", "/news", "/newsroom", "/media", "/press-releases",
    "/blog", "/insights",
    "/careers", "/jobs",
]


class WebsiteScraperService:
    """Scrape the company's own website for deep structured data."""

    async def scrape_company_site(self, company_name: str) -> dict:
        """
        1. Discover the company homepage via search
        2. Scrape homepage + key subpages
        3. Return structured data: {homepage_url, pages[], metadata{}, hiring_signals{}, leadership[]}
        """
        result: dict = {
            "homepage_url": "",
            "pages": [],
            "metadata": {},
            "hiring_signals": {},
            "leadership": [],
            "raw_content": "",
        }

        homepage = await self._find_homepage(company_name)
        if not homepage:
            logger.info(f"[WebsiteScraper] Could not find homepage for '{company_name}'")
            return result

        result["homepage_url"] = homepage
        logger.info(f"[WebsiteScraper] Found homepage: {homepage}")

        # Build list of pages to scrape
        urls_to_scrape = [homepage]
        for path in _TARGET_PATHS:
            urls_to_scrape.append(urljoin(homepage, path))

        # Scrape all pages in parallel
        sem = asyncio.Semaphore(8)
        async with httpx.AsyncClient(
            timeout=8.0,
            follow_redirects=True,
            limits=httpx.Limits(max_connections=10, max_keepalive_connections=5),
            headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"},
        ) as client:
            tasks = [self._scrape_page(client, url, sem) for url in urls_to_scrape]
            pages = await asyncio.gather(*tasks, return_exceptions=True)

        all_content_parts: list[str] = []
        for page_data in pages:
            if isinstance(page_data, Exception) or not page_data:
                continue
            if page_data.get("content"):
                result["pages"].append({
                    "url": page_data["url"],
                    "title": page_data.get("title", ""),
                    "page_type": page_data.get("page_type", "unknown"),
                })
                all_content_parts.append(
                    f"SOURCE_URL: {page_data['url']}\n"
                    f"SOURCE_TITLE: {page_data.get('title', '')}\n"
                    f"PAGE_TYPE: {page_data.get('page_type', 'general')}\n"
                    f"CONTENT:\n{page_data['content']}"
                )

            # Merge metadata
            if page_data.get("metadata"):
                result["metadata"].update(page_data["metadata"])

            # Hiring signals
            if page_data.get("job_count"):
                result["hiring_signals"]["job_listings_found"] = page_data["job_count"]
                result["hiring_signals"]["careers_url"] = page_data["url"]

            # Leadership
            if page_data.get("leadership"):
                result["leadership"].extend(page_data["leadership"])

        result["raw_content"] = "\n\n======\n\n".join(all_content_parts)
        logger.info(
            f"[WebsiteScraper] Scraped {len(result['pages'])} pages, "
            f"{len(result['raw_content'])} chars for '{company_name}'"
        )
        return result

    async def _find_homepage(self, company_name: str) -> str:
        """Use a quick search to find the company's official website."""
        try:
            from core.config import settings
            async with httpx.AsyncClient(timeout=8.0) as client:
                response = await client.get(
                    f"{settings.SEARXNG_URL}/search",
                    params={"q": f"{company_name} official website", "format": "json"},
                )
                if response.status_code == 200:
                    results = response.json().get("results", [])
                    for r in results[:5]:
                        url = r.get("url", "")
                        host = urlparse(url).hostname or ""
                        # Skip social media, news sites, Wikipedia
                        skip = {"wikipedia.org", "linkedin.com", "twitter.com", "x.com",
                                "facebook.com", "instagram.com", "youtube.com", "reddit.com",
                                "crunchbase.com", "bloomberg.com", "reuters.com"}
                        if not any(host.endswith(d) for d in skip):
                            return f"{urlparse(url).scheme}://{host}"
        except Exception as e:
            logger.warning(f"[WebsiteScraper] Homepage search error: {e}")
        return ""

    async def _scrape_page(self, client: httpx.AsyncClient, url: str, sem: asyncio.Semaphore) -> dict | None:
        """Scrape a single page and extract structured data."""
        async with sem:
            try:
                response = await client.get(url)
                if response.status_code != 200:
                    return None

                ct = response.headers.get("content-type", "")
                if "html" not in ct and "text" not in ct:
                    return None

                soup = BeautifulSoup(response.text, "html.parser")
                page_data: dict = {"url": url}

                # Title
                title_tag = soup.find("title")
                page_data["title"] = title_tag.get_text(strip=True) if title_tag else ""

                # Page type detection
                page_data["page_type"] = self._detect_page_type(url, soup)

                # Extract metadata (JSON-LD + OpenGraph)
                page_data["metadata"] = self._extract_metadata(soup)

                # Extract leadership info from about pages
                if page_data["page_type"] in ("about", "leadership"):
                    page_data["leadership"] = self._extract_leadership(soup)

                # Count job listings on careers pages
                if page_data["page_type"] == "careers":
                    page_data["job_count"] = self._count_jobs(soup)

                # Clean text content
                for tag in soup(["script", "style", "nav", "footer", "header", "aside",
                                 "iframe", "noscript", "svg", "form"]):
                    tag.decompose()

                # Extract key structured content
                key_facts = self._extract_key_facts(soup)
                text = soup.get_text(separator=" ")
                lines = (line.strip() for line in text.splitlines())
                chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
                clean_text = " ".join(c for c in chunks if c)

                # Combine key facts + clean text
                content_parts = []
                if key_facts:
                    content_parts.append("KEY FACTS:\n" + "\n".join(f"• {f}" for f in key_facts))
                content_parts.append(clean_text[:4000])
                page_data["content"] = "\n\n".join(content_parts)

                return page_data
            except Exception:
                return None

    def _detect_page_type(self, url: str, soup: BeautifulSoup) -> str:
        """Detect what kind of page this is."""
        path = urlparse(url).path.lower()
        if any(k in path for k in ["/press", "/news", "/media", "/newsroom"]):
            return "press"
        if any(k in path for k in ["/blog", "/insights", "/articles"]):
            return "blog"
        if any(k in path for k in ["/about", "/company", "/team", "/leadership"]):
            return "about"
        if any(k in path for k in ["/career", "/jobs", "/hiring", "/openings"]):
            return "careers"
        if any(k in path for k in ["/product", "/features", "/solution"]):
            return "product"
        return "general"

    def _extract_metadata(self, soup: BeautifulSoup) -> dict:
        """Extract JSON-LD structured data and OpenGraph tags."""
        metadata: dict = {}

        # JSON-LD
        for script in soup.find_all("script", type="application/ld+json"):
            try:
                data = json.loads(script.string or "")
                if isinstance(data, dict):
                    if data.get("@type") == "Organization":
                        metadata["org_name"] = data.get("name", "")
                        metadata["org_description"] = data.get("description", "")[:300]
                        metadata["org_url"] = data.get("url", "")
                        if data.get("foundingDate"):
                            metadata["founded"] = data["foundingDate"]
                        if data.get("numberOfEmployees"):
                            emp = data["numberOfEmployees"]
                            if isinstance(emp, dict):
                                metadata["employees"] = emp.get("value", "")
                            else:
                                metadata["employees"] = str(emp)
                    elif data.get("@type") == "WebSite":
                        metadata["site_name"] = data.get("name", "")
            except (json.JSONDecodeError, TypeError):
                continue

        # OpenGraph tags
        for meta in soup.find_all("meta", property=True):
            prop = meta.get("property", "")
            content = meta.get("content", "")
            if prop == "og:description" and content:
                metadata["og_description"] = content[:300]
            elif prop == "og:site_name" and content:
                metadata["site_name"] = content

        # Meta description
        desc_tag = soup.find("meta", attrs={"name": "description"})
        if desc_tag and desc_tag.get("content"):
            metadata["meta_description"] = str(desc_tag["content"])[:300]

        return metadata

    def _extract_leadership(self, soup: BeautifulSoup) -> list[str]:
        """Try to find leadership/team member names and titles."""
        leaders: list[str] = []
        # Look for common patterns: "Name, Title" or structured team sections
        for el in soup.find_all(["h3", "h4", "strong", "b"]):
            text = el.get_text(strip=True)
            # Pattern: "John Smith" followed by a title-like sibling
            if len(text.split()) in (2, 3) and text[0].isupper():
                next_el = el.find_next_sibling()
                if next_el:
                    title = next_el.get_text(strip=True)
                    if any(k in title.lower() for k in ["ceo", "cto", "cfo", "vp", "director",
                                                         "founder", "president", "chief", "head"]):
                        leaders.append(f"{text} — {title}")
        return leaders[:10]

    def _count_jobs(self, soup: BeautifulSoup) -> int:
        """Estimate the number of job listings on a careers page."""
        # Count elements that look like job postings
        job_links = soup.find_all("a", href=True)
        job_keywords = ["apply", "position", "opening", "role", "job"]
        count = sum(1 for a in job_links if any(k in (a.get_text(strip=True).lower()) for k in job_keywords))
        return max(count, 0)

    def _extract_key_facts(self, soup: BeautifulSoup) -> list[str]:
        """Pull out bullet points, bold/strong text, and short headlines as key facts."""
        facts: list[str] = []

        # Headers (h2, h3) as key topics
        for h in soup.find_all(["h2", "h3"]):
            text = h.get_text(strip=True)
            if 5 < len(text) < 120:
                facts.append(text)

        # List items
        for li in soup.find_all("li"):
            text = li.get_text(strip=True)
            if 10 < len(text) < 200:
                facts.append(text)
                if len(facts) > 25:
                    break

        return facts[:20]
