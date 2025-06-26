"""
Repository for statistics and analytics operations.
"""

import logging
from typing import Optional, Dict, Any
from sqlmodel import select, func
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy import text

from ..models import Article, Feed, FeedStatistics, FeedStatus
from ..database import get_session
from .base import BaseRepository
from .exceptions import DatabaseError

logger = logging.getLogger(__name__)


class StatisticsRepository(BaseRepository):
    """Repository for statistics operations"""

    def get_feed_statistics(self, feed_id: int) -> Optional[FeedStatistics]:
        """Get statistics for a feed"""
        try:
            with self.get_session() as session:
                feed = session.get(Feed, feed_id)
                if not feed:
                    return None

                # Get article counts
                total_articles = session.exec(
                    select(func.count())
                    .select_from(Article)
                    .where(Article.feed_url == feed.url)
                ).one()

                articles_with_content = session.exec(
                    select(func.count())
                    .select_from(Article)
                    .where(
                        (Article.feed_url == feed.url)
                        & (Article.content is not None)
                        & (Article.content != "")
                    )
                ).one()

                articles_with_summary = session.exec(
                    select(func.count())
                    .select_from(Article)
                    .where(
                        (Article.feed_url == feed.url)
                        & (Article.summary is not None)
                        & (Article.summary != "")
                    )
                ).one()

                # Get latest article date
                latest_article = session.exec(
                    select(Article.created_at)
                    .where(Article.feed_url == feed.url)
                    .order_by(text("created_at DESC"))
                    .limit(1)
                ).first()

                return FeedStatistics(
                    feed_id=feed.id,
                    feed_title=feed.display_name,
                    total_articles=total_articles,
                    articles_with_content=articles_with_content,
                    articles_with_summary=articles_with_summary,
                    latest_article_date=latest_article,
                    last_updated=feed.last_updated,
                    error_count=1 if feed.status == FeedStatus.ERROR else 0,
                )
        except SQLAlchemyError as e:
            logger.error(f"Error getting feed statistics for ID {feed_id}: {e}")
            raise DatabaseError(f"Failed to get feed statistics: {e}")

    def get_global_statistics(self) -> Dict[str, Any]:
        """Get global statistics"""
        try:
            with get_session() as session:
                # Total counts
                total_articles = session.exec(
                    select(func.count()).select_from(Article)
                ).one()

                total_feeds = session.exec(select(func.count()).select_from(Feed)).one()

                # Content and summary counts
                articles_with_content = session.exec(
                    select(func.count())
                    .select_from(Article)
                    .where((Article.content.is_not(None)) & (Article.content != ""))
                ).one()

                articles_with_summary = session.exec(
                    select(func.count())
                    .select_from(Article)
                    .where((Article.summary.is_not(None)) & (Article.summary != ""))
                ).one()

                # Active feeds
                active_feeds = session.exec(
                    select(func.count())
                    .select_from(Feed)
                    .where(Feed.status == FeedStatus.ACTIVE)
                ).one()

            return {
                "total_articles": total_articles,
                "total_feeds": total_feeds,
                "active_feeds": active_feeds,
                "articles_with_content": articles_with_content,
                "articles_with_summary": articles_with_summary,
                "content_completion_rate": (
                    articles_with_content / total_articles * 100
                )
                if total_articles > 0
                else 0,
                "summary_completion_rate": (
                    articles_with_summary / total_articles * 100
                )
                if total_articles > 0
                else 0,
            }
        except SQLAlchemyError as e:
            logger.error(f"Error getting global statistics: {e}")
            raise DatabaseError(f"Failed to get global statistics: {e}")
