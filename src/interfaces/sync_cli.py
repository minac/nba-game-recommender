#!/usr/bin/env python3
"""CLI for syncing NBA data to local SQLite database.

This script fetches NBA data from NBA.com via nba_api and stores it locally
to avoid rate limiting issues during normal operation.

Usage:
    uv run python src/interfaces/sync_cli.py           # Full sync (14 days)
    uv run python src/interfaces/sync_cli.py --days 7  # Sync last 7 days
    uv run python src/interfaces/sync_cli.py --status  # Show sync status
"""

import argparse
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

import structlog

from src.api.nba_api_client import NBASyncService
from src.utils.logging_config import setup_logging

log = structlog.get_logger(__name__)


def main():
    parser = argparse.ArgumentParser(
        description="Sync NBA data to local SQLite database",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    # Full sync of last 14 days
    uv run python src/interfaces/sync_cli.py

    # Sync last 7 days only
    uv run python src/interfaces/sync_cli.py --days 7

    # Show current sync status
    uv run python src/interfaces/sync_cli.py --status

    # Sync only standings and star players (fast)
    uv run python src/interfaces/sync_cli.py --metadata-only

    # Force re-sync of games (clears existing game data)
    uv run python src/interfaces/sync_cli.py --force
        """,
    )

    parser.add_argument(
        "--days",
        "-d",
        type=int,
        default=14,
        help="Number of days of games to sync (default: 14)",
    )

    parser.add_argument(
        "--status", "-s", action="store_true", help="Show current sync status and exit"
    )

    parser.add_argument(
        "--metadata-only",
        "-m",
        action="store_true",
        help="Only sync teams, standings, and star players (no games)",
    )

    parser.add_argument(
        "--games-only",
        "-g",
        action="store_true",
        help="Only sync games (assumes teams already synced)",
    )

    parser.add_argument(
        "--force",
        "-f",
        action="store_true",
        help="Force re-sync by clearing existing data first",
    )

    parser.add_argument(
        "--config",
        "-c",
        type=str,
        default="config.yaml",
        help="Path to config file (default: config.yaml)",
    )

    args = parser.parse_args()
    setup_logging()

    try:
        sync_service = NBASyncService(config_path=args.config)

        if args.status:
            log_status(sync_service)
            return

        if args.force:
            log.warning("force_clearing_data")
            sync_service.db.clear_all()

        if args.metadata_only:
            log.info("syncing_metadata")
            results = {
                "teams": sync_service.sync_teams(),
                "standings": sync_service.sync_standings(),
                "star_players": sync_service.sync_star_players(),
            }
        elif args.games_only:
            log.info("syncing_games_only", days=args.days)
            results = {"games": sync_service.sync_games(days=args.days)}
        else:
            log.info("starting_full_sync", days=args.days)
            results = sync_service.sync_all(days=args.days)

        log.info("sync_complete", **results)

        log_status(sync_service)

    except KeyboardInterrupt:
        log.warning("sync_interrupted")
        sys.exit(1)
    except Exception as e:
        log.error("sync_failed", error=str(e))
        sys.exit(1)


def log_status(sync_service: NBASyncService):
    """Log current sync status."""
    status = sync_service.get_sync_status()

    date_range = status.get("games_date_range", {})
    sync_times = {}
    for sync_type in ["teams", "standings", "star_players", "games"]:
        sync_times[sync_type] = status.get(f"last_{sync_type}_sync") or "Never"

    log.info(
        "database_status",
        db_path=status.get("db_path", "N/A"),
        db_size_mb=status.get("db_size_mb", 0),
        teams=status.get("teams_count", 0),
        players=status.get("players_count", 0),
        star_players=status.get("star_players_count", 0),
        games=status.get("games_count", 0),
        game_players=status.get("game_players_count", 0),
        standings=status.get("standings_count", 0),
        date_range_min=date_range.get("min"),
        date_range_max=date_range.get("max"),
        last_syncs=sync_times,
    )


if __name__ == "__main__":
    main()
