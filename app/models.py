"""
Pydantic models for request/response validation.
"""
from pydantic import BaseModel, HttpUrl, field_validator
from typing import Optional, Dict, List, Any


class AnalyzeRequest(BaseModel):
    """Request model for URL analysis."""
    url: str

    @field_validator("url")
    @classmethod
    def validate_and_normalize_url(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("URL tidak boleh kosong")
        if not v.startswith(("http://", "https://")):
            v = f"https://{v}"
        return v


class RobotsResult(BaseModel):
    """Result of robots.txt analysis."""
    exists: bool
    sitemap_urls: List[str] = []
    default_ua_allowed: bool = True
    ai_crawler_access: Dict[str, bool] = {}
    error: Optional[str] = None
    note: Optional[str] = None
    raw_content: Optional[str] = None


class SitemapResult(BaseModel):
    """Result of sitemap analysis."""
    found: bool
    url: Optional[str] = None
    type: Optional[str] = None  # "urlset" or "sitemapindex"
    total_urls: int = 0
    has_lastmod: bool = False
    most_recent_lastmod: Optional[str] = None
    error: Optional[str] = None


class SEOCheckItem(BaseModel):
    """Individual SEO check result."""
    name: str
    status: str  # "good", "warning", "error"
    message: str
    details: Optional[Any] = None


class SEOResult(BaseModel):
    """Result of SEO analysis."""
    score: int = 0
    checks: List[SEOCheckItem] = []
    word_count: int = 0
    internal_links: int = 0
    external_links: int = 0


class GEOCheckItem(BaseModel):
    """Individual GEO check result."""
    name: str
    status: str  # "good", "warning", "error"
    message: str
    weight: float = 1.0


class GEOResult(BaseModel):
    """Result of GEO analysis."""
    score: int = 0
    checks: List[GEOCheckItem] = []


class AuditResult(BaseModel):
    """Complete audit result."""
    url: str
    robots: RobotsResult
    sitemap: SitemapResult
    seo: SEOResult
    geo: GEOResult
    ai_recommendation: str = ""
