"""
Test feed management functionality.
"""

import pytest
from unittest.mock import Mock, patch
from src.core.models import Feed, Article, FeedStatus
from src.services.feed_manager import FeedManager


class TestFeedManager:
    """Test the FeedManager class"""

    @pytest.fixture
    def mock_config(self):
        """Mock configuration for testing"""
        config = Mock()
        config.get_default_feeds.return_value = [
            "https://feeds.bbci.co.uk/news/rss.xml",
            "https://rss.cnn.com/rss/edition.rss",
        ]
        return config

    @pytest.fixture
    def feed_manager(self, mock_config, test_repository):
        """Create FeedManager instance for testing"""
        return FeedManager(mock_config, test_repository)

    def test_initialization(self, feed_manager, mock_config, test_repository):
        """Test FeedManager initialization"""
        assert feed_manager.config == mock_config
        assert feed_manager.repository == test_repository

    @patch("src.services.feed_manager.feedparser.parse")
    def test_validate_feed_url_success(self, mock_parse, feed_manager):
        """Test successful feed URL validation"""
        # Mock successful feed parsing
        mock_feed = Mock()
        mock_feed.bozo = False
        mock_feed.feed.title = "Test Feed"
        mock_feed.feed.description = "Test Description"
        mock_feed.entries = [Mock()]  # Has entries
        mock_parse.return_value = mock_feed

        result = feed_manager.validate_feed_url("https://example.com/feed.xml")

        assert result["valid"] is True
        assert result["title"] == "Test Feed"
        assert result["description"] == "Test Description"

    @patch("src.services.feed_manager.feedparser.parse")
    def test_validate_feed_url_failure(self, mock_parse, feed_manager):
        """Test failed feed URL validation"""
        # Mock failed feed parsing
        mock_feed = Mock()
        mock_feed.bozo = True
        mock_feed.bozo_exception = Exception("Parse error")
        mock_parse.return_value = mock_feed

        result = feed_manager.validate_feed_url("https://invalid.com/feed.xml")

        assert result["valid"] is False
        assert "error" in result

    def test_add_feed_success(self, feed_manager, test_repository):
        """Test successful feed addition"""
        # Mock successful validation
        with patch.object(feed_manager, "validate_feed_url") as mock_validate:
            mock_validate.return_value = {
                "valid": True,
                "title": "Test Feed",
                "description": "Test Description",
            }

            success = feed_manager.add_feed("https://example.com/feed.xml")

        assert success

        # Verify feed was added to repository
        feeds = test_repository.get_all_feeds()
        assert len(feeds) == 1
        assert feeds[0].url == "https://example.com/feed.xml"
        assert feeds[0].title == "Test Feed"

    def test_add_feed_failure(self, feed_manager):
        """Test failed feed addition"""
        # Mock failed validation
        with patch.object(feed_manager, "validate_feed_url") as mock_validate:
            mock_validate.return_value = {"valid": False, "error": "Invalid feed"}

            success = feed_manager.add_feed("https://invalid.com/feed.xml")

        assert not success

    @patch("src.services.feed_manager.feedparser.parse")
    def test_fetch_feed_articles(self, mock_parse, feed_manager):
        """Test fetching articles from a feed"""
        # Mock feed with articles
        mock_entry1 = Mock()
        mock_entry1.title = "Article 1"
        mock_entry1.link = "https://example.com/article1"
        mock_entry1.description = "Description 1"
        mock_entry1.published = "2025-06-26T00:00:00Z"

        mock_entry2 = Mock()
        mock_entry2.title = "Article 2"
        mock_entry2.link = "https://example.com/article2"
        mock_entry2.summary = "Summary 2"  # Using summary instead of description
        mock_entry2.updated = (
            "2025-06-26T01:00:00Z"  # Using updated instead of published
        )

        mock_feed = Mock()
        mock_feed.entries = [mock_entry1, mock_entry2]
        mock_parse.return_value = mock_feed

        articles = feed_manager.fetch_feed_articles("https://example.com/feed.xml")

        assert len(articles) == 2
        assert articles[0].title == "Article 1"
        assert articles[0].link == "https://example.com/article1"
        assert articles[1].title == "Article 2"
        assert articles[1].description == "Summary 2"

    def test_update_all_feeds(self, feed_manager, test_repository, sample_feed_data):
        """Test updating all feeds"""
        # Add a test feed
        feed = Feed(**sample_feed_data)
        test_repository.create_feed(feed)

        # Mock feed fetching to return some articles
        mock_articles = [
            Article(
                title="Test Article 1",
                link="https://example.com/article1",
                description="Description 1",
                feed_url=sample_feed_data["url"],
            ),
            Article(
                title="Test Article 2",
                link="https://example.com/article2",
                description="Description 2",
                feed_url=sample_feed_data["url"],
            ),
        ]

        with patch.object(
            feed_manager, "fetch_feed_articles", return_value=mock_articles
        ):
            results = feed_manager.update_all_feeds()

        assert results["total_feeds"] == 1
        assert results["new_articles"] == 2
        assert results["errors"] == 0

    def test_get_feed_list(self, feed_manager, test_repository, sample_feed_data):
        """Test getting feed list (legacy compatibility)"""
        # Add a test feed
        feed = Feed(**sample_feed_data)
        test_repository.create_feed(feed)

        feed_list = feed_manager.get_feed_list()

        assert len(feed_list) == 1
        assert feed_list[0]["url"] == sample_feed_data["url"]
        assert feed_list[0]["title"] == sample_feed_data["title"]
        assert feed_list[0]["active"] is True

    def test_get_all_feeds(self, feed_manager, test_repository, sample_feed_data):
        """Test getting all feeds"""
        # Add test feeds with different statuses
        active_feed = Feed(**sample_feed_data)
        active_feed.status = FeedStatus.ACTIVE
        test_repository.create_feed(active_feed)

        inactive_feed_data = sample_feed_data.copy()
        inactive_feed_data["url"] = "https://example.com/inactive.xml"
        inactive_feed_data["title"] = "Inactive Feed"
        inactive_feed = Feed(**inactive_feed_data)
        inactive_feed.status = FeedStatus.INACTIVE
        test_repository.create_feed(inactive_feed)

        # Test including inactive feeds
        all_feeds = feed_manager.get_all_feeds(include_inactive=True)
        assert len(all_feeds) == 2

        # Test excluding inactive feeds
        active_feeds = feed_manager.get_all_feeds(include_inactive=False)
        assert len(active_feeds) == 1
        assert active_feeds[0].status == FeedStatus.ACTIVE
