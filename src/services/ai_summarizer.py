"""
AI summarization service for the News Aggregator application.

This module handles AI-powered summarization of article content using OpenAI's API.
"""

import openai
import logging
from typing import Optional, List

from ..core.models import AIModelInfo
from ..core.repository import NewsRepository
from ..core.config import ConfigManager

logger = logging.getLogger(__name__)


class AISummarizer:
    """
    Service class for AI-powered article summarization
    """

    def __init__(self, config: ConfigManager, repository: NewsRepository):
        """
        Initialize the AISummarizer

        Args:
            repository: Repository instance for data access
            config: Configuration manager instance
        """
        self.repository = repository
        self.config = config
        self.logger = logger
        self.client: Optional[openai.OpenAI] = None
        self._available_models_cache: Optional[List[AIModelInfo]] = None
        self._initialize_client()

    def _initialize_client(self) -> None:
        """Initialize OpenAI client if API key is available"""
        api_key = self.config.get_openai_api_key()
        if not api_key:
            self.logger.warning(
                "OpenAI API key not found. Summarization will be disabled."
            )
            self.client = None
        else:
            self.client = openai.OpenAI(api_key=api_key)

    def update_api_key(self, api_key: str) -> bool:
        """
        Update the OpenAI API key and reinitialize client

        Args:
            api_key: New OpenAI API key

        Returns:
            bool: True if client was successfully initialized
        """
        self.config.set_openai_api_key(api_key)
        self._initialize_client()
        # Clear the cache when API key changes
        self._available_models_cache = None
        return self.client is not None

    def test_model_availability(self, model: str) -> bool:
        """
        Test if a specific model is available for the current API key

        Args:
            model: Model name to test

        Returns:
            bool: True if model is available, False otherwise
        """
        if not self.client:
            return False

        try:
            # Try a minimal completion to test model availability
            self.client.chat.completions.create(
                model=model,
                messages=[{"role": "user", "content": "test"}],
                max_tokens=1,
                timeout=self.config.ai_config.timeout,
            )
            return True
        except Exception:
            # Silently fail - this is expected for unavailable models
            return False

    def get_available_models_for_user(self) -> List[AIModelInfo]:
        """
        Get list of models that are actually available for the user's API key

        Returns:
            List[AIModelInfo]: List of available AI models
        """
        if not self.client:
            return []

        # Return cached result if available
        if self._available_models_cache is not None:
            return self._available_models_cache

        # Check if we have known working models from config
        known_models = self.config.get_known_working_models()
        if known_models:
            self._available_models_cache = known_models
            self.logger.info(
                f"Using known working models: {[m.display_name for m in known_models]}"
            )
            return known_models

        all_models = self.config.get_available_models()
        available = []

        # Test models in order of likelihood to be available
        priority_order = [
            "gpt-4o-mini",
            "gpt-3.5-turbo",
            "gpt-4o",
            "gpt-4-turbo",
            "gpt-4",
        ]
        models_to_test = []

        # Add priority models first
        for model_name in priority_order:
            model = next((m for m in all_models if m.model_id == model_name), None)
            if model:
                models_to_test.append(model)

        # Add any remaining models
        for model in all_models:
            if model not in models_to_test:
                models_to_test.append(model)

        # Test each model
        for model in models_to_test:
            if self.test_model_availability(model.model_id):
                available.append(model)
                self.logger.info(f"Model {model.model_id} is available")
            else:
                self.logger.debug(f"Model {model.model_id} not available")

        # Cache the result and save to config
        self._available_models_cache = available
        if available:
            self.config.set_known_working_models(available)
            self.logger.info(
                f"Found {len(available)} available model(s): {[m.display_name for m in available]}"
            )
        else:
            self.logger.warning("No models available for this API key")

        return available

    def get_current_model(self) -> str:
        """
        Get the currently selected model

        Returns:
            str: Currently selected model name
        """
        return self.config.ai_config.selected_model

    def is_available(self) -> bool:
        """
        Check if AI summarization is available

        Returns:
            bool: True if AI summarization is available, False otherwise
        """
        return self.client is not None

    def generate_summary(self, content: str, title: str = "") -> Optional[str]:
        """
        Generate AI summary of article content

        Args:
            content: Article content to summarize
            title: Article title (optional)

        Returns:
            Optional[str]: Generated summary if successful, None otherwise
        """
        if not self.client:
            return "AI summarization unavailable - API key not configured"

        try:
            current_model = self.get_current_model()

            # Test if the current model is available before using it
            if not self.test_model_availability(current_model):
                # Try to find an available model
                available_models = self.get_available_models_for_user()
                if not available_models:
                    return "Error: No AI models available for your OpenAI project"

                # Switch to the first available model
                new_model = available_models[0]
                self.config.ai_config.selected_model = new_model.model_id
                self.logger.info(
                    f"Switched from unavailable model {current_model} to {new_model.display_name}"
                )
                current_model = new_model.model_id

            # Prepare the prompt
            max_summary_length = self.config.ai_config.max_summary_length
            prompt = f"""
            Please summarize the following news article in {max_summary_length // 4} words or less.
            Focus on the key facts, main points, and important details.

            Title: {title}

            Article Content:
            {content[:3000]}  # Limit content to avoid token limits

            Summary:
            """

            response = self.client.chat.completions.create(
                model=current_model,
                messages=[
                    {
                        "role": "system",
                        "content": "You are a professional news summarizer. Create concise, accurate summaries of news articles.",
                    },
                    {"role": "user", "content": prompt},
                ],
                max_tokens=max_summary_length // 2,
                temperature=self.config.ai_config.temperature,
                timeout=self.config.ai_config.timeout,
            )

            summary_content = response.choices[0].message.content
            if summary_content:
                summary = summary_content.strip()
                return str(summary) if summary else None
            return None

        except Exception as e:
            self.logger.error(f"Error generating summary: {e}")
            return f"Error generating summary: {str(e)}"

    def summarize_article(self, article_id: int) -> bool:
        """
        Generate and save summary for an article

        Args:
            article_id: ID of article to summarize

        Returns:
            bool: True if successful, False otherwise
        """
        try:
            article = self.repository.articles.get_by_id(article_id)
            if not article:
                return False

            # Use existing summary if available
            if article.summary:
                return True

            # Generate summary from content or description
            content_to_summarize = article.content or article.description
            if not content_to_summarize:
                return False

            summary = self.generate_summary(content_to_summarize, article.title)
            if summary:
                return self.repository.articles.update_summary(article_id, summary)

            return False

        except Exception as e:
            self.logger.error(f"Error summarizing article {article_id}: {e}")
            return False

    def bulk_summarize(self, limit: Optional[int] = None) -> int:
        """
        Summarize multiple articles that don't have summaries yet

        Args:
            limit: Maximum number of articles to summarize. If None, uses config default.

        Returns:
            int: Number of articles successfully summarized
        """
        if not self.client:
            return 0

        # Use config default if no limit specified
        if limit is None:
            limit = self.config.get_bulk_summarize_limit()

        try:
            # Get articles without summaries
            articles = self.repository.articles.get_without_summary(limit)
            summarized_count = 0

            for article in articles:
                if (article.content or article.description) and article.id is not None:
                    if self.summarize_article(article.id):
                        summarized_count += 1

            return summarized_count

        except Exception as e:
            self.logger.error(f"Error in bulk summarize: {e}")
            return 0

    def generate_daily_summary(self, content: str) -> Optional[str]:
        """
        Generate a comprehensive daily news summary optimized for readability

        Args:
            content: Combined content from multiple articles to summarize

        Returns:
            Optional[str]: Generated daily summary if successful, None otherwise
        """
        if not self.client:
            return "AI summarization unavailable - API key not configured"

        try:
            current_model = self.get_current_model()

            # Test if the current model is available before using it
            if not self.test_model_availability(current_model):
                # Try to find an available model
                available_models = self.get_available_models_for_user()
                if not available_models:
                    return "Error: No AI models available for your OpenAI project"

                # Switch to the first available model
                new_model = available_models[0]
                self.config.ai_config.selected_model = new_model.model_id
                self.logger.info(
                    f"Switched from unavailable model {current_model} to {new_model.display_name}"
                )
                current_model = new_model.model_id

            response = self.client.chat.completions.create(
                model=current_model,
                messages=[
                    {
                        "role": "system",
                        "content": """You are a professional news editor creating daily news digests. Your task is to synthesize multiple news articles into a single, flowing narrative that reads like a comprehensive news briefing. Write in a clear, engaging style that connects related stories and provides context.""",
                    },
                    {"role": "user", "content": content},
                ],
                max_tokens=800,  # Increased for longer, more comprehensive summaries
                temperature=0.3,  # Lower temperature for more focused, coherent output
                timeout=self.config.ai_config.timeout,
            )

            summary_content = response.choices[0].message.content
            if summary_content:
                summary = summary_content.strip()
                return str(summary) if summary else None
            return None

        except Exception as e:
            self.logger.error(f"Error generating daily summary: {e}")
            return f"Error generating daily summary: {str(e)}"
