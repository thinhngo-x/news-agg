"""
Test AI summarization functionality.
"""

import pytest
from unittest.mock import Mock, patch
from src.core.models import Article, AIModelInfo
from src.services.ai_summarizer import AISummarizer


class TestAISummarizer:
    """Test the AISummarizer class"""

    @pytest.fixture
    def mock_config(self):
        """Mock configuration for testing"""
        config = Mock()
        config.get_openai_api_key.return_value = "test-api-key"
        config.get_bulk_summarize_limit.return_value = 10  # Default limit
        config.ai_config.selected_model = "gpt-4o-mini"
        config.ai_config.max_summary_length = 500
        config.ai_config.temperature = 0.3
        config.ai_config.timeout = 30
        config.get_available_models.return_value = [
            AIModelInfo(
                model_id="gpt-4o-mini",
                display_name="GPT-4o Mini",
                description="Test model",
                cost_tier="low",
                max_tokens=4096,
            )
        ]
        config.get_known_working_models.return_value = []
        config.set_known_working_models = Mock()
        return config

    @pytest.fixture
    def ai_summarizer(self, mock_config, test_repository):
        """Create AISummarizer instance for testing"""
        with patch("src.services.ai_summarizer.openai.OpenAI"):
            return AISummarizer(mock_config, test_repository)

    def test_initialization_with_api_key(self, mock_config, test_repository):
        """Test AISummarizer initialization with API key"""
        with patch("src.services.ai_summarizer.openai.OpenAI") as mock_openai:
            mock_client = Mock()
            mock_openai.return_value = mock_client

            summarizer = AISummarizer(mock_config, test_repository)

            assert summarizer.config == mock_config
            assert summarizer.repository == test_repository
            assert summarizer.client == mock_client

    def test_initialization_without_api_key(self, test_repository):
        """Test AISummarizer initialization without API key"""
        config = Mock()
        config.get_openai_api_key.return_value = None

        summarizer = AISummarizer(config, test_repository)

        assert summarizer.client is None

    def test_is_available_with_client(self, ai_summarizer):
        """Test is_available returns True when client exists"""
        ai_summarizer.client = Mock()
        assert ai_summarizer.is_available() is True

    def test_is_available_without_client(self, ai_summarizer):
        """Test is_available returns False when no client"""
        ai_summarizer.client = None
        assert ai_summarizer.is_available() is False

    def test_update_api_key(self, ai_summarizer, mock_config):
        """Test updating API key"""
        with patch("src.services.ai_summarizer.openai.OpenAI") as mock_openai:
            mock_client = Mock()
            mock_openai.return_value = mock_client

            result = ai_summarizer.update_api_key("new-test-key")

            assert result is True
            mock_config.set_openai_api_key.assert_called_with("new-test-key")
            assert ai_summarizer.client == mock_client

    def test_generate_summary_success(self, ai_summarizer):
        """Test successful summary generation"""
        # Mock OpenAI client response
        mock_response = Mock()
        mock_response.choices = [Mock()]
        mock_response.choices[0].message.content = "This is a test summary."

        ai_summarizer.client = Mock()
        ai_summarizer.client.chat.completions.create.return_value = mock_response

        # Mock test_model_availability to return True
        with patch.object(ai_summarizer, "test_model_availability", return_value=True):
            summary = ai_summarizer.generate_summary("Test content", "Test Title")

        assert summary == "This is a test summary."
        ai_summarizer.client.chat.completions.create.assert_called_once()

    def test_generate_summary_no_client(self, ai_summarizer):
        """Test summary generation without client"""
        ai_summarizer.client = None

        summary = ai_summarizer.generate_summary("Test content", "Test Title")

        assert "unavailable" in summary.lower()

    def test_generate_summary_api_error(self, ai_summarizer):
        """Test summary generation with API error"""
        ai_summarizer.client = Mock()
        ai_summarizer.client.chat.completions.create.side_effect = Exception(
            "API Error"
        )

        with patch.object(ai_summarizer, "test_model_availability", return_value=True):
            summary = ai_summarizer.generate_summary("Test content", "Test Title")

        assert "Error generating summary" in summary

    def test_summarize_article_success(
        self, ai_summarizer, test_repository, sample_article_data
    ):
        """Test successful article summarization"""
        # Create article with content
        article_data = sample_article_data.copy()
        article_data["content"] = "This is test content for summarization."
        article = Article(**article_data)
        saved_article = test_repository.articles.save(article)

        # Mock successful summary generation
        with patch.object(
            ai_summarizer, "generate_summary", return_value="Test summary"
        ):
            success = ai_summarizer.summarize_article(saved_article.id)

        assert success

        # Verify summary was saved
        updated_article = test_repository.articles.get_by_id(saved_article.id)
        assert updated_article.summary == "Test summary"

    def test_summarize_article_no_content(
        self, ai_summarizer, test_repository, sample_article_data
    ):
        """Test article summarization with no content"""
        # Create article without content
        article = Article(**sample_article_data)
        saved_article = test_repository.articles.save(article)

        success = ai_summarizer.summarize_article(saved_article.id)

        assert not success

    def test_summarize_article_not_found(self, ai_summarizer):
        """Test summarization of non-existent article"""
        success = ai_summarizer.summarize_article(99999)  # Non-existent ID

        assert not success

    def test_bulk_summarize(self, ai_summarizer, test_repository, sample_article_data):
        """Test bulk summarization"""
        # Create multiple articles with content but no summaries
        articles = []
        for i in range(3):
            article_data = sample_article_data.copy()
            article_data["title"] = f"Article {i + 1}"
            article_data["link"] = f"https://example.com/article{i + 1}"
            article_data["content"] = f"Content for article {i + 1}"
            article = Article(**article_data)
            saved_article = test_repository.articles.save(article)
            articles.append(saved_article)

        # Mock successful summary generation
        with patch.object(
            ai_summarizer, "generate_summary", return_value="Test summary"
        ):
            count = ai_summarizer.bulk_summarize(limit=5)

        assert count == 3  # Should have summarized all 3 articles

        # Verify all articles have summaries
        for article in articles:
            updated_article = test_repository.articles.get_by_id(article.id)
            assert updated_article.summary == "Test summary"

    def test_bulk_summarize_no_client(self, ai_summarizer):
        """Test bulk summarization without client"""
        ai_summarizer.client = None

        count = ai_summarizer.bulk_summarize()

        assert count == 0

    def test_test_model_availability_success(self, ai_summarizer):
        """Test successful model availability check"""
        ai_summarizer.client = Mock()
        ai_summarizer.client.chat.completions.create.return_value = Mock()

        result = ai_summarizer.test_model_availability("gpt-4o-mini")

        assert result is True

    def test_test_model_availability_failure(self, ai_summarizer):
        """Test failed model availability check"""
        ai_summarizer.client = Mock()
        ai_summarizer.client.chat.completions.create.side_effect = Exception(
            "Model not available"
        )

        result = ai_summarizer.test_model_availability("invalid-model")

        assert result is False

    def test_get_current_model(self, ai_summarizer, mock_config):
        """Test getting current model"""
        model = ai_summarizer.get_current_model()

        assert model == "gpt-4o-mini"

    def test_bulk_summarize_uses_config_default(self, mock_config):
        """Test that bulk_summarize uses config default when no limit specified"""
        # Set up mock config to return a specific limit
        mock_config.get_bulk_summarize_limit.return_value = 15

        # Create mock repository
        mock_repository = Mock()
        mock_articles = [Mock(id=i, content=f"Content {i}") for i in range(1, 11)]
        mock_repository.articles.get_without_summary.return_value = mock_articles

        with patch("src.services.ai_summarizer.openai.OpenAI") as mock_openai:
            mock_client = Mock()
            mock_openai.return_value = mock_client

            summarizer = AISummarizer(mock_config, mock_repository)

            # Mock generate_summary to return success
            with patch.object(
                summarizer, "generate_summary", return_value="Test summary"
            ):
                with patch.object(summarizer, "summarize_article", return_value=True):
                    summarizer.bulk_summarize()  # No limit parameter

            # Verify that get_bulk_summarize_limit was called
            mock_config.get_bulk_summarize_limit.assert_called_once()

            # Verify that get_without_summary was called with the config limit
            mock_repository.articles.get_without_summary.assert_called_with(15)

    def test_bulk_summarize_with_explicit_limit(self, mock_config):
        """Test that bulk_summarize uses explicit limit when provided"""
        # Set up mock config (shouldn't be called when explicit limit is provided)
        mock_config.get_bulk_summarize_limit.return_value = 15

        # Create mock repository
        mock_repository = Mock()
        mock_articles = [Mock(id=i, content=f"Content {i}") for i in range(1, 6)]
        mock_repository.articles.get_without_summary.return_value = mock_articles

        with patch("src.services.ai_summarizer.openai.OpenAI") as mock_openai:
            mock_client = Mock()
            mock_openai.return_value = mock_client

            summarizer = AISummarizer(mock_config, mock_repository)

            # Mock generate_summary to return success
            with patch.object(
                summarizer, "generate_summary", return_value="Test summary"
            ):
                with patch.object(summarizer, "summarize_article", return_value=True):
                    summarizer.bulk_summarize(limit=5)  # Explicit limit

            # Verify that get_bulk_summarize_limit was NOT called
            mock_config.get_bulk_summarize_limit.assert_not_called()

            # Verify that get_without_summary was called with the explicit limit
            mock_repository.articles.get_without_summary.assert_called_with(5)
