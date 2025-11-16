#!/usr/bin/env python3
"""Test script for Balldontlie API integration."""

from src.api.balldontlie_client import BalldontlieClient
from datetime import datetime


def test_balldontlie_client():
    """Test the Balldontlie API client."""
    print("="*60)
    print("Testing Balldontlie API Integration")
    print("="*60)
    print()

    try:
        # Initialize client
        print("1. Initializing Balldontlie client...")
        client = BalldontlieClient()
        print("✓ Client initialized successfully")
        print()

        # Test fetching games
        print("2. Fetching games from the last 7 days...")
        games = client.get_games_last_n_days(days=7)
        print(f"✓ Successfully fetched {len(games)} completed games")
        print()

        # Display sample game if available
        if games:
            print("3. Sample game data:")
            game = games[0]
            print(f"   Game ID: {game['game_id']}")
            print(f"   Date: {game['game_date']}")
            print(f"   {game['away_team']['name']} @ {game['home_team']['name']}")
            print(f"   Score: {game['away_team']['abbr']} {game['away_team']['score']} - {game['home_team']['score']} {game['home_team']['abbr']}")
            print(f"   Total Points: {game['total_points']}")
            print(f"   Final Margin: {game['final_margin']}")
            print(f"   Lead Changes: {game['lead_changes']} (Note: Not available in Balldontlie API)")
            print(f"   Star Players: {game['star_players_count']}")
            print()

        # Test top 5 teams
        print("4. Fetching top 5 teams...")
        top_teams = client.TOP_5_TEAMS
        print(f"✓ Top 5 teams: {', '.join(sorted(top_teams))}")
        print()

        # Test star players
        print("5. Fetching star players list...")
        star_players = client.STAR_PLAYERS
        print(f"✓ Star players count: {len(star_players)}")
        print(f"   Sample: {', '.join(list(star_players)[:5])}...")
        print()

        print("="*60)
        print("✓ All tests passed successfully!")
        print("="*60)

    except Exception as e:
        print(f"✗ Error: {e}")
        import traceback
        traceback.print_exc()
        return False

    return True


if __name__ == "__main__":
    success = test_balldontlie_client()
    exit(0 if success else 1)
