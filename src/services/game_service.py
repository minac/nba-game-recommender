"""
Shared service layer for game recommendation logic.
This service provides a unified interface for all clients (CLI, Web, API).
"""

from typing import Dict, List, Optional, Tuple, Any
from src.core.recommender import GameRecommender
from src.utils.logger import get_logger
from src.api.nba_api_client import NBAAPIError

logger = get_logger(__name__)


class ValidationError(Exception):
    """Custom exception for validation errors."""

    pass


class GameService:
    """
    Unified service for game recommendations.
    Provides parameter validation, error handling, and consistent response formatting.
    """

    def __init__(self, recommender: Optional[GameRecommender] = None):
        """
        Initialize the game service.

        Args:
            recommender: GameRecommender instance. If None, creates a new one.
        """
        self.recommender = recommender or GameRecommender()

    @staticmethod
    def validate_days(days: Any) -> int:
        """
        Validate and normalize the days parameter.

        Args:
            days: Days value to validate (can be int, str, or None)

        Returns:
            Validated days as integer

        Raises:
            ValidationError: If days is invalid
        """
        try:
            days_int = int(days) if days is not None else 7
        except (ValueError, TypeError):
            raise ValidationError(f"Invalid days value: {days}. Must be an integer.")

        if days_int < 1 or days_int > 30:
            raise ValidationError("Days must be between 1 and 30")

        return days_int

    @staticmethod
    def validate_team(team: Any) -> Optional[str]:
        """
        Validate and normalize the team parameter.

        Args:
            team: Team abbreviation to validate

        Returns:
            Normalized team abbreviation (uppercase) or None
        """
        if team is None or team == "":
            return None

        team_str = str(team).strip().upper()
        return team_str if team_str else None

    def get_best_game(self, days: Any = 7, favorite_team: Any = None) -> Dict[str, Any]:
        """
        Get the best game recommendation.

        Args:
            days: Number of days to look back (1-30)
            favorite_team: Optional favorite team abbreviation

        Returns:
            Dictionary with success status and game data or error

        Example:
            {
                'success': True,
                'data': {
                    'game': {...},
                    'score': 285.5,
                    'breakdown': {...}
                }
            }
        """
        try:
            # Validate parameters
            validated_days = self.validate_days(days)
            validated_team = self.validate_team(favorite_team)

            logger.info(
                f"Getting best game for days={validated_days}, team={validated_team}"
            )

            # Get recommendation
            result = self.recommender.get_best_game(
                days=validated_days, favorite_team=validated_team
            )

            if not result:
                return {
                    "success": False,
                    "error": "No games found",
                    "error_code": "NO_GAMES",
                }

            return {"success": True, "data": result}

        except ValidationError as e:
            logger.warning(f"Validation error in get_best_game: {e}")
            return {"success": False, "error": str(e), "error_code": "VALIDATION_ERROR"}
        except NBAAPIError as e:
            logger.error(f"NBA API error in get_best_game: {e}")
            return {"success": False, "error": str(e), "error_code": "NBA_API_ERROR"}
        except Exception as e:
            logger.error(f"Error in get_best_game: {e}", exc_info=True)
            return {
                "success": False,
                "error": f"Internal error: {str(e)}",
                "error_code": "INTERNAL_ERROR",
            }

    def get_all_games_ranked(
        self, days: Any = 7, favorite_team: Any = None
    ) -> Dict[str, Any]:
        """
        Get all games ranked by engagement score.

        Args:
            days: Number of days to look back (1-30)
            favorite_team: Optional favorite team abbreviation

        Returns:
            Dictionary with success status and list of games or error

        Example:
            {
                'success': True,
                'count': 15,
                'data': [
                    {'game': {...}, 'score': 285.5, 'breakdown': {...}},
                    ...
                ]
            }
        """
        try:
            # Validate parameters
            validated_days = self.validate_days(days)
            validated_team = self.validate_team(favorite_team)

            logger.info(
                f"Getting all ranked games for days={validated_days}, team={validated_team}"
            )

            # Get recommendations
            results = self.recommender.get_all_games_ranked(
                days=validated_days, favorite_team=validated_team
            )

            # Empty list is a valid result (just means no games to rank)
            return {"success": True, "count": len(results), "data": results}

        except ValidationError as e:
            logger.warning(f"Validation error in get_all_games_ranked: {e}")
            return {"success": False, "error": str(e), "error_code": "VALIDATION_ERROR"}
        except NBAAPIError as e:
            logger.error(f"NBA API error in get_all_games_ranked: {e}")
            return {"success": False, "error": str(e), "error_code": "NBA_API_ERROR"}
        except Exception as e:
            logger.error(f"Error in get_all_games_ranked: {e}", exc_info=True)
            return {
                "success": False,
                "error": f"Internal error: {str(e)}",
                "error_code": "INTERNAL_ERROR",
            }

    def format_game_summary(
        self, game_result: Dict[str, Any], explain: bool = False
    ) -> str:
        """
        Format a game result as a human-readable summary.

        Args:
            game_result: Game result dictionary from get_best_game
            explain: Whether to include detailed scoring explanation

        Returns:
            Formatted string summary
        """
        return self.recommender.format_game_summary(game_result, explain=explain)

    def format_score_explanation(self, game_result: Dict[str, Any]) -> str:
        """
        Format the score breakdown as a human-readable explanation.

        Args:
            game_result: Game result dictionary with breakdown

        Returns:
            Formatted string explanation
        """
        return self.recommender.format_score_explanation(game_result)

    def get_metadata(self) -> Dict[str, Any]:
        """
        Get metadata about star players and top teams.

        Returns:
            Dictionary with star players and top teams
        """
        try:
            return {
                "success": True,
                "data": {
                    "star_players": sorted(
                        list(self.recommender.nba_client.STAR_PLAYERS)
                    ),
                    "top_teams": sorted(list(self.recommender.nba_client.TOP_5_TEAMS)),
                },
            }
        except Exception as e:
            logger.error(f"Error getting metadata: {e}", exc_info=True)
            return {
                "success": False,
                "error": f"Internal error: {str(e)}",
                "error_code": "INTERNAL_ERROR",
            }

    @property
    def star_players(self) -> set:
        """Get the set of current star players."""
        return self.recommender.nba_client.STAR_PLAYERS

    @property
    def top_teams(self) -> set:
        """Get the set of current top 5 teams."""
        return self.recommender.nba_client.TOP_5_TEAMS

    @property
    def star_power_weight(self) -> int:
        """Get the star power weight from scorer config."""
        return self.recommender.scorer.star_power_weight

    @property
    def top5_team_bonus(self) -> int:
        """Get the top 5 team bonus from scorer config."""
        return self.recommender.scorer.top5_team_bonus

    @property
    def config(self) -> dict:
        """Get the recommender configuration."""
        return self.recommender.config
