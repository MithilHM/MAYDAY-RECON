# MAYDAY RECON

Reconnaissance and analysis platform built with FastAPI and Next.js.

## Project Structure

```
mayday-recon/
├── apps/
│   ├── api/                # FastAPI backend
│   │   ├── app/
│   │   │   ├── __init__.py
│   │   │   ├── main.py     # FastAPI application entry
│   │   │   └── routers/
│   │   │       └── health.py
│   │   ├── Dockerfile
│   │   ├── requirements.txt
│   │   └── .env.example
│   └── web/                # Next.js frontend
│       ├── src/
│       │   └── app/
│       │       ├── globals.css
│       │       ├── layout.tsx
│       │       └── page.tsx
│       ├── Dockerfile
│       ├── package.json
│       ├── tsconfig.json
│       ├── tailwind.config.ts
│       └── next.config.ts
├── docker-compose.yml
├── .gitignore
└── README.md
```

## Prerequisites

- Python 3.12+
- Node.js v24+
- Docker & Docker Compose (optional)

## Quick Start

### With Docker

```bash
docker compose up --build
```

- API: http://localhost:8000
- Web: http://localhost:3000
- API Docs: http://localhost:8000/docs

### Without Docker

**API:**

```bash
cd apps/api
python -m venv .venv
.venv\Scripts\activate        # Windows
# source .venv/bin/activate   # macOS/Linux
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

**Web:**

```bash
cd apps/web
npm install
npm run dev
```

## API Endpoints

| Method | Path             | Description     |
|--------|------------------|-----------------|
| GET    | `/`              | Root message    |
| GET    | `/api/v1/health` | Health check    |

## Development

- API runs with `--reload` for live code changes
- Web has API proxy configured at `/api/*` -> `localhost:8000`
- CORS configured for `http://localhost:3000`

## Roadmap

- Phase 1: Project scaffold (current)
- Phase 2: Database integration, auth, core features
- Phase 3: Deployment configuration
