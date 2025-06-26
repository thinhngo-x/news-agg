"""
La Une (Front Page) UI component for the News Aggregator.

This module provides the user interface for displaying a comprehensive
daily summary of all news articles from active feeds fetched in the last 24 hours
as a single cohesive text, rather than individual article listings.
"""

import streamlit as st
import logging
from typing import List
from datetime import datetime

from ..core.models import Article
from ..services.feed_manager import FeedManager
from ..services.ai_summarizer import AISummarizer
from ..core.config import ConfigManager

logger = logging.getLogger(__name__)


def render_la_une_page(
    feed_manager: FeedManager, ai_summarizer: AISummarizer, config: ConfigManager
) -> None:
    """
    Render the La Une (Front Page) interface - A comprehensive daily news summary
    from active feeds only

    Args:
        feed_manager: Feed manager service instance
        ai_summarizer: AI summarizer service instance
        config: Configuration manager instance
    """
    st.header("📰 La Une - Daily News Summary")
    st.subheader("Your comprehensive daily news digest from active feeds")

    # Get recent articles from active feeds only (last 24 hours)
    recent_articles = feed_manager.get_recent_articles_from_active_feeds(hours=24)

    if not recent_articles:
        st.info(
            "🔍 No articles found from active feeds in the last 24 hours. Try updating your active feeds first!"
        )
        if st.button("🔄 Update All Feeds", type="primary", use_container_width=True):
            with st.spinner("Updating feeds..."):
                results = feed_manager.update_all_feeds()
                st.success(
                    f"Found {results['new_articles']} new articles from {results['total_feeds']} feeds"
                )
                st.rerun()
        return

    # Display basic metrics in a compact row
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.metric("📄 Articles", len(recent_articles))

    with col2:
        articles_with_content = len([a for a in recent_articles if a.has_content])
        st.metric("📝 Full Content", articles_with_content)

    with col3:
        unique_feeds = len(set(article.feed_url for article in recent_articles))
        st.metric("📡 Sources", unique_feeds)

    with col4:
        current_time = datetime.now()
        st.metric("⏰ Last Updated", current_time.strftime("%H:%M"))

    st.markdown("---")

    # Main action: Generate or display daily summary
    if not ai_summarizer.is_available():
        st.warning(
            "🔑 OpenAI API key required to generate daily summary. Please configure it in the sidebar."
        )
        st.info(
            "Configure your OpenAI API key in the sidebar to enable AI-powered daily summaries."
        )
        return

    # Check if we already have a daily summary
    daily_summary_key = f"daily_summary_{datetime.now().strftime('%Y-%m-%d')}"

    # Action buttons
    col1, col2, col3 = st.columns([2, 1, 1])

    with col1:
        if st.button(
            "🌟 Generate Today's Summary", type="primary", use_container_width=True
        ):
            with st.spinner(
                "Analyzing today's news and generating comprehensive summary..."
            ):
                daily_summary = generate_comprehensive_daily_summary(
                    recent_articles, ai_summarizer
                )
                if daily_summary:
                    st.session_state[daily_summary_key] = {
                        "summary": daily_summary,
                        "generated_at": datetime.now(),
                        "article_count": len(recent_articles),
                        "sources_count": unique_feeds,
                    }
                    st.success("Daily summary generated!")
                    st.rerun()
                else:
                    st.error("Failed to generate daily summary")

    with col2:
        if st.button("🔄 Refresh Summary", use_container_width=True):
            # Clear cached summary to force regeneration
            if daily_summary_key in st.session_state:
                del st.session_state[daily_summary_key]
            st.rerun()

    with col3:
        show_details = st.session_state.get("show_details", False)
        if st.button(
            "📊 Hide Details" if show_details else "📊 Show Details",
            use_container_width=True,
        ):
            st.session_state.show_details = not show_details
            st.rerun()

    # Display the daily summary
    if daily_summary_key in st.session_state:
        summary_data = st.session_state[daily_summary_key]

        # Summary header with metadata
        st.markdown("### 🌟 Today's News Summary")

        col1, col2, col3 = st.columns([2, 1, 1])
        with col1:
            st.caption(
                f"📊 Based on {summary_data['article_count']} articles from {summary_data['sources_count']} active sources"
            )
        with col2:
            generated_time = summary_data["generated_at"].strftime("%H:%M")
            st.caption(f"⏰ Generated at {generated_time}")
        with col3:
            date_str = summary_data["generated_at"].strftime("%B %d, %Y")
            st.caption(f"📅 {date_str}")

        st.markdown("---")

        # The main summary content - prominently displayed
        with st.container():
            # Use a nice background container for the summary
            st.markdown(
                """
                <div style="
                    background-color: #f0f2f6;
                    padding: 20px;
                    border-radius: 10px;
                    border-left: 5px solid #ff6b6b;
                    margin: 10px 0;
                ">
                """,
                unsafe_allow_html=True,
            )

            st.markdown(summary_data["summary"])

            st.markdown("</div>", unsafe_allow_html=True)

        # Optional detailed breakdown
        if st.session_state.get("show_details", False):
            st.markdown("---")
            with st.expander("📊 Detailed Article Breakdown", expanded=True):
                render_summary_analytics(recent_articles)

    else:
        # Encourage user to generate summary
        st.info(
            "👆 Click 'Generate Today's Summary' to get a comprehensive overview of today's news in one text!"
        )

        # Show a preview of what's available
        with st.container():
            st.markdown("### 📋 Ready to Summarize")
            st.write(
                f"**{len(recent_articles)} articles** from **{len(set(a.feed_url for a in recent_articles))} active sources** are ready to be summarized into your daily digest."
            )

            # Show top sources preview
            if st.session_state.get("show_details", False):
                feed_counts = {}
                for article in recent_articles:
                    feed_counts[article.feed_url] = (
                        feed_counts.get(article.feed_url, 0) + 1
                    )

                if feed_counts:
                    st.markdown("**Preview - Top Sources:**")
                    sorted_feeds = sorted(
                        feed_counts.items(), key=lambda x: x[1], reverse=True
                    )[:5]
                    for feed_url, count in sorted_feeds:
                        # Try to get feed title or use URL
                        feeds = feed_manager.get_all_feeds()
                        feed_title = next(
                            (f.title or f.url for f in feeds if f.url == feed_url),
                            feed_url,
                        )
                        # Shorten long feed titles
                        if len(feed_title) > 50:
                            feed_title = feed_title[:50] + "..."
                        st.write(f"• {feed_title}: {count} articles")


