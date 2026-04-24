# Sneak — AI-Powered Company Intelligence

**Sneak** is an open-source competitive intelligence platform that automatically gathers, analyzes, and summarizes deep insights about any company. Enter a company name and Sneak runs a multi-source OSINT pipeline — web search, news, direct website scraping, and deep crawl — then uses an LLM to generate board-ready strategic intelligence across 14 categories.

---

## Features

- **Multi-source data collection** — SearXNG web search, Google News, direct website scraping, OSINT harvesting, and Photon deep crawl, all run in parallel
- **AI-powered analysis** — 3-tier LLM fallback: local Ollama → OpenRouter free models → keyword summarizer (always works offline)
- **14 intelligence categories** — PR, podcasts, ads, influencers, social media, market analysis, product roadmap, financials, hiring signals, partnerships, strategic recommendations, risk assessment, digital footprint, and talent intelligence
- **PDF report generation** — download a formatted intelligence report from the UI or receive it via email
- **Email delivery** — reports sent via [Resend](https://resend.com) or SMTP (Brevo)
- **Async job pipeline** — jobs are processed in the background; poll for status or subscribe to email notifications

---

## Tech Stack

| Layer | Technology |
|---|---|
| Frontend | Next.js 15, TypeScript, Tailwind CSS, Framer Motion |
| Backend | FastAPI, Python 3.11+, asyncpg, SQLAlchemy (async) |
| Task queue | Celery + Redis |
| Database | PostgreSQL 15 |
| Search | SearXNG (self-hosted) |
| LLM | Ollama (local) / OpenRouter (cloud) |
| PDF | ReportLab |
| Email | Resend / SMTP (Brevo) |

---

## Quick Start (Docker)

### Prerequisites

- [Docker](https://docs.docker.com/get-docker/) & Docker Compose

### 1. Clone the repo

```bash
git clone https://github.com/Sidharth-06/Sneak.git
cd Sneak
```

### 2. Configure environment variables

```bash
cp backend/.env.example backend/.env
```

**`backend/.env`**

```env
POSTGRES_SERVER=postgres
POSTGRES_USER=user
POSTGRES_PASSWORD=password
POSTGRES_DB=insights_db

REDIS_URL=redis://redis:6379/0
SEARXNG_URL=http://searxng:8080

# LLM — pick one (or both; Ollama is tried first)
OLLAMA_URL=http://host.docker.internal:11434
OPENROUTER_API_KEY=          # optional

# Email (optional)
RESEND_API_KEY=
RESEND_FROM=onboarding@resend.dev
```

### 3. Start all services

```bash
docker compose up --build
```

| Service | URL |
|---|---|
| Frontend | http://localhost:3000 |
| Backend API | http://localhost:8000 |
| API docs (Swagger) | http://localhost:8000/docs |
| SearXNG | http://localhost:8080 |

---

## Local Development (without Docker)

See [LOCAL_SETUP.md](LOCAL_SETUP.md) for a step-by-step Windows guide.

### Backend

```bash
cd backend
python -m venv venv
source venv/bin/activate   # Windows: venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env       # fill in your values
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

### Frontend

```bash
cd frontend
npm install
echo "NEXT_PUBLIC_API_URL=http://localhost:8000/api/v1" > .env.local
npm run dev
```

### Infrastructure (Redis + PostgreSQL)

You need PostgreSQL and Redis running locally, or spin them up with Docker:

```bash
docker compose up postgres redis searxng
```

---

## API Reference

All endpoints are prefixed with `/api/v1`.

| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/analyze` | Start an intelligence analysis job |
| `GET` | `/jobs/{job_id}` | Poll job status and results |
| `PATCH` | `/jobs/{job_id}/email` | Subscribe to email delivery for a job |
| `GET` | `/jobs/{job_id}/report` | Download the PDF report (job must be `completed`) |

### Start analysis

```http
POST /api/v1/analyze
Content-Type: application/json

{
  "company_name": "Acme Corp",
  "email": "you@example.com"   // optional
}
```

Returns `{ "job_id": "...", "status": "pending" }`.

### Job status flow

```
pending → collecting_data → scraping → extracting_content → generating_insights → waiting_for_ai → completed / failed
```

---

## Intelligence Categories

| Category | What Sneak extracts |
|---|---|
| `pr` | Press releases, media coverage, public announcements |
| `podcasts` | Podcast appearances, interviews |
| `ads` | Active advertising campaigns and messaging |
| `influencers` | Brand ambassador and influencer partnerships |
| `social_media` | Social activity, engagement trends |
| `market_analysis` | Competitive positioning, market share signals |
| `product_roadmap` | Upcoming product launches and features |
| `financial` | Funding rounds, revenue signals, financial news |
| `hiring_signals` | Open roles, headcount growth, skill gaps |
| `partnerships` | Integrations, alliances, co-marketing deals |
| `strategic_recommendations` | Synthesized actionable recommendations |
| `risk_assessment` | Legal, regulatory, reputational risks |
| `digital_footprint` | Subdomains, exposed infrastructure, tech stack |
| `talent_intelligence` | Key executives, team composition, departures |

---

## LLM Configuration

Sneak uses a **3-tier fallback chain** for AI analysis:

1. **Ollama** (local, zero rate limits) — set `OLLAMA_URL` and pull a model:
   ```bash
   ollama pull qwen2.5:3b
   ```

2. **OpenRouter free models** — set `OPENROUTER_API_KEY`; Sneak automatically tries `google/gemma-3-4b-it:free` and others

3. **LocalSummarizer** — pure keyword extraction, no API key needed, always works offline

---

## Project Structure

```
Sneak/
├── backend/
│   ├── api/           # FastAPI routes
│   ├── core/          # Config, Celery setup
│   ├── db/            # Database session
│   ├── models/        # SQLAlchemy ORM models
│   ├── services/      # Scraping, OSINT, AI, PDF, email
│   ├── migrations/    # Alembic migrations
│   └── main.py
├── frontend/
│   └── src/app/       # Next.js app router pages
├── docker-compose.yml
└── setup_database.sql
```

---

## Contributing

1. Fork the repository
2. Create a feature branch: `git checkout -b feature/your-feature`
3. Commit your changes: `git commit -m "feat: add your feature"`
4. Push and open a Pull Request

---

## License

This project is open source. See [LICENSE](LICENSE) for details.
