"""
Robots.txt analyzer — checks access rules for standard and AI-specific crawlers.
Uses Protego library for accurate user-agent directive parsing.
"""
from protego import Protego
from typing import Dict, List, Optional


# AI crawler user-agents to check for GEO analysis
AI_CRAWLERS = [
    "GPTBot",
    "ClaudeBot",
    "anthropic-ai",
    "Google-Extended",
    "PerplexityBot",
    "CCBot",
    "Bytespider",
]


def _detect_content_signals_note(robots_txt_content: str) -> Optional[str]:
    """Return a human-readable note when the file uses content-signal-style comments."""
    lower_content = robots_txt_content.lower()
    if "content signals" in lower_content or "ai-input" in lower_content or "ai-train" in lower_content:
        return (
            "File ini menggunakan format 'content signals' yang berbeda dari robots.txt standar. "
            "Karena tidak ada perintah Disallow/Allow standar yang bisa diproses, "
            "aplikasi menilai crawler tetap diizinkan secara default."
        )
    return None


def analyze_robots(robots_txt_content: str, target_path: str = "/") -> dict:
    """
    Analyze robots.txt content.
    
    Returns a dict with:
    - exists: True (since content was provided)
    - sitemap_urls: list of sitemap URLs found in robots.txt
    - default_ua_allowed: whether wildcard user-agent can access target_path
    - ai_crawler_access: dict mapping each AI crawler to allowed/blocked status
    """
    try:
        rp = Protego.parse(robots_txt_content)

        ai_crawler_status = {}
        for bot in AI_CRAWLERS:
            ai_crawler_status[bot] = rp.can_fetch(target_path, bot)

        sitemap_urls = list(rp.sitemaps) if rp.sitemaps else []
        note = _detect_content_signals_note(robots_txt_content)

        return {
            "exists": True,
            "sitemap_urls": sitemap_urls,
            "default_ua_allowed": rp.can_fetch(target_path, "*"),
            "ai_crawler_access": ai_crawler_status,
            "error": None,
            "note": note,
            "raw_content": robots_txt_content,
        }
    except Exception as e:
        return {
            "exists": True,
            "sitemap_urls": [],
            "default_ua_allowed": True,
            "ai_crawler_access": {},
            "error": f"Gagal mem-parse robots.txt: {str(e)}",
            "note": _detect_content_signals_note(robots_txt_content),
            "raw_content": robots_txt_content,
        }


def get_robots_not_found() -> dict:
    """Return result when robots.txt is not found (404)."""
    return {
        "exists": False,
        "sitemap_urls": [],
        "default_ua_allowed": True,
        "ai_crawler_access": {bot: True for bot in AI_CRAWLERS},
        "error": None,
        "note": None,
        "raw_content": None,
    }
