"""
Article display UI components for the News Aggregator application.

This module provides Streamlit components for displaying and managing articles.
"""

import streamlit as st
from typing import List, TYPE_CHECKING

if TYPE_CHECKING:
    from ..core.models import Article


def render_article_display(articles: List["Article"]) -> None:
    """
    Render article display interface

    Args:
        articles: List of articles to display
    """

    if not articles:
        st.info("No articles to display.")
        return

    st.header(f"📰 Latest Articles ({len(articles)})")

    for article in articles:
        with st.expander(f"📄 {article.title}", expanded=False):
            if article.link:
                st.markdown(f"**[Read Full Article]({article.link})**")

            if article.description:
                st.write("**Description:**")
                st.write(article.description)

            if article.content:
                st.write("**Content:**")
                st.write(
                    article.content[:500] + "..."
                    if len(article.content) > 500
                    else article.content
                )

            if article.summary:
                st.write("**AI Summary:**")
                st.info(article.summary)

            # Article metadata
            col1, col2, col3 = st.columns(3)
            with col1:
                if article.published:
                    st.caption(f"Published: {article.published}")
            with col2:
                if article.feed_url:
                    st.caption(f"Source: {article.feed_url}")
            with col3:
                st.caption(f"Status: {article.status.value}")
