#!/usr/bin/env python3
"""Command-line interface for NBA Game Recommender."""
import argparse
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.core.recommender import GameRecommender


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description='Find the most engaging NBA game from the last week'
    )

    parser.add_argument(
        '-d', '--days',
        type=int,
        default=7,
        help='Number of days to look back (default: 7)'
    )

    parser.add_argument(
        '-t', '--team',
        type=str,
        help='Favorite team abbreviation (e.g., LAL, BOS, GSW)'
    )

    parser.add_argument(
        '-a', '--all',
        action='store_true',
        help='Show all games ranked by engagement score'
    )

    parser.add_argument(
        '-c', '--config',
        type=str,
        default='config.yaml',
        help='Path to configuration file (default: config.yaml)'
    )

    args = parser.parse_args()

    try:
        recommender = GameRecommender(config_path=args.config)

        if args.all:
            # Show all games ranked
            print(f"\n🏀 Fetching NBA games from the last {args.days} days...\n")
            games = recommender.get_all_games_ranked(days=args.days, favorite_team=args.team)

            if not games:
                print("No completed games found in the specified period.")
                return

            print(f"{'='*60}")
            print(f"ALL GAMES RANKED BY ENGAGEMENT")
            print(f"{'='*60}\n")

            for i, result in enumerate(games, 1):
                game = result['game']
                away = game['away_team']
                home = game['home_team']

                print(f"{i}. {away['abbr']} {away['score']} @ {home['score']} {home['abbr']}")
                print(f"   Date: {game['game_date']} | Score: {result['score']:.2f}")
                print(f"   Lead Changes: {result['breakdown']['lead_changes']['count']} | "
                      f"Margin: {result['breakdown']['close_game']['margin']} pts\n")

        else:
            # Show best game only
            best_game = recommender.get_best_game(days=args.days, favorite_team=args.team)

            if not best_game:
                print("No completed games found in the specified period.")
                return

            summary = recommender.format_game_summary(best_game)
            print(summary)

    except FileNotFoundError:
        print(f"Error: Configuration file '{args.config}' not found.")
        sys.exit(1)
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)


if __name__ == '__main__':
    main()
