"""
Async HTTP fetcher for target website HTML, robots.txt, sitemap, and llms.txt.
Uses httpx for async parallel fetching with proper timeout and size limits.
"""
import httpx
from urllib.parse import urlparse
from typing import Tuple, Optional

from app.config import settings


async def fetch_url(client: httpx.AsyncClient, url: str, max_size: int = None) -> Tuple[Optional[str], Optional[int]]:
    """
    Fetch a URL and return (content, status_code).
    Returns (None, status_code) on error, or (None, None) if connection fails.
    Streams response to enforce max_size limit.
    """
    if max_size is None:
        max_size = settings.MAX_CONTENT_SIZE
    try:
        async with client.stream("GET", url, follow_redirects=True) as response:
            status_code = response.status_code
            if status_code != 200:
                return None, status_code

            # Stream and accumulate content with size limit
            chunks = []
            total_size = 0
            async for chunk in response.aiter_text():
                total_size += len(chunk.encode("utf-8", errors="replace"))
                if total_size > max_size:
                    # Stop reading beyond limit but return what we have
                    chunks.append(chunk)
                    break
                chunks.append(chunk)

            return "".join(chunks), status_code
    except httpx.TimeoutException:
        return None, None
    except httpx.ConnectError:
        return None, None
    except httpx.HTTPError:
        return None, None
    except Exception:
        return None, None


def get_base_url(url: str) -> str:
    """Extract base URL (scheme + domain) from a full URL."""
    parsed = urlparse(url)
    return f"{parsed.scheme}://{parsed.netloc}"


async def fetch_all(url: str) -> dict:
    """
    Fetch all required resources in parallel:
    - Target page HTML
    - robots.txt
    - llms.txt
    
    Returns a dict with keys: html, robots, llms_txt, errors
    """
    import asyncio

    base_url = get_base_url(url)
    robots_url = f"{base_url}/robots.txt"
    llms_url = f"{base_url}/llms.txt"

    errors = []

    async with httpx.AsyncClient(
        timeout=httpx.Timeout(settings.REQUEST_TIMEOUT_SECONDS, connect=10),
        headers={
            "User-Agent": "Mozilla/5.0 (compatible; SEOGEOAnalyzer/1.0; +https://github.com/seo-geo-analyzer)"
        },
        limits=httpx.Limits(max_connections=10),
    ) as client:
        # Fetch HTML, robots.txt, and llms.txt in parallel
        html_task = fetch_url(client, url)
        robots_task = fetch_url(client, robots_url, max_size=1024 * 1024)  # 1MB limit for robots.txt
        llms_task = fetch_url(client, llms_url, max_size=1024 * 1024)  # 1MB limit for llms.txt

        results = await asyncio.gather(html_task, robots_task, llms_task, return_exceptions=True)

    # Process results
    html_content, html_status = (None, None)
    robots_content, robots_status = (None, None)
    llms_content, llms_status = (None, None)

    if isinstance(results[0], Exception):
        errors.append(f"Gagal mengambil halaman: {str(results[0])}")
    else:
        html_content, html_status = results[0]

    if isinstance(results[1], Exception):
        errors.append(f"Gagal mengambil robots.txt: {str(results[1])}")
    else:
        robots_content, robots_status = results[1]

    if isinstance(results[2], Exception):
        # llms.txt is optional, don't add to errors
        pass
    else:
        llms_content, llms_status = results[2]

    # Check HTML fetch results
    if html_content is None and html_status is not None:
        if html_status == 403:
            errors.append("Website memblokir akses otomatis (403 Forbidden), hasil analisa mungkin tidak lengkap.")
        elif html_status == 429:
            errors.append("Website membatasi akses (429 Too Many Requests), coba lagi beberapa saat.")
        elif html_status is not None:
            errors.append(f"Website mengembalikan status {html_status}.")
    elif html_content is None and html_status is None:
        errors.append("Website tidak dapat diakses. Cek kembali URL atau website terlalu lama merespons.")

    return {
        "html": html_content,
        "html_status": html_status,
        "robots": robots_content,
        "robots_status": robots_status,
        "llms_txt": llms_content,
        "llms_txt_status": llms_status,
        "errors": errors,
    }
