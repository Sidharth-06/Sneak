"""
Insight generation — 3-tier fallback chain:

  1. Ollama  (local Docker, zero rate limits, runs qwen2.5:7b by default)
  2. OpenRouter free models (cloud, may be rate-limited)
  3. LocalSummarizer (pure keyword extraction, always works)

UPGRADED: Strategic intelligence analyst prompt with 12 categories
including hiring signals, partnerships, strategic recommendations,
and risk assessment.
"""

import json
import re
import asyncio
import httpx
from core.config import settings
from services.rate_limiter import openrouter_limiter
from services.local_summarizer import LocalSummarizer
import logging

logger = logging.getLogger(__name__)

# OpenRouter free models — tried in order (most reliable first)
OPENROUTER_MODELS = [
    "google/gemma-3-4b-it:free",
    "stepfun/step-3.5-flash:free",
    "google/gemma-3-27b-it:free",
    "nvidia/nemotron-3-nano-30b-a3b:free",
]

# ── Strategic Intelligence Prompt ───────────────────────────────────────

_PROMPT_TEMPLATE = '''\
You are a SENIOR COMPETITIVE INTELLIGENCE ANALYST at a top-tier strategy consulting firm.
Your client needs board-ready intelligence on "{company}" to create competitive strategies.

RULES:
1. Extract CONCRETE, ACTIONABLE intelligence — names, numbers, dates, dollar figures.
2. For each insight: include WHO (person/org), WHAT happened, WHEN, and WHY it matters strategically.
3. Cite a real source_url from the content. Do NOT invent URLs.
4. If no data for a category, return [].
5. Max 5 items per category. Prioritize the most strategically significant findings.
6. For strategic_recommendations: synthesize the data into actionable recommendations a competitor could act on.

Return ONLY valid JSON — no markdown fences, no commentary.
{schema}

{categories}

{source_index}

INTELLIGENCE DATA:
{content}'''

# Three focused passes for comprehensive coverage
_PASS_CONFIGS = [
    {
        "name": "core_business",
        "categories": (
            "- pr: Major press releases, announcements, partnerships, executive appointments, corporate restructuring\n"
            "- financial: Revenue figures, valuation, funding rounds, M&A activity, IPO signals, earnings, burn rate\n"
            "- market_analysis: Competitive positioning, market share changes, industry trends, analyst commentary, TAM/SAM estimates\n"
            "- product_roadmap: Product launches, feature releases, beta programs, tech stack changes, API updates, pricing changes"
        ),
        "schema": '{{ "pr": [{{...}}], "financial": [{{...}}], "market_analysis": [{{...}}], "product_roadmap": [{{...}}] }}',
        "keys": ("pr", "financial", "market_analysis", "product_roadmap"),
    },
    {
        "name": "marketing_brand",
        "categories": (
            "- podcasts: Podcast/interview/keynote appearances — show name, host, guest name+title, key messages\n"
            "- social_media: Social media strategy & presence — platform growth, viral moments, content strategy, engagement rates\n"
            "- ads: Ad campaigns, brand activations, digital/OOH/TV — channel, budget if known, creative strategy, target audience\n"
            "- influencers: Creator partnerships, ambassadors — person name, platform, audience size, deal scope, campaign results"
        ),
        "schema": '{{ "podcasts": [{{...}}], "social_media": [{{...}}], "ads": [{{...}}], "influencers": [{{...}}] }}',
        "keys": ("podcasts", "social_media", "ads", "influencers"),
    },
    {
        "name": "strategic_signals",
        "categories": (
            "- hiring_signals: Job openings, team expansion areas, new office locations, key hires, headcount changes — what they're building next\n"
            "- partnerships: Strategic alliances, integrations, distribution deals, joint ventures, ecosystem plays\n"
            "- strategic_recommendations: Based on ALL the data above, provide 3-5 actionable strategies a competitor should execute. Each must be specific and tied to evidence.\n"
            "- risk_assessment: Potential risks, regulatory threats, market headwinds, dependency risks, competitive threats facing this company"
        ),
        "schema": '{{ "hiring_signals": [{{...}}], "partnerships": [{{...}}], "strategic_recommendations": [{{...}}], "risk_assessment": [{{...}}] }}',
        "keys": ("hiring_signals", "partnerships", "strategic_recommendations", "risk_assessment"),
    },
    {
        "name": "osint_intelligence",
        "categories": (
            "- digital_footprint: Technology stack analysis, subdomain infrastructure, CDN/hosting providers, security posture, development tools in use — what their tech choices reveal about strategy\n"
            "- talent_intelligence: Employee names and roles, organizational structure, department sizes, key leadership, hiring patterns by department — what their talent strategy reveals about growth areas"
        ),
        "schema": '{{ "digital_footprint": [{{...}}], "talent_intelligence": [{{...}}] }}',
        "keys": ("digital_footprint", "talent_intelligence"),
    },
]

