"""
FastAPI main application for News Aggregator.

This serves as the API backend for the React frontend.
"""

from fastapi import FastAPI, Depends, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from typing import List, Optional, Dict, Any
import logging
from datetime import datetime

from src.core.config import ConfigManager
from src.core.database import get_session
from src.core.models import Article, Feed, FeedStatus, ArticleStatus
from src.core.repositories import NewsRepository, FeedRepository, ArticleRepository
from src.services.feed_manager import FeedManager
from src.services.ai_summarizer import AISummarizer
from src.services.content_scraper import ContentScraper

# Import API models
from api_models import (
    FeedCreateRequest, FeedUpdateRequest, AIConfigRequest, FeedValidationRequest,
    APIResponse, HealthCheckResponse, ArticlesResponse, RecentArticlesResponse,
    FeedStatisticsResponse, FeedValidationResponse, AIStatusResponse,
    DailySummaryResponse, ConfigurationResponse, BulkOperationResponse
)

# Initialize logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(
    title="News Aggregator API",
    description="REST API for the News Aggregator application",
    version="1.0.0"
)

# Add CORS middleware for React frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:3001"],  # React dev server
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global configuration and services
config = ConfigManager()
repository = NewsRepository()
feed_manager = FeedManager(config, repository)
ai_summarizer = AISummarizer(config, repository)
content_scraper = ContentScraper(config, repository)


# Dependency injection
def get_config() -> ConfigManager:
    return config


def get_repository() -> NewsRepository:
    return repository


def get_feed_manager() -> FeedManager:
    return feed_manager


def get_ai_summarizer() -> AISummarizer:
    return ai_summarizer


def get_content_scraper() -> ContentScraper:
    return content_scraper


# API Routes

@app.get("/")
async def root():
    """Health check endpoint"""
    return {"message": "News Aggregator API is running"}


@app.get("/health", response_model=HealthCheckResponse)
async def health_check():
    """Detailed health check"""
    return HealthCheckResponse(
        status="healthy",
        api_key_configured=config.has_openai_api_key(),
        ai_available=ai_summarizer.is_available(),
        timestamp=datetime.now()
    )


# Articles endpoints
@app.get("/api/articles", response_model=ArticlesResponse)
async def get_articles(
    limit: int = 50,
    offset: int = 0,
    feed_id: Optional[int] = None,
    status: Optional[ArticleStatus] = None,
    repo: NewsRepository = Depends(get_repository)
):
    """Get articles with pagination and filtering"""
    articles = repo.get_articles(limit=limit, offset=offset, feed_id=feed_id, status=status)
    total_count = repo.count_articles(feed_id=feed_id, status=status)
    
    return ArticlesResponse(
        articles=articles,
        count=len(articles),
        total=total_count,
        has_more=(offset + len(articles)) < total_count
    )


@app.get("/api/articles/recent", response_model=RecentArticlesResponse)
async def get_recent_articles(
    hours: int = 24,
    active_feeds_only: bool = True,
    feed_mgr: FeedManager = Depends(get_feed_manager)
):
    """Get recent articles from the last N hours"""
    if active_feeds_only:
        articles = feed_mgr.get_recent_articles_from_active_feeds(hours=hours)
    else:
        articles = feed_mgr.get_recent_articles(hours=hours)
    
    return RecentArticlesResponse(
        articles=articles,
        count=len(articles),
        hours=hours,
        active_feeds_only=active_feeds_only
    )


@app.get("/api/articles/{article_id}", response_model=Article)
async def get_article(article_id: int, repo: NewsRepository = Depends(get_repository)):
    """Get a specific article by ID"""
    article = repo.get_article_by_id(article_id)
    if not article:
        raise HTTPException(status_code=404, detail="Article not found")
    return article


@app.post("/api/articles/{article_id}/scrape", response_model=Article)
async def scrape_article_content(
    article_id: int,
    scraper: ContentScraper = Depends(get_content_scraper),
    repo: NewsRepository = Depends(get_repository)
):
    """Scrape content for a specific article"""
    article = repo.get_article_by_id(article_id)
    if not article:
        raise HTTPException(status_code=404, detail="Article not found")
    
    success = scraper.scrape_and_save_content(article_id, article.link)
    if not success:
        raise HTTPException(status_code=500, detail="Failed to scrape article content")
    
    # Return updated article
    updated_article = repo.get_article_by_id(article_id)
    return updated_article


@app.post("/api/articles/{article_id}/summarize", response_model=Article)
async def summarize_article(
    article_id: int,
    ai: AISummarizer = Depends(get_ai_summarizer),
    repo: NewsRepository = Depends(get_repository)
):
    """Generate AI summary for a specific article"""
    if not ai.is_available():
        raise HTTPException(status_code=400, detail="AI summarization not available")
    
    article = repo.get_article_by_id(article_id)
    if not article:
        raise HTTPException(status_code=404, detail="Article not found")
    
    success = ai.summarize_article(article_id)
    if not success:
        raise HTTPException(status_code=500, detail="Failed to generate summary")
    
    # Return updated article
    updated_article = repo.get_article_by_id(article_id)
    return updated_article


