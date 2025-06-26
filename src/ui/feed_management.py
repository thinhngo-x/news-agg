"""
Feed management UI components for the News Aggregator application.

This module provides Streamlit components for managing RSS feeds including
adding, editing, deleting, and viewing feed statistics.
"""

import streamlit as st
from typing import TYPE_CHECKING

from ..core.models import FeedStatus

if TYPE_CHECKING:
    from ..services.feed_manager import FeedManager


def render_feed_management_ui(feed_manager: "FeedManager") -> None:
    """
    Render comprehensive feed management interface

    Args:
        feed_manager: FeedManager instance for feed operations
    """

    st.header("🗂️ Feed Management")

    # Tabs for different feed operations
    tab1, tab2, tab3, tab4 = st.tabs(
        ["📋 All Feeds", "➕ Add Feed", "📊 Statistics", "🗑️ Deleted Feeds"]
    )

    with tab1:
        render_feeds_list(feed_manager)

    with tab2:
        render_add_feed_ui(feed_manager)

    with tab3:
        render_feed_statistics(feed_manager)

    with tab4:
        render_deleted_feeds(feed_manager)


def render_feeds_list(feed_manager: "FeedManager") -> None:
    """
    Render list of active feeds with edit/delete options

    Args:
        feed_manager: FeedManager instance for feed operations
    """

    feeds = feed_manager.get_all_feeds(include_inactive=False)

    if not feeds:
        st.info("No active feeds found. Add some feeds to get started!")
        return

    st.subheader(f"Active Feeds ({len(feeds)})")

    # Bulk operations
    col1, col2, col3 = st.columns(3)
    with col1:
        if st.button("🔄 Update All Feeds"):
            feed_ids = [feed.id for feed in feeds if feed.id]
            with st.spinner("Updating all feeds..."):
                results = feed_manager.bulk_update_feeds(feed_ids)
                st.success(
                    f"Updated {results['updated']} feeds. Found {results['new_articles']} new articles."
                )
                if results["errors"] > 0:
                    st.warning(f"{results['errors']} feeds had errors")

    # Display feeds
    for feed in feeds:
        with st.expander(f"📡 {feed.title or feed.url}", expanded=False):
            col1, col2 = st.columns([3, 1])

            with col1:
                st.write(f"**URL:** {feed.url}")
                if feed.description:
                    st.write(f"**Description:** {feed.description}")
                st.caption(f"Created: {feed.created_at}")
                if feed.last_updated:
                    st.caption(f"Last Updated: {feed.last_updated}")

            with col2:
                # Edit button
                if st.button("✏️ Edit", key=f"edit_{feed.id}"):
                    st.session_state[f"editing_feed_{feed.id}"] = True

                # Delete button
                if st.button("🗑️ Delete", key=f"delete_{feed.id}", type="secondary"):
                    if feed.id is not None and feed_manager.delete_feed(feed.id):
                        st.success("Feed deleted successfully!")
                        st.rerun()
                    else:
                        st.error("Failed to delete feed")

            # Edit form (if editing)
            if st.session_state.get(f"editing_feed_{feed.id}", False):
                with st.form(f"edit_form_{feed.id}"):
                    st.write("**Edit Feed Information**")
                    new_title = st.text_input("Title", value=feed.title or "")
                    new_description = st.text_area(
                        "Description", value=feed.description or ""
                    )

                    col1, col2 = st.columns(2)
                    with col1:
                        if st.form_submit_button("💾 Save Changes"):
                            if feed.id is not None and feed_manager.update_feed(
                                feed.id, new_title, new_description
                            ):
                                st.success("Feed updated successfully!")
                                st.session_state[f"editing_feed_{feed.id}"] = False
                                st.rerun()
                            else:
                                st.error("Failed to update feed")

                    with col2:
                        if st.form_submit_button("❌ Cancel"):
                            st.session_state[f"editing_feed_{feed.id}"] = False
                            st.rerun()

            # Feed statistics
            if feed.id:
                stats = feed_manager.get_feed_statistics(feed.id)
                if stats:
                    col1, col2, col3 = st.columns(3)
                    with col1:
                        st.metric("Total Articles", stats.get("total_articles", 0))
                    with col2:
                        st.metric("With Content", stats.get("articles_with_content", 0))
                    with col3:
                        st.metric("With Summary", stats.get("articles_with_summary", 0))


