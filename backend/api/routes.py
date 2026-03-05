from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import Response
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from db.session import get_db, AsyncSessionLocal
from models.company import Company
from models.job import Job
from services.scraper import ScraperService
from services.insight_generator import InsightGenerator
from services.searxng import SearXNGService
from services.google_news import GoogleNewsService
from services.website_scraper import WebsiteScraperService
from services.osint_harvester import OSINTHarvesterService
from services.osint_photon import OSINTPhotonService
from services.pdf_generator import PDFGenerator
from services.email_service import EmailService
from pydantic import BaseModel, EmailStr
import uuid
import asyncio
import logging
import time

logger = logging.getLogger(__name__)
router = APIRouter()

class AnalyzeRequest(BaseModel):
    company_name: str

class EmailRequest(BaseModel):
    email: EmailStr


async def _process_insights(job_id: str, company_name: str):
    """Run the full multi-source scrape → extract → AI pipeline."""
    async with AsyncSessionLocal() as session:
        job = await session.get(Job, job_id)
        if not job:
            return

        try:
            t0 = time.time()

            # ── Phase 1: Multi-source data collection (ALL IN PARALLEL) ──
            job.status = "collecting_data"  # type: ignore[assignment]
            await session.commit()

            search_service = SearXNGService()
            news_service = GoogleNewsService()
            website_service = WebsiteScraperService()
            osint_harvester = OSINTHarvesterService()

            # Fire all 4 data sources simultaneously
            searxng_task = search_service.get_relevant_links(company_name)
            news_task = news_service.fetch_news(company_name, max_items=15)
            website_task = website_service.scrape_company_site(company_name)
            harvester_task = osint_harvester.harvest(company_name)

            searxng_sources, news_items, website_data, osint_data = await asyncio.gather(
                searxng_task, news_task, website_task, harvester_task,
                return_exceptions=True,
            )

            # Handle exceptions from gather
            if isinstance(searxng_sources, Exception):
                logger.error(f"[Pipeline] SearXNG error: {searxng_sources}")
                searxng_sources = []
            if isinstance(news_items, Exception):
                logger.error(f"[Pipeline] Google News error: {news_items}")
                news_items = []
            if isinstance(website_data, Exception):
                logger.error(f"[Pipeline] Website scraper error: {website_data}")
                website_data = {"raw_content": "", "pages": [], "metadata": {}, "hiring_signals": {}}
            if isinstance(osint_data, Exception):
                logger.error(f"[Pipeline] OSINT Harvester error: {osint_data}")
                osint_data = {"raw_content": "", "subdomains": [], "emails": [], "employees": []}

            # ── Phase 1.5: Run Photon deep crawl (needs homepage from website_data) ──
            homepage_url = website_data.get("homepage_url", "") if isinstance(website_data, dict) else ""
            photon_data = {"raw_content": "", "social_profiles": {}, "tech_stack": [], "documents": []}
            if homepage_url:
                try:
                    photon_service = OSINTPhotonService()
                    photon_data = await photon_service.crawl(homepage_url, company_name)
                except Exception as e:
                    logger.error(f"[Pipeline] Photon error: {e}")

            t1 = time.time()
            logger.info(
                f"[Pipeline] Data collection: {t1-t0:.1f}s — "
                f"SearXNG: {len(searxng_sources)} sources, "
                f"News: {len(news_items)} articles, "
                f"Website: {len(website_data.get('pages', []))} pages, "
                f"OSINT: {len(osint_data.get('subdomains', []))} subdomains/{len(osint_data.get('emails', []))} emails, "
                f"Photon: {len(photon_data.get('tech_stack', []))} techs/{len(photon_data.get('social_profiles', {}))} socials"
            )

            # ── Phase 2: Merge sources and deep scrape ──
            job.status = "scraping"  # type: ignore[assignment]
            await session.commit()

            # Combine SearXNG results + Google News URLs for deep scraping
            all_sources = list(searxng_sources)[:20]

            # Add Google News URLs (they're new sources not from SearXNG)
            seen_urls = {s["url"] for s in all_sources}
            for news in news_items:
                if news["url"] not in seen_urls:
                    all_sources.append({
                        "url": news["url"],
                        "title": news.get("title", ""),
                        "snippet": news.get("snippet", ""),
                    })
                    seen_urls.add(news["url"])

            # Cap total sources for scraping
            all_sources = all_sources[:25]

            job.status = "extracting_content"  # type: ignore[assignment]
            await session.commit()

            scraper = ScraperService()
            scraped_content = await scraper.extract_content(all_sources)
            t2 = time.time()
            logger.info(f"[Pipeline] Deep scraping: {len(all_sources)} pages in {t2-t1:.1f}s ({len(scraped_content)} chars)")

            # ── Phase 3: Merge all content for AI ──
            content_parts = [scraped_content]

            # Add website direct scrape content
            if website_data.get("raw_content"):
                content_parts.append(
                    "\n\n====== COMPANY WEBSITE DIRECT SCRAPE ======\n\n"
                    + website_data["raw_content"]
                )

            # Add structured metadata as context
            meta_context = []
            if website_data.get("metadata"):
                meta = website_data["metadata"]
                if meta.get("org_description"):
                    meta_context.append(f"Company description: {meta['org_description']}")
                if meta.get("founded"):
                    meta_context.append(f"Founded: {meta['founded']}")
                if meta.get("employees"):
                    meta_context.append(f"Employees: {meta['employees']}")

            if website_data.get("hiring_signals"):
                hs = website_data["hiring_signals"]
                if hs.get("job_listings_found"):
                    meta_context.append(f"Active job listings detected: {hs['job_listings_found']}")

            if website_data.get("leadership"):
                leaders = website_data["leadership"][:5]
                meta_context.append(f"Leadership team: {'; '.join(leaders)}")

            # Add Google News headlines as context
            if news_items:
                headlines = [f"- {n['title']} ({n.get('published', '')})" for n in news_items[:10]]
                meta_context.append("Recent news headlines:\n" + "\n".join(headlines))

            if meta_context:
                content_parts.append(
                    "\n\n====== STRUCTURED METADATA ======\n\n"
                    + "\n".join(meta_context)
                )

            # Add OSINT harvester data
            if osint_data.get("raw_content"):
                content_parts.append(
                    "\n\n====== OSINT HARVESTER SCAN ======\n\n"
                    + osint_data["raw_content"]
                )

            # Add Photon deep crawl data
            if photon_data.get("raw_content"):
                content_parts.append(
                    "\n\n====== OSINT DEEP CRAWL (TECH STACK & SOCIAL) ======\n\n"
                    + photon_data["raw_content"]
                )

            raw_contents = "\n\n".join(content_parts)

            # ── Phase 4: AI Analysis ──
            job.status = "generating_insights"  # type: ignore[assignment]
            await session.commit()

            generator = InsightGenerator()
            job.status = "waiting_for_ai"  # type: ignore[assignment]
            await session.commit()

            insights = await generator.generate_insights(company_name, raw_contents, source_metadata=all_sources)
            t3 = time.time()
            logger.info(f"[Pipeline] AI analysis: {t3-t2:.1f}s (source: {insights.get('_source','?')})")
            logger.info(f"[Pipeline] TOTAL: {t3-t0:.1f}s for '{company_name}'")

            # Merge additional metadata into insights
            if website_data.get("homepage_url"):
                insights["_homepage_url"] = website_data["homepage_url"]
            insights["_sources_count"] = len(all_sources) + len(website_data.get("pages", []))
            insights["_news_count"] = len(news_items)
            insights["_osint_subdomains"] = len(osint_data.get("subdomains", []))
            insights["_osint_emails"] = len(osint_data.get("emails", []))
            insights["_tech_stack"] = photon_data.get("tech_stack", [])
            insights["_social_profiles"] = photon_data.get("social_profiles", {})

            job.status = "completed"  # type: ignore[assignment]
            job.result_data = insights  # type: ignore[assignment]
            await session.commit()

            # ── Send email if user subscribed ──
            email: str | None = str(job.email) if job.email is not None else None
            if email and not insights.get("error"):
                logger.info(f"[Routes] Sending PDF report to {email} for job {job_id}")
                loop = asyncio.get_event_loop()
                await loop.run_in_executor(None, _send_report, email, insights)

        except Exception as e:
            logger.error(f"[Pipeline] Error: {e}", exc_info=True)
            job.status = "failed"  # type: ignore[assignment]
            job.result_data = {"error": str(e)}  # type: ignore[assignment]
            await session.commit()


