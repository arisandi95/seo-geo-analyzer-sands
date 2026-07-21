"""
History service — save & read analysis records.
DB failures must never break the analysis flow: save/update swallow errors
and log a warning instead.
"""
import json
import logging
import secrets
from typing import Optional
from urllib.parse import urlparse

from sqlalchemy import func, select

from app.db import async_session
from app.models_db import AnalysisRecord

logger = logging.getLogger(__name__)

PER_PAGE = 20


def normalize_domain(url: str) -> str:
    """Lowercase hostname without leading 'www.' — used for trend grouping."""
    host = (urlparse(url).hostname or "").lower()
    if host.startswith("www."):
        host = host[4:]
    return host


async def save_analysis(
    url: str,
    audit_data: dict,
    ai_recommendation: Optional[str] = None,
    compare_group: Optional[str] = None,
) -> Optional[str]:
    """
    Persist one analysis. Returns the record id, or None if the DB write failed
    (the analysis itself must still be shown to the user).
    """
    try:
        record = AnalysisRecord(
            id=secrets.token_urlsafe(8)[:12],
            url=url,
            domain=normalize_domain(url),
            seo_score=int(audit_data.get("seo", {}).get("score", 0)),
            geo_score=int(audit_data.get("geo", {}).get("score", 0)),
            audit_json=json.dumps(audit_data, ensure_ascii=False, default=str),
            ai_recommendation=ai_recommendation,
            compare_group=compare_group,
        )
        async with async_session() as session:
            session.add(record)
            await session.commit()
        return record.id
    except Exception as e:
        logger.warning("Gagal menyimpan riwayat analisa: %s", e)
        return None


async def update_ai_recommendation(record_id: str, text: str) -> None:
    """Store the finished AI recommendation on an existing record."""
    try:
        async with async_session() as session:
            record = await session.get(AnalysisRecord, record_id)
            if record is not None:
                record.ai_recommendation = text
                await session.commit()
    except Exception as e:
        logger.warning("Gagal menyimpan rekomendasi AI ke riwayat: %s", e)


async def get_record(record_id: str) -> Optional[AnalysisRecord]:
    try:
        async with async_session() as session:
            return await session.get(AnalysisRecord, record_id)
    except Exception as e:
        logger.warning("Gagal membaca riwayat %s: %s", record_id, e)
        return None


def parse_audit_json(record: AnalysisRecord) -> Optional[dict]:
    """Parse stored audit JSON; None if corrupt (caller shows friendly 404)."""
    try:
        data = json.loads(record.audit_json)
        if not isinstance(data, dict):
            return None
        return data
    except (json.JSONDecodeError, TypeError) as e:
        logger.error("audit_json korup untuk record %s: %s", record.id, e)
        return None


async def list_records(page: int = 1) -> tuple[list[AnalysisRecord], int, int]:
    """Return (records, total_count, total_pages) for the history page."""
    page = max(1, page)
    try:
        async with async_session() as session:
            total = (await session.execute(
                select(func.count()).select_from(AnalysisRecord)
            )).scalar_one()
            result = await session.execute(
                select(AnalysisRecord)
                .order_by(AnalysisRecord.created_at.desc())
                .offset((page - 1) * PER_PAGE)
                .limit(PER_PAGE)
            )
            records = list(result.scalars())
        total_pages = max(1, -(-total // PER_PAGE))
        return records, total, total_pages
    except Exception as e:
        logger.warning("Gagal membaca daftar riwayat: %s", e)
        return [], 0, 1


async def get_domain_trend(domain: str) -> list[AnalysisRecord]:
    """All records for one normalized domain, oldest first (for the trend chart)."""
    try:
        async with async_session() as session:
            result = await session.execute(
                select(AnalysisRecord)
                .where(AnalysisRecord.domain == domain)
                .order_by(AnalysisRecord.created_at.asc())
                .limit(60)
            )
            return list(result.scalars())
    except Exception as e:
        logger.warning("Gagal membaca tren domain %s: %s", domain, e)
        return []
