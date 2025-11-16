"""NBA Game Recommender Engine."""
from typing import List, Dict, Optional
from src.api.nba_client import NBAClient
from src.api.balldontlie_client import BalldontlieClient
from src.core.game_scorer import GameScorer
import yaml

from src.utils.logger import get_logger

logger = get_logger(__name__)


class GameRecommender:
    """Recommends the most engaging NBA game from recent games."""

    def __init__(self, config_path: str = 'config.yaml'):
        """
        Initialize the game recommender.

        Args:
            config_path: Path to configuration file
        """
        with open(config_path, 'r') as f:
            self.config = yaml.safe_load(f)

        # Determine which data source to use
        data_source = self.config.get('data_source', 'nba_stats')

        if data_source == 'balldontlie':
            print("Using Balldontlie API as data source")
            self.nba_client = BalldontlieClient()
        else:
            print("Using NBA Stats API as data source")
            self.nba_client = NBAClient()

        self.scorer = GameScorer(self.config.get('scoring', {}))
        self.favorite_team = self.config.get('favorite_team')

    def get_best_game(self, days: int = 7, favorite_team: Optional[str] = None) -> Optional[Dict]:
        """
        Get the best game to watch from the last N days.

        Args:
            days: Number of days to look back
            favorite_team: Optional favorite team (overrides config)

        Returns:
            Dictionary with best game and its score breakdown
        """
        # Fetch games
        logger.info(f"Fetching NBA games from the last {days} days...")
        games = self.nba_client.get_games_last_n_days(days)

        if not games:
            logger.warning("No completed games found")
            return None

        logger.info(f"Found {len(games)} completed games")

        # Score all games
        scored_games = []
        fav_team = favorite_team or self.favorite_team

        for game in games:
            score_result = self.scorer.score_game(
                game,
                favorite_team=fav_team,
                top5_teams=self.nba_client.TOP_5_TEAMS
            )

            scored_games.append({
                'game': game,
                'score': score_result['score'],
                'breakdown': score_result['breakdown']
            })

        # Sort by score (descending)
        scored_games.sort(key=lambda x: x['score'], reverse=True)

        return scored_games[0] if scored_games else None

    def get_all_games_ranked(self, days: int = 7, favorite_team: Optional[str] = None) -> List[Dict]:
        """
        Get all games ranked by engagement score.

        Args:
            days: Number of days to look back
            favorite_team: Optional favorite team (overrides config)

        Returns:
            List of games sorted by score (descending)
        """
        # Fetch games
        games = self.nba_client.get_games_last_n_days(days)

        if not games:
            return []

        # Score all games
        scored_games = []
        fav_team = favorite_team or self.favorite_team

        for game in games:
            score_result = self.scorer.score_game(
                game,
                favorite_team=fav_team,
                top5_teams=self.nba_client.TOP_5_TEAMS
            )

            scored_games.append({
                'game': game,
                'score': score_result['score'],
                'breakdown': score_result['breakdown']
            })

        # Sort by score (descending)
        scored_games.sort(key=lambda x: x['score'], reverse=True)

        return scored_games

    def format_game_summary(self, result: Dict) -> str:
        """
        Format a game result as a readable summary.

        Args:
            result: Game result dictionary with score and breakdown

        Returns:
            Formatted string summary
        """
        game = result['game']
        score = result['score']
        breakdown = result['breakdown']

        away = game['away_team']
        home = game['home_team']

        summary = f"""
{'='*60}
🏀 MOST ENGAGING GAME 🏀
{'='*60}

{away['name']} @ {home['name']}
Date: {game['game_date']}

Final Score: {away['abbr']} {away['score']} - {home['score']} {home['abbr']}

{'='*60}
ENGAGEMENT SCORE: {score:.2f}
{'='*60}

Score Breakdown:
  • Lead Changes: {breakdown['lead_changes']['count']} ({breakdown['lead_changes']['points']:.1f} pts)
  • Top 5 Teams: {breakdown['top5_teams']['count']} team(s) ({breakdown['top5_teams']['points']:.1f} pts)
  • Game Closeness: {breakdown['close_game']['margin']} pt margin ({breakdown['close_game']['points']:.1f} pts)
  • Total Points: {breakdown['total_points']['total']} (threshold: {breakdown['total_points']['threshold_met']})
  • Star Players: {breakdown['star_power']['count']} ({breakdown['star_power']['points']:.1f} pts)
  • Favorite Team: {'Yes' if breakdown['favorite_team']['has_favorite'] else 'No'} ({breakdown['favorite_team']['points']:.1f} pts)

{'='*60}
"""
        return summary
