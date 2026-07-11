"""
Sitemap.xml analyzer — checks existence, validates XML, counts URLs, checks freshness.
Uses defusedxml for safe XML parsing (prevents XXE attacks).
"""
import httpx
import asyncio
from typing import Optional, List
from urllib.parse import urlparse

import defusedxml.ElementTree as ET

from app.config import settings
from app.services.fetcher import fetch_url


# Common sitemap namespaces
SITEMAP_NS = {"sm": "http://www.sitemaps.org/schemas/sitemap/0.9"}


async def check_sitemap(url: str, robots_sitemap_urls: List[str] = None) -> dict:
    """
    Check and analyze sitemap for the given URL.
    
    Priority:
    1. Try URLs from robots.txt Sitemap directives
    2. Try common default paths (/sitemap.xml, /sitemap_index.xml)
    """
    parsed = urlparse(url)
    base_url = f"{parsed.scheme}://{parsed.netloc}"

    # Build list of sitemap URLs to try
    urls_to_try = []

    # Priority 1: URLs from robots.txt
    if robots_sitemap_urls:
        urls_to_try.extend(robots_sitemap_urls)

    # Priority 2: Common default paths
    default_paths = ["/sitemap.xml", "/sitemap_index.xml"]
    for path in default_paths:
        candidate = f"{base_url}{path}"
        if candidate not in urls_to_try:
            urls_to_try.append(candidate)

    async with httpx.AsyncClient(
        timeout=httpx.Timeout(settings.REQUEST_TIMEOUT_SECONDS, connect=10),
        headers={
            "User-Agent": "Mozilla/5.0 (compatible; SEOGEOAnalyzer/1.0)"
        },
    ) as client:
        for sitemap_url in urls_to_try:
            content, status = await fetch_url(client, sitemap_url, max_size=10 * 1024 * 1024)
            if content and status == 200:
                result = parse_sitemap(content, sitemap_url)
                if result["found"]:
                    return result

    return {
        "found": False,
        "url": None,
        "type": None,
        "total_urls": 0,
        "has_lastmod": False,
        "most_recent_lastmod": None,
        "error": None,
    }


def parse_sitemap(xml_content: str, sitemap_url: str) -> dict:
    """Parse sitemap XML content and extract metadata."""
    try:
        root = ET.fromstring(xml_content.encode("utf-8", errors="replace"))
    except ET.ParseError as e:
        return {
            "found": True,
            "url": sitemap_url,
            "type": None,
            "total_urls": 0,
            "has_lastmod": False,
            "most_recent_lastmod": None,
            "error": f"Format XML tidak valid: {str(e)}",
        }
    except Exception as e:
        return {
            "found": True,
            "url": sitemap_url,
            "type": None,
            "total_urls": 0,
            "has_lastmod": False,
            "most_recent_lastmod": None,
            "error": f"Gagal mem-parse sitemap: {str(e)}",
        }

    # Remove namespace prefixes for easier parsing
    tag = root.tag.split("}")[-1] if "}" in root.tag else root.tag

    if tag == "sitemapindex":
        return parse_sitemap_index(root, sitemap_url)
    elif tag == "urlset":
        return parse_urlset(root, sitemap_url)
    else:
        return {
            "found": True,
            "url": sitemap_url,
            "type": None,
            "total_urls": 0,
            "has_lastmod": False,
            "most_recent_lastmod": None,
            "error": f"Format sitemap tidak dikenali (root element: {tag})",
        }


def parse_sitemap_index(root, sitemap_url: str) -> dict:
    """Parse a sitemap index file."""
    # Find all sitemap entries
    sitemaps = root.findall(".//{http://www.sitemaps.org/schemas/sitemap/0.9}sitemap")
    if not sitemaps:
        sitemaps = root.findall(".//sitemap")

    total = len(sitemaps)

    # Check for lastmod
    lastmods = []
    for sm in sitemaps:
        lastmod_el = sm.find("{http://www.sitemaps.org/schemas/sitemap/0.9}lastmod")
        if lastmod_el is None:
            lastmod_el = sm.find("lastmod")
        if lastmod_el is not None and lastmod_el.text:
            lastmods.append(lastmod_el.text.strip())

    most_recent = None
    if lastmods:
        lastmods.sort(reverse=True)
        most_recent = lastmods[0][:10]  # Take date part only

    return {
        "found": True,
        "url": sitemap_url,
        "type": "sitemapindex",
        "total_urls": total,
        "has_lastmod": len(lastmods) > 0,
        "most_recent_lastmod": most_recent,
        "error": None,
    }


def parse_urlset(root, sitemap_url: str) -> dict:
    """Parse a URL set sitemap."""
    urls = root.findall(".//{http://www.sitemaps.org/schemas/sitemap/0.9}url")
    if not urls:
        urls = root.findall(".//url")

    total = len(urls)

    # Check for lastmod
    lastmods = []
    for url_el in urls:
        lastmod_el = url_el.find("{http://www.sitemaps.org/schemas/sitemap/0.9}lastmod")
        if lastmod_el is None:
            lastmod_el = url_el.find("lastmod")
        if lastmod_el is not None and lastmod_el.text:
            lastmods.append(lastmod_el.text.strip())

    most_recent = None
    if lastmods:
        lastmods.sort(reverse=True)
        most_recent = lastmods[0][:10]  # Take date part only

    return {
        "found": True,
        "url": sitemap_url,
        "type": "urlset",
        "total_urls": total,
        "has_lastmod": len(lastmods) > 0,
        "most_recent_lastmod": most_recent,
        "error": None,
    }
