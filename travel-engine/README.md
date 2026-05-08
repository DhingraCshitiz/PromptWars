# Travel Engine (full stack)

Angular **frontend** (`frontend/`) + FastAPI **backend** (`backend/`). Trip planning uses **Gemini** when `GEMINI_API_KEY` is set; otherwise a deterministic “curated heuristic” runs locally (no cloud call).

---

## Prerequisites

- **Node.js 18+** (for Angular 17) and npm  
- **Python 3.11+** (backend) **or** Docker / Docker Compose  
- Optional: **Gemini API key** from [Google AI Studio](https://aistudio.google.com/apikey) for real itineraries  

---

## Run locally (recommended for development)

Use **two terminals** from the **`travel-engine`** directory (this folder).

### 1. Backend API

```bash
cd backend
python -m venv .venv

# Windows PowerShell
.\.venv\Scripts\Activate.ps1
# macOS / Linux
# source .venv/bin/activate

pip install -e .

# Recommended: configure secrets in backend/.env (see below).
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### Backend `.env` file (optional but convenient)

The app loads **`travel-engine/backend/.env`** automatically **if that file exists**. Copy the template and edit:

```bash
# run inside travel-engine/backend/
cp .env.example .env   # Windows: Copy-Item .env.example .env
```

Set at least **`GEMINI_API_KEY`** for live Gemini itineraries. Anything you also set in the shell (**`export GEMINI_API_KEY=...`**) overrides the same key from `.env`.

- **Swagger UI:** [http://localhost:8000/docs](http://localhost:8000/docs)  
- **Health:** `GET http://localhost:8000/health`  

SQLite file defaults to `backend/traveldb.sqlite` (tables + `anonymous` user are created on startup).

### 2. Frontend app

```bash
cd frontend
npm install
npm start
```

Open [http://localhost:4200](http://localhost:4200). Dev build uses `src/environments/environment.ts` and calls the API at **`http://localhost:8000/api/v1`** (already configured).

### Useful environment variables (backend)

| Variable | Purpose |
|----------|---------|
| `GEMINI_API_KEY` | Enables Google AI Studio Gemini for JSON itineraries |
| `GEMINI_MODEL` | Default `gemini-1.5-flash` |
| `DATABASE_URL` | Default SQLite; for hosted DB use Postgres (see GCP below) |
| `CORS_ORIGINS` | Comma-separated origins, default `http://localhost:4200`. Add production front-end origins when deploying |

Set these in **`backend/.env`** (see `backend/.env.example`) or as real environment variables; **shell env wins over `.env`** for the same name.

### Troubleshooting: itineraries look like `"Morning · … immersion in Paris"` forever

Those strings and `place_id: "local heuristic 0-0"` mean you are on the **offline heuristic planner**, not a Gemini JSON response.

1. **`GET http://localhost:8000/health/planner`** — Inspect `gemini_api_key_configured`, `google_generativeai_installed`, `active_mode_this_process` (**`genai`** vs **`fallback`**), and `last_gemini_error` after a failing plan.
2. Put **`GEMINI_API_KEY`** in **`travel-engine/backend/.env`** (no wrapping quotes — paste the raw key after `=`). Restart **uvicorn** after any `.env` change (`--reload` does not reload env from disk reliably for all setups).
3. Run **`pip install -e .`** in `backend/` so **`google-generativeai`** is installed.
4. If `active_mode_this_process` is **`genai`** but results are still heuristic, the Gemini call threw — check **`last_gemini_error`** (invalid model ID, quota, API not enabled, etc.). Try another **`GEMINI_MODEL`** string from [Gemini models](https://ai.google.dev/gemini-api/docs/models/gemini).

---

## Run with Docker Compose (API only)

From **`travel-engine`**:

```bash
docker compose up --build api
```

The API listens on **port 8000**. You can put keys in **`backend/.env`** and add `env_file: - ./backend/.env` under the `api` service in `docker-compose.yml` so Compose picks them up (the file must exist). Otherwise set variables under `environment:` as today.

Compose pins **`PORT=8000`** inside the container so local URLs stay the same as uvicorn-from-host.

PowerShell helper (same folder):

```powershell
.\run-api-docker.ps1
```

Then run **`npm start`** in `frontend` separately.

---

## Deploy on Google Cloud Platform (GCP)

There is **no turnkey Terraform/Cloud Build YAML** checked into this repo; below is the **usual layout**, **commands**, and **which files you change**.

### Suggested architecture

| Piece | GCP option |
|-------|-------------|
| **API** | **Cloud Run** (container from `backend/Dockerfile`) |
| **SPA** | **Cloud Storage** static site + HTTPS (load balancer / Cloud CDN), **Firebase Hosting**, or a second **Cloud Run** serving `dist/` with nginx |
| **Secrets** | **Secret Manager** for `GEMINI_API_KEY`; mount as env in Cloud Run |
| **Optional DB** | **Cloud SQL (PostgreSQL)** with async driver (`asyncpg`; set `DATABASE_URL` to Postgres) |

SQLite on Cloud Run is **ephemeral** (data is lost when the revision scales to zero unless you attach a persistent volume, which adds complexity). For production persistence, prefer **Cloud SQL** or migrate later.

---

### Files / settings to adjust for GCP

| What | Where to change |
|------|----------------|
| **Production API URL** used by the browser | **`frontend/src/environments/environment.prod.ts`** → set `apiBaseUrl` to your Cloud Run URL **including** `/api/v1`, e.g. `https://travel-api-xxxxx-uc.a.run.app/api/v1` |
| **Enable production env in build** | **`frontend/angular.json`** — `configurations.production` already replaces `environment.ts` with **`environment.prod.ts`** for `ng build` |
| **CORS for your deployed Angular origin** | Set env **`CORS_ORIGINS`** on Cloud Run (comma-separated), e.g. `https://your-app.web.app,https://www.yoursite.com`. **No code change** if you use this variable (see **`backend/app/core/config.py`**). |
| **Database** | **`backend/app/core/config.py`** / env **`DATABASE_URL`** — point to Cloud SQL Postgres when ready (connection string via Secret Manager). |
| **Gemini key** | Cloud Run secret or env **`GEMINI_API_KEY`** (not committed). |
| **Container port** | **`backend/Dockerfile`** uses **`${PORT:-8000}`**. **Cloud Run sets `PORT` (often 8080)** automatically — no change required for standard deploys. |
| **Compose local port** | **`docker-compose.yml`** sets **`PORT: "8000"`** so local Docker still matches `8000:8000`. |

### Example: build and deploy API to Cloud Run

Replace project/region/service names with yours.

```bash
cd travel-engine/backend
gcloud auth login
gcloud config set project YOUR_GCP_PROJECT

# Build and push image (Artifact Registry)
gcloud builds submit --tag REGION-docker.pkg.dev/YOUR_GCP_PROJECT/REPO/travel-api:latest .

# Deploy (allow unauthenticated for a public API, or add IAM as needed)
gcloud run deploy travel-api \
  --image REGION-docker.pkg.dev/YOUR_GCP_PROJECT/REPO/travel-api:latest \
  --region REGION \
  --set-secrets GEMINI_API_KEY=gemini-api-key:latest \
  --set-env-vars CORS_ORIGINS=https://YOUR_FRONTEND_ORIGIN \
  --allow-unauthenticated
```

Create the secret first, e.g.:

```bash
echo -n "YOUR_GEMINI_KEY" | gcloud secrets create gemini-api-key --data-file=-
```

### Example: production frontend build

After updating **`environment.prod.ts`**:

```bash
cd travel-engine/frontend
npm ci
npm run build
```

Upload the contents of **`frontend/dist/travel-engine/`** to your static host (GCS website, Firebase Hosting, etc.) and map the domain / TLS as usual.

---

## More detail (backend-only)

See **`backend/README.md`** for extra backend notes and dev dependencies.
