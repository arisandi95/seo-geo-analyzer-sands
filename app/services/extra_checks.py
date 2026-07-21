"""
Extra checks service — additional technical audits (redirects, favicon, hreflang, 404, size/time).
"""
import asyncio
import logging
from typing import Dict, List
from urllib.parse import urlparse
import uuid

from app.services.fetcher import fetch_url, make_client
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)


async def check_redirects_and_canonical(base_url: str) -> Dict[str, str]:
    """
    Check redirect consistency for www/non-www and http/https variants.
    Returns check result with status (good/warning/error).
    """
    parsed = urlparse(base_url)
    domain = parsed.netloc
    
    # Generate URL variants
    variants = []
    if domain.startswith("www."):
        non_www = domain[4:]
        variants.append(f"http://{non_www}/")
        variants.append(f"https://{non_www}/")
    else:
        variants.append(f"http://www.{domain}/")
        variants.append(f"https://www.{domain}/")
    
    variants.append(f"http://{domain}/")
    variants.append(f"https://{domain}/")
    
    # Test all variants
    results = {}
    async with make_client() as client:
        for variant in variants:
            try:
                _, status = await fetch_url(client, variant, max_size=100)
                results[variant] = status or 0
            except Exception:
                results[variant] = 0
    
    # Analyze consistency
    success_urls = [u for u, s in results.items() if 200 <= s < 300]
    
    if len(set(success_urls)) <= 1:
        return {
            "name": "Redirect & Canonical",
            "status": "good",
            "message": "Redirect consistency baik — semua varian menuju satu URL kanonik",
            "value": "OK"
        }
    else:
        return {
            "name": "Redirect & Canonical",
            "status": "warning",
            "message": "Beberapa varian URL mengarah ke halaman berbeda (inconsistent canonicalization)",
            "value": "Inkonsisten"
        }


async def check_favicon(html_content: str, base_url: str) -> Dict[str, str]:
    """Check if favicon is present and accessible."""
    try:
        soup = BeautifulSoup(html_content, "lxml")
        
        # Look for favicon link
        favicon_link = soup.find("link", rel=["icon", "shortcut icon"])
        if favicon_link and favicon_link.get("href"):
            return {
                "name": "Favicon",
                "status": "good",
                "message": "Favicon ditemukan dan dikonfigurasi.",
                "value": favicon_link.get("href")[:50]
            }
        
        return {
            "name": "Favicon",
            "status": "warning",
            "message": "Favicon tidak ditemukan atau tidak dikonfigurasi.",
            "value": "Tidak ada"
        }
    except Exception as e:
        logger.error(f"Error checking favicon: {e}")
        return {
            "name": "Favicon",
            "status": "warning",
            "message": "Tidak dapat memeriksa favicon.",
            "value": "Error"
        }


async def check_hreflang(html_content: str) -> Dict[str, str]:
    """Check hreflang configuration."""
    try:
        soup = BeautifulSoup(html_content, "lxml")
        
        hreflang_links = soup.find_all("link", rel="alternate", hreflang=True)
        
        if not hreflang_links:
            return {
                "name": "Hreflang Tags",
                "status": "info",
                "message": "Tidak ada hreflang tags (OK jika website single-language).",
                "value": "Tidak ada"
            }
        
        # Validate hreflang values
        valid = True
        for link in hreflang_links:
            hreflang = link.get("hreflang", "")
            # Check format (should be like 'en', 'en-US', 'x-default')
            if not (hreflang == "x-default" or len(hreflang.split("-")[0]) == 2):
                valid = False
                break
        
        if valid:
            return {
                "name": "Hreflang Tags",
                "status": "good",
                "message": f"Hreflang configuration valid — {len(hreflang_links)} tags ditemukan.",
                "value": f"{len(hreflang_links)} tags"
            }
        else:
            return {
                "name": "Hreflang Tags",
                "status": "warning",
                "message": "Beberapa hreflang tags memiliki format invalid.",
                "value": "Invalid format"
            }
    except Exception as e:
        logger.error(f"Error checking hreflang: {e}")
        return {
            "name": "Hreflang Tags",
            "status": "info",
            "message": "Tidak dapat memeriksa hreflang.",
            "value": "Error"
        }


