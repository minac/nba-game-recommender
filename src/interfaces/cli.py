#!/usr/bin/env python3
"""Command-line interface for NBA Game Recommender."""
import argparse
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.services.game_service import GameService
from src.core.recommender import GameRecommender
from src.utils.logger import get_logger

logger = get_logger(__name__)


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

    parser.add_argument(
        '-e', '--explain',
        action='store_true',
        help='Show detailed scoring explanation with numbers and reasoning'
    )

    parser.add_argument(
        '--list-stars',
        action='store_true',
        help='List all current star players tracked by the system'
    )

    parser.add_argument(
        '--top-teams',
        action='store_true',
        help='List current top 5 teams by win percentage'
    )

    args = parser.parse_args()

    logger.info(f"CLI invoked: days={args.days}, team={args.team}, show_all={args.all}, explain={args.explain}")

    try:
        # Create recommender for config loading (for now, to maintain compatibility)
        recommender = GameRecommender(config_path=args.config)
        # Create shared game service
        game_service = GameService(recommender=recommender)
        logger.info(f"Loaded configuration from {args.config}")

        # Handle --list-stars command
        if args.list_stars:
            star_players = game_service.star_players
            data_source = game_service.config.get('data_source', 'nba_stats')

            print(f"\n{'='*60}")
            print(f"⭐ CURRENT STAR PLAYERS")
            print(f"{'='*60}")
            print(f"Data Source: {data_source}")
            print(f"Total Players: {len(star_players)}")
            print(f"{'='*60}\n")

            # Sort players alphabetically for better readability
            sorted_players = sorted(star_players)

            for i, player in enumerate(sorted_players, 1):
                print(f"{i:2d}. {player}")

            print(f"\n{'='*60}")
            print(f"Note: Star players are weighted at {game_service.star_power_weight} points each")
            print(f"      in the engagement scoring algorithm.")
            print(f"{'='*60}\n")
            return

        # Handle --top-teams command
        if args.top_teams:
            top_teams = game_service.top_teams
            data_source = game_service.config.get('data_source', 'nba_stats')

            print(f"\n{'='*60}")
            print(f"🏆 TOP 5 TEAMS BY WIN PERCENTAGE")
            print(f"{'='*60}")
            print(f"Data Source: {data_source}")
            print(f"Total Teams: {len(top_teams)}")
            print(f"{'='*60}\n")

            # Sort teams alphabetically for better readability
            sorted_teams = sorted(top_teams)

            for i, team in enumerate(sorted_teams, 1):
                print(f"{i}. {team}")

            print(f"\n{'='*60}")
            print(f"Note: Top 5 teams receive a {game_service.top5_team_bonus} point bonus")
            print(f"      in the engagement scoring algorithm.")
            print(f"{'='*60}\n")
            return

        if args.all:
            # Show all games ranked
            print(f"\n🏀 Fetching NBA games from the last {args.days} days...\n")

            # Use shared service (handles validation and error handling)
            response = game_service.get_all_games_ranked(days=args.days, favorite_team=args.team)

            if not response['success']:
                error_code = response.get('error_code')
                error_message = response.get('error', 'Unknown error')
                logger.warning(f"Error getting games: {error_message}")
                print(f"Error: {error_message}")
                if error_code == 'VALIDATION_ERROR':
                    sys.exit(1)
                return

            games = response['data']

            if not games:
                logger.warning("No games found for the specified criteria")
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

                if args.explain:
                    # Show detailed breakdown
                    print(f"   {game_service.format_score_explanation(result)}")
                else:
                    print(f"   Lead Changes: {result['breakdown']['lead_changes']['count']} | "
                          f"Margin: {result['breakdown']['close_game']['margin']} pts\n")

        else:
            # Show best game only
            # Use shared service (handles validation and error handling)
            response = game_service.get_best_game(days=args.days, favorite_team=args.team)

            if not response['success']:
                error_code = response.get('error_code')
                error_message = response.get('error', 'Unknown error')
                logger.warning(f"Error getting best game: {error_message}")
                if error_code == 'NO_GAMES':
                    print("No completed games found in the specified period.")
                else:
                    print(f"Error: {error_message}")
                    if error_code == 'VALIDATION_ERROR':
                        sys.exit(1)
                return

            best_game = response['data']
            logger.info("Successfully retrieved best game recommendation")
            summary = game_service.format_game_summary(best_game, explain=args.explain)
            print(summary)

    except FileNotFoundError:
        logger.error(f"Configuration file '{args.config}' not found")
        print(f"Error: Configuration file '{args.config}' not found.")
        sys.exit(1)
    except Exception as e:
        logger.error(f"CLI error: {e}", exc_info=True)
        print(f"Error: {e}")
        sys.exit(1)


if __name__ == '__main__':
    main()
