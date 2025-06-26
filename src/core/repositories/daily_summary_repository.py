"""
Repository for managing daily summaries in the database.
"""

import logging
from typing import List, Optional
from datetime import datetime, timedelta
from sqlmodel import select
from sqlalchemy.exc import SQLAlchemyError

from ..models import DailySummary
from .base import BaseRepository
from .exceptions import DatabaseError

logger = logging.getLogger(__name__)


class DailySummaryRepository(BaseRepository):
    """Repository for managing daily summaries"""

    def create_summary(
        self,
        summary: str,
        article_count: int,
        sources_count: int,
        time_range_hours: int = 24,
        active_feeds_only: bool = True,
        title: Optional[str] = None
    ) -> DailySummary:
        """Create a new daily summary"""
        try:
            with self.get_session() as session:
                daily_summary = DailySummary(
                    title=title or "Daily News Summary",
                    summary=summary,
                    article_count=article_count,
                    sources_count=sources_count,
                    time_range_hours=time_range_hours,
                    active_feeds_only=active_feeds_only,
                    generated_at=datetime.now()
                )
                session.add(daily_summary)
                session.commit()
                session.refresh(daily_summary)
                return daily_summary
        except SQLAlchemyError as e:
            logger.error(f"Error creating daily summary: {e}")
            raise DatabaseError(f"Failed to create daily summary: {e}")

    def get_latest(self) -> Optional[DailySummary]:
        """Get the most recent daily summary"""
        try:
            with self.get_session() as session:
                statement = (
                    select(DailySummary)
                    .order_by(DailySummary.generated_at.desc())
                    .limit(1)
                )
                result = session.exec(statement).first()
                return result
        except SQLAlchemyError as e:
            logger.error(f"Error getting latest daily summary: {e}")
            raise DatabaseError(f"Failed to get latest daily summary: {e}")

    def get_summaries_since(self, since: datetime) -> List[DailySummary]:
        """Get all summaries generated since a specific datetime"""
        try:
            with self.get_session() as session:
                statement = (
                    select(DailySummary)
                    .where(DailySummary.generated_at >= since)
                    .order_by(DailySummary.generated_at.desc())
                )
                return list(session.exec(statement))
        except SQLAlchemyError as e:
            logger.error(f"Error getting summaries since {since}: {e}")
            raise DatabaseError(f"Failed to get summaries since {since}: {e}")

    def get_recent_summaries(self, limit: int = 10) -> List[DailySummary]:
        """Get recent daily summaries"""
        try:
            with self.get_session() as session:
                statement = (
                    select(DailySummary)
                    .order_by(DailySummary.generated_at.desc())
                    .limit(limit)
                )
                return list(session.exec(statement))
        except SQLAlchemyError as e:
            logger.error(f"Error getting recent summaries: {e}")
            raise DatabaseError(f"Failed to get recent summaries: {e}")

    def delete_old_summaries(self, days_old: int = 30) -> int:
        """Delete summaries older than specified days"""
        try:
            with self.get_session() as session:
                cutoff_date = datetime.now() - timedelta(days=days_old)
                statement = select(DailySummary).where(
                    DailySummary.generated_at < cutoff_date
                )
                old_summaries = session.exec(statement).all()
                
                count = 0
                for summary in old_summaries:
                    session.delete(summary)
                    count += 1
                
                session.commit()
                logger.info(f"Deleted {count} old daily summaries")
                return count
        except SQLAlchemyError as e:
            logger.error(f"Error deleting old summaries: {e}")
            raise DatabaseError(f"Failed to delete old summaries: {e}")
