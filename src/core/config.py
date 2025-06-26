"""
Configuration management for the News Aggregator application.

This module handles all configuration settings, environment variables,
and persistent storage of user preferences.
"""

import os
import json
import logging
from typing import Optional, Dict, Any, List
from pathlib import Path
from dataclasses import dataclass, asdict
from dotenv import load_dotenv

from .models import AIModelInfo

load_dotenv()

logger = logging.getLogger(__name__)


@dataclass
class DatabaseConfig:
    """Database configuration"""

    url: str = "sqlite:///data/news_aggregator.db"
    backup_enabled: bool = True
    backup_interval: int = 86400  # 24 hours in seconds


@dataclass
class AIConfig:
    """AI configuration"""

    openai_api_key: Optional[str] = None
    selected_model: str = "gpt-4o-mini"
    max_summary_length: int = 500
    temperature: float = 0.3
    timeout: int = 30
    bulk_summarize_limit: int = 10  # Number of articles to summarize in bulk operations


@dataclass
class FeedConfig:
    """Feed processing configuration"""

    default_fetch_interval: int = 3600  # 1 hour
    max_articles_per_feed: int = 100
    concurrent_fetches: int = 5
    request_timeout: int = 30


@dataclass
class UIConfig:
    """UI configuration"""

    items_per_page: int = 20
    theme: str = "light"
    sidebar_expanded: bool = True
    max_content_length: int = 10000  # Maximum length for scraped content


