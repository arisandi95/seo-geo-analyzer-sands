"""
Analysis route — POST /analyze endpoint.
"""
import asyncio
from fastapi import APIRouter, Request, Form, Depends
from fastapi.templating import Jinja2Templates
from slowapi import Limiter
from slowapi.util import get_remote_address

from app.services.fetcher import fetch_all, UnsafeURLError
from app.services.robots_checker import analyze_robots, get_robots_not_found
from app.services.sitemap_checker import check_sitemap
from app.services.seo_analyzer import analyze_seo
from app.services.geo_analyzer import analyze_geo
from app.services.ai_advisor import get_ai_recommendations, get_keyword_estimates, get_backlink_estimates
from app.services.usability_checker import get_pagespeed_data
from app.services.history_service import save_analysis
from app.config import settings

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")
limiter = Limiter(key_func=get_remote_address)


@router.post("/analyze")
@limiter.limit("10/minute")
async def analyze(request: Request, url: str = Form(...)):
    """
    Main analysis endpoint. Fetches target URL resources in parallel,
    runs all analyzers, then gets AI recommendations, and saves to history.
    Returns partial HTML for HTMX swap.
    """
    # Validate and normalize URL
    url = url.strip()
    if not url:
        return templates.TemplateResponse(request, "partials/result.html", {
            "request": request,
            "error": "URL tidak boleh kosong.",
        })

    if not url.startswith(("http://", "https://")):
        url = f"https://{url}"

    # Step 1: Fetch all resources in parallel
    try:
        fetch_results = await fetch_all(url)
    except UnsafeURLError as e:
        return templates.TemplateResponse(request, "partials/result.html", {
            "request": request,
            "error": str(e),
        })

    html_content = fetch_results["html"]
    robots_content = fetch_results["robots"]
    llms_txt_content = fetch_results["llms_txt"]
    fetch_errors = fetch_results["errors"]

    # If HTML couldn't be fetched at all, show error but continue with what we have
    if html_content is None and not robots_content:
        return templates.TemplateResponse(request, "partials/result.html", {
            "request": request,
            "error": fetch_errors[0] if fetch_errors else "Website tidak dapat diakses. Cek kembali URL.",
        })

    # Step 2: Analyze robots.txt
    if robots_content:
        robots_result = analyze_robots(robots_content, target_path="/")
    else:
        robots_result = get_robots_not_found()

    # Step 3: Analyze sitemap (uses robots.txt sitemap URLs as priority)
    sitemap_result = await check_sitemap(url, robots_result.get("sitemap_urls", []))

    # Step 4: Analyze SEO and GEO
    seo_result = {}
    geo_result = {}
    if html_content:
        seo_result = analyze_seo(html_content, url)
        geo_result = analyze_geo(html_content, robots_result, llms_txt_content)
    else:
        seo_result = {"score": 0, "checks": [], "word_count": 0, "internal_links": 0, "external_links": 0}
        geo_result = {"score": 0, "checks": []}

    # Step 5: Prepare audit data and get AI recommendations
    audit_data = {
        "url": url,
        "robots": robots_result,
        "sitemap": sitemap_result,
        "seo": seo_result,
        "geo": geo_result,
    }

    # Get AI recommendation + keyword ranking estimates in parallel
    # (both never raise by contract — errors become fallback messages)
    ai_recommendation, keyword_estimates, backlink_estimates, pagespeed = await asyncio.gather(
        get_ai_recommendations(audit_data),
        get_keyword_estimates(audit_data),
        get_backlink_estimates(audit_data),
        get_pagespeed_data(url),
    )
    audit_data["keyword_estimates"] = keyword_estimates
    audit_data["backlink_estimates"] = backlink_estimates
    audit_data["pagespeed"] = pagespeed

    # Step 6: Save analysis to history (non-blocking — errors logged but don't break flow)
    record_id = await save_analysis(url, audit_data, ai_recommendation=ai_recommendation)

    return templates.TemplateResponse(request, "partials/result.html", {
        "request": request,
        "audit": audit_data,
        "ai_recommendation": ai_recommendation,
        "fetch_errors": fetch_errors,
        "record_id": record_id,
    })
