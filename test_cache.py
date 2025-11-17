#!/usr/bin/env python
"""Quick test script to verify the cache implementation."""
import sys
import time
from src.utils.cache import DateBasedCache
from datetime import datetime

def test_cache():
    """Test the date-based cache functionality."""
    print("=" * 60)
    print("Testing Date-Based Cache Implementation")
    print("=" * 60)

    # Initialize cache
    cache = DateBasedCache(cache_dir="/tmp/nba_cache_test", default_ttl_days=30)
    print(f"\n✓ Cache initialized at: {cache.cache_dir}")

    # Test 1: Scoreboard cache
    print("\n[Test 1: Scoreboard Cache]")
    test_date = "2025-01-15"
    test_games = [
        {
            'game_id': '0022400123',
            'game_date': test_date,
            'home_team': {'name': 'Lakers', 'abbr': 'LAL', 'score': 110},
            'away_team': {'name': 'Celtics', 'abbr': 'BOS', 'score': 108}
        }
    ]

    # Write to cache
    cache.set_scoreboard(test_date, test_games)
    print(f"✓ Wrote scoreboard for {test_date}")

    # Read from cache
    cached_games = cache.get_scoreboard(test_date)
    if cached_games and len(cached_games) == 1:
        print(f"✓ Cache HIT: Retrieved {len(cached_games)} game(s)")
        print(f"  Game: {cached_games[0]['away_team']['abbr']} @ {cached_games[0]['home_team']['abbr']}")
    else:
        print("✗ Cache MISS: Could not retrieve games")
        return False

    # Test 2: Game details cache
    print("\n[Test 2: Game Details Cache]")
    test_game_id = "0022400123"
    test_details = {
        'lead_changes': 15,
        'star_players_count': 4
    }

    # Write to cache
    cache.set_game_details(test_game_id, test_details)
    print(f"✓ Wrote game details for {test_game_id}")

    # Read from cache
    cached_details = cache.get_game_details(test_game_id)
    if cached_details:
        print(f"✓ Cache HIT: Retrieved game details")
        print(f"  Lead changes: {cached_details['lead_changes']}")
        print(f"  Star players: {cached_details['star_players_count']}")
    else:
        print("✗ Cache MISS: Could not retrieve game details")
        return False

    # Test 3: Cache stats
    print("\n[Test 3: Cache Statistics]")
    stats = cache.get_cache_stats()
    print(f"✓ Scoreboard entries: {stats['scoreboard_entries']}")
    print(f"✓ Game details entries: {stats['game_details_entries']}")
    print(f"✓ Total size: {stats['total_size_mb']} MB")

    # Test 4: Cache miss for non-existent data
    print("\n[Test 4: Cache Miss Handling]")
    missing_games = cache.get_scoreboard("1999-01-01")
    if missing_games is None:
        print("✓ Correctly returned None for cache miss")
    else:
        print("✗ Should have returned None for cache miss")
        return False

    # Clean up test cache
    cache.clear_all()
    print("\n✓ Cleaned up test cache")

    print("\n" + "=" * 60)
    print("All tests passed! ✓")
    print("=" * 60)
    return True

if __name__ == "__main__":
    try:
        success = test_cache()
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"\n✗ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