def render_add_feed_ui(feed_manager: "FeedManager") -> None:
    """
    Render add new feed interface

    Args:
        feed_manager: FeedManager instance for feed operations
    """

    st.subheader("Add New RSS Feed")

    with st.form("add_feed_form"):
        feed_url = st.text_input(
            "Feed URL *",
            placeholder="https://example.com/feed.xml",
            help="Enter the RSS/Atom feed URL",
        )

        feed_title = st.text_input(
            "Feed Title (Optional)", placeholder="Will be auto-detected if not provided"
        )

        feed_description = st.text_area(
            "Description (Optional)", placeholder="Brief description of the feed"
        )

        # Validate URL button
        col1, col2 = st.columns(2)

        with col1:
            validate_clicked = st.form_submit_button("🔍 Validate Feed")

        with col2:
            add_clicked = st.form_submit_button("➕ Add Feed", type="primary")

        if validate_clicked and feed_url:
            with st.spinner("Validating feed..."):
                validation = feed_manager.validate_feed_url(feed_url)

                if validation["valid"]:
                    st.success("✅ Feed is valid!")
                    st.info(f"**Title:** {validation.get('title', 'N/A')}")
                    st.info(f"**Entries found:** {validation.get('entry_count', 0)}")
                    if validation.get("latest_entry"):
                        st.info(f"**Latest entry:** {validation['latest_entry']}")
                else:
                    st.error(
                        f"❌ Feed validation failed: {validation.get('error', 'Unknown error')}"
                    )

        if add_clicked and feed_url:
            with st.spinner("Adding feed..."):
                if feed_manager.add_feed(feed_url, feed_title, feed_description):
                    st.success("✅ Feed added successfully!")
                    st.rerun()
                else:
                    st.error(
                        "❌ Failed to add feed. It may already exist or be invalid."
                    )


def render_feed_statistics(feed_manager: "FeedManager") -> None:
    """
    Render overall feed statistics

    Args:
        feed_manager: FeedManager instance for feed operations
    """

    st.subheader("Feed Statistics Overview")

    feeds = feed_manager.get_all_feeds(include_inactive=False)

    if not feeds:
        st.info("No feeds to show statistics for.")
        return

    # Overall metrics
    total_feeds = len(feeds)
    total_articles = sum(
        feed_manager.get_feed_statistics(feed.id).get("total_articles", 0)
        for feed in feeds
        if feed.id
    )

    col1, col2 = st.columns(2)
    with col1:
        st.metric("Total Active Feeds", total_feeds)
    with col2:
        st.metric("Total Articles", total_articles)

    # Individual feed statistics
    st.subheader("Per-Feed Statistics")

    for feed in feeds:
        if feed.id:
            stats = feed_manager.get_feed_statistics(feed.id)
            if stats:
                with st.expander(
                    f"📊 {stats.get('feed_title', 'Unknown Feed')}", expanded=False
                ):
                    col1, col2, col3, col4 = st.columns(4)

                    with col1:
                        st.metric("Articles", stats.get("total_articles", 0))
                    with col2:
                        st.metric("With Content", stats.get("articles_with_content", 0))
                    with col3:
                        st.metric("With Summary", stats.get("articles_with_summary", 0))
                    with col4:
                        completion_rate = 0
                        if stats.get("total_articles", 0) > 0:
                            completion_rate = round(
                                (
                                    stats.get("articles_with_summary", 0)
                                    / stats.get("total_articles", 1)
                                )
                                * 100,
                                1,
                            )
                        st.metric("Summary Rate", f"{completion_rate}%")

                    if stats.get("latest_article"):
                        st.caption(f"Latest article: {stats['latest_article']}")


def render_deleted_feeds(feed_manager: "FeedManager") -> None:
    """
    Render interface for managing deleted feeds

    Args:
        feed_manager: FeedManager instance for feed operations
    """

    st.subheader("Deleted Feeds")

    deleted_feeds = feed_manager.get_all_feeds(include_inactive=True)
    deleted_feeds = [feed for feed in deleted_feeds if feed.status != FeedStatus.ACTIVE]

    if not deleted_feeds:
        st.info("No deleted feeds found.")
        return

    st.warning(f"Found {len(deleted_feeds)} deleted feed(s)")

    for feed in deleted_feeds:
        with st.expander(f"🗑️ {feed.title or feed.url}", expanded=False):
            st.write(f"**URL:** {feed.url}")
            if feed.description:
                st.write(f"**Description:** {feed.description}")
            st.caption(f"Created: {feed.created_at}")

            col1, col2 = st.columns(2)

            with col1:
                if st.button("♻️ Restore", key=f"restore_{feed.id}"):
                    if feed.id is not None and feed_manager.restore_feed(feed.id):
                        st.success("Feed restored successfully!")
                        st.rerun()
                    else:
                        st.error("Failed to restore feed")

            with col2:
                if st.button(
                    "🗑️ Delete Permanently",
                    key=f"perm_delete_{feed.id}",
                    type="secondary",
                ):
                    st.warning(
                        "⚠️ This will permanently delete the feed and ALL its articles!"
                    )
                    if st.button("Confirm Delete", key=f"confirm_delete_{feed.id}"):
                        if feed.id is not None and feed_manager.permanently_delete_feed(
                            feed.id
                        ):
                            st.success("Feed permanently deleted!")
                            st.rerun()
                        else:
                            st.error("Failed to delete feed")
