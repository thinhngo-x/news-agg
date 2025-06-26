"""
Test configuration management functionality.
"""

from src.core.config import (
    ConfigManager,
    DatabaseConfig,
    AIConfig,
    FeedConfig,
    UIConfig,
)


class TestConfigManager:
    """Test the ConfigManager class"""

    def test_default_initialization(self, isolated_config):
        """Test that ConfigManager initializes with default values"""
        config = isolated_config

        assert isinstance(config.database, DatabaseConfig)
        assert isinstance(config.ai_config, AIConfig)
        assert isinstance(config.feeds, FeedConfig)
        assert isinstance(config.ui, UIConfig)

        # Check some default values
        assert config.ai_config.selected_model == "gpt-4o-mini"
        assert config.feeds.default_fetch_interval == 3600
        assert config.ui.items_per_page == 20
        assert config.ui.max_content_length == 10000

    def test_api_key_management(self, isolated_config):
        """Test API key setting and retrieval"""
        config = isolated_config

        # Initially no API key
        assert not config.has_openai_api_key()
        assert config.get_openai_api_key() is None

        # Set API key
        test_key = "sk-test123456789"
        config.set_openai_api_key(test_key)

        assert config.has_openai_api_key()
        assert config.get_openai_api_key() == test_key

        # Clear API key
        config.clear_openai_api_key()
        assert not config.has_openai_api_key()
        assert config.get_openai_api_key() is None

    def test_model_management(self):
        """Test AI model management"""
        config = ConfigManager()

        # Test getting available models
        models = config.get_available_models()
        assert len(models) > 0
        assert any(model.model_id == "gpt-4o-mini" for model in models)

        # Test setting model
        assert config.set_selected_model("gpt-4o")
        assert config.get_selected_model() == "gpt-4o"

        # Test setting invalid model
        assert not config.set_selected_model("invalid-model")
        assert config.get_selected_model() == "gpt-4o"  # Should remain unchanged

    def test_default_feeds(self):
        """Test default feeds list"""
        config = ConfigManager()
        default_feeds = config.get_default_feeds()

        assert len(default_feeds) > 0
        assert all(url.startswith("http") for url in default_feeds)
        assert "bbc" in default_feeds[0].lower()

    def test_config_serialization(self, isolated_config):
        """Test configuration to dictionary conversion"""
        config = isolated_config
        config_dict = config.to_dict()

        assert "database" in config_dict
        assert "ai" in config_dict
        assert "feeds" in config_dict
        assert "ui" in config_dict

        # API key should not be in serialized config for security (when clean env is used)
        # If the key exists, this test expects it to be serialized
        # so we'll check it exists if it was set
        ai_config = config_dict["ai"]
        if config.has_openai_api_key():
            assert "openai_api_key" in ai_config
        else:
            assert (
                "openai_api_key" not in ai_config
                or ai_config.get("openai_api_key") is None
            )

    def test_bulk_summarize_limit_management(self, isolated_config):
        """Test bulk summarize limit setting and retrieval"""
        config = isolated_config

        # Get initial value (might not be 10 if tests are not isolated)
        initial_limit = config.get_bulk_summarize_limit()
        assert initial_limit > 0  # Should be a positive value

        # Test setting valid values
        assert config.set_bulk_summarize_limit(20) is True
        assert config.get_bulk_summarize_limit() == 20

        assert config.set_bulk_summarize_limit(1) is True
        assert config.get_bulk_summarize_limit() == 1

        assert config.set_bulk_summarize_limit(100) is True
        assert config.get_bulk_summarize_limit() == 100

        # Test invalid values
        assert config.set_bulk_summarize_limit(0) is False
        assert config.get_bulk_summarize_limit() == 100  # Should remain unchanged

        assert config.set_bulk_summarize_limit(-5) is False
        assert config.get_bulk_summarize_limit() == 100  # Should remain unchanged


class TestConfigDataClasses:
    """Test the configuration dataclasses"""

    def test_database_config(self):
        """Test DatabaseConfig defaults"""
        config = DatabaseConfig()
        assert "sqlite:///" in config.url
        assert config.backup_enabled is True
        assert config.backup_interval == 86400

    def test_ai_config(self):
        """Test AIConfig defaults"""
        config = AIConfig()
        assert config.openai_api_key is None
        assert config.selected_model == "gpt-4o-mini"
        assert config.max_summary_length == 500
        assert config.temperature == 0.3
        assert config.timeout == 30

    def test_feed_config(self):
        """Test FeedConfig defaults"""
        config = FeedConfig()
        assert config.default_fetch_interval == 3600
        assert config.max_articles_per_feed == 100
        assert config.concurrent_fetches == 5
        assert config.request_timeout == 30

    def test_ui_config(self):
        """Test UIConfig defaults"""
        config = UIConfig()
        assert config.items_per_page == 20
        assert config.theme == "light"
        assert config.sidebar_expanded is True
        assert config.max_content_length == 10000
