"""
Enhanced scraper — uses BeautifulSoup for deep structured extraction:
- JSON-LD schema data
- OpenGraph metadata
- HTML tables → readable text
- Key facts (headlines, bullet points, bold text)
- Press release detection
- Increased content limit for richer AI input
"""

import httpx
from bs4 import BeautifulSoup
import asyncio
import json
import re
import logging

logger = logging.getLogger(__name__)


class ScraperService:
    async def extract_content(self, sources: list[dict]) -> str:
        """
        Accept list of {url, title, snippet} dicts from SearXNG / Google News.
        Returns a single string with each source deeply extracted.
        """
        all_sections: list[str] = []
        sem = asyncio.Semaphore(12)

        async with httpx.AsyncClient(
            timeout=10.0,
            follow_redirects=True,
            limits=httpx.Limits(max_connections=15, max_keepalive_connections=10),
        ) as client:
            tasks = [self._fetch(client, src, sem) for src in sources]
            results = await asyncio.gather(*tasks, return_exceptions=True)

            for src, res in zip(sources, results):
                if isinstance(res, str) and res:
                    all_sections.append(res)
                elif src.get("snippet"):
                    all_sections.append(
                        f"SOURCE_URL: {src['url']}\n"
                        f"SOURCE_TITLE: {src.get('title', '')}\n"
                        f"CONTENT (snippet only):\n{src['snippet']}"
                    )

        return "\n\n======\n\n".join(all_sections)

    async def _fetch(self, client: httpx.AsyncClient, src: dict, sem: asyncio.Semaphore) -> str:
        url = src.get("url", "")
        if not url:
            return ""

        async with sem:
            try:
                headers = {
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                                  "AppleWebKit/537.36 (KHTML, like Gecko) "
                                  "Chrome/120.0.0.0 Safari/537.36",
                    "Accept": "text/html,application/xhtml+xml",
                    "Accept-Language": "en-US,en;q=0.9",
                }
                response = await client.get(url, headers=headers)
                if response.status_code != 200:
                    return ""

                ct = response.headers.get("content-type", "")
                if "html" not in ct and "text" not in ct:
                    return ""

                soup = BeautifulSoup(response.text, "html.parser")

                # ── 1. Extract structured metadata ──
                structured_data = self._extract_structured_data(soup)

                # ── 2. Detect content type ──
                content_type = self._detect_content_type(url, soup)

                # ── 3. Extract key facts (headlines, bullets, bold) ──
                key_facts = self._extract_key_facts(soup)

                # ── 4. Extract tables as text ──
                table_text = self._extract_tables(soup)

                # ── 5. Clean main body text ──
                for tag in soup(["script", "style", "nav", "footer", "header",
                                 "aside", "iframe", "noscript", "svg", "form",
                                 "button", "input"]):
                    tag.decompose()

                text = soup.get_text(separator=" ")
                lines = (line.strip() for line in text.splitlines())
                chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
                clean_text = " ".join(c for c in chunks if c)

                # ── Assemble rich output ──
                parts = [
                    f"SOURCE_URL: {url}",
                    f"SOURCE_TITLE: {src.get('title', '')}",
                    f"CONTENT_TYPE: {content_type}",
                ]

                if structured_data:
                    parts.append(f"STRUCTURED_DATA: {structured_data}")

                if key_facts:
                    parts.append("KEY_FACTS:\n" + "\n".join(f"• {f}" for f in key_facts[:15]))

                if table_text:
                    parts.append(f"TABLES:\n{table_text[:1500]}")

                parts.append(f"CONTENT:\n{clean_text[:5000]}")

                return "\n".join(parts)
            except Exception as e:
                logger.debug(f"[Scraper] Error fetching {url}: {e}")
                return ""

    def _extract_structured_data(self, soup: BeautifulSoup) -> str:
        """Extract JSON-LD and OpenGraph metadata as a compact string."""
        facts: list[str] = []

        # JSON-LD
        for script in soup.find_all("script", type="application/ld+json"):
            try:
                data = json.loads(script.string or "")
                if isinstance(data, dict):
                    dtype = data.get("@type", "")
                    if dtype in ("NewsArticle", "Article", "BlogPosting"):
                        facts.append(f"Article: {data.get('headline', '')}")
                        if data.get("datePublished"):
                            facts.append(f"Published: {data['datePublished'][:10]}")
                        if data.get("author"):
                            author = data["author"]
                            if isinstance(author, dict):
                                facts.append(f"Author: {author.get('name', '')}")
                            elif isinstance(author, list) and author:
                                names = [a.get("name", "") for a in author if isinstance(a, dict)]
                                facts.append(f"Authors: {', '.join(names)}")
                    elif dtype == "Organization":
                        if data.get("name"):
                            facts.append(f"Org: {data['name']}")
                        if data.get("description"):
                            facts.append(f"Desc: {data['description'][:200]}")
                        if data.get("foundingDate"):
                            facts.append(f"Founded: {data['foundingDate']}")
                        if data.get("numberOfEmployees"):
                            emp = data["numberOfEmployees"]
                            val = emp.get("value", emp) if isinstance(emp, dict) else emp
                            facts.append(f"Employees: {val}")
            except (json.JSONDecodeError, TypeError):
                continue

        # OpenGraph
        for meta in soup.find_all("meta", property=True):
            prop = meta.get("property", "")
            content = meta.get("content", "")
            if prop == "og:description" and content:
                facts.append(f"OG: {content[:200]}")
            elif prop == "article:published_time" and content:
                facts.append(f"Published: {content[:10]}")

        return " | ".join(facts[:10]) if facts else ""

    def _detect_content_type(self, url: str, soup: BeautifulSoup) -> str:
        """Classify the page: press_release, news, blog, financial, general."""
        url_lower = url.lower()
        text_lower = (soup.get_text()[:500]).lower()

        if any(k in url_lower for k in ["/press", "/news", "/pr/", "/media"]):
            return "press_release"
        if any(k in url_lower for k in ["/blog", "/article", "/post"]):
            return "blog"
        if any(k in text_lower for k in ["earnings", "revenue", "quarterly", "fiscal", "sec filing"]):
            return "financial_report"
        if any(k in text_lower for k in ["partnership", "strategic alliance", "collaboration"]):
            return "partnership_announcement"
        if any(k in text_lower for k in ["launched", "introducing", "new product", "release"]):
            return "product_launch"
        return "general"

    def _extract_key_facts(self, soup: BeautifulSoup) -> list[str]:
        """Pull headlines, bold text, and bullet points as key facts."""
        facts: list[str] = []

        # Headlines
        for h in soup.find_all(["h1", "h2", "h3"]):
            text = h.get_text(strip=True)
            if 8 < len(text) < 150:
                facts.append(text)

        # Strong/bold text (often contains key data points)
        for strong in soup.find_all(["strong", "b"]):
            text = strong.get_text(strip=True)
            if 8 < len(text) < 150 and text not in facts:
                # Filter out navigation-like text
                if not any(k in text.lower() for k in ["click", "subscribe", "sign up", "cookie"]):
                    facts.append(text)
                    if len(facts) > 20:
                        break

        return facts

    def _extract_tables(self, soup: BeautifulSoup) -> str:
        """Convert HTML tables to readable text (great for financial data)."""
        table_texts: list[str] = []

        for table in soup.find_all("table"):
            rows: list[str] = []
            for tr in table.find_all("tr"):
                cells = [td.get_text(strip=True) for td in tr.find_all(["td", "th"])]
                if cells and any(c for c in cells):
                    rows.append(" | ".join(cells))
            if rows:
                table_texts.append("\n".join(rows[:15]))  # Cap rows per table
                if len(table_texts) >= 3:
                    break

        return "\n---\n".join(table_texts) if table_texts else ""
