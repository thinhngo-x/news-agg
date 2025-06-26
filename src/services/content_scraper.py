"""
Content scraping service for the News Aggregator application.

This module handles web scraping of article content from URLs.
"""

import requests
import logging
from bs4 import BeautifulSoup
from typing import Optional

from ..core.models import Article, ArticleStatus
from ..core.repository import NewsRepository
from ..core.config import ConfigManager

logger = logging.getLogger(__name__)


class ContentScraper:
    """
    Service class for scraping web content from article URLs

    Note: This is a simplified version using requests and BeautifulSoup.
    For production, consider using more sophisticated scraping tools.
    """

    def __init__(self, config: ConfigManager, repository: NewsRepository):
        """
        Initialize the ContentScraper

        Args:
            repository: Repository instance for data access
            config: Configuration manager instance
        """
        self.repository = repository
        self.config = config
        self.logger = logger

        # Setup requests session with headers
        self.session = requests.Session()
        self.session.headers.update(
            {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
            }
        )

    def scrape_article_content(self, url: str) -> Optional[str]:
        """
        Scrape full article content from URL

        Args:
            url: Article URL to scrape

        Returns:
            Optional[str]: Scraped content if successful, None otherwise
        """
        try:
            # Use timeout from config
            timeout = self.config.feeds.request_timeout

            # Add more headers to avoid blocking
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
                "Accept-Language": "en-US,en;q=0.5",
                "Accept-Encoding": "gzip, deflate",
                "Connection": "keep-alive",
            }

            response = self.session.get(
                url, timeout=timeout, headers=headers, allow_redirects=True
            )
            response.raise_for_status()

            # Check if we got a valid HTML response
            content_type = response.headers.get("content-type", "").lower()
            if "text/html" not in content_type:
                self.logger.warning(f"Non-HTML content type for {url}: {content_type}")
                return None

            soup = BeautifulSoup(response.content, "html.parser")

            # Remove unwanted elements
            for element in soup(
                [
                    "script",
                    "style",
                    "nav",
                    "header",
                    "footer",
                    "aside",
                    ".advertisement",
                    ".ads",
                    ".social-share",
                ]
            ):
                element.decompose()

            # Try to find article content using comprehensive selectors
            content_selectors = [
                # Specific article selectors
                "article",
                '[role="main"] article',
                ".article-body",
                ".article-content",
                ".post-content",
                ".entry-content",
                ".content-body",
                ".story-body",
                ".article-text",
                # More general content selectors
                "main",
                '[role="main"]',
                ".main-content",
                "#main-content",
                ".content",
                ".post",
                ".entry",
                # Fallback selectors
                "#content",
                ".container .content",
                ".wrapper .content",
            ]

            content = None
            for selector in content_selectors:
                try:
                    elements = soup.select(selector)
                    if elements:
                        # Get the largest element (most likely to contain main content)
                        largest_element = max(elements, key=lambda x: len(x.get_text()))
                        content = largest_element.get_text(separator=" ", strip=True)
                        if len(content) > 100:  # Ensure we got substantial content
                            break
                except Exception as e:
                    self.logger.debug(f"Error with selector {selector}: {e}")
                    continue

            # Fallback: get all paragraph text
            if not content or len(content) < 100:
                paragraphs = soup.find_all("p")
                if paragraphs:
                    content = " ".join(
                        [
                            p.get_text(separator=" ", strip=True)
                            for p in paragraphs
                            if len(p.get_text(strip=True)) > 20
                        ]
                    )

            # Final fallback: get body text
            if not content or len(content) < 50:
                body = soup.find("body")
                if body:
                    content = body.get_text(separator=" ", strip=True)

            # Clean up the content
            if content:
                # Remove extra whitespace and normalize
                content = " ".join(content.split())

                # Remove common footer/header noise
                noise_patterns = [
                    "Subscribe to our newsletter",
                    "Follow us on",
                    "Share this article",
                    "Related articles",
                    "You may also like",
                    "Advertisement",
                    "Cookie policy",
                ]

                for pattern in noise_patterns:
                    content = content.replace(pattern, "")

                # Truncate if too long
                max_content_length = getattr(
                    self.config.ui, "max_content_length", 10000
                )
                if len(content) > max_content_length:
                    content = content[:max_content_length] + "..."

                # Return None if content is too short (likely not actual article content)
                if len(content) < 50:
                    self.logger.warning(
                        f"Content too short for {url}: {len(content)} characters"
                    )
                    return None

            return content

        except requests.exceptions.Timeout:
            self.logger.error(f"Timeout scraping {url}")
            return None
        except requests.exceptions.ConnectionError:
            self.logger.error(f"Connection error scraping {url}")
            return None
        except requests.exceptions.HTTPError as e:
            self.logger.error(f"HTTP error scraping {url}: {e.response.status_code}")
            return None
        except requests.RequestException as e:
            self.logger.error(f"Request error scraping {url}: {e}")
            return None
        except Exception as e:
            self.logger.error(f"Unexpected error scraping {url}: {e}")
            return None

    def scrape_and_save_content(self, article_id: int, url: str) -> bool:
        """
        Scrape content and save to database

        Args:
            article_id: Article ID to update
            url: URL to scrape content from

        Returns:
            bool: True if successful, False otherwise
        """
        try:
            content = self.scrape_article_content(url)
            if content:
                # Update article content directly in repository
                return self.repository.articles.update_content(article_id, content)
            return False

        except Exception as e:
            self.logger.error(
                f"Error scraping and saving content for article {article_id}: {e}"
            )
            return False

    def scrape_article(self, article: Article) -> bool:
        """
        Scrape content for an article object

        Args:
            article: Article object to scrape content for

        Returns:
            bool: True if successful, False otherwise
        """
        if not article.link:
            self.logger.warning(f"No link available for article {article.id}")
            return False

        content = self.scrape_article_content(article.link)
        if content:
            article.content = content
            article.status = ArticleStatus.SCRAPED
            return True
        else:
            article.status = ArticleStatus.ERROR
            return False

    def bulk_scrape(self, limit: Optional[int] = None) -> int:
        """
        Scrape content for multiple articles without content.

        Args:
            limit: Maximum number of articles to scrape. Defaults to 10.

        Returns:
            int: Number of articles successfully scraped.
        """
        try:
            # Use a reasonable default limit
            max_articles = limit or 10

            # Fetch articles missing content
            articles = self.repository.articles.get_without_content(max_articles)

            if not articles:
                self.logger.info("No articles need content scraping")
                return 0

            scraped_count = 0
            failed_count = 0

            self.logger.info(f"Starting to scrape content for {len(articles)} articles")

            for i, article in enumerate(articles, 1):
                if not article.link:
                    self.logger.warning(f"Article {article.id} has no link to scrape")
                    failed_count += 1
                    continue

                if not article.id:
                    self.logger.warning(f"Article has no ID: {article.title}")
                    failed_count += 1
                    continue

                self.logger.info(
                    f"Scraping article {i}/{len(articles)}: {article.title[:50]}..."
                )

                try:
                    if self.scrape_and_save_content(article.id, article.link):
                        scraped_count += 1
                        self.logger.info(f"Successfully scraped article {article.id}")
                    else:
                        failed_count += 1
                        self.logger.warning(
                            f"Failed to scrape article {article.id}: {article.link}"
                        )

                except Exception as e:
                    failed_count += 1
                    self.logger.error(f"Error scraping article {article.id}: {e}")

            self.logger.info(
                f"Bulk scraping completed: {scraped_count} successful, {failed_count} failed"
            )
            return scraped_count

        except Exception as e:
            self.logger.error(f"Error in bulk_scrape: {e}")
            return 0

    def test_scrape_url(self, url: str) -> Optional[str]:
        """
        Test scraping a single URL for debugging purposes

        Args:
            url: URL to test scraping

        Returns:
            Optional[str]: Scraped content if successful, None otherwise
        """
        self.logger.info(f"Testing scrape for URL: {url}")

        content = self.scrape_article_content(url)

        if content:
            self.logger.info(
                f"Successfully scraped {len(content)} characters from {url}"
            )
            # Show a preview of the content
            preview = content[:200] + "..." if len(content) > 200 else content
            self.logger.info(f"Content preview: {preview}")
        else:
            self.logger.warning(f"Failed to scrape content from {url}")

        return content
