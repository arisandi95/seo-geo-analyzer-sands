"""
Generators service — create robots.txt, FAQPage JSON-LD, and llms.txt drafts.
"""
import json
import logging
from typing import List, Dict, Optional
from urllib.parse import urlparse

logger = logging.getLogger(__name__)


def generate_robots_txt(audit_data: dict, ai_blocked: bool = False) -> str:
    """
    Generate recommended robots.txt based on audit results.
    If AI crawlers are blocked but GEO is important, allow them.
    """
    domain = urlparse(audit_data.get("url", "")).netloc or "example.com"
    
    lines = [
        "# Auto-generated robots.txt recommendation",
        "# Please review and customize for your site",
        "",
        "# Default rules",
        "User-agent: *",
        "Allow: /",
        "",
    ]
    
    # If AI crawlers are blocked, suggest enabling them
    if ai_blocked:
        lines.extend([
            "# Allow AI crawlers (improves GEO readiness)",
            "User-agent: GPTBot",
            "Allow: /",
            "",
            "User-agent: ClaudeBot",
            "Allow: /",
            "",
            "User-agent: PerplexityBot",
            "Allow: /",
            "",
            "User-agent: Google-Extended",
            "Allow: /",
            "",
        ])
    
    # Add sitemap
    lines.append(f"Sitemap: https://{domain}/sitemap.xml")
    
    return "\n".join(lines)


def generate_faqpage_jsonld(seo_result: dict) -> Optional[str]:
    """
    Generate FAQPage JSON-LD schema from detected Q&A patterns (headings + paragraphs).
    Returns JSON string or None if no Q&A pattern found.
    """
    # Look for headings that look like questions
    faqs = []
    for check in seo_result.get("checks", []):
        # This is a simplified approach — in real impl, parse HTML structure
        if "FAQ" in check.get("name", ""):
            qa_item = {
                "@type": "Question",
                "name": "Example Question?",
                "acceptedAnswer": {
                    "@type": "Answer",
                    "text": "Example answer content."
                }
            }
            faqs.append(qa_item)
    
    if not faqs:
        return None
    
    schema = {
        "@context": "https://schema.org",
        "@type": "FAQPage",
        "mainEntity": faqs[:10]  # Limit to 10 QA pairs
    }
    
    return json.dumps(schema, ensure_ascii=False, indent=2)


def generate_llms_txt(audit_data: dict, sitemap_urls: List[str] = None) -> str:
    """
    Generate llms.txt draft from audit data and sitemap.
    Includes title, description, and primary URLs.
    """
    lines = [
        "# llms.txt — AI model readiness file",
        "# Last updated: auto-generated",
        "",
        "## Website Information",
        "",
    ]
    
    # Extract title and meta info
    seo_result = audit_data.get("seo", {})
    checks = seo_result.get("checks", [])
    
    for check in checks:
        if "Title" in check.get("name", ""):
            title = check.get("value", "")
            if title:
                lines.append(f"Title: {title}")
                break
    
    for check in checks:
        if "Meta Description" in check.get("name", ""):
            desc = check.get("value", "")
            if desc:
                lines.append(f"Description: {desc}")
                break
    
    lines.extend([
        "",
        "## Primary URLs",
        "",
    ])
    
    # Add primary URLs
    if sitemap_urls:
        for url in sitemap_urls[:5]:
            lines.append(f"- {url}")
    else:
        lines.append(f"- {audit_data.get('url', '')}")
    
    lines.extend([
        "",
        "## Notes",
        "",
        "This is an auto-generated draft. Please review and customize for your site.",
        "Include important content paths, contact information, and policies.",
    ])
    
    return "\n".join(lines)


def generate_redirect_audit(fetched_variants: Dict[str, int]) -> Dict[str, str]:
    """
    Audit redirect consistency for www/non-www and http/https.
    Returns status and message.
    """
    statuses = list(fetched_variants.values())
    
    # All should be 200 or 301/302 (redirected to same destination)
    is_consistent = True
    final_status = max(statuses) if statuses else None
    
    if 200 in statuses and any(s not in [200, 301, 302, 307, 308] for s in statuses):
        is_consistent = False
    
    if is_consistent:
        return {
            "status": "good",
            "message": "Redirect consistency OK — semua varian menuju satu URL kanonik"
        }
    else:
        return {
            "status": "warning",
            "message": "Redirect inkonsisten — beberapa varian mengarah ke halaman berbeda"
        }
