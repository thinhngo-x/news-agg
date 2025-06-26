"""
La Une (Front Page) UI component for the News Aggregator.

This module provides the user interface for displaying a daily summary
of all news articles fetched in the last 24 hours.
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

    Args:
        feed_manager: Feed manager service instance
        ai_summarizer: AI summarizer service instance
        config: Configuration manager instance
    """
    st.header("📰 La Une - Daily News Summary")
    st.subheader("Today's News at a Glance")

    # Get recent articles (last 24 hours)
    recent_articles = feed_manager.get_recent_articles(hours=24)

    if not recent_articles:
        st.info(
            "🔍 No articles found in the last 24 hours. Try updating your feeds first!"
        )
        if st.button("🔄 Update All Feeds"):
            with st.spinner("Updating feeds..."):
                results = feed_manager.update_all_feeds()
                st.success(
                    f"Found {results['new_articles']} new articles from {results['total_feeds']} feeds"
                )
                st.rerun()
        return

    # Display basic metrics
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

    col1, col2 = st.columns([3, 1])

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
                    }
                    st.success("Daily summary generated!")
                    st.rerun()
                else:
                    st.error("Failed to generate daily summary")

    with col2:
        if st.button("� Refresh", use_container_width=True):
            # Clear cached summary to force regeneration
            if daily_summary_key in st.session_state:
                del st.session_state[daily_summary_key]
            st.rerun()

    # Display the daily summary
    if daily_summary_key in st.session_state:
        summary_data = st.session_state[daily_summary_key]

        # Summary metadata
        col1, col2 = st.columns([3, 1])
        with col1:
            st.caption(f"� Summary based on {summary_data['article_count']} articles")
        with col2:
            generated_time = summary_data["generated_at"].strftime("%H:%M")
            st.caption(f"⏰ Generated at {generated_time}")

        # The main summary content
        st.markdown("### 🌟 Today's News Summary")

        # Display the summary in a nice container
        with st.container():
            st.markdown(summary_data["summary"])

        st.markdown("---")

        # Optional: Show quick stats toggle
        with st.expander("📊 View Article Breakdown"):
            render_summary_analytics(recent_articles)

    else:
        # Encourage user to generate summary
        st.info(
            "👆 Click 'Generate Today's Summary' to get a comprehensive overview of today's news!"
        )

        # Show a preview of what's available
        st.markdown("### 📋 Available Articles")
        st.write(
            f"Ready to summarize **{len(recent_articles)} articles** from **{len(set(a.feed_url for a in recent_articles))} sources** published in the last 24 hours."
        )

        # Show top sources
        feed_counts = {}
        for article in recent_articles:
            feed_counts[article.feed_url] = feed_counts.get(article.feed_url, 0) + 1

        if feed_counts:
            st.markdown("**Top Sources:**")
            sorted_feeds = sorted(
                feed_counts.items(), key=lambda x: x[1], reverse=True
            )[:5]
            for feed_url, count in sorted_feeds:
                # Try to get feed title or use URL
                feeds = feed_manager.get_all_feeds()
                feed_title = next(
                    (f.title or f.url for f in feeds if f.url == feed_url), feed_url
                )
                st.write(f"• {feed_title}: {count} articles")
            with st.spinner("Generating daily summary..."):
                daily_summary = generate_comprehensive_daily_summary(
                    recent_articles, ai_summarizer
                )
                if daily_summary:
                    st.session_state.daily_summary = daily_summary
                    st.success("Daily summary generated!")
                else:
                    st.error("Failed to generate daily summary")

    with col3:
        if st.button("📊 View Analytics"):
            show_analytics = not st.session_state.get("show_analytics", False)
            st.session_state.show_analytics = show_analytics

    # Display daily summary if available
    if "daily_summary" in st.session_state:
        st.subheader("🌟 Daily Summary")
        st.markdown("---")
        summary_container = st.container()
        with summary_container:
            st.markdown(st.session_state.daily_summary)

            # Add timestamp
            st.caption(f"Generated on {datetime.now().strftime('%H:%M:%S')}")

            # Clear summary button
            if st.button("🗑️ Clear Summary"):
                del st.session_state.daily_summary
                st.rerun()

        st.markdown("---")

    # Display analytics if requested
    if st.session_state.get("show_analytics", False):
        render_summary_analytics(recent_articles)


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
            :30
        ]:  # Limit to first 30 articles to avoid token limits
            # Use the best available content
            content = ""
            if article.has_summary:
                content = article.summary
            elif article.has_content:
                # Truncate long content to avoid token limits
                content = (
                    article.content[:800] + "..."
                    if len(article.content) > 800
                    else article.content
                )
            elif article.description:
                content = article.description
            else:
                content = article.title or "No content available"

            # Format the article entry
            title = article.title or "Untitled"
            articles_content.append(f"**{title}**\n{content}")

        # Combine all articles into one text
        combined_content = "\n\n---\n\n".join(articles_content)

        # Create a comprehensive prompt for daily summary
        prompt = f"""Create a comprehensive daily news summary based on the following {len(articles)} articles from the last 24 hours.

Please provide:
1. A brief executive summary (2-3 sentences) highlighting the most important developments
2. Key themes and trends identified across all articles
3. Major breaking news or significant events
4. Notable developments by category/topic
5. Important updates that readers should be aware of

Focus on synthesizing information rather than listing individual articles. Organize the content in a clear, engaging format that gives readers a complete picture of today's news landscape.

Articles to summarize:
{combined_content}

Please create a well-structured, comprehensive summary that captures the essence of today's news."""

        # Generate the summary using AI
        summary = ai_summarizer.generate_summary(prompt)

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

    # Feed distribution
    st.subheader("📡 Articles by Feed")
    feed_distribution = {}
    for article in articles:
        # Get feed title or use URL as fallback
        feed_key = article.feed_url
        feed_distribution[feed_key] = feed_distribution.get(feed_key, 0) + 1

    if feed_distribution:
        # Sort by count and show top 10
        sorted_feeds = sorted(
            feed_distribution.items(), key=lambda x: x[1], reverse=True
        )[:10]
        feed_chart_data = {feed: count for feed, count in sorted_feeds}
        st.bar_chart(feed_chart_data)

    # Content status
    st.subheader("📋 Content Status")
    status_counts = {
        "With Content": len([a for a in articles if a.has_content]),
        "With Summary": len([a for a in articles if a.has_summary]),
        "Complete": len([a for a in articles if a.is_complete]),
        "Pending": len(
            [a for a in articles if not a.has_content and not a.has_summary]
        ),
    }

    col1, col2, col3, col4 = st.columns(4)
    cols = [col1, col2, col3, col4]

    for i, (status, count) in enumerate(status_counts.items()):
        with cols[i]:
            st.metric(status, count)


