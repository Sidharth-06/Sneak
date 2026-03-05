"""
SearXNG search service — generates diverse intelligence queries
for comprehensive competitive analysis.
"""

import asyncio
import httpx
import logging
from core.config import settings

logger = logging.getLogger(__name__)


class SearXNGService:
    def __init__(self) -> None:
        self.base_url: str = settings.SEARXNG_URL

    async def get_relevant_links(self, company_name: str, max_results: int = 8) -> list[dict]:
        """
        Returns a list of {url, title, snippet} dicts.
        Fires 12 category queries in parallel for deep, diverse coverage.
        """
        ctx = f"{company_name} company"
        queries = [
            # ── Core Business Intel ──
            f'"{company_name}" press release announcement OR partnership 2024 2025 2026',
            f'"{company_name}" revenue valuation funding round financial results 2025 2026',
            f'"{company_name}" market analysis competitive landscape market share industry',
            f'"{company_name}" product launch roadmap features release 2025 2026',

            # ── Marketing & Brand ──
            f'"{company_name}" advertising campaign marketing brand strategy 2024 2025',
            f'"{company_name}" influencer partnership creator collaboration brand deal',
            f'"{company_name}" social media strategy twitter linkedin tiktok followers growth',
            f'"{company_name}" CEO founder podcast interview keynote speech 2024 2025',

            # ── Strategic Signals ──
            f'"{company_name}" hiring expanding engineering team job openings 2025',
            f'"{company_name}" patent filing innovation R&D technology',
            f'"{company_name}" partnership strategic alliance integration collaboration',
            f'"{company_name}" executive leadership CEO CTO appointment board changes',
        ]

        BLOCKED_DOMAINS = {
            "city-data.com", "wikipedia.org", "youtube.com", "reddit.com",
            "quora.com", "pinterest.com", "instagram.com", "facebook.com",
            "twitter.com", "x.com", "tiktok.com", "amazon.com", "ebay.com",
            "indeed.com", "glassdoor.com", "linkedin.com", "wannagosailing.com",
        }

        def _is_blocked(url: str) -> bool:
            try:
                from urllib.parse import urlparse
                host = urlparse(url).hostname or ""
                return any(host == d or host.endswith(f".{d}") for d in BLOCKED_DOMAINS)
            except Exception:
                return False

        seen_urls: set[str] = set()
        results_meta: list[dict] = []

        async def _run_query(client: httpx.AsyncClient, query: str) -> list:
            """Fire a SearXNG query — no sleep needed for our own local instance."""
            try:
                response = await client.get(
                    f"{self.base_url}/search",
                    params={"q": query, "format": "json"},
                )
                if response.status_code == 200:
                    return response.json().get("results", [])[:max_results]
            except Exception as e:
                logger.warning(f"[SearXNG] Error for '{query[:50]}...': {e}")
            return []

        # Fire ALL queries in parallel — our own SearXNG has no rate limit
        async with httpx.AsyncClient(timeout=10.0) as client:
            all_results = await asyncio.gather(
                *[_run_query(client, q) for q in queries]
            )

        for batch in all_results:
            for res in batch:
                url = res.get("url", "")
                if url and url not in seen_urls and not _is_blocked(url):
                    seen_urls.add(url)
                    results_meta.append({
                        "url":     url,
                        "title":   res.get("title", ""),
                        "snippet": res.get("content", ""),
                    })

        logger.info(f"[SearXNG] {len(results_meta)} unique sources for '{company_name}'")
        return results_meta
