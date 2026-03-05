"""
Local template-based summarizer — zero-API fallback.

When OpenRouter is rate-limited or down, this module extracts structured
insights directly from the scraped web content using keyword matching,
regex date/name extraction, and simple heuristic scoring.

The output matches the exact same JSON shape as the AI-generated response
so the frontend and PDF renderer work identically.
"""

import re
from dataclasses import dataclass, field

# ── Category keyword banks ────────────────────────────────────────────────────
# Each keyword carries a weight.  Sentences matching more keywords score higher.

PR_KEYWORDS = {
    "announce": 3, "announced": 3, "announcement": 3, "press release": 4,
    "launch": 3, "launched": 3, "launches": 3, "unveil": 3, "unveiled": 3,
    "partnership": 3, "partner": 2, "partners": 2, "acquire": 3, "acquisition": 3,
    "funding": 4, "raised": 4, "valuation": 4, "series": 3, "ipo": 4,
    "revenue": 3, "earnings": 3, "quarterly": 2, "fiscal": 2,
    "appoint": 3, "appointed": 3, "hire": 2, "hired": 2, "ceo": 2, "cto": 2, "cfo": 2,
    "regulatory": 2, "compliance": 2, "filing": 2, "sec": 2,
    "product": 2, "release": 2, "update": 1, "expansion": 2, "expand": 2,
    "milestone": 2, "record": 2, "billion": 3, "million": 3,
}

PODCAST_KEYWORDS = {
    "podcast": 5, "episode": 4, "interview": 3, "interviewed": 3,
    "host": 2, "hosted": 2, "guest": 3, "appeared": 2, "appearance": 2,
    "spoke": 2, "speaking": 2, "conversation": 2, "discussed": 2,
    "show": 1, "listen": 2, "streaming": 1, "spotify": 2, "apple podcasts": 3,
    "youtube": 1, "live": 1, "talk": 1, "fireside": 2, "chat": 1,
}

AD_KEYWORDS = {
    "campaign": 4, "advertising": 4, "advertisement": 4, "ad ": 3,
    "commercial": 4, "super bowl": 5, "brand": 2, "marketing": 3,
    "creative": 2, "media": 1, "digital": 2, "tv": 2, "television": 2,
    "billboard": 3, "ooh": 3, "out-of-home": 3, "spot": 2,
    "promoted": 2, "promotion": 2, "spend": 3, "budget": 3,
    "impressions": 3, "reach": 2, "awareness": 2, "activation": 3,
}

INFLUENCER_KEYWORDS = {
    "influencer": 5, "creator": 4, "ambassador": 4, "brand ambassador": 5,
    "collaboration": 3, "collaborated": 3, "collab": 3,
    "sponsored": 4, "sponsorship": 4,
    "instagram": 3, "tiktok": 3, "youtube": 2, "twitter": 2,
    "followers": 3, "subscriber": 3, "subscribers": 3,
    "partnership": 2, "endorsement": 3, "endorses": 3,
    "unboxing": 3, "review": 1, "content creator": 4,
}

SOCIAL_MEDIA_KEYWORDS = {
    "social media": 5, "twitter": 3, "x.com": 3, "linkedin": 3,
    "tiktok": 3, "instagram": 3, "followers": 4, "following": 3,
    "viral": 4, "engagement": 4, "impressions": 3, "retweet": 3,
    "post": 1, "thread": 2, "hashtag": 3, "trending": 4,
    "community": 2, "audience": 2, "growth": 2, "subscriber": 3,
    "profile": 1, "social": 2, "platform": 1, "milestone": 3,
}

MARKET_ANALYSIS_KEYWORDS = {
    "market share": 5, "competitive": 4, "competitor": 4, "landscape": 3,
    "industry": 3, "analyst": 4, "forecast": 4, "outlook": 4,
    "trend": 3, "growth rate": 4, "addressable market": 5, "tam": 4,
    "positioning": 3, "leader": 2, "disruptor": 3, "market cap": 4,
    "benchmark": 3, "comparison": 2, "ranking": 3, "sector": 2,
    "vertical": 2, "adoption": 3, "penetration": 3,
}