# Feeds endpoints
@app.get("/api/feeds", response_model=List[Feed])
async def get_feeds(
    include_inactive: bool = False,
    feed_mgr: FeedManager = Depends(get_feed_manager)
):
    """Get all feeds"""
    feeds = feed_mgr.get_all_feeds(include_inactive=include_inactive)
    return feeds


@app.post("/api/feeds", response_model=Feed)
async def create_feed(
    request: FeedCreateRequest,
    feed_mgr: FeedManager = Depends(get_feed_manager)
):
    """Add a new RSS feed"""
    success = feed_mgr.add_feed(str(request.url), request.title or "", request.description or "")
    if not success:
        raise HTTPException(status_code=400, detail="Failed to add feed")
    
    # Get the newly created feed
    feeds = feed_mgr.get_all_feeds()
    new_feed = next((f for f in feeds if f.url == str(request.url)), None)
    if not new_feed:
        raise HTTPException(status_code=500, detail="Feed created but could not be retrieved")
    
    return new_feed


@app.put("/api/feeds/{feed_id}", response_model=Feed)
async def update_feed(
    feed_id: int,
    request: FeedUpdateRequest,
    feed_mgr: FeedManager = Depends(get_feed_manager)
):
    """Update an existing feed"""
    success = feed_mgr.update_feed(feed_id, request.title, request.description, request.status)
    if not success:
        raise HTTPException(status_code=404, detail="Feed not found or update failed")
    
    # Get the updated feed
    updated_feed = feed_mgr.get_feed_by_id(feed_id)
    if not updated_feed:
        raise HTTPException(status_code=500, detail="Feed updated but could not be retrieved")
    
    return updated_feed


@app.delete("/api/feeds/{feed_id}", response_model=APIResponse)
async def delete_feed(feed_id: int, feed_mgr: FeedManager = Depends(get_feed_manager)):
    """Delete a feed (soft delete)"""
    success = feed_mgr.delete_feed(feed_id)
    if not success:
        raise HTTPException(status_code=404, detail="Feed not found")
    
    return APIResponse(message="Feed deleted successfully", success=True)


@app.post("/api/feeds/update-all", response_model=BulkOperationResponse)
async def update_all_feeds(
    background_tasks: BackgroundTasks,
    feed_mgr: FeedManager = Depends(get_feed_manager)
):
    """Update all active feeds"""
    results = feed_mgr.update_all_feeds()
    
    return BulkOperationResponse(
        message="Feed update completed",
        total_items=results.get("total", 0),
        processed_items=results.get("processed", 0),
        success_count=results.get("success", 0),
        error_count=results.get("errors", 0),
        errors=results.get("error_details", [])
    )


# Bulk operations
@app.post("/api/articles/bulk-scrape", response_model=BulkOperationResponse)
async def bulk_scrape_content(
    scraper: ContentScraper = Depends(get_content_scraper),
    repo: NewsRepository = Depends(get_repository)
):
    """Bulk scrape content for articles that need it"""
    articles_to_scrape = repo.get_articles_needing_content_scrape()
    
    total_items = len(articles_to_scrape)
    success_count = 0
    error_count = 0
    errors = []
    
    for article in articles_to_scrape:
        try:
            success = scraper.scrape_and_save_content(article.id, article.link)
            if success:
                success_count += 1
            else:
                error_count += 1
                errors.append(f"Failed to scrape article {article.id}: {article.title}")
        except Exception as e:
            error_count += 1
            errors.append(f"Error scraping article {article.id}: {str(e)}")
    
    return BulkOperationResponse(
        message=f"Bulk scraping completed: {success_count} successful, {error_count} failed",
        total_items=total_items,
        processed_items=total_items,
        success_count=success_count,
        error_count=error_count,
        errors=errors[:10]  # Limit errors to first 10
    )


@app.post("/api/articles/bulk-summarize", response_model=BulkOperationResponse)
async def bulk_generate_summaries(
    ai: AISummarizer = Depends(get_ai_summarizer),
    repo: NewsRepository = Depends(get_repository)
):
    """Bulk generate AI summaries for articles with content"""
    if not ai.is_available():
        raise HTTPException(status_code=400, detail="AI summarization not available")
    
    articles_to_summarize = repo.get_articles_needing_summary()
    
    total_items = len(articles_to_summarize)
    success_count = 0
    error_count = 0
    errors = []
    
    for article in articles_to_summarize:
        try:
            success = ai.summarize_article(article.id)
            if success:
                success_count += 1
            else:
                error_count += 1
                errors.append(f"Failed to summarize article {article.id}: {article.title}")
        except Exception as e:
            error_count += 1
            errors.append(f"Error summarizing article {article.id}: {str(e)}")
    
    return BulkOperationResponse(
        message=f"Bulk summarization completed: {success_count} successful, {error_count} failed",
        total_items=total_items,
        processed_items=total_items,
        success_count=success_count,
        error_count=error_count,
        errors=errors[:10]  # Limit errors to first 10
    )


