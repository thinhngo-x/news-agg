"""
Test content scraping functionality.
"""

import pytest
from unittest.mock import Mock, patch
import requests
from src.core.models import Article, ArticleStatus
from src.services.content_scraper import ContentScraper


class TestContentScraper:
    """Test the ContentScraper class"""

    @pytest.fixture
    def mock_config(self):
        """Mock configuration for testing"""
        config = Mock()
        config.feeds.request_timeout = 30
        config.ui.max_content_length = 10000
        return config

    @pytest.fixture
    def content_scraper(self, mock_config, test_repository):
        """Create ContentScraper instance for testing"""
        return ContentScraper(mock_config, test_repository)

    def test_initialization(self, content_scraper, mock_config, test_repository):
        """Test ContentScraper initialization"""
        assert content_scraper.config == mock_config
        assert content_scraper.repository == test_repository
        assert content_scraper.session is not None

    @patch("src.services.content_scraper.requests.Session.get")
    def test_scrape_article_content_success(self, mock_get, content_scraper):
        """Test successful content scraping"""
        # Mock successful HTTP response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.headers = {"content-type": "text/html; charset=utf-8"}
        mock_response.content = b"""
        <html>
            <body>
                <article>
                    <h1>Test Article</h1>
                    <p>This is the first paragraph of content.</p>
                    <p>This is the second paragraph with more content.</p>
                </article>
            </body>
        </html>
        """
        mock_response.raise_for_status.return_value = None
        mock_get.return_value = mock_response

        # Test scraping
        url = "https://example.com/article"
        content = content_scraper.scrape_article_content(url)

        assert content is not None
        assert "Test Article" in content
        assert "first paragraph" in content
        assert "second paragraph" in content
        assert len(content) > 50  # Should have substantial content

    @patch("src.services.content_scraper.requests.Session.get")
    def test_scrape_article_content_no_content(self, mock_get, content_scraper):
        """Test scraping with minimal content"""
        # Mock response with very little content
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.headers = {"content-type": "text/html; charset=utf-8"}
        mock_response.content = b"<html><body><p>Short</p></body></html>"
        mock_response.raise_for_status.return_value = None
        mock_get.return_value = mock_response

        # Test scraping
        url = "https://example.com/article"
        content = content_scraper.scrape_article_content(url)

        # Should return None for content that's too short
        assert content is None

    @patch("src.services.content_scraper.requests.Session.get")
    def test_scrape_article_content_timeout(self, mock_get, content_scraper):
        """Test scraping with timeout error"""
        mock_get.side_effect = requests.exceptions.Timeout()

        url = "https://example.com/article"
        content = content_scraper.scrape_article_content(url)

        assert content is None

    @patch("src.services.content_scraper.requests.Session.get")
    def test_scrape_article_content_http_error(self, mock_get, content_scraper):
        """Test scraping with HTTP error"""
        mock_response = Mock()
        mock_response.status_code = 404
        mock_response.raise_for_status.side_effect = requests.exceptions.HTTPError()
        mock_get.return_value = mock_response

        url = "https://example.com/article"
        content = content_scraper.scrape_article_content(url)

        assert content is None

    def test_scrape_and_save_content(
        self, content_scraper, test_repository, sample_article_data
    ):
        """Test scraping and saving content to database"""
        # Create and save an article
        article = Article(**sample_article_data)
        saved_article = test_repository.articles.save(article)

        # Mock successful scraping
        test_content = "This is scraped content for testing"
        with patch.object(
            content_scraper, "scrape_article_content", return_value=test_content
        ):
            success = content_scraper.scrape_and_save_content(
                saved_article.id, article.link
            )

        assert success

        # Verify content was saved
        updated_article = test_repository.articles.get_by_id(saved_article.id)
        assert updated_article.content == test_content
        assert updated_article.status == ArticleStatus.SCRAPED

    def test_scrape_and_save_content_failure(
        self, content_scraper, test_repository, sample_article_data
    ):
        """Test scraping failure"""
        # Create and save an article
        article = Article(**sample_article_data)
        saved_article = test_repository.articles.save(article)

        # Mock failed scraping
        with patch.object(content_scraper, "scrape_article_content", return_value=None):
            success = content_scraper.scrape_and_save_content(
                saved_article.id, article.link
            )

        assert not success

    def test_scrape_article_object(self, content_scraper):
        """Test scraping with Article object"""
        # Create article object
        article = Article(
            title="Test Article",
            link="https://example.com/article",
            description="Test description",
        )

        # Mock successful scraping
        test_content = "Scraped content"
        with patch.object(
            content_scraper, "scrape_article_content", return_value=test_content
        ):
            success = content_scraper.scrape_article(article)

        assert success
        assert article.content == test_content
        assert article.status == ArticleStatus.SCRAPED

    def test_scrape_article_object_no_link(self, content_scraper):
        """Test scraping article with no link"""
        article = Article(title="Test Article", description="Test description")
        # No link provided

        success = content_scraper.scrape_article(article)

        assert not success

    def test_bulk_scrape(self, content_scraper, test_repository, sample_article_data):
        """Test bulk scraping functionality"""
        # Create multiple articles without content
        articles = []
        for i in range(3):
            article_data = sample_article_data.copy()
            article_data["title"] = f"Article {i + 1}"
            article_data["link"] = f"https://example.com/article{i + 1}"
            article = Article(**article_data)
            saved_article = test_repository.articles.save(article)
            articles.append(saved_article)

        # Mock successful scraping for all articles
        test_content = "Bulk scraped content"
        with patch.object(
            content_scraper, "scrape_article_content", return_value=test_content
        ):
            count = content_scraper.bulk_scrape(limit=5)

        assert count == 3  # Should have scraped all 3 articles

        # Verify all articles have content
        for article in articles:
            updated_article = test_repository.articles.get_by_id(article.id)
            assert updated_article.content == test_content
            assert updated_article.status == ArticleStatus.SCRAPED

    def test_bulk_scrape_no_articles(self, content_scraper, test_repository):
        """Test bulk scraping with no articles needing content"""
        count = content_scraper.bulk_scrape()
        assert count == 0
