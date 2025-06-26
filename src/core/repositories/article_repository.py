"""
Repository for article-related database operations.
"""

import logging
from typing import List, Optional
from sqlmodel import select, func
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy import or_, text
from datetime import datetime

from ..models import Article, ArticleStatus, Feed, FeedStatus
from .base import BaseRepository
from .exceptions import DatabaseError

logger = logging.getLogger(__name__)


class ArticleRepository(BaseRepository):
    """Repository for article operations"""

    def save(self, article: Article) -> Article:
        """Save an article to the database"""
        try:
            with self.get_session() as session:
                if article.id is None:
                    # New article
                    session.add(article)
                else:
                    # Update existing article
                    session.merge(article)
                session.commit()
                session.refresh(article)
                return article
        except SQLAlchemyError as e:
            logger.error(f"Error saving article: {e}")
            raise DatabaseError(f"Failed to save article: {e}")

    def get_by_id(self, article_id: int) -> Optional[Article]:
        """Get article by ID"""
        try:
            with self.get_session() as session:
                return session.get(Article, article_id)
        except SQLAlchemyError as e:
            logger.error(f"Error getting article by ID {article_id}: {e}")
            raise DatabaseError(f"Failed to get article: {e}")

    def get_by_link(self, link: str) -> Optional[Article]:
        """Get article by link"""
        try:
            with self.get_session() as session:
                statement = select(Article).where(Article.link == link)
                return session.exec(statement).first()
        except SQLAlchemyError as e:
            logger.error(f"Error getting article by link {link}: {e}")
            raise DatabaseError(f"Failed to get article: {e}")

    def get_all(self, limit: Optional[int] = None, offset: int = 0) -> List[Article]:
        """Get all articles with optional pagination"""
        try:
            with self.get_session() as session:
                statement = (
                    select(Article).order_by(text("created_at DESC")).offset(offset)
                )
                if limit:
                    statement = statement.limit(limit)
                return list(session.exec(statement))
        except SQLAlchemyError as e:
            logger.error(f"Error getting all articles: {e}")
            raise DatabaseError(f"Failed to get articles: {e}")

    def get_by_feed_url(
        self, feed_url: str, limit: Optional[int] = None
    ) -> List[Article]:
        """Get articles by feed URL"""
        try:
            with self.get_session() as session:
                statement = (
                    select(Article)
                    .where(Article.feed_url == feed_url)
                    .order_by(text("created_at DESC"))
                )
                if limit:
                    statement = statement.limit(limit)
                return list(session.exec(statement))
        except SQLAlchemyError as e:
            logger.error(f"Error getting articles by feed URL {feed_url}: {e}")
            raise DatabaseError(f"Failed to get articles: {e}")

    def get_by_status(
        self, status: ArticleStatus, limit: Optional[int] = None
    ) -> List[Article]:
        """Get articles by status"""
        try:
            with self.get_session() as session:
                statement = (
                    select(Article)
                    .where(Article.status == status)
                    .order_by(text("created_at DESC"))
                )
                if limit:
                    statement = statement.limit(limit)
                return list(session.exec(statement))
        except SQLAlchemyError as e:
            logger.error(f"Error getting articles by status {status}: {e}")
            raise DatabaseError(f"Failed to get articles: {e}")

    def get_without_content(self, limit: Optional[int] = None) -> List[Article]:
        """Get articles without scraped content"""
        try:
            with self.get_session() as session:
                statement = (
                    select(Article)
                    .where(
                        or_(
                            Article.content.is_(None), Article.content == ""
                        )  # Use is_(None) for NULL check
                    )
                    .order_by(text("created_at DESC"))
                )
                if limit:
                    statement = statement.limit(limit)
                result = list(session.exec(statement))
                return result
        except SQLAlchemyError as e:
            logger.error(f"Error getting articles without content: {e}")
            raise DatabaseError(f"Failed to get articles: {e}")

    def get_without_summary(self, limit: Optional[int] = None) -> List[Article]:
        """Get articles without AI summary"""
        try:
            with self.get_session() as session:
                statement = (
                    select(Article)
                    .where(or_(Article.summary.is_(None), Article.summary == ""))
                    .order_by(text("created_at DESC"))
                )
                if limit:
                    statement = statement.limit(limit)
                return list(session.exec(statement))
        except SQLAlchemyError as e:
            logger.error(f"Error getting articles without summary: {e}")
            raise DatabaseError(f"Failed to get articles: {e}")

    def update_content(self, article_id: int, content: str) -> bool:
        """Update article content"""
        try:
            with self.get_session() as session:
                article = session.get(Article, article_id)
                if article:
                    article.content = content
                    article.status = ArticleStatus.SCRAPED
                    session.add(article)
                    session.commit()
                    return True
                return False
        except SQLAlchemyError as e:
            logger.error(f"Error updating article content for ID {article_id}: {e}")
            raise DatabaseError(f"Failed to update article content: {e}")

    def update_summary(self, article_id: int, summary: str) -> bool:
        """Update article summary"""
        try:
            with self.get_session() as session:
                article = session.get(Article, article_id)
                if article:
                    article.summary = summary
                    article.status = ArticleStatus.SUMMARIZED
                    session.add(article)
                    session.commit()
                    return True
                return False
        except SQLAlchemyError as e:
            logger.error(f"Error updating article summary for ID {article_id}: {e}")
            raise DatabaseError(f"Failed to update article summary: {e}")

    def delete(self, article_id: int) -> bool:
        """Delete an article"""
        try:
            with self.get_session() as session:
                article = session.get(Article, article_id)
                if article:
                    session.delete(article)
                    session.commit()
                    return True
                return False
        except SQLAlchemyError as e:
            logger.error(f"Error deleting article ID {article_id}: {e}")
            raise DatabaseError(f"Failed to delete article: {e}")

    def delete_by_feed_url(self, feed_url: str) -> int:
        """Delete all articles from a feed"""
        try:
            with self.get_session() as session:
                statement = select(Article).where(Article.feed_url == feed_url)
                articles = session.exec(statement).all()
                count = len(articles)
                for article in articles:
                    session.delete(article)
                session.commit()
                return count
        except SQLAlchemyError as e:
            logger.error(f"Error deleting articles by feed URL {feed_url}: {e}")
            raise DatabaseError(f"Failed to delete articles: {e}")

    def get_count(self) -> int:
        """Get total article count"""
        try:
            with self.get_session() as session:
                statement = select(func.count()).select_from(Article)
                return session.exec(statement).one()
        except SQLAlchemyError as e:
            logger.error(f"Error getting article count: {e}")
            raise DatabaseError(f"Failed to get article count: {e}")

    def get_count_by_feed_url(self, feed_url: str) -> int:
        """Get article count by feed URL"""
        try:
            with self.get_session() as session:
                statement = (
                    select(func.count())
                    .select_from(Article)
                    .where(Article.feed_url == feed_url)
                )
                return session.exec(statement).one()
        except SQLAlchemyError as e:
            logger.error(f"Error getting article count by feed URL {feed_url}: {e}")
            raise DatabaseError(f"Failed to get article count: {e}")

    def get_articles_since(self, cutoff_time: datetime) -> List[Article]:
        """Get articles created since a specific datetime"""
        try:
            with self.get_session() as session:
                statement = (
                    select(Article)
                    .where(Article.created_at >= cutoff_time)
                    .order_by(text("created_at DESC"))
                )
                return list(session.exec(statement))
        except SQLAlchemyError as e:
            logger.error(f"Error getting articles since {cutoff_time}: {e}")
            raise DatabaseError(f"Failed to get articles: {e}")

    def get_articles_from_active_feeds_since(
        self, cutoff_time: datetime
    ) -> List[Article]:
        """Get articles from active feeds created since a specific datetime"""
        try:
            with self.get_session() as session:
                # Join with Feed table to filter by active status
                statement = (
                    select(Article)
                    .join(Feed, Article.feed_url == Feed.url)
                    .where(Article.created_at >= cutoff_time)
                    .where(Feed.status == FeedStatus.ACTIVE)
                    .order_by(text("articles.created_at DESC"))
                )
                return list(session.exec(statement))
        except SQLAlchemyError as e:
            logger.error(
                f"Error getting articles from active feeds since {cutoff_time}: {e}"
            )
            raise DatabaseError(f"Failed to get articles from active feeds: {e}")

    def get_articles(
        self,
        limit: int = 50,
        offset: int = 0,
        feed_id: Optional[int] = None,
        status: Optional[ArticleStatus] = None,
    ) -> List[Article]:
        """Get articles with pagination and filtering"""
        try:
            with self.get_session() as session:
                statement = select(Article)

                # Apply filters
                if feed_id:
                    statement = statement.where(Article.feed_id == feed_id)
                if status:
                    statement = statement.where(Article.status == status)

                # Apply pagination and ordering
                statement = (
                    statement
                    .order_by(text("created_at DESC"))
                    .offset(offset)
                    .limit(limit)
                )

                return list(session.exec(statement))
        except SQLAlchemyError as e:
            logger.error(f"Error getting articles: {e}")
            raise DatabaseError(f"Failed to get articles: {e}")

    def count_articles(
        self, feed_id: Optional[int] = None, status: Optional[ArticleStatus] = None
    ) -> int:
        """Count articles with filtering"""
        try:
            with self.get_session() as session:
                statement = select(func.count(Article.id))

                # Apply filters
                if feed_id:
                    statement = statement.where(Article.feed_id == feed_id)
                if status:
                    statement = statement.where(Article.status == status)

                return session.exec(statement).one()
        except SQLAlchemyError as e:
            logger.error(f"Error counting articles: {e}")
            raise DatabaseError(f"Failed to count articles: {e}")

    def get_articles_needing_content_scrape(self) -> List[Article]:
        """Get articles that need content scraping"""
        try:
            with self.get_session() as session:
                statement = (
                    select(Article)
                    .where(Article.status == ArticleStatus.PENDING)
                    .where(Article.content.is_(None))
                    .order_by(text("created_at DESC"))
                    .limit(100)  # Limit for performance
                )
                return list(session.exec(statement))
        except SQLAlchemyError as e:
            logger.error(f"Error getting articles needing content scrape: {e}")
            raise DatabaseError(f"Failed to get articles needing content scrape: {e}")

    def get_articles_needing_summary(self) -> List[Article]:
        """Get articles that need AI summarization"""
        try:
            with self.get_session() as session:
                statement = (
                    select(Article)
                    .where(Article.status == ArticleStatus.SCRAPED)
                    .where(Article.summary.is_(None))
                    .where(Article.content.is_not(None))
                    .order_by(text("created_at DESC"))
                    .limit(50)  # Limit for performance and API costs
                )
                return list(session.exec(statement))
        except SQLAlchemyError as e:
            logger.error(f"Error getting articles needing summary: {e}")
            raise DatabaseError(f"Failed to get articles needing summary: {e}")
