"""
Feed management service for the News Aggregator application.

This module handles all feed-related operations including CRUD operations,
feed validation, and bulk operations.
"""

import feedparser  # type: ignore
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta

from ..core.models import Article, Feed, FeedStatus
from ..core.repository import NewsRepository
from ..core.config import ConfigManager

logger = logging.getLogger(__name__)


class FeedManager:
    """Service class for managing RSS feeds"""

    def __init__(self, config: ConfigManager, repository: NewsRepository):
        """
        Initialize the FeedManager

        Args:
            config: Configuration manager instance
            repository: Repository instance for data access
        """
        self.config = config
        self.repository = repository
        self.logger = logger

    def add_feed(self, url: str, title: str = "", description: str = "") -> bool:
        """
        Add a new RSS feed to the database

        Args:
            url: RSS feed URL
            title: Feed title (optional, will be auto-detected if not provided)
            description: Feed description (optional, will be auto-detected if not provided)

        Returns:
            bool: True if feed was added successfully, False otherwise
        """
        try:
            # Validate feed first
            validation = self.validate_feed_url(url)
            if not validation["valid"]:
                self.logger.warning(
                    f"Invalid feed URL: {url} - {validation.get('error', 'Unknown error')}"
                )
                return False

            # Use auto-detected metadata if not provided
            if not title:
                title = validation.get("title", "Unknown Feed")
            if not description:
                description = validation.get("description", "")

            # Create feed object
            feed = Feed(
                url=url, title=title, description=description, status=FeedStatus.ACTIVE
            )

            # Add to repository
            feed_id = self.repository.create_feed(feed)
            return feed_id is not None

        except Exception as e:
            self.logger.error(f"Error adding feed {url}: {e}")
            return False

    def fetch_feed_articles(self, feed_url: str) -> List[Article]:
        """
        Fetch articles from a single RSS feed

        Args:
            feed_url: RSS feed URL

        Returns:
            List[Article]: List of article objects
        """
        articles = []
        try:
            feed = feedparser.parse(feed_url)

            for entry in feed.entries:
                # Extract article data
                title = entry.get("title", "No Title")
                link = entry.get("link", "")
                description = entry.get("description", entry.get("summary", ""))

                # Handle published date
                published = ""
                if hasattr(entry, "published"):
                    published = entry.published
                elif hasattr(entry, "updated"):
                    published = entry.updated

                article = Article(
                    title=title,
                    link=link,
                    description=description,
                    published=published,
                    feed_url=feed_url,
                )
                articles.append(article)

        except Exception as e:
            self.logger.error(f"Error fetching feed {feed_url}: {e}")

        return articles

    def update_all_feeds(self) -> Dict[str, int]:
        """
        Update all active feeds and return summary

        Returns:
            Dict[str, int]: Summary of update results
        """
        feeds = self.repository.get_all_feeds(include_inactive=False)
        results = {"total_feeds": len(feeds), "new_articles": 0, "errors": 0}

        for feed in feeds:
            try:
                articles = self.fetch_feed_articles(feed.url)

                for article in articles:
                    article_id = self.repository.create_article(article)
                    if article_id:
                        results["new_articles"] += 1

                # Update feed's last updated timestamp
                if feed.id is not None:
                    self.repository.update_feed_last_updated(feed.id)

            except Exception as e:
                self.logger.error(f"Error updating feed {feed.url}: {e}")
                results["errors"] += 1

        return results

    def get_feed_list(self) -> List[Dict[str, Any]]:
        """
        Get list of all feeds (legacy compatibility method)

        Returns:
            List[Dict[str, Any]]: List of feed dictionaries
        """
        feeds = self.repository.get_all_feeds()
        return [
            {
                "id": feed.id,
                "url": feed.url,
                "title": feed.title,
                "description": feed.description,
                "last_updated": feed.last_updated,
                "active": feed.status == FeedStatus.ACTIVE,
                "created_at": feed.created_at,
            }
            for feed in feeds
        ]

    # CRUD Operations for Feeds

    def get_feed_by_id(self, feed_id: int) -> Optional[Feed]:
        """
        Get a specific feed by ID

        Args:
            feed_id: Feed ID

        Returns:
            Optional[Feed]: Feed object if found, None otherwise
        """
        return self.repository.get_feed_by_id(feed_id)

    def get_all_feeds(self, include_inactive: bool = False) -> List[Feed]:
        """
        Get all feeds as Feed objects

        Args:
            include_inactive: Whether to include inactive feeds

        Returns:
            List[Feed]: List of feed objects
        """
        return self.repository.get_all_feeds(include_inactive)

    def update_feed(
        self,
        feed_id: int,
        title: Optional[str] = None,
        description: Optional[str] = None,
        status: Optional[FeedStatus] = None,
    ) -> bool:
        """
        Update feed information

        Args:
            feed_id: Feed ID
            title: New title (optional)
            description: New description (optional)
            status: New status (optional)

        Returns:
            bool: True if update was successful, False otherwise
        """
        try:
            feed = self.repository.get_feed_by_id(feed_id)
            if not feed:
                return False

            # Update fields if provided
            if title is not None:
                feed.title = title
            if description is not None:
                feed.description = description
            if status is not None:
                feed.status = status

            return self.repository.update_feed(feed)

        except Exception as e:
            self.logger.error(f"Error updating feed {feed_id}: {e}")
            return False

    def delete_feed(self, feed_id: int) -> bool:
        """
        Soft delete a feed (mark as inactive)

        Args:
            feed_id: Feed ID

        Returns:
            bool: True if deletion was successful, False otherwise
        """
        return self.update_feed(feed_id, status=FeedStatus.INACTIVE)

    def restore_feed(self, feed_id: int) -> bool:
        """
        Restore a soft-deleted feed

        Args:
            feed_id: Feed ID

        Returns:
            bool: True if restoration was successful, False otherwise
        """
        return self.update_feed(feed_id, status=FeedStatus.ACTIVE)

    def permanently_delete_feed(self, feed_id: int) -> bool:
        """
        Permanently delete a feed and all its articles

        Args:
            feed_id: Feed ID

        Returns:
            bool: True if deletion was successful, False otherwise
        """
        try:
            return self.repository.permanently_delete_feed(feed_id)
        except Exception as e:
            self.logger.error(f"Error permanently deleting feed {feed_id}: {e}")
            return False

    def get_feed_statistics(self, feed_id: int) -> Dict[str, Any]:
        """
        Get detailed statistics for a feed

        Args:
            feed_id: Feed ID

        Returns:
            Dict[str, Any]: Feed statistics
        """
        try:
            stats = self.repository.get_feed_statistics(feed_id)
            if stats:
                return {
                    "feed_id": stats.feed_id,
                    "feed_title": stats.feed_title,
                    "total_articles": stats.total_articles,
                    "articles_with_content": stats.articles_with_content,
                    "articles_with_summary": stats.articles_with_summary,
                    "latest_article_date": stats.latest_article_date.isoformat()
                    if stats.latest_article_date
                    else None,
                    "last_updated": stats.last_updated.isoformat()
                    if stats.last_updated
                    else None,
                    "error_count": stats.error_count,
                }
            return {}
        except Exception as e:
            self.logger.error(f"Error getting feed statistics for {feed_id}: {e}")
            return {}

    def validate_feed_url(self, url: str) -> Dict[str, Any]:
        """
        Validate a feed URL and return metadata

        Args:
            url: Feed URL to validate

        Returns:
            Dict[str, Any]: Validation result with metadata
        """
        try:
            # Parse feed (feedparser handles timeouts internally)
            feed = feedparser.parse(url)

            if not feed.entries:
                return {"valid": False, "error": "No entries found in feed", "url": url}

            return {
                "valid": True,
                "url": url,
                "title": feed.feed.get("title", "Unknown Feed"),
                "description": feed.feed.get("description", ""),
                "entry_count": len(feed.entries),
                "latest_entry": feed.entries[0].get("title", "No title")
                if feed.entries
                else None,
            }

        except Exception as e:
            return {"valid": False, "error": str(e), "url": url}

    def bulk_update_feeds(self, feed_ids: List[int]) -> Dict[str, int]:
        """
        Update multiple feeds at once

        Args:
            feed_ids: List of feed IDs to update

        Returns:
            Dict[str, int]: Summary of bulk update results
        """
        results = {"updated": 0, "errors": 0, "new_articles": 0}

        for feed_id in feed_ids:
            try:
                feed = self.get_feed_by_id(feed_id)
                if feed and feed.status == FeedStatus.ACTIVE:
                    articles = self.fetch_feed_articles(feed.url)
                    new_count = 0

                    for article in articles:
                        if self.repository.create_article(article):
                            new_count += 1

                    # Update last_updated timestamp
                    self.repository.update_feed_last_updated(feed_id)

                    results["updated"] += 1
                    results["new_articles"] += new_count

            except Exception as e:
                self.logger.error(f"Error updating feed {feed_id}: {e}")
                results["errors"] += 1

        return results

    def get_recent_articles(self, hours: int = 24) -> List[Article]:
        """
        Get recent articles from database within the last N hours

        Args:
            hours: Number of hours to look back (default: 24)

        Returns:
            List[Article]: List of recent article objects
        """
        try:
            cutoff_time = datetime.now() - timedelta(hours=hours)
            return self.repository.get_articles_since(cutoff_time)
        except Exception as e:
            self.logger.error(f"Error fetching recent articles: {e}")
            return []
