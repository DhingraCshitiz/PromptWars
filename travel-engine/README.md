# Travel Planning and Experience Engine

A full-stack application built with FastAPI (Python) and Angular that dynamically plans trips using user preferences, constraints, and real-time updates via Vertex AI Gemini.

## Folder Structure
- `/backend`: FastAPI Python application.
- `/frontend`: Angular application.
- `/infra/gcp`: Deployment scripts and IAM definitions.
- `/docs`: Architecture, security, testing, and deployment documentation.

## Running Locally

### Backend
1. `cd backend`
2. `python -m venv venv`
3. `source venv/bin/activate` (or `venv\Scripts\activate` on Windows)
4. `pip install -e ".[dev]"`
5. `alembic upgrade head` (to initialize the SQLite database locally)
6. `uvicorn app.main:app --reload`

### Frontend
1. `cd frontend`
2. `npm install`
3. `npm start`

## Deployment
See `docs/deployment.md` and `infra/gcp/provision-gcp.sh` for details on deploying to Google Cloud via Cloud Run and Firebase Hosting.