def _send_report(email: str, insights: dict):
    """Synchronous helper: generate PDF and send email (runs in thread executor)."""
    try:
        pdf_bytes = PDFGenerator().generate(insights)
        EmailService().send_insights_report(email, insights, pdf_bytes)
    except Exception as exc:
        logger.error(f"[Routes] PDF/email error: {exc}")


@router.post("/analyze")
async def analyze_company(request: AnalyzeRequest, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Company).filter(Company.name == request.company_name))
    company = result.scalars().first()
    
    if not company:
        company = Company(name=request.company_name)
        db.add(company)
        await db.commit()
        await db.refresh(company)
        
    job_id = str(uuid.uuid4())
    job = Job(id=job_id, company_id=company.id, status="pending")
    db.add(job)
    await db.commit()
    
    asyncio.ensure_future(_process_insights(job_id, str(company.name)))
    
    return {"job_id": job_id, "status": "pending", "message": "Deep intelligence pipeline initiated"}

@router.get("/jobs/{job_id}")
async def get_job_status(job_id: str, db: AsyncSession = Depends(get_db)):
    job = await db.get(Job, job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
        
    return {
        "job_id": job.id,
        "status": job.status,
        "company_id": job.company_id,
        "result": job.result_data,
        "email": job.email,
    }


@router.patch("/jobs/{job_id}/email")
async def set_job_email(job_id: str, body: EmailRequest, db: AsyncSession = Depends(get_db)):
    """Store the user's email on the job so we can notify them when done."""
    job = await db.get(Job, job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    job.email = body.email  # type: ignore[assignment]
    await db.commit()

    job_status: str = str(job.status)
    job_result: dict | None = dict(job.result_data) if job.result_data else None  # type: ignore[arg-type]
    if job_status == "completed" and job_result and not job_result.get("error"):
        insights = job_result
        loop = asyncio.get_event_loop()
        asyncio.ensure_future(
            loop.run_in_executor(None, _send_report, str(body.email), insights)
        )
        return {"message": "Email saved. Report is being sent now.", "sent_immediately": True}

    return {"message": "Email saved. We'll send the report when analysis completes.", "sent_immediately": False}


@router.get("/jobs/{job_id}/report")
async def download_report(job_id: str, db: AsyncSession = Depends(get_db)):
    """Generate and return the PDF report for a completed job."""
    job = await db.get(Job, job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    job_status: str = str(job.status)
    job_result: dict | None = dict(job.result_data) if job.result_data else None  # type: ignore[arg-type]
    if job_status != "completed" or not job_result:
        raise HTTPException(status_code=400, detail="Report not ready yet")
    if job_result.get("error"):
        raise HTTPException(status_code=400, detail="Job completed with errors — no report available")

    pdf_bytes = PDFGenerator().generate(job_result)
    company_name = job_result.get("companyName", "company").replace(" ", "_").lower()
    filename = f"{company_name}_intelligence_report.pdf"

    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
