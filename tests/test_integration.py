"""
Integration tests for the complete architecture.
"""

from src.core.config import ConfigManager
from src.core.repository import NewsRepository
from src.services.feed_manager import FeedManager
from src.services.content_scraper import ContentScraper
from src.services.ai_summarizer import AISummarizer
from src.core.models import Feed, Article, FeedStatus, ArticleStatus


class TestArchitectureIntegration:
    """Test the complete architecture integration"""

    def test_complete_workflow(self, test_config):
        """Test the complete workflow from feed to summary"""
        # Initialize all components
        repository = NewsRepository()
        content_scraper = ContentScraper(test_config, repository)
        ai_summarizer = AISummarizer(test_config, repository)

        # 1. Add a feed
        test_feed = Feed(
            url="https://example.com/test-feed.xml",
            title="Test Feed",
            description="A test feed for integration testing",
            status=FeedStatus.ACTIVE,
        )
        feed_id = repository.create_feed(test_feed)
        assert feed_id is not None

        # 2. Create some test articles
        test_articles = [
            Article(
                title="Test Article 1",
                link="https://example.com/article1",
                description="Description for article 1",
                feed_url=test_feed.url,
                status=ArticleStatus.PENDING,
            ),
            Article(
                title="Test Article 2",
                link="https://example.com/article2",
                description="Description for article 2",
                feed_url=test_feed.url,
                status=ArticleStatus.PENDING,
            ),
        ]

        article_ids = []
        for article in test_articles:
            saved_article = repository.articles.save(article)
            article_ids.append(saved_article.id)

        # 3. Verify we can get articles without content
        articles_without_content = repository.articles.get_without_content()
        assert len(articles_without_content) >= 2

        # 4. Test content scraping (mock the actual scraping)
        from unittest.mock import patch

        with patch.object(content_scraper, "scrape_article_content") as mock_scrape:
            mock_scrape.return_value = "This is scraped content for testing purposes."

            scraped_count = content_scraper.bulk_scrape(limit=2)
            assert scraped_count == 2

        # 5. Verify articles now have content
        for article_id in article_ids:
            article = repository.articles.get_by_id(article_id)
            assert article.content is not None
            assert len(article.content) > 0
            assert article.status == ArticleStatus.SCRAPED

        # 6. Test AI summarization (mock the API call)
        with patch.object(ai_summarizer, "generate_summary") as mock_summarize:
            mock_summarize.return_value = "This is an AI-generated summary."

            summarized_count = ai_summarizer.bulk_summarize(limit=2)
            # Only test if AI is available (has client)
            if ai_summarizer.is_available():
                assert summarized_count == 2

                # 7. Verify articles now have summaries
                for article_id in article_ids:
                    article = repository.articles.get_by_id(article_id)
                    assert article.summary == "This is an AI-generated summary."
                    assert article.status == ArticleStatus.SUMMARIZED

    def test_feed_management_workflow(self, test_config):
        """Test feed management workflow"""
        repository = NewsRepository()
        feed_manager = FeedManager(test_config, repository)

        # Test feed validation (mock external call)
        from unittest.mock import patch

        with patch("src.services.feed_manager.feedparser.parse") as mock_parse:
            mock_feed = type(
                "MockFeed",
                (),
                {
                    "bozo": False,
                    "feed": type(
                        "MockFeedInfo",
                        (),
                        {"title": "Test Feed", "description": "Test Description"},
                    )(),
                    "entries": [type("MockEntry", (), {})()],  # Has entries
                },
            )()
            mock_parse.return_value = mock_feed

            # Test feed validation
            validation = feed_manager.validate_feed_url("https://example.com/feed.xml")
            assert validation["valid"] is True
            assert validation["title"] == "Test Feed"

            # Test adding feed
            success = feed_manager.add_feed("https://example.com/feed.xml")
            assert success

        # Verify feed was added
        feeds = feed_manager.get_all_feeds()
        assert len(feeds) == 1
        assert feeds[0].url == "https://example.com/feed.xml"

    def test_repository_statistics(self, test_config):
        """Test repository statistics functionality"""
        repository = NewsRepository()

        # Add some test data
        feed = Feed(
            url="https://example.com/stats-feed.xml",
            title="Stats Test Feed",
            status=FeedStatus.ACTIVE,
        )
        repository.create_feed(feed)

        # Add articles with different statuses
        articles = [
            Article(title="Article 1", feed_url=feed.url, status=ArticleStatus.PENDING),
            Article(
                title="Article 2",
                feed_url=feed.url,
                content="Content",
                status=ArticleStatus.SCRAPED,
            ),
            Article(
                title="Article 3",
                feed_url=feed.url,
                content="Content",
                summary="Summary",
                status=ArticleStatus.SUMMARIZED,
            ),
        ]

        for article in articles:
            repository.articles.save(article)

        # Test global statistics
        stats = repository.get_global_statistics()

        assert stats["total_articles"] >= 3
        assert stats["total_feeds"] >= 1
        assert stats["active_feeds"] >= 1
        assert stats["articles_with_content"] >= 2
        assert stats["articles_with_summary"] >= 1

    def test_error_handling(self, test_config):
        """Test error handling throughout the architecture"""
        repository = NewsRepository()
        content_scraper = ContentScraper(test_config, repository)

        # Test handling of invalid article ID
        success = content_scraper.scrape_and_save_content(99999, "https://example.com")
        assert not success

        # Test handling of invalid URL
        from unittest.mock import patch

        with patch.object(content_scraper, "scrape_article_content", return_value=None):
            success = content_scraper.scrape_and_save_content(1, "invalid-url")
            assert not success

    def test_configuration_integration(self):
        """Test configuration integration with all components"""
        config = ConfigManager()

        # Test that all components can use the config
        repository = NewsRepository()
        feed_manager = FeedManager(config, repository)
        content_scraper = ContentScraper(config, repository)
        ai_summarizer = AISummarizer(config, repository)

        # Verify components have access to config
        assert feed_manager.config == config
        assert content_scraper.config == config
        assert ai_summarizer.config == config

        # Test config provides expected values
        assert config.feeds.request_timeout > 0
        assert config.ui.max_content_length > 0
        assert len(config.get_default_feeds()) > 0
