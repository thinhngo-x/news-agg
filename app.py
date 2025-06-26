"""
Main application entry point using the new architecture.

This is the new Streamlit app that uses the refactored architecture with
the repository pattern, configuration manager, and service layer.
"""

import streamlit as st
import logging

# Import from the new architecture
from src.core.config import ConfigManager
from src.core.repository import NewsRepository
from src.services.feed_manager import FeedManager
from src.services.content_scraper import ContentScraper
from src.services.ai_summarizer import AISummarizer
from src.ui.feed_management import render_feed_management_ui
from src.ui.la_une import render_la_une_page

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Streamlit page configuration
st.set_page_config(
    page_title="News Aggregator",
    page_icon="📰",
    layout="wide",
    initial_sidebar_state="expanded",
)


@st.cache_resource
def initialize_app() -> tuple[
    ConfigManager, NewsRepository, FeedManager, ContentScraper, AISummarizer
]:
    """
    Initialize the application components

    Returns:
        Tuple of initialized components
    """
    try:
        # Initialize configuration manager
        config = ConfigManager()

        # Initialize repository
        repository = NewsRepository()

        # Initialize services
        feed_manager = FeedManager(config, repository)
        content_scraper = ContentScraper(config, repository)
        ai_summarizer = AISummarizer(config, repository)

        logger.info("Application initialized successfully")
        return config, repository, feed_manager, content_scraper, ai_summarizer

    except Exception as e:
        logger.error(f"Failed to initialize application: {e}")
        st.error(f"Failed to initialize application: {e}")
        st.stop()


def render_api_key_setup(config: ConfigManager, ai_summarizer: AISummarizer) -> None:
    """
    Render API key setup interface

    Args:
        config: Configuration manager instance
        ai_summarizer: AI summarizer service instance
    """
    st.sidebar.header("🔑 OpenAI API Configuration")

    # Check current API key status
    has_key = config.has_openai_api_key()

    if has_key:
        st.sidebar.success("✅ API Key configured")

        # Model selection
        available_models = ai_summarizer.get_available_models_for_user()
        if available_models:
            current_model = config.ai_config.selected_model
            model_names = [model.display_name for model in available_models]

            if current_model in model_names:
                current_index = model_names.index(current_model)
            else:
                current_index = 0

            selected_model = st.sidebar.selectbox(
                "AI Model",
                options=model_names,
                index=current_index,
                help="Select the AI model for summarization",
            )

            if selected_model != current_model:
                config.ai_config.selected_model = selected_model
                st.sidebar.success("Model updated!")
        else:
            st.sidebar.warning("No AI models available for your API key")

        # Clear API key option
        if st.sidebar.button("🗑️ Clear API Key"):
            config.clear_openai_api_key()
            st.sidebar.success("API key cleared!")
            st.rerun()

    else:
        st.sidebar.warning("⚠️ No API key configured")

        # API key input
        with st.sidebar.form("api_key_form"):
            api_key = st.text_input(
                "Enter OpenAI API Key",
                type="password",
                placeholder="sk-proj-...",
                help="Your OpenAI API key for AI summarization",
            )

            if st.form_submit_button("💾 Save API Key"):
                if api_key.startswith("sk-"):
                    if ai_summarizer.update_api_key(api_key):
                        st.sidebar.success("✅ API key saved!")
                        st.rerun()
                    else:
                        st.sidebar.error("❌ Invalid API key")
                else:
                    st.sidebar.error("❌ Invalid API key format")


def render_sidebar_stats(feed_manager: FeedManager, repository: NewsRepository) -> None:
    """
    Render sidebar statistics

    Args:
        feed_manager: Feed manager service instance
        repository: Repository instance
    """
    st.sidebar.header("📊 Statistics")

    # Get statistics
    feeds = feed_manager.get_all_feeds(include_inactive=False)
    total_feeds = len(feeds)

    # Calculate total articles
    total_articles = sum(
        feed_manager.get_feed_statistics(feed.id).get("total_articles", 0)
        for feed in feeds
        if feed.id
    )

    # Display metrics
    col1, col2 = st.sidebar.columns(2)
    with col1:
        st.metric("Active Feeds", total_feeds)
    with col2:
        st.metric("Total Articles", total_articles)


def main() -> None:
    """Main application function"""

    # Initialize components
    config, repository, feed_manager, content_scraper, ai_summarizer = initialize_app()

    # Render sidebar
    render_api_key_setup(config, ai_summarizer)
    render_sidebar_stats(feed_manager, repository)

    # Main navigation
    st.title("📰 News Aggregator")

    # Page selection
    page = st.selectbox(
        "Navigate to:",
        ["🌟 La Une", "📄 Articles", "🗂️ Feed Management", "⚙️ Settings"],
        index=0,
        help="Select the page you want to view",
    )

    if page == "🌟 La Une":
        render_la_une_page(feed_manager, ai_summarizer, config)
    elif page == "📄 Articles":
        render_articles_page(feed_manager, content_scraper, ai_summarizer, config)
    elif page == "🗂️ Feed Management":
        render_feed_management_ui(feed_manager)
    elif page == "⚙️ Settings":
        render_settings_page(config, ai_summarizer)