PRODUCT_ROADMAP_KEYWORDS = {
    "product launch": 5, "new feature": 5, "feature": 2, "launch": 3,
    "beta": 4, "preview": 3, "roadmap": 5, "upcoming": 4,
    "release": 3, "update": 2, "version": 3, "api": 2,
    "integration": 3, "deprecat": 3, "migrate": 2, "migration": 2,
    "sdk": 3, "developer": 2, "platform": 1, "tool": 1,
    "announcement": 2, "general availability": 5, "ga ": 3,
}

FINANCIAL_KEYWORDS = {
    "revenue": 5, "valuation": 5, "funding": 5, "series": 4,
    "raised": 4, "ipo": 5, "acquisition": 5, "acquire": 4,
    "merger": 5, "billion": 4, "million": 4, "profit": 4,
    "loss": 3, "earnings": 4, "quarterly": 3, "fiscal": 3,
    "investor": 3, "investment": 3, "stock": 3, "shares": 3,
    "capitalization": 4, "growth": 2, "arr": 4, "mrr": 4,
    "ebitda": 4, "margin": 3, "tender": 3, "secondary": 3,
}

# ── Date extraction ───────────────────────────────────────────────────────────
_MONTH_NAMES = (
    "january|february|march|april|may|june|july|august|september|october|november|december"
    "|jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec"
)
_DATE_RE = re.compile(
    rf"(?:(?:{_MONTH_NAMES})[\s,]+\d{{1,2}}[\s,]+\d{{4}})"   # March 15, 2025
    rf"|(?:(?:{_MONTH_NAMES})[\s,]+\d{{4}})"                   # March 2025
    rf"|(?:Q[1-4]\s+\d{{4}})"                                  # Q1 2025
    rf"|(?:\d{{1,2}}/\d{{1,2}}/\d{{4}})"                       # 03/15/2025
    rf"|(?:\d{{4}}-\d{{2}}-\d{{2}})",                           # 2025-03-15
    re.IGNORECASE,
)

# ── Helpers ───────────────────────────────────────────────────────────────────

@dataclass
class _SourceBlock:
    url: str = ""
    title: str = ""
    content: str = ""


@dataclass
class _ScoredInsight:
    sentence: str
    score: float = 0.0
    date: str = ""
    source_url: str = ""
    source_title: str = ""


def _parse_source_blocks(raw_content: str) -> list[_SourceBlock]:
    """Split the '======'-delimited scraped content into per-source blocks."""
    blocks: list[_SourceBlock] = []
    for chunk in raw_content.split("======"):
        chunk = chunk.strip()
        if not chunk:
            continue
        b = _SourceBlock()
        for line in chunk.splitlines():
            if line.startswith("SOURCE_URL:"):
                b.url = line.split("SOURCE_URL:", 1)[1].strip()
            elif line.startswith("SOURCE_TITLE:"):
                b.title = line.split("SOURCE_TITLE:", 1)[1].strip()
            elif line.startswith("CONTENT"):
                # Everything after the CONTENT line is the body
                idx = chunk.index(line) + len(line)
                b.content = chunk[idx:].strip()
                break
        if not b.content and not b.url:
            b.content = chunk  # raw text with no labels
        blocks.append(b)
    return blocks


def _extract_sentences(text: str) -> list[str]:
    """Rough sentence splitting that keeps meaningful chunks."""
    # Split on period/newline but keep sentences > 40 chars
    raw = re.split(r'(?<=[.!?])\s+|\n+', text)
    return [s.strip() for s in raw if len(s.strip()) >= 40]


def _score_sentence(sentence: str, keyword_bank: dict[str, int]) -> float:
    lower = sentence.lower()
    score = 0.0
    for kw, weight in keyword_bank.items():
        if kw in lower:
            score += weight
    return score


