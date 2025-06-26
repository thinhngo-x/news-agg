"""
Repository package for data access operations.

This package contains repository implementations following the repository pattern
for better separation of concerns and testability.
"""

from .exceptions import DatabaseError
from .base import BaseRepository
from .article_repository import ArticleRepository
from .feed_repository import FeedRepository
from .statistics_repository import StatisticsRepository
from .news_repository import NewsRepository

__all__ = [
    "DatabaseError",
    "BaseRepository",
    "ArticleRepository",
    "FeedRepository",
    "StatisticsRepository",
    "NewsRepository",
]
