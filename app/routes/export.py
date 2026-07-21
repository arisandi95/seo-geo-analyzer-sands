"""
Export routes — GET /r/{id}/pdf (export to PDF).
WeasyPrint is optional; if import fails, returns HTML with print-friendly CSS.
"""
from fastapi import APIRouter, Request
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.templating import Jinja2Templates
import tempfile
import logging
from pathlib import Path

from app.services.history_service import get_record, parse_audit_json

logger = logging.getLogger(__name__)
router = APIRouter()
templates = Jinja2Templates(directory="app/templates")

# Try to import WeasyPrint; if it fails, set flag to use print-CSS fallback
try:
    from weasyprint import HTML, CSS
    WEASYPRINT_AVAILABLE = True
except Exception:  # on Windows without GTK, weasyprint raises OSError (missing DLLs), not ImportError
    WEASYPRINT_AVAILABLE = False
    logger.warning("WeasyPrint not available. PDF export will use print-CSS fallback.")


@router.get("/r/{record_id}/pdf")
async def export_pdf(request: Request, record_id: str):
    """Export analysis result as PDF."""
    record = await get_record(record_id)
    if record is None:
        return HTMLResponse(
            "<p>Analisa tidak ditemukan.</p>",
            status_code=404
        )
    
    audit_data = parse_audit_json(record)
    if audit_data is None:
        return HTMLResponse(
            "<p>Data analisa tidak dapat dibaca.</p>",
            status_code=404
        )
    
    if WEASYPRINT_AVAILABLE:
        return await _export_pdf_weasyprint(record, audit_data)
    else:
        return await _export_pdf_print_css(request, record, audit_data)


async def _export_pdf_weasyprint(record, audit_data: dict):
    """Generate PDF using WeasyPrint."""
    try:
        # Render HTML template
        html_content = templates.get_template("report_pdf.html").render({
            "record": record,
            "audit": audit_data,
        })
        
        # Generate PDF
        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
            pdf_path = tmp.name
            HTML(string=html_content).write_pdf(pdf_path)
        
        # Return PDF file
        filename = f"seo-geo-report-{record.domain}-{record.created_at.strftime('%Y%m%d')}.pdf"
        return FileResponse(
            pdf_path,
            media_type="application/pdf",
            filename=filename,
            headers={"Content-Disposition": f"attachment; filename={filename}"}
        )
    except Exception as e:
        logger.error(f"WeasyPrint PDF generation failed: {e}")
        # Fall back to print-CSS version
        return HTMLResponse(
            f'<p>PDF generation error. <a href="javascript:window.print()">Click here to print</a> instead.</p>',
            status_code=500
        )


async def _export_pdf_print_css(request: Request, record, audit_data: dict):
    """Return printable HTML (uses browser print dialog for PDF save)."""
    # Render with print-friendly CSS class
    html_response = templates.TemplateResponse(request, "report_print.html", {
        "request": request,
        "record": record,
        "audit": audit_data,
    })
    return html_response