class ConfigManager:
    """Manages application configuration and persistent settings"""

    def __init__(self, config_dir: str = ".config"):
        self.config_dir = Path(config_dir)
        self.config_dir.mkdir(exist_ok=True)

        self.config_file = self.config_dir / "settings.json"
        self.api_key_file = Path(
            ".api_key_cache.json"
        )  # Keep in project root for backward compatibility

        # Default configurations
        self.database = DatabaseConfig()
        self.ai_config = AIConfig()
        self.feeds = FeedConfig()
        self.ui = UIConfig()

        # Available AI models
        self.available_models = {
            "gpt-4o-mini": AIModelInfo(
                model_id="gpt-4o-mini",
                display_name="GPT-4o Mini (Efficient & Widely Available)",
                description="Fast and cost-effective model suitable for most tasks",
                cost_tier="low",
                max_tokens=16384,
            ),
            "gpt-4o": AIModelInfo(
                model_id="gpt-4o",
                display_name="GPT-4o (Latest & High Quality)",
                description="Latest model with best performance",
                cost_tier="high",
                max_tokens=128000,
            ),
            "gpt-4-turbo": AIModelInfo(
                model_id="gpt-4-turbo",
                display_name="GPT-4 Turbo (Balanced Performance)",
                description="Balanced performance and cost",
                cost_tier="medium",
                max_tokens=128000,
            ),
            "gpt-4": AIModelInfo(
                model_id="gpt-4",
                display_name="GPT-4 (Premium Quality)",
                description="High quality but more expensive",
                cost_tier="high",
                max_tokens=8192,
            ),
            "gpt-3.5-turbo": AIModelInfo(
                model_id="gpt-3.5-turbo",
                display_name="GPT-3.5 Turbo (Legacy)",
                description="Legacy model, may not be available",
                cost_tier="low",
                max_tokens=4096,
            ),
        }

        # Cache for model availability
        self._available_model_cache: Optional[List[str]] = None

        # Load configuration
        self.load_config()

        # Load API key from environment or cache
        self._load_api_key()

        # Initialize database
        self._init_database()

    def _load_api_key(self) -> None:
        """Load API key from environment or cache"""
        # Try environment variable first
        env_key = os.getenv("OPENAI_API_KEY")
        if env_key:
            self.ai_config.openai_api_key = env_key
            return

        # Try cached key
        cached_key = self._load_cached_api_key()
        if cached_key:
            self.ai_config.openai_api_key = cached_key

    def _load_cached_api_key(self) -> Optional[str]:
        """Load API key from cache file"""
        try:
            if self.api_key_file.exists():
                with open(self.api_key_file, "r") as f:
                    data = json.load(f)
                    key = data.get("openai_api_key")
                    return key if isinstance(key, str) else None
        except Exception as e:
            logger.warning(f"Failed to load cached API key: {e}")
        return None

    def _save_api_key_to_cache(self, api_key: Optional[str]) -> None:
        """Save API key to cache file"""
        try:
            data = {"openai_api_key": api_key} if api_key else {}
            with open(self.api_key_file, "w") as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            logger.warning(f"Failed to save API key to cache: {e}")

    def set_openai_api_key(self, api_key: str) -> None:
        """Set OpenAI API key and save to cache"""
        self.ai_config.openai_api_key = api_key.strip() if api_key.strip() else None
        self._save_api_key_to_cache(self.ai_config.openai_api_key)
        # Clear model availability cache when key changes
        self._available_model_cache = None
        self.save_config()

    def clear_openai_api_key(self) -> None:
        """Clear OpenAI API key from memory and cache"""
        self.ai_config.openai_api_key = None
        self._save_api_key_to_cache(None)
        self._available_model_cache = None
        self.save_config()

    def has_openai_api_key(self) -> bool:
        """Check if OpenAI API key is configured"""
        return bool(
            self.ai_config.openai_api_key and self.ai_config.openai_api_key.strip()
        )

    def get_openai_api_key(self) -> Optional[str]:
        """Get the OpenAI API key"""
        return self.ai_config.openai_api_key

    def get_selected_model(self) -> str:
        """Get currently selected AI model"""
        return self.ai_config.selected_model

    def set_selected_model(self, model_id: str) -> bool:
        """Set AI model if it exists"""
        if model_id in self.available_models:
            self.ai_config.selected_model = model_id
            self.save_config()
            return True
        return False

    def get_available_models(self) -> List[AIModelInfo]:
        """Get all available AI models as a list"""
        return list(self.available_models.values())

    def set_available_model_cache(self, models: List[str]) -> None:
        """Cache which models are actually available"""
        self._available_model_cache = models

    def get_available_model_cache(self) -> Optional[List[str]]:
        """Get cached available models"""
        return self._available_model_cache

    def clear_available_model_cache(self) -> None:
        """Clear model availability cache"""
        self._available_model_cache = None

    def load_config(self) -> None:
        """Load configuration from file"""
        try:
            if self.config_file.exists():
                with open(self.config_file, "r") as f:
                    data = json.load(f)

                # Update configurations
                if "database" in data:
                    self.database = DatabaseConfig(**data["database"])
                if "ai" in data:
                    ai_data = data["ai"]
                    # Don't load API key from config file for security
                    ai_data.pop("openai_api_key", None)
                    self.ai_config = AIConfig(
                        **ai_data, openai_api_key=self.ai_config.openai_api_key
                    )
                if "feeds" in data:
                    self.feeds = FeedConfig(**data["feeds"])
                if "ui" in data:
                    self.ui = UIConfig(**data["ui"])

        except Exception as e:
            logger.warning(f"Failed to load config: {e}")

    def save_config(self) -> None:
        """Save configuration to file"""
        try:
            data = {
                "database": asdict(self.database),
                "ai": {
                    k: v
                    for k, v in asdict(self.ai_config).items()
                    if k != "openai_api_key"
                },
                "feeds": asdict(self.feeds),
                "ui": asdict(self.ui),
            }

            with open(self.config_file, "w") as f:
                json.dump(data, f, indent=2)

        except Exception as e:
            logger.error(f"Failed to save config: {e}")

    def get_known_working_models(self) -> List[AIModelInfo]:
        """Get cached list of known working models"""
        if self._available_model_cache:
            return [
                self.available_models[model_id]
                for model_id in self._available_model_cache
                if model_id in self.available_models
            ]
        return []

    def set_known_working_models(self, models: List[AIModelInfo]) -> None:
        """Cache known working models"""
        self._available_model_cache = [model.model_id for model in models]
        self.save_config()

    def get_default_feeds(self) -> List[str]:
        """Get list of default RSS feeds"""
        return [
            "https://feeds.bbci.co.uk/news/rss.xml",
            "https://rss.cnn.com/rss/edition.rss",
            "https://feeds.reuters.com/reuters/topNews",
            "https://techcrunch.com/feed/",
            "https://feeds.npr.org/1001/rss.xml",
        ]

    def to_dict(self) -> Dict[str, Any]:
        """Convert configuration to dictionary"""
        return {
            "database": asdict(self.database),
            "ai": asdict(self.ai_config),
            "feeds": asdict(self.feeds),
            "ui": asdict(self.ui),
        }

    def _init_database(self) -> None:
        """Initialize the SQLModel database"""
        try:
            from .database import init_database

            init_database(self.database.url)
            logger.info("Database initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize database: {e}")
            raise

    def get_bulk_summarize_limit(self) -> int:
        """Get the limit for bulk summarization operations"""
        return self.ai_config.bulk_summarize_limit

    def set_bulk_summarize_limit(self, limit: int) -> bool:
        """
        Set the limit for bulk summarization operations

        Args:
            limit: Number of articles to summarize in bulk (must be > 0)

        Returns:
            bool: True if successfully set, False otherwise
        """
        if limit > 0:
            self.ai_config.bulk_summarize_limit = limit
            self.save_config()
            return True
        return False


# Global configuration instance
config = ConfigManager()
