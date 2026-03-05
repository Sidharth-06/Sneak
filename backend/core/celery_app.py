from celery import Celery
from core.config import settings

celery_app = Celery(
    "worker",
    broker=settings.REDIS_URL,
    backend=settings.REDIS_URL,
    include=["worker.tasks"]
)

celery_app.conf.task_routes = {
    "worker.tasks.*": "main-queue"
}
