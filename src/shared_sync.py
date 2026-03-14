"""
Integration with yt-shared-data: sync analysis results to the shared database.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

from rich.console import Console

try:
    from yt_shared import SharedDatabase, Channel, Video
    SHARED_AVAILABLE = True
except ImportError:
    SHARED_AVAILABLE = False

console = Console()

PROJECT_NAME = "investigator"


def is_available() -> bool:
    """Check if the shared data layer is installed."""
    return SHARED_AVAILABLE


def sync_analysis(analysis: dict) -> int:
    """Sync channel analysis results to the shared database.

    Args:
        analysis: Result dict from ChannelAnalyzer.analyze_channel()

    Returns:
        Number of videos synced.
    """
    if not SHARED_AVAILABLE:
        return 0

    db = SharedDatabase(project_name=PROJECT_NAME)
    ch = analysis["channel"]

    with db.connect() as conn:
        # Upsert channel
        db.upsert_channel(conn, Channel(
            youtube_channel_id=ch["id"],
            title=ch["title"],
            description=ch.get("description", ""),
            subscriber_count=ch.get("subscribers"),
            video_count=ch.get("total_videos"),
            view_count=ch.get("total_views"),
            published_at=ch.get("created_at"),
            last_fetched_at=analysis["meta"]["fetched_at"],
        ))

        # Upsert videos
        videos = analysis.get("videos", [])
        for v in videos:
            db.upsert_video(conn, Video(
                youtube_video_id=v["video_id"],
                title=v["title"],
                youtube_channel_id=ch["id"],
                published_at=v.get("published_at"),
                duration=v.get("duration"),
                view_count=v.get("view_count", 0),
                like_count=v.get("like_count", 0),
                comment_count=v.get("comment_count", 0),
                last_fetched_at=analysis["meta"]["fetched_at"],
            ))

    return len(videos)


def get_cached_channel(identifier: str, max_age_hours: int = 24) -> Optional[dict]:
    """Check if we have recent data for a channel in the shared DB.

    Args:
        identifier: YouTube channel ID (UC...) — must be resolved already.
        max_age_hours: Maximum age of cached data in hours.

    Returns:
        Cached channel dict or None if not found / too stale.
    """
    if not SHARED_AVAILABLE:
        return None

    db = SharedDatabase(project_name=PROJECT_NAME)

    with db.connect() as conn:
        channel = db.get_channel(conn, identifier)
        if not channel or not channel.last_fetched_at:
            return None

        # Check staleness
        fetched = datetime.fromisoformat(channel.last_fetched_at)
        age = datetime.now(timezone.utc) - fetched
        if age.total_seconds() > max_age_hours * 3600:
            return None

        videos = db.get_videos_by_channel(conn, identifier)

    return {
        "channel": channel,
        "videos": videos,
        "cached": True,
    }


def show_lock_warning():
    """Show a warning if another project is using the shared DB."""
    if not SHARED_AVAILABLE:
        return

    db = SharedDatabase(project_name=PROJECT_NAME)
    existing = db.acquire_lock()
    if existing:
        console.print(
            f"\n[yellow][i] Hinweis: Shared DB wird gerade von "
            f"'{existing.project_name}' genutzt (PID {existing.pid}, "
            f"seit {existing.started_at})[/yellow]"
        )
    # Lock is released when the process exits or release_lock() is called


def release_lock():
    """Release our lock on the shared DB."""
    if not SHARED_AVAILABLE:
        return
    db = SharedDatabase(project_name=PROJECT_NAME)
    db.release_lock()


def show_gaps():
    """Show data gaps that other tools could fill."""
    if not SHARED_AVAILABLE:
        return

    db = SharedDatabase(project_name=PROJECT_NAME)
    with db.connect() as conn:
        gaps = db.detect_gaps(conn)
        stats = db.get_stats(conn)

    if stats["channels"] == 0 and stats["videos"] == 0:
        return  # Empty DB, no point showing gaps

    if gaps:
        console.print(f"\n[dim]Shared DB: {stats['channels']} Kanaele, {stats['videos']} Videos[/dim]")
        for gap in gaps:
            if gap.suggested_tool != "Youtube-Investigator":
                console.print(
                    f"[dim]  -> {gap.description}: {gap.entity_count}x "
                    f"(Tipp: {gap.suggested_tool})[/dim]"
                )
