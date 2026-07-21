"""
Compare routes — POST /compare (compare 2 URLs side-by-side).
Reuses the run_full_audit function without duplicating logic.
"""
import asyncio
import secrets
import json
from fastapi import APIRouter, Request, Form
from fastapi.templating import Jinja2Templates

from app.services.fetcher import fetch_all, UnsafeURLError
from app.services.robots_checker import analyze_robots, get_robots_not_found
from app.services.sitemap_checker import check_sitemap
from app.services.seo_analyzer import analyze_seo
from app.services.geo_analyzer import analyze_geo
from app.services.ai_advisor import get_ai_recommendations
from app.services.history_service import save_analysis

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")


async def run_full_audit(url: str) -> dict:
    """
    Full audit pipeline for one URL. Reusable from /analyze and /compare.
    Returns audit_data dict with all checks.
    """
    # Validate and normalize URL
    url = url.strip()
    if not url.startswith(("http://", "https://")):
        url = f"https://{url}"
    
    # Fetch all resources
    try:
        fetch_results = await fetch_all(url)
    except UnsafeURLError as e:
        return {
            "error": str(e),
            "url": url,
        }
    
    html_content = fetch_results["html"]
    robots_content = fetch_results["robots"]
    llms_txt_content = fetch_results["llms_txt"]
    fetch_errors = fetch_results["errors"]
    
    # If HTML couldn't be fetched at all
    if html_content is None and not robots_content:
        return {
            "error": fetch_errors[0] if fetch_errors else "Website tidak dapat diakses.",
            "url": url,
        }
    
    # Analyze robots.txt
    if robots_content:
        robots_result = analyze_robots(robots_content, target_path="/")
    else:
        robots_result = get_robots_not_found()
    
    # Analyze sitemap
    sitemap_result = await check_sitemap(url, robots_result.get("sitemap_urls", []))
    
    # Analyze SEO and GEO
    seo_result = {}
    geo_result = {}
    if html_content:
        seo_result = analyze_seo(html_content, url)
        geo_result = analyze_geo(html_content, robots_result, llms_txt_content)
    else:
        seo_result = {"score": 0, "checks": [], "word_count": 0, "internal_links": 0, "external_links": 0}
        geo_result = {"score": 0, "checks": []}
    
    return {
        "url": url,
        "robots": robots_result,
        "sitemap": sitemap_result,
        "seo": seo_result,
        "geo": geo_result,
        "fetch_errors": fetch_errors,
        "html_bytes": fetch_results.get("html_bytes", 0),
        "html_fetch_seconds": fetch_results.get("html_fetch_seconds", 0),
    }


@router.get("/compare")
async def compare_page(request: Request):
    """Render the compare page."""
    return templates.TemplateResponse(request, "compare.html", {"request": request})


@router.post("/compare")
async def compare_urls(request: Request, url1: str = Form(...), url2: str = Form(...)):
    """
    Compare two URLs in parallel. Both get the full audit pipeline.
    """
    if not url1.strip() or not url2.strip():
        return templates.TemplateResponse(request, "partials/compare_result.html", {
            "request": request,
            "error": "Kedua URL harus diisi.",
        })
    
    # Run both audits in parallel
    audit1, audit2 = await asyncio.gather(
        run_full_audit(url1),
        run_full_audit(url2),
        return_exceptions=False
    )
    
    # Check for errors
    if "error" in audit1 or "error" in audit2:
        error_msg = audit1.get("error") or audit2.get("error")
        return templates.TemplateResponse(request, "partials/compare_result.html", {
            "request": request,
            "error": error_msg,
        })
    
    # Prepare for AI recommendation (compare mode — different system prompt)
    compare_payload = {
        "url1": audit1["url"],
        "url2": audit2["url"],
        "audit1": {k: v for k, v in audit1.items() if k not in ["fetch_errors", "html_bytes", "html_fetch_seconds"]},
        "audit2": {k: v for k, v in audit2.items() if k not in ["fetch_errors", "html_bytes", "html_fetch_seconds"]},
    }
    
    ai_recommendation = await get_ai_recommendations_compare(compare_payload)
    
    # Save both records with compare_group marker
    compare_group = secrets.token_urlsafe(8)[:12]
    record1_id = await save_analysis(audit1["url"], {
        "url": audit1["url"],
        "robots": audit1["robots"],
        "sitemap": audit1["sitemap"],
        "seo": audit1["seo"],
        "geo": audit1["geo"],
    }, ai_recommendation=None, compare_group=compare_group)
    
    record2_id = await save_analysis(audit2["url"], {
        "url": audit2["url"],
        "robots": audit2["robots"],
        "sitemap": audit2["sitemap"],
        "seo": audit2["seo"],
        "geo": audit2["geo"],
    }, ai_recommendation=None, compare_group=compare_group)
    
    return templates.TemplateResponse(request, "partials/compare_result.html", {
        "request": request,
        "audit1": audit1,
        "audit2": audit2,
        "ai_recommendation": ai_recommendation,
        "record1_id": record1_id,
        "record2_id": record2_id,
    })


async def get_ai_recommendations_compare(compare_data: dict) -> str:
    """
    Get AI recommendations for compare mode.
    Different system prompt that focuses on competitive insights.
    """
    from app.config import settings
    import httpx
    
    SYSTEM_PROMPT_COMPARE = """Kamu adalah konsultan SEO dan GEO profesional yang ahli dalam analisis kompetitif.
    Kamu akan menerima data audit dua website dalam format JSON. Tugasmu:
    1. Bandingkan kedua situs secara ringkas (mana yang lebih siap untuk SEO/GEO, margin kemenangan).
    2. Identifikasi 3-4 area kunci dimana situs A unggul atau kalah dari situs B, berdasarkan data yang diberikan.
    3. Untuk tiap area, jelaskan actionable steps apa yang perlu dilakukan situs yang tertinggal.
    4. Gunakan bahasa Indonesia yang jelas dan fokus pada praktik/implementasi, bukan teori.
    5. Jangan mengarang data; hanya gunakan apa yang ada di JSON yang diberikan.
    Format output dalam markdown."""
    
    if not settings.OLLAMA_API_KEY or settings.OLLAMA_API_KEY == "your_ollama_cloud_api_key_here":
        return "⚠️ API key Ollama belum dikonfigurasi."
    
    payload = {
        "model": settings.OLLAMA_MODEL,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT_COMPARE},
            {"role": "user", "content": json.dumps(compare_data, ensure_ascii=False, default=str)},
        ],
        "stream": False,
    }
    headers = {
        "Authorization": f"Bearer {settings.OLLAMA_API_KEY}",
        "Content-Type": "application/json",
    }
    
    async with httpx.AsyncClient(timeout=60) as client:
        try:
            resp = await client.post(
                f"{settings.OLLAMA_BASE_URL}/api/chat",
                headers=headers,
                json=payload,
            )
            resp.raise_for_status()
            data = resp.json()
            return data["message"]["content"]
        except Exception as e:
            return f"⚠️ Gagal mendapatkan analisis perbandingan: {str(e)}"