def render_articles_page(
    feed_manager: FeedManager,
    content_scraper: ContentScraper,
    ai_summarizer: AISummarizer,
    config: ConfigManager,
) -> None:
    """
    Render the articles page

    Args:
        feed_manager: Feed manager service instance
        content_scraper: Content scraper service instance
        ai_summarizer: AI summarizer service instance
        config: Configuration manager instance
    """

    st.header("📄 Latest Articles")

    # Action buttons
    col1, col2, col3 = st.columns(3)

    with col1:
        if st.button("🔄 Update All Feeds"):
            with st.spinner("Updating feeds..."):
                results = feed_manager.update_all_feeds()
                st.success(
                    f"Found {results['new_articles']} new articles from {results['total_feeds']} feeds"
                )
                if results["errors"] > 0:
                    st.warning(f"{results['errors']} feeds had errors")

    with col2:
        if st.button("🤖 Generate Summaries") and ai_summarizer.is_available():
            with st.spinner("Generating AI summaries..."):
                count = ai_summarizer.bulk_summarize()  # Uses config default
                if count > 0:
                    st.success(f"Generated {count} summaries")
                else:
                    st.info("No articles need summarization")

    with col3:
        if st.button("🔍 Scrape Content"):
            with st.spinner("Scraping article content..."):
                count = content_scraper.bulk_scrape()
            if count > 0:
                st.success(f"Scraped content for {count} articles")
            else:
                st.info("No articles needed content scraping")

    # Display articles
    st.info("Article display functionality will be implemented in the next phase")

    # For now, show basic feed information
    feeds = feed_manager.get_all_feeds(include_inactive=False)
    if feeds:
        st.subheader("Current Feeds")
        for feed in feeds[:5]:  # Show first 5 feeds
            with st.expander(f"📡 {feed.title or feed.url}"):
                st.write(f"**URL:** {feed.url}")
                if feed.description:
                    st.write(f"**Description:** {feed.description}")

                # Show feed statistics
                if feed.id:
                    stats = feed_manager.get_feed_statistics(feed.id)
                    if stats:
                        col1, col2, col3 = st.columns(3)
                        with col1:
                            st.metric("Articles", stats.get("total_articles", 0))
                        with col2:
                            st.metric(
                                "With Content", stats.get("articles_with_content", 0)
                            )
                        with col3:
                            st.metric(
                                "With Summary", stats.get("articles_with_summary", 0)
                            )


def render_settings_page(config: ConfigManager, ai_summarizer: AISummarizer) -> None:
    """
    Render the settings page

    Args:
        config: Configuration manager instance
        ai_summarizer: AI summarizer service instance
    """
    st.header("⚙️ Settings")

    # AI Configuration Section
    st.subheader("🤖 AI Configuration")

    col1, col2 = st.columns(2)

    with col1:
        # Bulk summarize limit setting
        current_limit = config.get_bulk_summarize_limit()
        new_limit = st.number_input(
            "Bulk Summarize Limit",
            min_value=1,
            max_value=100,
            value=current_limit,
            step=1,
            help="Number of articles to summarize when using 'Generate Summaries' button",
        )

        if new_limit != current_limit:
            if st.button("💾 Save Limit"):
                if config.set_bulk_summarize_limit(new_limit):
                    st.success(f"✅ Bulk summarize limit updated to {new_limit}")
                    st.rerun()
                else:
                    st.error("❌ Failed to update limit")

    with col2:
        # AI Model selection
        if ai_summarizer.is_available():
            available_models = ai_summarizer.get_available_models_for_user()
            current_model = config.get_selected_model()

            model_options = [model.model_id for model in available_models]
            if current_model in model_options:
                current_index = model_options.index(current_model)
            else:
                current_index = 0

            selected_model = st.selectbox(
                "AI Model",
                options=model_options,
                index=current_index,
                help="Select the AI model for summarization",
            )

            if selected_model != current_model:
                if st.button("💾 Save Model"):
                    if config.set_selected_model(selected_model):
                        st.success(f"✅ AI model updated to {selected_model}")
                        st.rerun()
                    else:
                        st.error("❌ Failed to update model")
        else:
            st.info("🔑 OpenAI API key required for AI model configuration")

    # Display current configuration
    st.subheader("📊 Current Configuration")

    config_info = {
        "Bulk Summarize Limit": config.get_bulk_summarize_limit(),
        "AI Model": config.get_selected_model(),
        "Max Summary Length": config.ai_config.max_summary_length,
        "AI Temperature": config.ai_config.temperature,
        "AI Timeout": f"{config.ai_config.timeout}s",
        "Feed Fetch Interval": f"{config.feeds.default_fetch_interval}s",
        "Max Articles per Feed": config.feeds.max_articles_per_feed,
    }

    for key, value in config_info.items():
        col1, col2, col3 = st.columns([2, 1, 1])
        with col1:
            st.text(key)
        with col2:
            st.text(str(value))


if __name__ == "__main__":
    main()
