"""NBA Game Recommender Engine."""
from typing import List, Dict, Optional
from src.api.nba_client import NBAClient
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

        # Use NBA Stats API as data source
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

    def format_score_explanation(self, result: Dict) -> str:
        """
        Format a compact score explanation for a game.

        Args:
            result: Game result dictionary with score and breakdown

        Returns:
            Formatted string explanation (compact for --all mode)
        """
        breakdown = result['breakdown']
        config = self.scorer.__dict__

        parts = []
        parts.append(f"Lead Changes: {breakdown['lead_changes']['count']} × {config['lead_changes_weight']} = {breakdown['lead_changes']['points']:.1f}")
        parts.append(f"Top5 Teams: {breakdown['top5_teams']['count']} × {config['top5_team_bonus']} = {breakdown['top5_teams']['points']:.1f}")
        parts.append(f"Close Game: {breakdown['close_game']['margin']}pt margin = {breakdown['close_game']['points']:.1f}")
        parts.append(f"Stars: {breakdown['star_power']['count']} × {config['star_power_weight']} = {breakdown['star_power']['points']:.1f}")

        if breakdown['favorite_team']['has_favorite']:
            parts.append(f"Favorite Team: +{breakdown['favorite_team']['points']:.1f}")

        if breakdown['total_points'].get('penalty_applied'):
            parts.append(f"Low Score Penalty: {breakdown['total_points']['total']} pts (90% penalty)")

        return "\n   ".join(parts) + "\n"

    def format_game_summary(self, result: Dict, explain: bool = False) -> str:
        """
        Format a game result as a readable summary.

        Args:
            result: Game result dictionary with score and breakdown
            explain: If True, show detailed scoring explanation

        Returns:
            Formatted string summary
        """
        game = result['game']
        score = result['score']
        breakdown = result['breakdown']

        away = game['away_team']
        home = game['home_team']

        if explain:
            # Detailed explanation mode
            config = self.scorer.__dict__
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

DETAILED SCORING EXPLANATION:
{'='*60}

1. LEAD CHANGES (Weight: {config['lead_changes_weight']} pts per change)
   Count: {breakdown['lead_changes']['count']}
   Calculation: {breakdown['lead_changes']['count']} × {config['lead_changes_weight']} = {breakdown['lead_changes']['points']:.1f} points

2. TOP 5 TEAMS (Bonus: {config['top5_team_bonus']} pts per team)
   Teams in game: {breakdown['top5_teams']['count']}
   Calculation: {breakdown['top5_teams']['count']} × {config['top5_team_bonus']} = {breakdown['top5_teams']['points']:.1f} points

3. GAME CLOSENESS (Max Bonus: {config['close_game_bonus']} pts)
   Final Margin: {breakdown['close_game']['margin']} points
   Scoring Tiers:
     • 0-3 pts: {config['close_game_bonus']} points (100%)
     • 4-5 pts: {config['close_game_bonus'] * 0.8:.1f} points (80%)
     • 6-10 pts: {config['close_game_bonus'] * 0.5:.1f} points (50%)
     • 11-15 pts: {config['close_game_bonus'] * 0.25:.1f} points (25%)
     • 16+ pts: 0 points
   Points Awarded: {breakdown['close_game']['points']:.1f} points

4. TOTAL POINTS (Minimum Threshold: {config['min_total_points']})
   Total Points: {breakdown['total_points']['total']}
   Threshold Met: {breakdown['total_points']['threshold_met']}
   {'   Penalty: 90% reduction applied to final score' if breakdown['total_points'].get('penalty_applied') else '   No penalty applied'}

5. STAR POWER (Weight: {config['star_power_weight']} pts per star)
   Star Players: {breakdown['star_power']['count']}
   Calculation: {breakdown['star_power']['count']} × {config['star_power_weight']} = {breakdown['star_power']['points']:.1f} points

6. FAVORITE TEAM (Bonus: {config['favorite_team_bonus']} pts)
   Has Favorite Team: {'Yes' if breakdown['favorite_team']['has_favorite'] else 'No'}
   Points Awarded: {breakdown['favorite_team']['points']:.1f} points

{'='*60}
FINAL CALCULATION:
{'='*60}

Base Score: {breakdown['lead_changes']['points']:.1f} + {breakdown['top5_teams']['points']:.1f} + {breakdown['close_game']['points']:.1f} + {breakdown['star_power']['points']:.1f} + {breakdown['favorite_team']['points']:.1f}
{f"After Penalty: × 0.1 (low total points)" if breakdown['total_points'].get('penalty_applied') else ''}
FINAL SCORE: {score:.2f}

{'='*60}
"""
        else:
            # Standard summary mode
            summary = f"""
{'='*60}
🏀 MOST ENGAGING GAME 🏀
{'='*60}

{away['name']} @ {home['name']}
Date: {game['game_date']}

{'='*60}
ENGAGEMENT SCORE: {score:.2f}
{'='*60}

Score Breakdown:
  • Lead Changes: {breakdown['lead_changes']['count']} ({breakdown['lead_changes']['points']:.1f} pts)
  • Top 5 Teams: {breakdown['top5_teams']['count']} team(s) ({breakdown['top5_teams']['points']:.1f} pts)
  • Close Game: ({breakdown['close_game']['points']:.1f} pts)
  • Total Points: {breakdown['total_points']['total']} (threshold: {breakdown['total_points']['threshold_met']})
  • Star Players: {breakdown['star_power']['count']} ({breakdown['star_power']['points']:.1f} pts)
  • Favorite Team: {'Yes' if breakdown['favorite_team']['has_favorite'] else 'No'} ({breakdown['favorite_team']['points']:.1f} pts)

{'='*60}
"""
        return summary