ALL_CATEGORIES = (
    "pr", "financial", "market_analysis", "product_roadmap",
    "podcasts", "social_media", "ads", "influencers",
    "hiring_signals", "partnerships", "strategic_recommendations", "risk_assessment",
    "digital_footprint", "talent_intelligence",
)


def _build_prompt(
    company_name: str,
    raw_content: str,
    source_metadata: list[dict] | None,
    pass_config: dict | None = None,
) -> str:
    source_index = ""
    if source_metadata:
        lines = [f"  [{i+1}] {s['url']}  |  {s.get('title', '')}" for i, s in enumerate(source_metadata)]
        source_index = "Source URLs for citation:\n" + "\n".join(lines)

    if pass_config:
        schema_block = (
            "Each item must have: {\"title\": \"...\", \"detail\": \"...\", \"date\": \"Month YYYY\", \"source_url\": \"https://...\"}\n"
            f"Return JSON matching this shape: {pass_config['schema']}"
        )
        return _PROMPT_TEMPLATE.format(
            company=company_name,
            schema=schema_block,
            categories=f"Categories to extract:\n{pass_config['categories']}",
            source_index=source_index,
            content=raw_content[:10000],
        )

    # Fallback: single-pass with all categories
    all_cats = "\n".join(cfg["categories"] for cfg in _PASS_CONFIGS)
    return _PROMPT_TEMPLATE.format(
        company=company_name,
        schema='Each item: {"title": "...", "detail": "...", "date": "Month YYYY", "source_url": "https://..."}\nReturn JSON with keys: ' + ", ".join(ALL_CATEGORIES),
        categories=f"Categories:\n{all_cats}",
        source_index=source_index,
        content=raw_content[:10000],
    )


def _parse_json(text: str) -> dict:
    if "```json" in text:
        text = text.split("```json", 1)[1].split("```", 1)[0].strip()
    elif "```" in text:
        text = text.split("```", 1)[1].split("```", 1)[0].strip()
    start = text.find("{")
    end = text.rfind("}") + 1
    if start == -1 or end == 0:
        raise ValueError("No JSON object found in response")
    result = json.loads(text[start:end])

    # Ensure every category exists
    for cat in ALL_CATEGORIES:
        if cat not in result:
            result[cat] = []

    # Normalise every insight item to {title, detail, date, source_url}
    url_pattern = re.compile(r"https?://\S+")
    for cat in ALL_CATEGORIES:
        normalised = []
        for item in result.get(cat, []):
            if isinstance(item, str):
                item = {"title": item, "detail": item, "date": "", "source_url": ""}
            elif isinstance(item, dict):
                detail_parts = [
                    item.get("detail", ""),
                    item.get("description", ""),
                    item.get("rationale", ""),
                    item.get("evidence", ""),
                    item.get("impact", ""),
                    item.get("episode", ""),
                    item.get("channel", ""),
                    item.get("platform", ""),
                    item.get("budget", ""),
                    item.get("followers", ""),
                    item.get("action", ""),
                    item.get("recommendation", ""),
                ]
                combined = " | ".join(str(p) for p in detail_parts if p)

                item = {
                    "title": item.get("title") or item.get("name") or item.get("headline") or item.get("strategy") or "",
                    "detail": combined or item.get("title", ""),
                    "date": item.get("date") or item.get("period") or item.get("year") or item.get("timeline") or "",
                    "source_url": item.get("source_url") or item.get("url") or item.get("link") or "",
                }

                # Strip "[1] " prefix from URLs
                url = item["source_url"]
                if url:
                    m = url_pattern.search(str(url))
                    item["source_url"] = m.group(0).rstrip(".,)") if m else str(url)

            normalised.append(item)
        result[cat] = normalised

    return result


# ── Tier 1: Ollama (local Docker) — 3-pass for small models ───────────────────

async def _try_ollama_single(prompt: str, model: str) -> dict | None:
    """Make a single Ollama call and return parsed JSON or None."""
    url = f"{settings.OLLAMA_URL}/api/chat"
    payload = {
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "stream": False,
        "options": {"temperature": 0.1, "num_predict": 2048, "num_ctx": 4096},
    }
    try:
        async with httpx.AsyncClient(timeout=300.0) as client:
            resp = await client.post(url, json=payload)
        if resp.status_code != 200:
            logger.warning(f"[InsightGenerator] Ollama HTTP {resp.status_code}")
            return None
        text = resp.json()["message"]["content"]
        logger.info(f"[InsightGenerator] Ollama raw ({len(text)} chars)")
        return _parse_json(text)
    except Exception as e:
        logger.warning(f"[InsightGenerator] Ollama call failed: {e}")
        return None


