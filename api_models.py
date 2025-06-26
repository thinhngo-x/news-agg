"""
API response models and request schemas for the News Aggregator API.
"""

from pydantic import BaseModel, HttpUrl
from typing import Optional, List, Dict, Any
from datetime import datetime
from enum import Enum

from src.core.models import ArticleStatus, FeedStatus, Article, Feed


# Request Models
class FeedCreateRequest(BaseModel):
    url: HttpUrl
    title: Optional[str] = None
    description: Optional[str] = None


class FeedUpdateRequest(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    status: Optional[FeedStatus] = None


class AIConfigRequest(BaseModel):
    api_key: str
    model: Optional[str] = None


class FeedValidationRequest(BaseModel):
    url: HttpUrl


# Response Models
class APIResponse(BaseModel):
    message: str
    success: bool = True


class HealthCheckResponse(BaseModel):
    status: str
    api_key_configured: bool
    ai_available: bool
    timestamp: datetime


class ArticlesResponse(BaseModel):
    articles: List[Article]
    count: int
    total: Optional[int] = None
    has_more: bool = False


class RecentArticlesResponse(BaseModel):
    articles: List[Article]
    count: int
    hours: int
    active_feeds_only: bool


class FeedStatisticsResponse(BaseModel):
    feed_id: int
    feed_title: str
    total_articles: int
    articles_with_content: int
    articles_with_summary: int
    latest_article_date: Optional[datetime]
    last_updated: Optional[datetime]
    completion_rate: float


class FeedValidationResponse(BaseModel):
    valid: bool
    title: Optional[str] = None
    description: Optional[str] = None
    entry_count: Optional[int] = None
    latest_entry: Optional[str] = None
    error: Optional[str] = None


class AIStatusResponse(BaseModel):
    available: bool
    current_model: str
    available_models: List[Dict[str, Any]]


class DailySummaryResponse(BaseModel):
    summary: str
    article_count: int
    sources_count: int
    generated_at: datetime


class ConfigurationResponse(BaseModel):
    ai_configured: bool
    selected_model: str
    bulk_summarize_limit: int
    default_feeds: List[str]


class BulkOperationResponse(BaseModel):
    message: str
    total_items: int
    processed_items: int
    success_count: int
    error_count: int
    errors: List[str] = []