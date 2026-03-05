"""
Google News RSS scraper — fetches structured news articles for a company.
No API key needed. Uses Google News RSS feed which returns XML with
titles, dates, sources, and links.
"""

import httpx
from bs4 import BeautifulSoup
import asyncio
import logging
from datetime import datetime

logger = logging.getLogger(__name__)


class GoogleNewsService:
    """Scrape Google News RSS for structured, dated news items."""

    RSS_URL = "https://news.google.com/rss/search"

    async def fetch_news(self, company_name: str, max_items: int = 15) -> list[dict]:
        """
        Returns list of {title, url, published, source} dicts.
        Fires multiple queries in parallel for broader coverage.
        """
        queries = [
            f'"{company_name}" company',
            f'"{company_name}" funding OR partnership OR acquisition',
            f'"{company_name}" product launch OR expansion',
        ]

        async with httpx.AsyncClient(timeout=10.0) as client:
            tasks = [self._fetch_rss(client, q) for q in queries]
            all_batches = await asyncio.gather(*tasks, return_exceptions=True)

        seen_urls: set[str] = set()
        results: list[dict] = []

        for batch in all_batches:
            if isinstance(batch, Exception):
                continue
            for item in batch:
                url = item.get("url", "")
                if url and url not in seen_urls:
                    seen_urls.add(url)
                    results.append(item)

        results.sort(key=lambda x: x.get("published", ""), reverse=True)
        logger.info(f"[GoogleNews] {len(results)} articles for '{company_name}'")
        return results[:max_items]

    async def _fetch_rss(self, client: httpx.AsyncClient, query: str) -> list[dict]:
        """Parse a single Google News RSS feed query."""
        try:
            response = await client.get(
                self.RSS_URL,
                params={"q": query, "hl": "en-US", "gl": "US", "ceid": "US:en"},
                headers={"User-Agent": "Mozilla/5.0"},
            )
            if response.status_code != 200:
                return []

            soup = BeautifulSoup(response.text, "xml")
            items = []
            for entry in soup.find_all("item"):
                title_tag = entry.find("title")
                link_tag = entry.find("link")
                pub_tag = entry.find("pubDate")
                source_tag = entry.find("source")

                title = title_tag.get_text(strip=True) if title_tag else ""
                link = link_tag.get_text(strip=True) if link_tag else ""
                pub_date = pub_tag.get_text(strip=True) if pub_tag else ""
                source = source_tag.get_text(strip=True) if source_tag else ""

                # Parse date to standard format
                date_str = ""
                if pub_date:
                    try:
                        dt = datetime.strptime(pub_date, "%a, %d %b %Y %H:%M:%S %Z")
                        date_str = dt.strftime("%B %Y")
                    except ValueError:
                        date_str = pub_date[:20]

                if title and link:
                    items.append({
                        "title": title,
                        "url": link,
                        "published": date_str,
                        "source": source,
                        "snippet": f"{title} — reported by {source}" if source else title,
                    })
            return items
        except Exception as e:
            logger.warning(f"[GoogleNews] RSS error: {e}")
            return []
