"""
FastAPI application entry point.
"""
from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import JSONResponse

from app.routes.analyze import router as analyze_router
from app.config import settings

app = FastAPI(
    title="SEO & GEO Analyzer",
    description="Analyze website SEO and GEO readiness with AI-powered recommendations",
    version="1.0.0",
)

# Mount static files
app.mount("/static", StaticFiles(directory="app/static"), name="static")

# Templates
templates = Jinja2Templates(directory="app/templates")

# Include routes
app.include_router(analyze_router)


@app.get("/")
async def index(request: Request):
    """Render the landing page with URL input form."""
    return templates.TemplateResponse(request, "index.html", {"request": request})


@app.get("/health")
async def health():
    """Health check endpoint."""
    return JSONResponse({"status": "ok", "env": settings.APP_ENV})
