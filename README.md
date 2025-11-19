# Phoenix

Content generation engine with Zep-centric architecture, deep research, and unified workflows.

## Architecture

Phoenix is built on three core principles:

1. **Zep-First** - Check knowledge graph before research, enrich with context, deposit back as hybrid (narrative + entities)
2. **Deep Research** - Serper pages 1+2 → Smart filtering → Crawl4AI everything → 53% cost savings vs Exa
3. **Unified Worker** - Single worker runs both CompanyCreationWorkflow and ArticleCreationWorkflow

## Project Structure

```
phoenix/
├── gateway/           # FastAPI HTTP API
├── worker/            # Unified Temporal worker
│   ├── workflows/     # CompanyCreation, ArticleCreation
│   ├── activities/    # Shared activities pool
│   └── models/        # Pydantic models
├── crawl-service/     # Playwright/Crawl4AI microservice
├── streamlit/         # Dual-mode dashboard
├── shared/            # Shared utilities
└── docs/              # Documentation
```

## Services

| Service | Port | Purpose |
|---------|------|---------|
| Gateway | 8000 | Public HTTP API |
| Worker | - | Temporal worker (background) |
| Crawl Service | 8080 | Browser automation |
| Streamlit | 8501 | Internal dashboard |

## Task Queue

Single unified queue: `phoenix-queue`

## Environment Variables

```bash
# Temporal
TEMPORAL_ADDRESS=europe-west3.gcp.api.temporal.io:7233
TEMPORAL_NAMESPACE=quickstart-quest.zivkb
TEMPORAL_API_KEY=<key>
TEMPORAL_TASK_QUEUE=phoenix-queue

# Database
DATABASE_URL=postgresql://...neon.tech/neondb

# AI
ANTHROPIC_API_KEY=<key>

# Research
SERPER_API_KEY=<key>
EXA_API_KEY=<key>  # Optional
FIRECRAWL_API_KEY=<key>

# Media
CLOUDINARY_URL=cloudinary://<key>:<secret>@<cloud>
FLUX_API_KEY=<key>

# Knowledge Graph
ZEP_API_KEY=<key>

# Services
CRAWL_SERVICE_URL=http://crawl-service:8080
```

## Development

```bash
# Clone
git clone https://github.com/Londondannyboy/phoenix.git
cd phoenix

# Gateway
cd gateway
pip install -r requirements.txt
uvicorn main:app --reload

# Worker
cd worker
pip install -r requirements.txt
python worker.py

# Streamlit
cd streamlit
pip install -r requirements.txt
streamlit run app.py
```

## Deployment

Railway with RAILPACK for unified worker:

```bash
railway up
```

## Cost per Workflow

| Workflow | Timeline | Cost |
|----------|----------|------|
| Company Profile | 90-150s | $0.07 |
| Article | 5-12min | $0.10 |

## License

Private - Proprietary
