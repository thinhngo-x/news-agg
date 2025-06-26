"""
Repository pattern implementation for data access using SQLModel.

This module provides a clean abstraction layer for database operations
following the repository pattern for better testability and maintainability.

DEPRECATED: This module is kept for backwards compatibility.
Use the individual repositories from the repositories package instead.
"""

# Import everything from the new repositories package for backwards compatibility
from .repositories import (
    DatabaseError,
    BaseRepository,
    ArticleRepository,
    FeedRepository,
    NewsRepository,
)

# Legacy imports - maintain backwards compatibility
__all__ = [
    "DatabaseError",
    "BaseRepository",
    "ArticleRepository",
    "FeedRepository",
    "NewsRepository",
    # Note: StatisticsRepository is not included in legacy compatibility
    # as it wasn't part of the original interface
]