async def check_soft_404(base_url: str) -> Dict[str, str]:
    """Check if 404 handling is correct (returns actual 404 status, not 200 soft 404)."""
    try:
        parsed = urlparse(base_url)
        fake_path = f"/{uuid.uuid4()}"
        test_url = f"{parsed.scheme}://{parsed.netloc}{fake_path}"
        
        async with make_client() as client:
            _, status = await fetch_url(client, test_url, max_size=50 * 1024)
        
        if status == 404:
            return {
                "name": "Custom 404 Page",
                "status": "good",
                "message": "404 handling correct — mengembalikan status code 404.",
                "value": "OK"
            }
        elif status == 200:
            return {
                "name": "Custom 404 Page",
                "status": "warning",
                "message": "Soft 404 terdeteksi — halaman tak ada mengembalikan status 200 (buruk untuk SEO).",
                "value": "Soft 404"
            }
        else:
            return {
                "name": "Custom 404 Page",
                "status": "info",
                "message": f"404 handling mengembalikan status {status}.",
                "value": str(status)
            }
    except Exception as e:
        logger.error(f"Error checking soft 404: {e}")
        return {
            "name": "Custom 404 Page",
            "status": "info",
            "message": "Tidak dapat memeriksa 404 handling.",
            "value": "Error"
        }


async def check_page_size_and_speed(html_bytes: int, fetch_seconds: float) -> Dict[str, str]:
    """Check page size and response time."""
    checks = []
    
    # Size check
    size_mb = html_bytes / (1024 * 1024)
    if html_bytes > 1.5 * 1024 * 1024:
        size_status = "warning"
        size_msg = f"Halaman terlalu besar ({size_mb:.2f}MB) — dapat mempengaruhi kecepatan loading."
    else:
        size_status = "good"
        size_msg = f"Ukuran halaman baik ({size_mb:.2f}MB)."
    
    checks.append({
        "name": "Page Size",
        "status": size_status,
        "message": size_msg,
        "value": f"{size_mb:.2f}MB"
    })
    
    # Response time check
    if fetch_seconds > 3:
        time_status = "warning"
        time_msg = f"Response time lambat ({fetch_seconds}s) — pertimbangkan optimasi server/CDN."
    else:
        time_status = "good"
        time_msg = f"Response time baik ({fetch_seconds}s)."
    
    checks.append({
        "name": "Response Time",
        "status": time_status,
        "message": time_msg,
        "value": f"{fetch_seconds}s"
    })
    
    return checks


async def run_all_extra_checks(
    html_content: str,
    base_url: str,
    html_bytes: int,
    fetch_seconds: float
) -> List[Dict[str, str]]:
    """
    Run all extra checks in parallel where possible.
    Returns list of check results.
    """
    results = []
    
    # Run checks concurrently
    redirect_result, hreflang_result, soft_404_result = await asyncio.gather(
        check_redirects_and_canonical(base_url),
        check_hreflang(html_content),
        check_soft_404(base_url),
        return_exceptions=True
    )
    
    # Handle exceptions
    if not isinstance(redirect_result, Exception):
        results.append(redirect_result)
    if not isinstance(hreflang_result, Exception):
        results.append(hreflang_result)
    if not isinstance(soft_404_result, Exception):
        results.append(soft_404_result)
    
    # Favicon check (non-blocking)
    try:
        favicon_result = await check_favicon(html_content, base_url)
        results.append(favicon_result)
    except Exception as e:
        logger.error(f"Error in favicon check: {e}")
    
    # Size and speed checks
    try:
        size_time_results = await check_page_size_and_speed(html_bytes, fetch_seconds)
        results.extend(size_time_results)
    except Exception as e:
        logger.error(f"Error in size/time check: {e}")
    
    return results
