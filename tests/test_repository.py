"""
Test repository functionality.
"""

from src.core.models import Article, Feed, ArticleStatus, FeedStatus


class TestArticleRepository:
    """Test the ArticleRepository class"""

    def test_save_and_get_article(self, test_repository, sample_article_data):
        """Test saving and retrieving an article"""
        # Create article
        article = Article(**sample_article_data)

        # Save article
        saved_article = test_repository.articles.save(article)
        assert saved_article.id is not None
        assert saved_article.title == sample_article_data["title"]

        # Retrieve article
        retrieved_article = test_repository.articles.get_by_id(saved_article.id)
        assert retrieved_article is not None
        assert retrieved_article.title == sample_article_data["title"]
        assert retrieved_article.link == sample_article_data["link"]

    def test_get_by_link(self, test_repository, sample_article_data):
        """Test retrieving article by link"""
        # Create and save article
        article = Article(**sample_article_data)
        saved_article = test_repository.articles.save(article)

        # Retrieve by link
        retrieved_article = test_repository.articles.get_by_link(
            sample_article_data["link"]
        )
        assert retrieved_article is not None
        assert retrieved_article.id == saved_article.id

    def test_get_without_content(self, test_repository, sample_article_data):
        """Test retrieving articles without content"""
        # Create articles - one with content, one without
        article1 = Article(**sample_article_data)
        article1.content = "This article has content"

        article2_data = sample_article_data.copy()
        article2_data["title"] = "Article without content"
        article2_data["link"] = "https://example.com/article2"
        article2 = Article(**article2_data)
        # article2.content remains None

        # Save both articles
        test_repository.articles.save(article1)
        test_repository.articles.save(article2)

        # Get articles without content
        articles_without_content = test_repository.articles.get_without_content()

        # Should only return article2
        assert len(articles_without_content) == 1
        assert articles_without_content[0].title == "Article without content"

    def test_get_without_summary(self, test_repository, sample_article_data):
        """Test retrieving articles without summary"""
        # Create articles - one with summary, one without
        article1 = Article(**sample_article_data)
        article1.summary = "This is a summary"

        article2_data = sample_article_data.copy()
        article2_data["title"] = "Article without summary"
        article2_data["link"] = "https://example.com/article2"
        article2 = Article(**article2_data)
        # article2.summary remains None

        # Save both articles
        test_repository.articles.save(article1)
        test_repository.articles.save(article2)

        # Get articles without summary
        articles_without_summary = test_repository.articles.get_without_summary()

        # Should only return article2
        assert len(articles_without_summary) == 1
        assert articles_without_summary[0].title == "Article without summary"

    def test_update_content(self, test_repository, sample_article_data):
        """Test updating article content"""
        # Create and save article
        article = Article(**sample_article_data)
        saved_article = test_repository.articles.save(article)

        # Update content
        test_content = "This is updated content"
        success = test_repository.articles.update_content(
            saved_article.id, test_content
        )
        assert success

        # Verify update
        updated_article = test_repository.articles.get_by_id(saved_article.id)
        assert updated_article.content == test_content
        assert updated_article.status == ArticleStatus.SCRAPED

    def test_update_summary(self, test_repository, sample_article_data):
        """Test updating article summary"""
        # Create and save article
        article = Article(**sample_article_data)
        saved_article = test_repository.articles.save(article)

        # Update summary
        test_summary = "This is a test summary"
        success = test_repository.articles.update_summary(
            saved_article.id, test_summary
        )
        assert success

        # Verify update
        updated_article = test_repository.articles.get_by_id(saved_article.id)
        assert updated_article.summary == test_summary
        assert updated_article.status == ArticleStatus.SUMMARIZED

    def test_get_by_status(self, test_repository, sample_article_data):
        """Test retrieving articles by status"""
        # Create articles with different statuses
        article1 = Article(**sample_article_data)
        article1.status = ArticleStatus.PENDING

        article2_data = sample_article_data.copy()
        article2_data["title"] = "Scraped article"
        article2_data["link"] = "https://example.com/article2"
        article2 = Article(**article2_data)
        article2.status = ArticleStatus.SCRAPED

        # Save articles
        test_repository.articles.save(article1)
        test_repository.articles.save(article2)

        # Get pending articles
        pending_articles = test_repository.articles.get_by_status(ArticleStatus.PENDING)
        assert len(pending_articles) == 1
        assert pending_articles[0].title == sample_article_data["title"]

        # Get scraped articles
        scraped_articles = test_repository.articles.get_by_status(ArticleStatus.SCRAPED)
        assert len(scraped_articles) == 1
        assert scraped_articles[0].title == "Scraped article"


class TestFeedRepository:
    """Test the FeedRepository class"""

    def test_save_and_get_feed(self, test_repository, sample_feed_data):
        """Test saving and retrieving a feed"""
        # Create feed
        feed = Feed(**sample_feed_data)

        # Save feed
        saved_feed = test_repository.feeds.save(feed)
        assert saved_feed.id is not None
        assert saved_feed.title == sample_feed_data["title"]

        # Retrieve feed
        retrieved_feed = test_repository.feeds.get_by_id(saved_feed.id)
        assert retrieved_feed is not None
        assert retrieved_feed.title == sample_feed_data["title"]
        assert retrieved_feed.url == sample_feed_data["url"]

    def test_get_by_url(self, test_repository, sample_feed_data):
        """Test retrieving feed by URL"""
        # Create and save feed
        feed = Feed(**sample_feed_data)
        saved_feed = test_repository.feeds.save(feed)

        # Retrieve by URL
        retrieved_feed = test_repository.feeds.get_by_url(sample_feed_data["url"])
        assert retrieved_feed is not None
        assert retrieved_feed.id == saved_feed.id

    def test_get_active_feeds(self, test_repository, sample_feed_data):
        """Test retrieving active feeds"""
        # Create feeds with different statuses
        active_feed = Feed(**sample_feed_data)
        active_feed.status = FeedStatus.ACTIVE

        inactive_feed_data = sample_feed_data.copy()
        inactive_feed_data["url"] = "https://example.com/inactive.xml"
        inactive_feed_data["title"] = "Inactive Feed"
        inactive_feed = Feed(**inactive_feed_data)
        inactive_feed.status = FeedStatus.INACTIVE

        # Save feeds
        test_repository.feeds.save(active_feed)
        test_repository.feeds.save(inactive_feed)

        # Get active feeds
        active_feeds = test_repository.feeds.get_active()
        assert len(active_feeds) == 1
        assert active_feeds[0].title == sample_feed_data["title"]

        # Get all feeds
        all_feeds = test_repository.feeds.get_all()
        assert len(all_feeds) == 2


class TestNewsRepository:
    """Test the main NewsRepository class"""

    def test_initialization(self, test_repository):
        """Test that NewsRepository initializes correctly"""
        assert test_repository.articles is not None
        assert test_repository.feeds is not None

    def test_legacy_methods(self, test_repository, sample_feed_data):
        """Test legacy compatibility methods"""
        # Test create_feed
        feed = Feed(**sample_feed_data)
        feed_id = test_repository.create_feed(feed)
        assert feed_id is not None

        # Test get_feed_by_id
        retrieved_feed = test_repository.get_feed_by_id(feed_id)
        assert retrieved_feed is not None
        assert retrieved_feed.title == sample_feed_data["title"]

        # Test get_all_feeds
        all_feeds = test_repository.get_all_feeds()
        assert len(all_feeds) >= 1

        active_feeds = test_repository.get_all_feeds(include_inactive=False)
        assert len(active_feeds) >= 1
