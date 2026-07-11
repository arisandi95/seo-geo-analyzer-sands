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

        return {
            "exists": True,
            "sitemap_urls": sitemap_urls,
            "default_ua_allowed": rp.can_fetch(target_path, "*"),
            "ai_crawler_access": ai_crawler_status,
            "error": None,
        }
    except Exception as e:
        return {
            "exists": True,
            "sitemap_urls": [],
            "default_ua_allowed": True,
            "ai_crawler_access": {},
            "error": f"Gagal mem-parse robots.txt: {str(e)}",
        }


def get_robots_not_found() -> dict:
    """Return result when robots.txt is not found (404)."""
    return {
        "exists": False,
        "sitemap_urls": [],
        "default_ua_allowed": True,
        "ai_crawler_access": {bot: True for bot in AI_CRAWLERS},
        "error": None,
    }
