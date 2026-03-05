from core.celery_app import celery_app
from db.session import AsyncSessionLocal
from models.job import Job
from services.scraper import ScraperService
from services.insight_generator import InsightGenerator
from services.searxng import SearXNGService
import asyncio

@celery_app.task(name="worker.tasks.process_company_insights")
def process_company_insights(job_id: str, company_name: str, company_id: int):
    # Celery tasks are synchronous by default, but we can run an async loop
    return asyncio.run(_async_process_company_insights(job_id, company_name, company_id))

async def _async_process_company_insights(job_id: str, company_name: str, company_id: int):
    async with AsyncSessionLocal() as session:
        job = await session.get(Job, job_id)
        if not job:
            return
            
        try:
            job.status = "scraping"
            await session.commit()
            
            # 1. Search for urls
            search_service = SearXNGService()
            urls = await search_service.get_relevant_links(company_name)
            
            job.status = "extracting_content"
            await session.commit()
            
            # 2. Extract content from URLs
            scraper = ScraperService()
            raw_contents = await scraper.extract_content(urls)
            
            job.status = "generating_insights"
            await session.commit()
            
            # 3. Generate Insights
            generator = InsightGenerator()
            insights = await generator.generate_insights(company_name, raw_contents)
            
            job.status = "completed"
            job.result_data = insights
            await session.commit()
            
            return insights
            
        except Exception as e:
            job.status = "failed"
            job.result_data = {"error": str(e)}
            await session.commit()
            raise e