# AI and configuration endpoints
@app.get("/api/ai/status", response_model=AIStatusResponse)
async def get_ai_status(ai: AISummarizer = Depends(get_ai_summarizer)):
    """Get AI summarization status and available models"""
    return AIStatusResponse(
        available=ai.is_available(),
        current_model=ai.get_current_model(),
        available_models=ai.get_available_models_for_user()
    )


@app.post("/api/ai/configure", response_model=APIResponse)
async def configure_ai(
    request: AIConfigRequest,
    ai: AISummarizer = Depends(get_ai_summarizer),
    config: ConfigManager = Depends(get_config)
):
    """Configure AI settings"""
    success = ai.update_api_key(request.api_key)
    if not success:
        raise HTTPException(status_code=400, detail="Invalid API key")
    
    if request.model:
        config.set_selected_model(request.model)
    
    return APIResponse(message="AI configuration updated successfully", success=True)


# La Une (Daily Summary) endpoints
@app.post("/api/la-une/generate", response_model=DailySummaryResponse)
async def generate_daily_summary(
    hours: int = 24,
    active_feeds_only: bool = True,
    ai: AISummarizer = Depends(get_ai_summarizer),
    feed_mgr: FeedManager = Depends(get_feed_manager),
    repo: NewsRepository = Depends(get_repository)
):
    """Generate comprehensive daily summary"""
    if not ai.is_available():
        raise HTTPException(status_code=400, detail="AI summarization not available")
    
    if active_feeds_only:
        recent_articles = feed_mgr.get_recent_articles_from_active_feeds(hours=hours)
    else:
        recent_articles = feed_mgr.get_recent_articles(hours=hours)
    
    if not recent_articles:
        # Save empty summary to database
        saved_summary = repo.daily_summaries.create_summary(
            summary="No articles available for the requested time period.",
            article_count=0,
            sources_count=0,
            time_range_hours=hours,
            active_feeds_only=active_feeds_only
        )
        return DailySummaryResponse(
            summary=saved_summary.summary,
            article_count=saved_summary.article_count,
            sources_count=saved_summary.sources_count,
            generated_at=saved_summary.generated_at
        )
    
    # Generate summary using AI
    try:
        # Get unique sources
        unique_sources = set()
        for article in recent_articles:
            if hasattr(article, 'feed_title') and article.feed_title:
                unique_sources.add(article.feed_title)
            elif hasattr(article, 'feed_url') and article.feed_url:
                unique_sources.add(article.feed_url)
        
        # Prepare articles for summarization
        articles_text = []
        for article in recent_articles[:50]:  # Limit to avoid token limits
            article_summary = f"Title: {article.title}\n"
            if article.description:
                article_summary += f"Description: {article.description}\n"
            if article.summary:
                article_summary += f"Summary: {article.summary}\n"
            articles_text.append(article_summary)
        
        # Generate comprehensive summary
        combined_text = "\n\n".join(articles_text)
        summary_prompt = f"""Please create a comprehensive daily news summary based on the following {len(recent_articles)} articles from the last {hours} hours:

{combined_text}

Please provide:
1. A brief overview of the main themes and topics
2. Key developments and breaking news
3. Important trends or patterns
4. A conclusion with the most significant stories

Format the response as a well-structured summary suitable for a daily briefing."""

        summary = ai.generate_summary_from_text(summary_prompt)
        
        # Save summary to database
        saved_summary = repo.daily_summaries.create_summary(
            summary=summary,
            article_count=len(recent_articles),
            sources_count=len(unique_sources),
            time_range_hours=hours,
            active_feeds_only=active_feeds_only
        )
        
        return DailySummaryResponse(
            summary=saved_summary.summary,
            article_count=saved_summary.article_count,
            sources_count=saved_summary.sources_count,
            generated_at=saved_summary.generated_at
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to generate summary: {str(e)}")


@app.get("/api/la-une/latest", response_model=Optional[DailySummaryResponse])
async def get_latest_daily_summary(repo: NewsRepository = Depends(get_repository)):
    """Get the latest generated daily summary"""
    try:
        latest_summary = repo.daily_summaries.get_latest()
        if latest_summary:
            return DailySummaryResponse(
                summary=latest_summary.summary,
                article_count=latest_summary.article_count,
                sources_count=latest_summary.sources_count,
                generated_at=latest_summary.generated_at
            )
        return None
    except Exception as e:
        logger.error(f"Error retrieving latest daily summary: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to retrieve latest summary: {str(e)}")


@app.get("/api/config", response_model=ConfigurationResponse)
async def get_configuration(config: ConfigManager = Depends(get_config)):
    """Get current configuration"""
    return ConfigurationResponse(
        ai_configured=config.has_openai_api_key(),
        selected_model=config.get_selected_model(),
        bulk_summarize_limit=config.get_bulk_summarize_limit(),
        default_feeds=config.get_default_feeds()
    )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
