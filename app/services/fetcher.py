"""
Async HTTP fetcher for target website HTML, robots.txt, sitemap, and llms.txt.
Uses httpx for async parallel fetching with proper timeout and size limits.

V2: SSRF guard (reject private/loopback IPs & non-http schemes) and
in-memory TTL cache for robots.txt/llms.txt per domain.
"""
import asyncio
import ipaddress
import socket
import time
import httpx
from urllib.parse import urlparse
from typing import Tuple, Optional

from cachetools import TTLCache

from app.config import settings


class UnsafeURLError(Exception):
    """Raised when a user-supplied URL fails the SSRF guard."""


# Cache robots.txt/llms.txt fetch results per URL — 10 minutes, max 100 entries
_fetch_cache: TTLCache = TTLCache(maxsize=100, ttl=600)
_cache_lock = asyncio.Lock()


async def ensure_url_safe(url: str) -> None:
    """
    SSRF guard: reject non-http(s) schemes and hostnames that resolve to
    private / loopback / link-local / reserved addresses.
    Raises UnsafeURLError with an Indonesian, user-facing message.
    """
    parsed = urlparse(url)
    if parsed.scheme not in ("http", "https"):
        raise UnsafeURLError("URL tidak diizinkan: hanya skema http/https yang didukung.")

    hostname = parsed.hostname
    if not hostname:
        raise UnsafeURLError("URL tidak valid.")

    # Resolve hostname (non-blocking) and inspect every returned address
    try:
        loop = asyncio.get_running_loop()
        infos = await loop.getaddrinfo(hostname, None, proto=socket.IPPROTO_TCP)
    except (socket.gaierror, OSError):
        raise UnsafeURLError("Hostname tidak dapat di-resolve. Cek kembali URL.")

    for info in infos:
        ip_str = info[4][0]
        try:
            ip = ipaddress.ip_address(ip_str)
        except ValueError:
            continue
        if (
            ip.is_private
            or ip.is_loopback
            or ip.is_link_local
            or ip.is_reserved
            or ip.is_multicast
            or ip.is_unspecified
        ):
            raise UnsafeURLError("URL tidak diizinkan (mengarah ke alamat internal/private).")


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


async def fetch_url_cached(client: httpx.AsyncClient, url: str, max_size: int = None) -> Tuple[Optional[str], Optional[int]]:
    """
    Same as fetch_url, but consults the TTL cache first.
    Used for robots.txt / sitemap / llms.txt which rarely change within minutes.
    """
    async with _cache_lock:
        if url in _fetch_cache:
            return _fetch_cache[url]

    result = await fetch_url(client, url, max_size=max_size)

    # Only cache definitive results (a successful fetch or a definitive status),
    # never connection failures — those should be retried next time.
    if result[1] is not None:
        async with _cache_lock:
            _fetch_cache[url] = result
    return result


def get_base_url(url: str) -> str:
    """Extract base URL (scheme + domain) from a full URL."""
    parsed = urlparse(url)
    return f"{parsed.scheme}://{parsed.netloc}"


def make_client() -> httpx.AsyncClient:
    """Shared client factory so every feature uses the same UA/timeout config."""
    return httpx.AsyncClient(
        timeout=httpx.Timeout(settings.REQUEST_TIMEOUT_SECONDS, connect=10),
        headers={
            "User-Agent": "Mozilla/5.0 (compatible; SEOGEOAnalyzer/2.0; +https://github.com/seo-geo-analyzer)"
        },
        limits=httpx.Limits(max_connections=10),
    )


async def fetch_all(url: str) -> dict:
    """
    Fetch all required resources in parallel:
    - Target page HTML
    - robots.txt (cached)
    - llms.txt (cached)

    Returns a dict with keys: html, robots, llms_txt, errors,
    plus html_bytes & html_fetch_seconds for the V2 extra checks.
    Raises UnsafeURLError if the URL fails the SSRF guard.
    """
    await ensure_url_safe(url)

    base_url = get_base_url(url)
    robots_url = f"{base_url}/robots.txt"
    llms_url = f"{base_url}/llms.txt"

    errors = []

    async with make_client() as client:
        # Fetch HTML, robots.txt, and llms.txt in parallel
        started = time.monotonic()
        html_task = fetch_url(client, url)
        robots_task = fetch_url_cached(client, robots_url, max_size=1024 * 1024)  # 1MB limit for robots.txt
        llms_task = fetch_url_cached(client, llms_url, max_size=1024 * 1024)  # 1MB limit for llms.txt

        results = await asyncio.gather(html_task, robots_task, llms_task, return_exceptions=True)
        elapsed = time.monotonic() - started

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
        "html_bytes": len(html_content.encode("utf-8", errors="replace")) if html_content else 0,
        "html_fetch_seconds": round(elapsed, 2),
        "robots": robots_content,
        "robots_status": robots_status,
        "llms_txt": llms_content,
        "llms_txt_status": llms_status,
        "errors": errors,
    }
