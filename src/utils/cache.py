"""Date-based caching utility for NBA game data."""
import json
import os
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, Dict, Any
from src.utils.logger import get_logger

logger = get_logger(__name__)


class DateBasedCache:
    """File-based cache for NBA game data with date-based organization."""

    def __init__(self, cache_dir: str = "/tmp/nba_cache", default_ttl_days: int = 30):
        """
        Initialize the cache.

        Args:
            cache_dir: Base directory for cache storage
            default_ttl_days: Default time-to-live in days for cached items
        """
        self.cache_dir = Path(cache_dir)
        self.default_ttl_days = default_ttl_days

        # Create cache directory structure
        self.scoreboard_dir = self.cache_dir / "scoreboards"
        self.game_details_dir = self.cache_dir / "games"

        self._ensure_directories()

    def _ensure_directories(self):
        """Ensure cache directories exist."""
        try:
            self.scoreboard_dir.mkdir(parents=True, exist_ok=True)
            self.game_details_dir.mkdir(parents=True, exist_ok=True)
            logger.debug(f"Cache directories ready at {self.cache_dir}")
        except Exception as e:
            logger.error(f"Error creating cache directories: {e}")

    def _is_cache_valid(self, cache_file: Path, ttl_days: Optional[int] = None) -> bool:
        """
        Check if a cache file is still valid based on TTL.

        Args:
            cache_file: Path to cache file
            ttl_days: Time-to-live in days (uses default if None)

        Returns:
            True if cache is valid, False otherwise
        """
        if not cache_file.exists():
            return False

        try:
            ttl = ttl_days if ttl_days is not None else self.default_ttl_days
            file_age = datetime.now() - datetime.fromtimestamp(cache_file.stat().st_mtime)
            is_valid = file_age < timedelta(days=ttl)

            if not is_valid:
                logger.debug(f"Cache expired: {cache_file.name} (age: {file_age.days} days)")

            return is_valid
        except Exception as e:
            logger.error(f"Error checking cache validity: {e}")
            return False

    def get_scoreboard(self, game_date: str, ttl_days: Optional[int] = None) -> Optional[list]:
        """
        Get cached scoreboard data for a specific date.

        Args:
            game_date: Date in YYYY-MM-DD format
            ttl_days: Time-to-live in days (uses default if None)

        Returns:
            List of games or None if cache miss
        """
        cache_file = self.scoreboard_dir / f"{game_date}.json"

        if not self._is_cache_valid(cache_file, ttl_days):
            return None

        try:
            with open(cache_file, 'r') as f:
                data = json.load(f)
                logger.info(f"Cache HIT: Scoreboard for {game_date} ({len(data)} games)")
                return data
        except Exception as e:
            logger.error(f"Error reading scoreboard cache for {game_date}: {e}")
            return None

    def set_scoreboard(self, game_date: str, games: list):
        """
        Cache scoreboard data for a specific date.

        Args:
            game_date: Date in YYYY-MM-DD format
            games: List of game dictionaries
        """
        cache_file = self.scoreboard_dir / f"{game_date}.json"

        try:
            with open(cache_file, 'w') as f:
                json.dump(games, f, indent=2)
            logger.info(f"Cache WRITE: Scoreboard for {game_date} ({len(games)} games)")
        except Exception as e:
            logger.error(f"Error writing scoreboard cache for {game_date}: {e}")

    def get_game_details(self, game_id: str, ttl_days: Optional[int] = None) -> Optional[Dict[str, Any]]:
        """
        Get cached game details (lead changes, star players).

        Args:
            game_id: NBA game ID
            ttl_days: Time-to-live in days (uses default if None)

        Returns:
            Dictionary with game details or None if cache miss
        """
        cache_file = self.game_details_dir / f"{game_id}.json"

        if not self._is_cache_valid(cache_file, ttl_days):
            return None

        try:
            with open(cache_file, 'r') as f:
                data = json.load(f)
                logger.debug(f"Cache HIT: Game details for {game_id}")
                return data
        except Exception as e:
            logger.error(f"Error reading game details cache for {game_id}: {e}")
            return None

    def set_game_details(self, game_id: str, details: Dict[str, Any]):
        """
        Cache game details (lead changes, star players).

        Args:
            game_id: NBA game ID
            details: Dictionary with game details
        """
        cache_file = self.game_details_dir / f"{game_id}.json"

        try:
            with open(cache_file, 'w') as f:
                json.dump(details, f, indent=2)
            logger.debug(f"Cache WRITE: Game details for {game_id}")
        except Exception as e:
            logger.error(f"Error writing game details cache for {game_id}: {e}")

    def clear_expired(self, ttl_days: Optional[int] = None):
        """
        Remove expired cache files.

        Args:
            ttl_days: Time-to-live in days (uses default if None)
        """
        ttl = ttl_days if ttl_days is not None else self.default_ttl_days
        cutoff_time = datetime.now() - timedelta(days=ttl)
        removed_count = 0

        try:
            for cache_dir in [self.scoreboard_dir, self.game_details_dir]:
                for cache_file in cache_dir.glob("*.json"):
                    file_time = datetime.fromtimestamp(cache_file.stat().st_mtime)
                    if file_time < cutoff_time:
                        cache_file.unlink()
                        removed_count += 1

            if removed_count > 0:
                logger.info(f"Cleared {removed_count} expired cache files")
        except Exception as e:
            logger.error(f"Error clearing expired cache: {e}")

    def get_cache_stats(self) -> Dict[str, Any]:
        """
        Get cache statistics.

        Returns:
            Dictionary with cache statistics
        """
        try:
            scoreboard_count = len(list(self.scoreboard_dir.glob("*.json")))
            game_details_count = len(list(self.game_details_dir.glob("*.json")))

            # Calculate total cache size
            total_size = 0
            for cache_dir in [self.scoreboard_dir, self.game_details_dir]:
                for cache_file in cache_dir.glob("*.json"):
                    total_size += cache_file.stat().st_size

            return {
                'scoreboard_entries': scoreboard_count,
                'game_details_entries': game_details_count,
                'total_entries': scoreboard_count + game_details_count,
                'total_size_bytes': total_size,
                'total_size_mb': round(total_size / (1024 * 1024), 2),
                'cache_dir': str(self.cache_dir)
            }
        except Exception as e:
            logger.error(f"Error getting cache stats: {e}")
            return {}

    def clear_all(self):
        """Clear all cached data."""
        try:
            removed_count = 0
            for cache_dir in [self.scoreboard_dir, self.game_details_dir]:
                for cache_file in cache_dir.glob("*.json"):
                    cache_file.unlink()
                    removed_count += 1

            logger.info(f"Cleared all cache ({removed_count} files)")
        except Exception as e:
            logger.error(f"Error clearing cache: {e}")
