"""
Multi-page audit service — analyze up to 10 URLs from sitemap with concurrency control.
"""
import asyncio
import json
import logging
from typing import List, Dict, Optional
from urllib.parse import urljoin, urlparse

from app.services.fetcher import fetch_url, make_client, UnsafeURLError, ensure_url_safe
from app.services.seo_analyzer import analyze_seo
from app.services.geo_analyzer import analyze_geo
from app.config import settings

logger = logging.getLogger(__name__)


async def audit_multi_page(
    base_url: str,
    sitemap_urls: List[str],
    robots_result: dict,
) -> Dict:
    """
    Audit multiple URLs from sitemap (max MAX_MULTI_PAGE_URLS) with concurrency control.
    Returns aggregated results and per-URL breakdowns.
    """
    if not sitemap_urls:
        return {
            "total_urls": 0,
            "audited": 0,
            "failed": 0,
            "aggregated_issues": [],
            "urls": [],
        }
    
    # Limit to configured max
    urls_to_audit = sitemap_urls[:settings.MAX_MULTI_PAGE_URLS]
    
    # Validate all URLs first
    safe_urls = []
    for url in urls_to_audit:
        try:
            await ensure_url_safe(url)
            safe_urls.append(url)
        except UnsafeURLError:
            logger.warning(f"Skipped unsafe URL in multi-page audit: {url}")
    
    if not safe_urls:
        return {
            "total_urls": len(urls_to_audit),
            "audited": 0,
            "failed": len(urls_to_audit),
            "aggregated_issues": [],
            "urls": [],
        }
    
    # Audit with concurrency limit
    semaphore = asyncio.Semaphore(settings.MULTI_PAGE_CONCURRENCY)
    
    async def audit_one(url: str) -> Optional[dict]:
        async with semaphore:
            try:
                return await _audit_single_url(url, robots_result)
            except Exception as e:
                logger.error(f"Error auditing {url}: {e}")
                return None
    
    results = await asyncio.gather(
        *[audit_one(url) for url in safe_urls],
        return_exceptions=False
    )
    
    # Filter out None results
    successful = [r for r in results if r is not None]
    failed = len(results) - len(successful)
    
    # Aggregate issues
    aggregated_issues = _aggregate_issues(successful)
    
    return {
        "total_urls": len(urls_to_audit),
        "audited": len(successful),
        "failed": failed,
        "aggregated_issues": aggregated_issues,
        "urls": successful,
    }


async def _audit_single_url(url: str, robots_result: dict) -> Optional[dict]:
    """Audit one URL for SEO only (mini-check, not full audit)."""
    # Check robots.txt disallow
    if robots_result.get("default_ua_allowed") is False:
        return {
            "url": url,
            "status": "skipped",
            "reason": "Diblokir robots.txt",
            "seo_score": 0,
        }
    
    # Fetch HTML
    async with make_client() as client:
        html_content, status = await fetch_url(client, url, max_size=2 * 1024 * 1024)
    
    if html_content is None:
        return {
            "url": url,
            "status": "error",
            "reason": f"Fetch gagal (status {status})" if status else "Fetch timeout",
            "seo_score": 0,
        }
    
    # Quick SEO analysis (title, meta, headings only — mini version)
    try:
        from bs4 import BeautifulSoup
        soup = BeautifulSoup(html_content, "lxml")
        
        has_title = bool(soup.find("title"))
        has_meta_desc = bool(soup.find("meta", attrs={"name": "description"}))
        has_h1 = bool(soup.find("h1"))
        
        issues = []
        if not has_title:
            issues.append("Tidak ada <title>")
        if not has_meta_desc:
            issues.append("Tidak ada meta description")
        if not has_h1:
            issues.append("Tidak ada <h1>")
        
        seo_score = max(0, 100 - len(issues) * 20)  # Simple scoring
        
        return {
            "url": url,
            "status": "ok",
            "seo_score": seo_score,
            "issues": issues,
        }
    except Exception as e:
        logger.error(f"Error parsing {url}: {e}")
        return {
            "url": url,
            "status": "error",
            "reason": "Parse error",
            "seo_score": 0,
        }


def _aggregate_issues(urls: List[dict]) -> List[dict]:
    """Aggregate common issues across all audited URLs."""
    issue_counts = {}
    total_urls = len(urls)
    
    for url_result in urls:
        if url_result.get("status") == "ok":
            for issue in url_result.get("issues", []):
                issue_counts[issue] = issue_counts.get(issue, 0) + 1
    
    # Build aggregated list
    aggregated = []
    for issue, count in sorted(issue_counts.items(), key=lambda x: -x[1]):
        percentage = int((count / total_urls) * 100)
        aggregated.append({
            "issue": issue,
            "count": count,
            "percentage": percentage,
        })
    
    return aggregated
