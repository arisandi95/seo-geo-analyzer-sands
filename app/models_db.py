"""
ORM models for analysis history.
"""
from datetime import datetime, timezone

from sqlalchemy import DateTime, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


def utcnow_naive() -> datetime:
    """Naive UTC timestamp (SQLite DateTime column stores naive values)."""
    return datetime.now(timezone.utc).replace(tzinfo=None)


class AnalysisRecord(Base):
    __tablename__ = "analysis_records"

    # Short random id (secrets.token_urlsafe), used as a public permalink — NOT auto-increment
    id: Mapped[str] = mapped_column(String(12), primary_key=True)
    url: Mapped[str] = mapped_column(String(2048), index=True)
    # Normalized lowercase without "www." for trend grouping
    domain: Mapped[str] = mapped_column(String(255), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow_naive, index=True)
    seo_score: Mapped[int]
    geo_score: Mapped[int]
    audit_json: Mapped[str] = mapped_column(Text)  # full audit result as JSON
    ai_recommendation: Mapped[str | None] = mapped_column(Text, nullable=True)
    # Pair marker for compare mode (two records share one group id)
    compare_group: Mapped[str | None] = mapped_column(String(12), nullable=True, index=True)
