"""
Repository for feed-related database operations.
"""

import logging
from typing import List, Optional
from sqlmodel import select, func
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy import text

from ..models import Feed, FeedStatus
from .base import BaseRepository
from .exceptions import DatabaseError

logger = logging.getLogger(__name__)


class FeedRepository(BaseRepository):
    """Repository for feed operations"""

    def save(self, feed: Feed) -> Feed:
        """Save a feed to the database"""
        try:
            with self.get_session() as session:
                if feed.id is None:
                    # New feed
                    session.add(feed)
                else:
                    # Update existing feed
                    session.merge(feed)
                session.commit()
                session.refresh(feed)
                return feed
        except SQLAlchemyError as e:
            logger.error(f"Error saving feed: {e}")
            raise DatabaseError(f"Failed to save feed: {e}")

    def get_by_id(self, feed_id: int) -> Optional[Feed]:
        """Get feed by ID"""
        try:
            with self.get_session() as session:
                return session.get(Feed, feed_id)
        except SQLAlchemyError as e:
            logger.error(f"Error getting feed by ID {feed_id}: {e}")
            raise DatabaseError(f"Failed to get feed: {e}")

    def get_by_url(self, url: str) -> Optional[Feed]:
        """Get feed by URL"""
        try:
            with self.get_session() as session:
                statement = select(Feed).where(Feed.url == url)
                return session.exec(statement).first()
        except SQLAlchemyError as e:
            logger.error(f"Error getting feed by URL {url}: {e}")
            raise DatabaseError(f"Failed to get feed: {e}")

    def get_all(self) -> List[Feed]:
        """Get all feeds"""
        try:
            with self.get_session() as session:
                statement = select(Feed).order_by(text("created_at DESC"))
                return list(session.exec(statement))
        except SQLAlchemyError as e:
            logger.error(f"Error getting all feeds: {e}")
            raise DatabaseError(f"Failed to get feeds: {e}")

    def get_active(self) -> List[Feed]:
        """Get active feeds"""
        try:
            with self.get_session() as session:
                statement = select(Feed).where(Feed.status == FeedStatus.ACTIVE)
                return list(session.exec(statement))
        except SQLAlchemyError as e:
            logger.error(f"Error getting active feeds: {e}")
            raise DatabaseError(f"Failed to get active feeds: {e}")

    def delete(self, feed_id: int) -> bool:
        """Delete a feed"""
        try:
            with self.get_session() as session:
                feed = session.get(Feed, feed_id)
                if feed:
                    session.delete(feed)
                    session.commit()
                    return True
                return False
        except SQLAlchemyError as e:
            logger.error(f"Error deleting feed ID {feed_id}: {e}")
            raise DatabaseError(f"Failed to delete feed: {e}")

    def get_count(self) -> int:
        """Get total feed count"""
        try:
            with self.get_session() as session:
                statement = select(func.count()).select_from(Feed)
                return session.exec(statement).one()
        except SQLAlchemyError as e:
            logger.error(f"Error getting feed count: {e}")
            raise DatabaseError(f"Failed to get feed count: {e}")

    def update_last_updated(self, feed_id: int) -> bool:
        """Update feed last updated timestamp"""
        try:
            feed = self.get_by_id(feed_id)
            if feed:
                from datetime import datetime

                feed.last_updated = datetime.now()
                self.save(feed)
                return True
            return False
        except Exception as e:
            logger.error(f"Error updating feed last updated for ID {feed_id}: {e}")
            return False
