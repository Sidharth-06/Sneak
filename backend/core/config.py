from pydantic import computed_field
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    API_V1_STR: str = "/api/v1"
    PROJECT_NAME: str = "Sneak"
    PORT: int = 8000
    
    # CORS — accepts comma-separated origins via env var
    BACKEND_CORS_ORIGINS: list[str] = [
        "http://localhost:3000",
        "http://localhost",
        "http://127.0.0.1:3000",
        "http://127.0.0.1",
    ]
    # Extra origins from env (comma-separated), e.g. "https://sneak.vercel.app,https://sneak-api.onrender.com"
    EXTRA_CORS_ORIGINS: str = ""
    
    # Redis & Celery
    REDIS_URL: str = "redis://localhost:6379/0"

    # DB — individual fields (used locally via docker-compose)
    POSTGRES_SERVER: str = "localhost"
    POSTGRES_USER: str = "user"
    POSTGRES_PASSWORD: str = "password"
    POSTGRES_DB: str = "insights_db"
    
    # Full DATABASE_URL (used by Render/Neon/Railway — takes priority)
    DATABASE_URL: str = ""

    @computed_field  # type: ignore[prop-decorator]
    @property
    def SQLALCHEMY_DATABASE_URI(self) -> str:
        if self.DATABASE_URL:
            url = self.DATABASE_URL
            # asyncpg needs postgresql+asyncpg://
            if url.startswith("postgres://"):
                url = url.replace("postgres://", "postgresql+asyncpg://", 1)
            elif url.startswith("postgresql://"):
                url = url.replace("postgresql://", "postgresql+asyncpg://", 1)
            return url
        return f"postgresql+asyncpg://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}@{self.POSTGRES_SERVER}/{self.POSTGRES_DB}"

    @property
    def all_cors_origins(self) -> list[str]:
        origins = list(self.BACKEND_CORS_ORIGINS)
        if self.EXTRA_CORS_ORIGINS:
            origins.extend([o.strip() for o in self.EXTRA_CORS_ORIGINS.split(",") if o.strip()])
        return origins

    # SearXNG
    SEARXNG_URL: str = "http://localhost:8080"

    # Ollama (local LLM — no rate limits)
    OLLAMA_URL: str = "http://localhost:11434"
    OLLAMA_MODEL: str = "qwen2.5:3b"

    # OpenRouter
    OPENROUTER_API_KEY: str = ""

    # Resend (primary email delivery)
    RESEND_API_KEY: str = ""
    RESEND_FROM: str = "onboarding@resend.dev"

    # SMTP fallback (Gmail / any provider) — only used if RESEND_API_KEY is empty
    SMTP_HOST: str = "smtp.gmail.com"
    SMTP_PORT: int = 587
    SMTP_USER: str = ""
    SMTP_PASS: str = ""
    SMTP_FROM: str = "Company Insights <noreply@example.com>"
    SMTP_ENABLED: bool = False

    class Config:
        case_sensitive = True
        env_file = ".env"

settings = Settings()
