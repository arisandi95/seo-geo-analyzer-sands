"""
History routes — GET /history (list), GET /r/{id} (permalink), GET /history/trend (partial).
"""
from fastapi import APIRouter, Request
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse

from app.services.history_service import list_records, get_record, parse_audit_json, get_domain_trend, normalize_domain

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")


@router.get("/history")
async def history_page(request: Request, page: int = 1):
    """List all analyses with pagination."""
    records, total, total_pages = await list_records(page=page)
    return templates.TemplateResponse(request, "history.html", {
        "request": request,
        "records": records,
        "current_page": page,
        "total_pages": total_pages,
        "total": total,
    })


@router.get("/r/{record_id}")
async def permalink(request: Request, record_id: str):
    """Render a saved analysis result (permalink)."""
    record = await get_record(record_id)
    if record is None:
        return templates.TemplateResponse(request, "404.html", {
            "request": request,
            "message": "Analisa tidak ditemukan atau telah dihapus."
        }, status_code=404)
    
    audit_data = parse_audit_json(record)
    if audit_data is None:
        return templates.TemplateResponse(request, "404.html", {
            "request": request,
            "message": "Data analisa tidak dapat dibaca."
        }, status_code=404)
    
    # Render result partial with record metadata
    return templates.TemplateResponse(request, "permalink.html", {
        "request": request,
        "record": record,
        "audit": audit_data,
        "ai_recommendation": record.ai_recommendation,
        "fetch_errors": [],
    })


@router.get("/history/trend")
async def trend_partial(request: Request, domain: str):
    """Return HTML partial with trend chart for one domain (HTMX call)."""
    records = await get_domain_trend(domain)
    
    if len(records) < 2:
        return HTMLResponse(
            '<p style="font-size: 0.875rem; color: var(--color-text-secondary); padding: 12px;">Analisa lagi di kemudian hari untuk melihat tren skor.</p>'
        )
    
    # Generate SVG chart (server-side, no JS)
    svg = _generate_trend_chart(records)
    return HTMLResponse(svg)


def _generate_trend_chart(records: list) -> str:
    """Generate SVG line chart from records (oldest first)."""
    if not records or len(records) < 2:
        return ""
    
    # Chart dimensions
    width, height = 300, 150
    padding = 30
    chart_width = width - padding * 2
    chart_height = height - padding * 2
    
    # Extract scores
    seo_scores = [r.seo_score for r in records]
    geo_scores = [r.geo_score for r in records]
    
    # Calculate points
    num_points = len(records)
    x_step = chart_width / max(1, num_points - 1)
    
    # Generate polylines
    seo_points = []
    geo_points = []
    for i, (seo, geo) in enumerate(zip(seo_scores, geo_scores)):
        x = padding + i * x_step
        y_seo = padding + chart_height - (seo / 100 * chart_height)
        y_geo = padding + chart_height - (geo / 100 * chart_height)
        seo_points.append(f"{x},{y_seo}")
        geo_points.append(f"{x},{y_geo}")
    
    seo_polyline = " ".join(seo_points)
    geo_polyline = " ".join(geo_points)
    
    svg = f"""
    <svg width="{width}" height="{height}" style="margin: 12px 0;" xmlns="http://www.w3.org/2000/svg">
        <!-- Background grid -->
        <defs>
            <pattern id="grid" width="40" height="40" patternUnits="userSpaceOnUse">
                <path d="M 40 0 L 0 0 0 40" fill="none" stroke="#e5e5e5" stroke-width="0.5"/>
            </pattern>
        </defs>
        <rect width="{width}" height="{height}" fill="url(#grid)" />
        
        <!-- Axis labels -->
        <text x="5" y="20" font-size="11" fill="#999">100</text>
        <text x="5" y="{padding + chart_height}" font-size="11" fill="#999">0</text>
        
        <!-- SEO line -->
        <polyline points="{seo_polyline}" fill="none" stroke="#34C759" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
        
        <!-- GEO line -->
        <polyline points="{geo_polyline}" fill="none" stroke="#007AFF" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
        
        <!-- Legend -->
        <rect x="10" y="{height - 25}" width="12" height="12" fill="#34C759"/>
        <text x="25" y="{height - 17}" font-size="11" fill="#34C759">SEO</text>
        
        <rect x="70" y="{height - 25}" width="12" height="12" fill="#007AFF"/>
        <text x="85" y="{height - 17}" font-size="11" fill="#007AFF">GEO</text>
    </svg>
    """
    return svg.strip()
