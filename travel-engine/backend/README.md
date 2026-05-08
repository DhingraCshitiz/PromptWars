# Backend

FastAPI application for the Travel Planning Engine.

**Full-stack local run, Docker, and GCP deployment:** see the parent [README.md](../README.md).

Local secrets: copy [`.env.example`](./.env.example) to **`.env`** in this folder (`backend/`). Values are loaded automatically when the file exists; OS environment variables override the file.

SQLite is used by default. **On startup**, the app creates missing tables and seeds a `user_profiles` row with id `anonymous` (required for trip creation until auth is wired).

## Local (Python 3.11+)

```bash
cd backend
python -m venv .venv
# Windows: .venv\Scripts\activate
# Unix:    source .venv/bin/activate

pip install -e .
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Docs: `http://localhost:8000/docs`. Health: `GET /health`.

## Docker (from `travel-engine/`)

```bash
cd travel-engine
docker compose up --build api
```

The API listens on **port 8000** (matches frontend `environment.ts`).

## Environment

Variables can be set in **`backend/.env`** (from [`.env.example`](./.env.example)) or in the process environment (env vars override the file).

| Variable | Purpose |
|----------|---------|
| `DATABASE_URL` | Default `sqlite+aiosqlite:///./traveldb.sqlite` (relative to process cwd) |
| `CORS_ORIGINS` | Comma-separated browser origins for CORS (default `http://localhost:4200`). Set to your production Angular URL on GCP. |
| `GEMINI_API_KEY` | **Google AI Studio** API key — when set, itineraries are generated with the **Gemini API** (JSON). Best for real curation without Vertex. |
| `GEMINI_MODEL` | Default `gemini-1.5-flash` |
| `USE_MOCK_GOOGLE` | Default `true`; when **no** `GEMINI_API_KEY`, disables **Vertex** fallback. When a key is present, Gemini API is used regardless. If no key and Vertex is off, the service uses a **curated local heuristic** (still personalized from interests, diet, pace — not the old generic placeholders). |
| `GOOGLE_CLOUD_PROJECT` | Used only if Vertex is enabled (`USE_MOCK_GOOGLE=false` and Vertex init succeeds) |
| `SQLALCHEMY_ECHO` | Set `true` to log SQL |

## Dev tools

```bash
pip install -e ".[dev]"
```
