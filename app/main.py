"""
FastAPI application entry point.
"""
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import JSONResponse
from slowapi import Limiter
from slowapi.util import get_remote_address

from app.db import init_db
from app.routes.analyze import router as analyze_router
from app.routes.history import router as history_router
from app.routes.export import router as export_router
from app.routes.compare import router as compare_router
from app.config import settings


# Setup rate limiter
limiter = Limiter(key_func=get_remote_address)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """FastAPI lifespan: initialize DB on startup."""
    await init_db()
    yield


app = FastAPI(
    title="SEO & GEO Analyzer",
    description="Analyze website SEO and GEO readiness with AI-powered recommendations",
    version="2.0.0",
    lifespan=lifespan,
)

# Add rate limiter
app.state.limiter = limiter

# Mount static files
app.mount("/static", StaticFiles(directory="app/static"), name="static")

# Templates
templates = Jinja2Templates(directory="app/templates")

# Include routes
app.include_router(analyze_router)
app.include_router(history_router)
app.include_router(export_router)
app.include_router(compare_router)


@app.get("/")
async def index(request: Request):
    """Render the landing page with URL input form."""
    return templates.TemplateResponse(request, "index.html", {"request": request})


@app.get("/health")
async def health():
    """Health check endpoint."""
    return JSONResponse({"status": "ok", "env": settings.APP_ENV})