def _find_date(sentence: str) -> str:
    m = _DATE_RE.search(sentence)
    return m.group(0).strip() if m else ""


def _make_title(sentence: str, max_words: int = 10) -> str:
    """First N words of the sentence, cleaned up."""
    words = sentence.split()[:max_words]
    title = " ".join(words)
    # Remove trailing punctuation
    title = title.rstrip(".,;:!?")
    if len(words) == max_words:
        title += "…"
    return title


def _extract_for_category(
    blocks: list[_SourceBlock],
    keyword_bank: dict[str, int],
    company_name: str,
    max_items: int = 5,
) -> list[dict]:
    """Score every sentence across all source blocks, return top-N as insight dicts."""
    scored: list[_ScoredInsight] = []
    company_lower = company_name.lower()

    for block in blocks:
        sentences = _extract_sentences(block.content)
        for sent in sentences:
            base_score = _score_sentence(sent, keyword_bank)
            if base_score < 3:
                continue  # skip irrelevant sentences

            # Boost if the company is mentioned
            if company_lower in sent.lower():
                base_score += 2

            date = _find_date(sent)
            if date:
                base_score += 2  # dated facts are more valuable

            scored.append(_ScoredInsight(
                sentence=sent,
                score=base_score,
                date=date,
                source_url=block.url,
                source_title=block.title,
            ))

    # Deduplicate by checking overlap (simple Jaccard on word sets)
    scored.sort(key=lambda s: s.score, reverse=True)
    selected: list[_ScoredInsight] = []
    seen_word_sets: list[set[str]] = []
    for item in scored:
        words = set(item.sentence.lower().split())
        is_dup = False
        for existing in seen_word_sets:
            overlap = len(words & existing) / max(len(words | existing), 1)
            if overlap > 0.6:
                is_dup = True
                break
        if not is_dup:
            selected.append(item)
            seen_word_sets.append(words)
        if len(selected) >= max_items:
            break

    return [
        {
            "title": _make_title(s.sentence),
            "detail": s.sentence,
            "date": s.date if s.date else "Date not specified",
            "source_url": s.source_url,
        }
        for s in selected
    ]


class LocalSummarizer:
    """
    Extracts structured insights from scraped content using keyword heuristics.
    No API calls — runs instantly, never rate-limited.
    """

    def summarize(self, company_name: str, raw_content: str) -> dict:
        blocks = _parse_source_blocks(raw_content)

        if not blocks:
            return {
                "companyName": company_name,
                "pr": [], "podcasts": [], "ads": [], "influencers": [],
                "social_media": [], "market_analysis": [], "product_roadmap": [], "financial": [],
                "_source": "local_summarizer",
            }

        pr = _extract_for_category(blocks, PR_KEYWORDS, company_name, max_items=6)
        podcasts = _extract_for_category(blocks, PODCAST_KEYWORDS, company_name, max_items=4)
        ads = _extract_for_category(blocks, AD_KEYWORDS, company_name, max_items=4)
        influencers = _extract_for_category(blocks, INFLUENCER_KEYWORDS, company_name, max_items=4)
        social_media = _extract_for_category(blocks, SOCIAL_MEDIA_KEYWORDS, company_name, max_items=4)
        market_analysis = _extract_for_category(blocks, MARKET_ANALYSIS_KEYWORDS, company_name, max_items=4)
        product_roadmap = _extract_for_category(blocks, PRODUCT_ROADMAP_KEYWORDS, company_name, max_items=4)
        financial = _extract_for_category(blocks, FINANCIAL_KEYWORDS, company_name, max_items=4)

        return {
            "companyName": company_name,
            "pr": pr,
            "podcasts": podcasts,
            "ads": ads,
            "influencers": influencers,
            "social_media": social_media,
            "market_analysis": market_analysis,
            "product_roadmap": product_roadmap,
            "financial": financial,
            "_source": "local_summarizer",
        }