async def _try_ollama(company_name: str, raw_content: str, source_metadata: list[dict] | None) -> dict | None:
    model = settings.OLLAMA_MODEL

    # Pre-check: is Ollama up and model available?
    try:
        async with httpx.AsyncClient(timeout=3.0) as probe:
            tags_resp = await probe.get(f"{settings.OLLAMA_URL}/api/tags")
            if tags_resp.status_code != 200:
                logger.info("[InsightGenerator] Ollama not reachable — skipping.")
                return None
            available = [m["name"].split(":")[0] for m in tags_resp.json().get("models", [])]
            if model.split(":")[0] not in available:
                logger.info(f"[InsightGenerator] Ollama model '{model}' not pulled — skipping.")
                return None
    except Exception as e:
        logger.info(f"[InsightGenerator] Ollama probe failed: {e} — skipping.")
        return None

    logger.info(f"[InsightGenerator] Tier 1 — Ollama ({model}) 3-pass CONCURRENT extraction")

    # Build all 3 prompts
    prompts = [
        _build_prompt(company_name, raw_content, source_metadata, pass_config=cfg)
        for cfg in _PASS_CONFIGS
    ]

    # Fire all passes concurrently
    results = await asyncio.gather(
        *[_try_ollama_single(p, model) for p in prompts]
    )

    merged: dict = {"companyName": company_name}
    all_keys: set = set()

    for i, (result, pass_config) in enumerate(zip(results, _PASS_CONFIGS), 1):
        if result:
            for key in pass_config["keys"]:
                items = result.get(key, [])
                if items:
                    merged[key] = items
                    all_keys.add(key)
                    logger.info(f"[InsightGenerator]   Pass {i} ({pass_config['name']}) {key}: {len(items)} items")
                else:
                    merged.setdefault(key, [])
        else:
            for key in pass_config["keys"]:
                merged.setdefault(key, [])
            logger.info(f"[InsightGenerator]   Pass {i} ({pass_config['name']}) failed")

    if all_keys:
        logger.info(f"[InsightGenerator] Ollama success ✓ — filled {len(all_keys)} categories")
        return merged
    else:
        logger.info("[InsightGenerator] Ollama returned no data across all passes")
        return None


# ── Tier 2: OpenRouter (cloud free models — single pass, larger models) ───────

async def _try_openrouter(company_name: str, raw_content: str, source_metadata: list[dict] | None) -> dict | None:
    if not settings.OPENROUTER_API_KEY:
        logger.info("[InsightGenerator] No OpenRouter key — skipping.")
        return None

    prompt = _build_prompt(company_name, raw_content, source_metadata)  # single-pass for large models

    headers = {
        "Authorization": f"Bearer {settings.OPENROUTER_API_KEY}",
        "HTTP-Referer": "https://sneak-3jg1.onrender.com",
        "X-OpenRouter-Title": "Sneak Intelligence",
        "Content-Type": "application/json",
    }

    for i, model in enumerate(OPENROUTER_MODELS, 1):
        try:
            logger.info(f"[InsightGenerator] OpenRouter {i}/{len(OPENROUTER_MODELS)}: {model}")
            async with httpx.AsyncClient(timeout=90.0) as client:
                resp = await client.post(
                    "https://openrouter.ai/api/v1/chat/completions",
                    headers=headers,
                    json={"model": model, "messages": [{"role": "user", "content": prompt}]},
                )
            if resp.status_code == 429:
                logger.info(f"[InsightGenerator] 429 from {model} — trying next")
                continue
            if resp.status_code != 200:
                logger.info(f"[InsightGenerator] HTTP {resp.status_code} from {model}")
                continue
            text = resp.json()["choices"][0]["message"]["content"]
            logger.info(f"[InsightGenerator] OpenRouter raw ({len(text)} chars)")
            result = _parse_json(text)
            logger.info(f"[InsightGenerator] OpenRouter success with {model} ✓")
            return result
        except json.JSONDecodeError as e:
            logger.warning(f"[InsightGenerator] JSON parse error ({model}): {e}")
        except Exception as e:
            logger.warning(f"[InsightGenerator] Error ({model}): {e}")

    return None


# ── Public entry point ────────────────────────────────────────────────────────

class InsightGenerator:
    async def generate_insights(
        self,
        company_name: str,
        raw_content: str,
        source_metadata: list[dict] | None = None,
    ) -> dict:
        # Tier 1 — OpenRouter cloud (fast, multiple free models)
        result = await _try_openrouter(company_name, raw_content, source_metadata)
        if result:
            result["_source"] = "openrouter"
            result["companyName"] = company_name
            return result

        # Tier 2 — local Ollama GPU (3-pass for small models)
        result = await _try_ollama(company_name, raw_content, source_metadata)
        if result:
            result["_source"] = "ollama"
            return result

        # Tier 3 — local keyword summarizer (always works)
        logger.info(f"[InsightGenerator] All AI tiers failed — local summarizer for '{company_name}'")
        return LocalSummarizer().summarize(company_name, raw_content)
