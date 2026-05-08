import asyncio
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, RedirectResponse
from sqlalchemy import select

from app.api.v1.endpoints import trips
from app.core.config import settings
from app.core.database import SessionLocal, engine
from app.domain.models import Base, UserProfile
from app.integrations.gemini import get_planner_client, planner_diagnostics

logger = logging.getLogger(__name__)

_db_boot_done = asyncio.Event()
_db_boot_exc: list[BaseException | None] = [
    None,
]  # single-element box so middleware can see updates without globals in nested defs


async def _bootstrap_db_schema_and_seed() -> None:
    try:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

        async with SessionLocal() as session:
            existing = await session.execute(select(UserProfile).where(UserProfile.id == "anonymous"))
            if existing.scalars().first() is None:
                session.add(UserProfile(id="anonymous", email="anonymous@local.dev"))
                await session.commit()
        logger.info("Database bootstrap completed.")
    except BaseException as exc:
        logger.exception("Database bootstrap failed.")
        _db_boot_exc[0] = exc
    finally:
        _db_boot_done.set()


def _parse_cors_origins(raw: str) -> tuple[list[str], bool]:
    """Return (origins, allow_credentials). Wildcard * cannot combine with credentials."""
    s = raw.strip()
    if not s or s.upper() == "ALLOW_ALL":
        return (["*"], False)
    parts = [p.strip() for p in s.split(",") if p.strip()]
    if not parts:
        return (["*"], False)
    if parts == ["*"]:
        return (["*"], False)
    return (parts, True)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Do not block here on Cloud SQL: Cloud Run requires the process to listen on PORT quickly.
    # Schema + seed run in the background; /api/* waits for completion (see middleware).
    asyncio.create_task(_bootstrap_db_schema_and_seed())
    yield


app = FastAPI(
    title=settings.PROJECT_NAME,
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
    lifespan=lifespan,
)

cors_origins, cors_allow_credentials = _parse_cors_origins(settings.CORS_ORIGINS)

app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=cors_allow_credentials,
    allow_methods=["*"],
    allow_headers=["*"],
)


def _openapi_json_path() -> str:
    """OpenAPI JSON lives under API_V1_STR; must not require DB (Swagger loads it first)."""
    base = settings.API_V1_STR.rstrip("/")
    return f"{base}/openapi.json"


@app.middleware("http")
async def wait_for_db_before_api(request: Request, call_next):
    path = request.url.path
    if request.method == "OPTIONS":
        return await call_next(request)
    # Let /docs and ReDoc fetch the schema even while DB is starting or after a DB failure.
    openapi_path = _openapi_json_path()
    if path == openapi_path or path == openapi_path + "/":
        return await call_next(request)
    if path.startswith(settings.API_V1_STR):
        await _db_boot_done.wait()
        err = _db_boot_exc[0]
        if err is not None:
            return JSONResponse(
                status_code=503,
                content={"detail": "Database unavailable", "error": str(err)},
            )
    return await call_next(request)


@app.get("/", include_in_schema=False)
def root():
    return RedirectResponse(url="/docs")


@app.get("/health")
def health_check():
    return {"status": "ok"}


@app.get("/health/ready")
async def health_ready():
    """503 until DB bootstrap finished; 503 with error if bootstrap failed."""
    if not _db_boot_done.is_set():
        return JSONResponse(status_code=503, content={"status": "starting"})
    if _db_boot_exc[0] is not None:
        return JSONResponse(
            status_code=503,
            content={"status": "db_failed", "error": str(_db_boot_exc[0])},
        )
    return {"status": "ok"}


@app.get("/health/planner")
def planner_health():
    """Why AI might be skipped: confirms API key wired + last Gemini failure (non-secret)."""
    payload = planner_diagnostics()
    planner = get_planner_client()
    effective = getattr(planner, "_mode", "?")
    return {"status": "ok", **payload, "active_mode_this_process": effective}


app.include_router(trips.router, prefix=f"{settings.API_V1_STR}/trips", tags=["trips"])
