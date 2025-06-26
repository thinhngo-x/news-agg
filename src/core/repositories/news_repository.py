"""
Main repository aggregating all sub-repositories with legacy compatibility.
"""

import logging
from typing import List, Optional
from datetime import datetime
from sqlmodel import Session

from ..models import Article, Feed, FeedStatistics, ArticleStatus, DailySummary
from .article_repository import ArticleRepository
from .feed_repository import FeedRepository
from .statistics_repository import StatisticsRepository
from .daily_summary_repository import DailySummaryRepository

logger = logging.getLogger(__name__)


class NewsRepository:
    """Main repository aggregating all sub-repositories"""

    def __init__(self, session: Optional[Session] = None):
        self.articles = ArticleRepository(session)
        self.feeds = FeedRepository(session)
        self.statistics = StatisticsRepository(session)
        self.daily_summaries = DailySummaryRepository(session)

    def get_global_statistics(self):
        """Get global statistics"""
        return self.statistics.get_global_statistics()

    # Legacy compatibility methods for backwards compatibility
    def create_feed(self, feed: Feed) -> Optional[int]:
        """Legacy method: Create a feed and return its ID"""
        try:
            saved_feed = self.feeds.save(feed)
            return saved_feed.id
        except Exception:
            return None

    def get_all_feeds(self, include_inactive: bool = True) -> List[Feed]:
        """Legacy method: Get all feeds"""
        if include_inactive:
            return self.feeds.get_all()
        else:
            return self.feeds.get_active()

    def get_feed_by_id(self, feed_id: int) -> Optional[Feed]:
        """Legacy method: Get feed by ID"""
        return self.feeds.get_by_id(feed_id)

    def update_feed(self, feed: Feed) -> bool:
        """Legacy method: Update a feed"""
        try:
            self.feeds.save(feed)
            return True
        except Exception:
            return False

    def update_feed_last_updated(self, feed_id: int) -> bool:
        """Legacy method: Update feed last updated timestamp"""
        return self.feeds.update_last_updated(feed_id)

    def permanently_delete_feed(self, feed_id: int) -> bool:
        """Legacy method: Delete a feed"""
        return self.feeds.delete(feed_id)

    def get_feed_statistics(self, feed_id: int) -> Optional[FeedStatistics]:
        """Legacy method: Get feed statistics"""
        return self.statistics.get_feed_statistics(feed_id)

    def create_article(self, article: Article) -> Optional[int]:
        """Legacy method: Create an article and return its ID"""
        try:
            saved_article = self.articles.save(article)
            return saved_article.id
        except Exception:
            return None

    def get_articles_since(self, cutoff_time: datetime) -> List[Article]:
        """Get articles created since a specific datetime"""
        return self.articles.get_articles_since(cutoff_time)

    def get_articles_from_active_feeds_since(
        self, cutoff_time: datetime
    ) -> List[Article]:
        """Get articles from active feeds created since a specific datetime"""
        return self.articles.get_articles_from_active_feeds_since(cutoff_time)

    def get_articles(
        self,
        limit: int = 50,
        offset: int = 0,
        feed_id: Optional[int] = None,
        status: Optional[ArticleStatus] = None,
    ) -> List[Article]:
        """Get articles with pagination and filtering"""
        return self.articles.get_articles(limit, offset, feed_id, status)

    def count_articles(
        self, feed_id: Optional[int] = None, status: Optional[ArticleStatus] = None
    ) -> int:
        """Count articles with filtering"""
        return self.articles.count_articles(feed_id, status)

    def get_article_by_id(self, article_id: int) -> Optional[Article]:
        """Get article by ID"""
        return self.articles.get_by_id(article_id)

    def get_articles_needing_content_scrape(self) -> List[Article]:
        """Get articles that need content scraping"""
        return self.articles.get_articles_needing_content_scrape()

    def get_articles_needing_summary(self) -> List[Article]:
        """Get articles that need AI summarization"""
        return self.articles.get_articles_needing_summary()