def render_articles_by_category(
    articles: List[Article], feed_manager: FeedManager
) -> None:
    """
    Render articles grouped by feed/category

    Args:
        articles: List of articles to display
        feed_manager: Feed manager service instance
    """
    st.subheader("📰 Articles by Feed")

    # Group articles by feed
    articles_by_feed = {}
    for article in articles:
        feed_url = article.feed_url
        if feed_url not in articles_by_feed:
            articles_by_feed[feed_url] = []
        articles_by_feed[feed_url].append(article)

    # Get feed information
    feeds = feed_manager.get_all_feeds()
    feed_info = {feed.url: feed for feed in feeds}

    # Display articles by feed
    for feed_url, feed_articles in articles_by_feed.items():
        feed = feed_info.get(feed_url)
        feed_title = feed.title if feed else feed_url

        # Sort articles by creation time (newest first)
        feed_articles.sort(key=lambda x: x.created_at or datetime.min, reverse=True)

        with st.expander(
            f"📡 {feed_title} ({len(feed_articles)} articles)", expanded=True
        ):
            for article in feed_articles[:10]:  # Show first 10 articles per feed
                render_article_card(article)


def render_article_card(article: Article) -> None:
    """
    Render a single article card

    Args:
        article: Article to display
    """
    # Article container
    with st.container():
        # Title with link
        title = article.title or "Untitled Article"
        if article.link:
            st.markdown(f"**[{title}]({article.link})**")
        else:
            st.markdown(f"**{title}**")

        # Article info
        col1, col2, col3 = st.columns([2, 1, 1])

        with col1:
            if article.created_at:
                time_ago = datetime.now() - article.created_at
                if time_ago.days > 0:
                    time_str = f"{time_ago.days}d ago"
                elif time_ago.seconds > 3600:
                    time_str = f"{time_ago.seconds // 3600}h ago"
                else:
                    time_str = f"{time_ago.seconds // 60}m ago"
                st.caption(f"⏰ {time_str}")

        with col2:
            if article.has_content:
                st.caption("📝 Content ✅")
            else:
                st.caption("📝 Content ❌")

        with col3:
            if article.has_summary:
                st.caption("🤖 Summary ✅")
            else:
                st.caption("🤖 Summary ❌")

        # Show description or summary
        if article.has_summary:
            with st.expander("🤖 AI Summary"):
                st.write(article.summary)
        elif article.description:
            description = article.description
            if len(description) > 200:
                description = description[:200] + "..."
            st.caption(description)

        st.markdown("---")
