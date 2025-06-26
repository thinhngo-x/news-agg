"""
Pytest configuration for the News Aggregator tests.
"""

import pytest
import tempfile
import os
from pathlib import Path
from sqlmodel import create_engine, Session
from src.core.config import ConfigManager
from src.core.repository import NewsRepository
from src.core.database import init_database


@pytest.fixture(scope="function")
def clean_env():
    """Clean environment fixture for config tests"""
    # Store original environment
    original_env = os.environ.copy()

    # Remove API key from environment for testing
    if "OPENAI_API_KEY" in os.environ:
        del os.environ["OPENAI_API_KEY"]

    yield

    # Restore original environment
    os.environ.clear()
    os.environ.update(original_env)


@pytest.fixture(scope="function")
def test_db_url():
    """Create a temporary database for testing"""
    temp_dir = tempfile.mkdtemp()
    db_path = Path(temp_dir) / "test_news_aggregator.db"
    return f"sqlite:///{db_path}"


@pytest.fixture(scope="function")
def test_config(test_db_url):
    """Create a test configuration"""
    config = ConfigManager()
    config.database.url = test_db_url
    return config


@pytest.fixture(scope="function")
def isolated_config(test_db_url, clean_env):
    """Create a test configuration with clean environment"""
    config = ConfigManager()
    config.database.url = test_db_url
    return config


@pytest.fixture(scope="function")
def test_repository(test_db_url):
    """Create a fresh test repository for each test"""
    # Initialize test database
    init_database(test_db_url)

    # Create repository with session pointing to test database
    repository = NewsRepository()

    # Override the session to use our test database
    engine = create_engine(test_db_url)

    # Patch the get_session method to use our test engine
    def test_get_session():
        # Create a new session each time, just like the original implementation
        return Session(engine)

    repository.articles.get_session = test_get_session
    repository.feeds.get_session = test_get_session
    repository.statistics.get_session = test_get_session

    yield repository

    # Cleanup
    engine.dispose()


@pytest.fixture(scope="function")
def sample_feed_data():
    """Sample feed data for testing"""
    return {
        "url": "https://feeds.bbci.co.uk/news/rss.xml",
        "title": "BBC News - Home",
        "description": "BBC News",
    }


@pytest.fixture(scope="function")
def sample_article_data():
    """Sample article data for testing"""
    return {
        "title": "Test Article",
        "link": "https://example.com/article1",
        "published": "2025-06-26T00:00:00Z",
        "feed_url": "https://feeds.bbci.co.uk/news/rss.xml",
    }
