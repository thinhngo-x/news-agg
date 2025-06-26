"""
Domain models for the News Aggregator application.

This module defines the core data structures using SQLModel for database management.
"""

from typing import Optional, Dict, Any
from datetime import datetime
from enum import Enum
from sqlmodel import SQLModel, Field, Column, String, DateTime, JSON
from sqlalchemy import func


class ArticleStatus(str, Enum):
    """Status of an article in the processing pipeline"""

    PENDING = "pending"
    SCRAPED = "scraped"
    SUMMARIZED = "summarized"
    ERROR = "error"


class FeedStatus(str, Enum):
    """Status of a feed"""

    ACTIVE = "active"
    INACTIVE = "inactive"
    ERROR = "error"
    PAUSED = "paused"


class Article(SQLModel, table=True):
    """Represents a news article"""

    __tablename__ = "articles"
    __table_args__ = {"extend_existing": True}

    id: Optional[int] = Field(default=None, primary_key=True)
    title: str = Field(index=True)
    link: str = Field(unique=True, index=True)
    description: Optional[str] = None
    published: Optional[str] = None
    feed_url: str = Field(index=True)
    content: Optional[str] = None
    summary: Optional[str] = None
    status: ArticleStatus = Field(
        default=ArticleStatus.PENDING, sa_column=Column(String)
    )
    created_at: datetime = Field(
        default_factory=datetime.now,
        sa_column=Column(DateTime(timezone=True), server_default=func.now()),
    )
    updated_at: Optional[datetime] = Field(
        default=None, sa_column=Column(DateTime(timezone=True), onupdate=func.now())
    )

    @property
    def has_content(self) -> bool:
        """Check if article has scraped content"""
        return bool(self.content and self.content.strip())

    @property
    def has_summary(self) -> bool:
        """Check if article has AI summary"""
        return bool(self.summary and self.summary.strip())

    @property
    def is_complete(self) -> bool:
        """Check if article is fully processed"""
        return self.has_content and self.has_summary


class Feed(SQLModel, table=True):
    """Represents an RSS/Atom feed"""

    __tablename__ = "feeds"
    __table_args__ = {"extend_existing": True}

    id: Optional[int] = Field(default=None, primary_key=True)
    url: str = Field(unique=True, index=True)
    title: Optional[str] = None
    description: Optional[str] = None
    status: FeedStatus = Field(default=FeedStatus.ACTIVE, sa_column=Column(String))
    last_updated: Optional[datetime] = None
    last_fetch_error: Optional[str] = None
    fetch_interval: int = Field(default=3600)  # seconds
    created_at: datetime = Field(
        default_factory=datetime.now,
        sa_column=Column(DateTime(timezone=True), server_default=func.now()),
    )
    updated_at: Optional[datetime] = Field(
        default=None, sa_column=Column(DateTime(timezone=True), onupdate=func.now())
    )

    # Custom metadata as JSON field (renamed to avoid conflict with SQLModel.metadata)
    feed_metadata: Optional[Dict[str, Any]] = Field(
        default_factory=dict, sa_column=Column(JSON)
    )

    @property
    def is_active(self) -> bool:
        """Check if feed is active"""
        return self.status == FeedStatus.ACTIVE

    @property
    def display_name(self) -> str:
        """Get display name for the feed"""
        return self.title or self.url

    def mark_error(self, error_message: str) -> None:
        """Mark feed as having an error"""
        self.status = FeedStatus.ERROR
        self.last_fetch_error = error_message
        self.updated_at = datetime.now()

    def mark_success(self) -> None:
        """Mark feed as successfully updated"""
        if self.status == FeedStatus.ERROR:
            self.status = FeedStatus.ACTIVE
        self.last_fetch_error = None
        self.last_updated = datetime.now()
        self.updated_at = datetime.now()


# Non-table models (for DTOs and statistics)
class FeedStatistics(SQLModel):
    """Statistics for a feed"""

    feed_id: int
    feed_title: str
    total_articles: int = 0
    articles_with_content: int = 0
    articles_with_summary: int = 0
    latest_article_date: Optional[datetime] = None
    last_updated: Optional[datetime] = None
    error_count: int = 0

    @property
    def content_completion_rate(self) -> float:
        """Percentage of articles with content"""
        if self.total_articles == 0:
            return 0.0
        return (self.articles_with_content / self.total_articles) * 100

    @property
    def summary_completion_rate(self) -> float:
        """Percentage of articles with summaries"""
        if self.total_articles == 0:
            return 0.0
        return (self.articles_with_summary / self.total_articles) * 100


class AIModelInfo(SQLModel):
    """Information about an AI model"""

    model_id: str
    display_name: str
    description: str = ""
    is_available: bool = False
    cost_tier: str = "unknown"  # free, low, medium, high
    max_tokens: Optional[int] = None

    @property
    def is_recommended(self) -> bool:
        """Check if this model is recommended for general use"""
        return self.is_available and self.cost_tier in ["free", "low"]


class ProcessingJob(SQLModel):
    """Represents a background processing job"""

    id: str
    job_type: str  # "scrape", "summarize", "bulk_update"
    status: str = "pending"  # pending, running, completed, failed
    progress: float = 0.0
    total_items: int = 0
    processed_items: int = 0
    error_message: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.now)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None

    @property
    def is_running(self) -> bool:
        """Check if job is currently running"""
        return self.status == "running"

    @property
    def is_completed(self) -> bool:
        """Check if job completed successfully"""
        return self.status == "completed"

    @property
    def has_error(self) -> bool:
        """Check if job failed"""
        return self.status == "failed"
