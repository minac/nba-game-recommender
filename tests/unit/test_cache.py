"""Unit tests for DateBasedCache class."""
import pytest
import json
import time
from pathlib import Path
from datetime import datetime, timedelta
from unittest.mock import patch, mock_open
from src.utils.cache import DateBasedCache


class TestDateBasedCache:
    """Test cases for DateBasedCache class."""

    @pytest.fixture
    def cache(self, temp_cache_dir):
        """Create a cache instance with temporary directory."""
        return DateBasedCache(cache_dir=temp_cache_dir, default_ttl_days=30)

    def test_initialization(self, temp_cache_dir):
        """Test cache initializes with correct directory structure."""
        cache = DateBasedCache(cache_dir=temp_cache_dir, default_ttl_days=30)

        assert cache.cache_dir == Path(temp_cache_dir)
        assert cache.default_ttl_days == 30
        assert cache.scoreboard_dir.exists()
        assert cache.game_details_dir.exists()

    def test_initialization_creates_directories(self, temp_cache_dir):
        """Test that cache creates directories if they don't exist."""
        cache_path = Path(temp_cache_dir) / "nested" / "cache"
        cache = DateBasedCache(cache_dir=str(cache_path))

        assert cache.scoreboard_dir.exists()
        assert cache.game_details_dir.exists()

    def test_set_and_get_scoreboard(self, cache):
        """Test caching and retrieving scoreboard data."""
        game_date = "2024-01-15"
        games_data = [
            {'game_id': '001', 'home_team': 'LAL', 'away_team': 'BOS'},
            {'game_id': '002', 'home_team': 'DEN', 'away_team': 'MIL'}
        ]

        # Set cache
        cache.set_scoreboard(game_date, games_data)

        # Get cache
        cached_data = cache.get_scoreboard(game_date)

        assert cached_data is not None
        assert len(cached_data) == 2
        assert cached_data == games_data

    def test_get_scoreboard_cache_miss(self, cache):
        """Test getting scoreboard returns None on cache miss."""
        result = cache.get_scoreboard("2024-01-15")
        assert result is None

    def test_get_scoreboard_expired(self, cache):
        """Test getting scoreboard returns None when cache is expired."""
        game_date = "2024-01-15"
        games_data = [{'game_id': '001'}]

        # Set cache
        cache.set_scoreboard(game_date, games_data)

        # Verify it exists
        assert cache.get_scoreboard(game_date) is not None

        # Try to get with 0 days TTL (immediately expired)
        result = cache.get_scoreboard(game_date, ttl_days=0)
        assert result is None

    def test_set_and_get_game_details(self, cache):
        """Test caching and retrieving game details."""
        game_id = "0022300123"
        details = {
            'lead_changes': 12,
            'star_players_count': 4
        }

        # Set cache
        cache.set_game_details(game_id, details)

        # Get cache
        cached_details = cache.get_game_details(game_id)

        assert cached_details is not None
        assert cached_details == details

    def test_get_game_details_cache_miss(self, cache):
        """Test getting game details returns None on cache miss."""
        result = cache.get_game_details("nonexistent_id")
        assert result is None

    def test_get_game_details_expired(self, cache):
        """Test getting game details returns None when cache is expired."""
        game_id = "0022300123"
        details = {'lead_changes': 10}

        # Set cache
        cache.set_game_details(game_id, details)

        # Verify it exists
        assert cache.get_game_details(game_id) is not None

        # Try to get with 0 days TTL (immediately expired)
        result = cache.get_game_details(game_id, ttl_days=0)
        assert result is None

    def test_clear_all(self, cache):
        """Test clearing all cache."""
        # Add some cache data
        cache.set_scoreboard("2024-01-15", [{'game_id': '001'}])
        cache.set_scoreboard("2024-01-16", [{'game_id': '002'}])
        cache.set_game_details("game1", {'lead_changes': 5})
        cache.set_game_details("game2", {'lead_changes': 8})

        # Clear all
        cache.clear_all()

        # Verify everything is cleared
        assert cache.get_scoreboard("2024-01-15") is None
        assert cache.get_scoreboard("2024-01-16") is None
        assert cache.get_game_details("game1") is None
        assert cache.get_game_details("game2") is None

    def test_clear_expired(self, cache, temp_cache_dir):
        """Test clearing only expired cache files."""
        # Add some cache data
        cache.set_scoreboard("2024-01-15", [{'game_id': '001'}])
        cache.set_game_details("game1", {'lead_changes': 5})

        # Manually set an old timestamp on one file to simulate expiration
        old_file = cache.scoreboard_dir / "2024-01-15.json"
        old_time = (datetime.now() - timedelta(days=40)).timestamp()
        old_file.touch()
        import os
        os.utime(old_file, (old_time, old_time))

        # Clear expired (default TTL is 30 days)
        cache.clear_expired()

        # Old file should be gone
        assert cache.get_scoreboard("2024-01-15") is None

        # Recent file should still exist
        assert cache.get_game_details("game1") is not None

    def test_get_cache_stats(self, cache):
        """Test getting cache statistics."""
        # Add some cache data
        cache.set_scoreboard("2024-01-15", [{'game_id': '001'}])
        cache.set_scoreboard("2024-01-16", [{'game_id': '002'}])
        cache.set_game_details("game1", {'lead_changes': 5})

        stats = cache.get_cache_stats()

        assert stats['scoreboard_entries'] == 2
        assert stats['game_details_entries'] == 1
        assert stats['total_entries'] == 3
        assert stats['total_size_bytes'] > 0
        assert stats['total_size_mb'] >= 0
        assert 'cache_dir' in stats

    def test_get_cache_stats_empty(self, cache):
        """Test getting cache statistics when cache is empty."""
        stats = cache.get_cache_stats()

        assert stats['scoreboard_entries'] == 0
        assert stats['game_details_entries'] == 0
        assert stats['total_entries'] == 0
        assert stats['total_size_bytes'] == 0

    def test_is_cache_valid_nonexistent_file(self, cache):
        """Test _is_cache_valid returns False for nonexistent file."""
        fake_file = cache.scoreboard_dir / "nonexistent.json"
        assert not cache._is_cache_valid(fake_file)

    def test_is_cache_valid_recent_file(self, cache):
        """Test _is_cache_valid returns True for recent file."""
        # Create a cache file
        cache.set_scoreboard("2024-01-15", [{'game_id': '001'}])
        cache_file = cache.scoreboard_dir / "2024-01-15.json"

        assert cache._is_cache_valid(cache_file, ttl_days=30)

    def test_is_cache_valid_custom_ttl(self, cache):
        """Test _is_cache_valid with custom TTL."""
        # Create a cache file
        cache.set_scoreboard("2024-01-15", [{'game_id': '001'}])
        cache_file = cache.scoreboard_dir / "2024-01-15.json"

        # Should be valid with generous TTL
        assert cache._is_cache_valid(cache_file, ttl_days=365)

        # Should be invalid with strict TTL
        assert not cache._is_cache_valid(cache_file, ttl_days=0)

    def test_set_scoreboard_creates_file(self, cache):
        """Test that set_scoreboard creates the cache file."""
        game_date = "2024-01-15"
        games_data = [{'game_id': '001'}]

        cache.set_scoreboard(game_date, games_data)

        cache_file = cache.scoreboard_dir / f"{game_date}.json"
        assert cache_file.exists()

        # Verify content
        with open(cache_file, 'r') as f:
            data = json.load(f)
            assert data == games_data

    def test_set_game_details_creates_file(self, cache):
        """Test that set_game_details creates the cache file."""
        game_id = "0022300123"
        details = {'lead_changes': 12}

        cache.set_game_details(game_id, details)

        cache_file = cache.game_details_dir / f"{game_id}.json"
        assert cache_file.exists()

        # Verify content
        with open(cache_file, 'r') as f:
            data = json.load(f)
            assert data == details

    def test_scoreboard_overwrites_existing_cache(self, cache):
        """Test that set_scoreboard overwrites existing cache."""
        game_date = "2024-01-15"

        # Set initial data
        cache.set_scoreboard(game_date, [{'game_id': '001'}])

        # Overwrite with new data
        new_data = [{'game_id': '002'}, {'game_id': '003'}]
        cache.set_scoreboard(game_date, new_data)

        # Get should return new data
        cached_data = cache.get_scoreboard(game_date)
        assert cached_data == new_data

    def test_game_details_overwrites_existing_cache(self, cache):
        """Test that set_game_details overwrites existing cache."""
        game_id = "0022300123"

        # Set initial data
        cache.set_game_details(game_id, {'lead_changes': 5})

        # Overwrite with new data
        new_details = {'lead_changes': 12, 'star_players_count': 4}
        cache.set_game_details(game_id, new_details)

        # Get should return new data
        cached_details = cache.get_game_details(game_id)
        assert cached_details == new_details

    def test_cache_handles_empty_lists(self, cache):
        """Test that cache handles empty lists properly."""
        game_date = "2024-01-15"
        cache.set_scoreboard(game_date, [])

        cached_data = cache.get_scoreboard(game_date)
        assert cached_data == []

    def test_cache_handles_complex_data(self, cache):
        """Test that cache handles complex nested data structures."""
        game_date = "2024-01-15"
        complex_data = [
            {
                'game_id': '001',
                'teams': {
                    'home': {'name': 'Lakers', 'players': ['LeBron', 'AD']},
                    'away': {'name': 'Celtics', 'players': ['Tatum', 'Brown']}
                },
                'scores': [110, 108]
            }
        ]

        cache.set_scoreboard(game_date, complex_data)
        cached_data = cache.get_scoreboard(game_date)

        assert cached_data == complex_data

    def test_multiple_scoreboards_independent(self, cache):
        """Test that different scoreboard dates are independent."""
        cache.set_scoreboard("2024-01-15", [{'game_id': '001'}])
        cache.set_scoreboard("2024-01-16", [{'game_id': '002'}])

        assert cache.get_scoreboard("2024-01-15") == [{'game_id': '001'}]
        assert cache.get_scoreboard("2024-01-16") == [{'game_id': '002'}]

    def test_multiple_game_details_independent(self, cache):
        """Test that different game details are independent."""
        cache.set_game_details("game1", {'lead_changes': 5})
        cache.set_game_details("game2", {'lead_changes': 10})

        assert cache.get_game_details("game1")['lead_changes'] == 5
        assert cache.get_game_details("game2")['lead_changes'] == 10

    def test_default_ttl_used_when_none(self, cache):
        """Test that default TTL is used when ttl_days is None."""
        game_date = "2024-01-15"
        cache.set_scoreboard(game_date, [{'game_id': '001'}])

        # Should use default TTL (30 days)
        cache_file = cache.scoreboard_dir / f"{game_date}.json"
        assert cache._is_cache_valid(cache_file, ttl_days=None)

    @patch('builtins.open', side_effect=PermissionError("Permission denied"))
    def test_set_scoreboard_handles_write_error(self, mock_file, cache, capsys):
        """Test that set_scoreboard handles write errors gracefully."""
        game_date = "2024-01-15"
        games_data = [{'game_id': '001'}]

        # Should not raise exception
        cache.set_scoreboard(game_date, games_data)

    def test_get_scoreboard_handles_corrupted_file(self, cache):
        """Test that get_scoreboard handles corrupted JSON files."""
        game_date = "2024-01-15"
        cache_file = cache.scoreboard_dir / f"{game_date}.json"

        # Write corrupted JSON
        with open(cache_file, 'w') as f:
            f.write("{ invalid json }")

        # Should return None instead of raising exception
        result = cache.get_scoreboard(game_date)
        assert result is None

    def test_clear_expired_with_custom_ttl(self, cache, temp_cache_dir):
        """Test clearing expired cache with custom TTL."""
        # Add cache data
        cache.set_scoreboard("2024-01-15", [{'game_id': '001'}])

        # Make it old
        old_file = cache.scoreboard_dir / "2024-01-15.json"
        old_time = (datetime.now() - timedelta(days=10)).timestamp()
        import os
        os.utime(old_file, (old_time, old_time))

        # Clear with TTL of 5 days (file is 10 days old, should be cleared)
        cache.clear_expired(ttl_days=5)

        assert cache.get_scoreboard("2024-01-15") is None

    def test_cache_stats_calculates_size_correctly(self, cache):
        """Test that cache stats calculates total size correctly."""
        # Add known-size data
        cache.set_scoreboard("2024-01-15", [{'game_id': '001', 'data': 'x' * 100}])

        stats = cache.get_cache_stats()

        assert stats['total_size_bytes'] > 100  # Should be larger than just the data
        assert stats['total_size_mb'] >= 0

    def test_ensure_directories_error_handling(self, temp_cache_dir):
        """Test that _ensure_directories handles errors gracefully."""
        with patch('pathlib.Path.mkdir', side_effect=OSError("Cannot create directory")):
            # Should not raise exception
            cache = DateBasedCache(cache_dir=temp_cache_dir)
            # Cache object is created but directories may not exist
            assert cache is not None