def generate_comprehensive_daily_summary(
    articles: List[Article], ai_summarizer: AISummarizer
) -> str:
    """
    Generate a comprehensive daily summary of all articles using AI

    Args:
        articles: List of articles to summarize
        ai_summarizer: AI summarizer service instance

    Returns:
        Generated comprehensive daily summary text
    """
    try:
        if not articles:
            return "No articles available for summary."

        # Prepare content from articles for summarization
        articles_content = []

        for article in articles[
            :50
        ]:  # Increased limit to 50 articles for better coverage
            # Use the best available content
            content = ""
            if article.has_summary:
                content = article.summary
            elif article.has_content:
                # Truncate long content to avoid token limits
                content = (
                    article.content[:1000] + "..."
                    if len(article.content) > 1000
                    else article.content
                )
            elif article.description:
                content = article.description
            else:
                content = article.title or "No content available"

            # Format the article entry with source and timestamp
            title = article.title or "Untitled"
            time_info = ""
            if article.created_at:
                time_info = f" ({article.created_at.strftime('%H:%M')})"

            articles_content.append(f"**{title}**{time_info}\n{content}")

        # Combine all articles into one text
        combined_content = "\n\n---\n\n".join(articles_content)

        # Create an enhanced prompt for daily summary focused on cohesive narrative
        prompt = f"""You are a professional news editor creating a comprehensive daily digest. Based on the {len(articles)} articles from active news feeds in the last 24 hours below, create a single, cohesive narrative summary that flows naturally from topic to topic.

Requirements:
1. Write as ONE continuous text (not bullet points or sections)
2. Start with the most significant breaking news or developments
3. Connect related stories and themes naturally in the narrative
4. Include key details, numbers, and quotes where relevant
5. Transition smoothly between different topics and regions
6. End with a brief outlook or context for tomorrow
7. Write in an engaging, journalistic style suitable for an informed reader
8. Aim for 300-500 words

Focus on creating a flowing narrative that gives readers a complete picture of today's news landscape, as if you were briefing someone who's been away and needs to catch up on everything important that happened today.

Articles to synthesize:
{combined_content}

Write a comprehensive daily news summary:"""

        # Generate the summary using the specialized daily summary method
        summary = ai_summarizer.generate_daily_summary(prompt)

        if not summary:
            return (
                "Unable to generate daily summary at this time. Please try again later."
            )

        return summary

    except Exception as e:
        logger.error(f"Error generating comprehensive daily summary: {e}")
        return f"Error generating daily summary: {str(e)}"


def render_summary_analytics(articles: List[Article]) -> None:
    """
    Render a simplified analytics section for the daily summary

    Args:
        articles: List of articles to analyze
    """
    if not articles:
        st.write("No articles to analyze.")
        return

    col1, col2 = st.columns(2)

    with col1:
        st.markdown("**📊 Content Status**")

        # Content status breakdown
        with_content = len([a for a in articles if a.has_content])
        with_summary = len([a for a in articles if a.has_summary])
        complete = len([a for a in articles if a.is_complete])

        st.write(f"• Articles with full content: {with_content}")
        st.write(f"• Articles with AI summary: {with_summary}")
        st.write(f"• Fully processed articles: {complete}")

        # Progress bar
        if articles:
            completion_rate = (complete / len(articles)) * 100
            st.progress(completion_rate / 100)
            st.caption(f"Processing completion: {completion_rate:.1f}%")

    with col2:
        st.markdown("**📡 Top Sources**")

        # Source distribution
        feed_counts = {}
        for article in articles:
            feed_counts[article.feed_url] = feed_counts.get(article.feed_url, 0) + 1

        # Sort and show top 5 sources
        if feed_counts:
            sorted_feeds = sorted(
                feed_counts.items(), key=lambda x: x[1], reverse=True
            )[:5]
            for i, (feed_url, count) in enumerate(sorted_feeds, 1):
                # Shorten URL for display
                display_url = feed_url.replace("https://", "").replace("http://", "")
                if len(display_url) > 30:
                    display_url = display_url[:30] + "..."
                st.write(f"{i}. {display_url}: {count} articles")
        else:
            st.write("No source data available")

    # Time distribution
    st.markdown("**⏰ Timeline**")

    # Group articles by hour
    hourly_counts = {}
    for article in articles:
        if article.created_at:
            hour = article.created_at.hour
            hourly_counts[hour] = hourly_counts.get(hour, 0) + 1

    if hourly_counts:
        # Create a simple text-based timeline
        max_count = max(hourly_counts.values())
        for hour in sorted(hourly_counts.keys()):
            count = hourly_counts[hour]
            bar_length = int((count / max_count) * 20)  # Scale to 20 characters
            bar = "█" * bar_length + "▒" * (20 - bar_length)
            st.write(f"{hour:02d}:00 │{bar}│ {count} articles")
    else:
        st.write("No timeline data available")
