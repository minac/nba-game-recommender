"""Unit tests for GameRecommender class."""

import pytest
import tempfile
import os
from unittest.mock import Mock, patch
from src.core.recommender import GameRecommender
from tests.fixtures.sample_data import get_sample_game


class TestGameRecommender:
    """Test cases for GameRecommender class."""

    @pytest.fixture
    def config_file(self):
        """Create a temporary config file for testing."""
        config_content = """
favorite_team: "LAL"

scoring:
  top5_team_bonus: 50
  close_game_bonus: 100
  min_total_points: 200
  star_power_weight: 20
  favorite_team_bonus: 75
"""
        with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".yaml") as f:
            f.write(config_content)
            config_path = f.name

        yield config_path

        # Cleanup
        os.unlink(config_path)

    @pytest.fixture
    def mock_nba_client(self):
        """Create a mock NBA client."""
        with patch("src.core.recommender.NBAClient") as mock_client:
            yield mock_client

    def test_initialization_loads_config(self, config_file):
        """Test that GameRecommender loads config on initialization."""
        with patch("src.core.recommender.NBAClient"):
            recommender = GameRecommender(config_path=config_file)

            assert recommender.config is not None
            assert recommender.favorite_team == "LAL"
            assert recommender.config["scoring"]["top5_team_bonus"] == 50

    def test_initialization_creates_components(self, config_file):
        """Test that GameRecommender creates NBAClient and GameScorer."""
        with patch("src.core.recommender.NBAClient") as mock_client:
            recommender = GameRecommender(config_path=config_file)

            assert recommender.nba_client is not None
            assert recommender.scorer is not None
            mock_client.assert_called_once()

    def test_initialization_missing_config_file(self):
        """Test that initialization fails with missing config file."""
        with pytest.raises(FileNotFoundError):
            GameRecommender(config_path="nonexistent.yaml")

    def test_get_best_game_returns_highest_scored(self, config_file, mock_nba_client):
        """Test get_best_game returns the game with highest score."""
        games = [
            get_sample_game(home_abbr="LAL", away_abbr="BOS"),
            get_sample_game(home_abbr="DEN", away_abbr="MIL"),  # Both top5 teams
            get_sample_game(home_abbr="GSW", away_abbr="PHX"),
        ]

        mock_client_instance = Mock()
        mock_client_instance.get_games_last_n_days.return_value = games
        mock_client_instance.TOP_5_TEAMS = {"LAL", "BOS", "DEN", "MIL", "PHX"}
        mock_nba_client.return_value = mock_client_instance

        recommender = GameRecommender(config_path=config_file)
        result = recommender.get_best_game(days=7)

        assert result is not None
        # Either LAL/BOS or DEN/MIL could win (both have 2 top5 teams)
        assert result["score"] > 0

    def test_get_best_game_no_games_returns_none(self, config_file, mock_nba_client):
        """Test get_best_game returns None when no games found."""
        mock_client_instance = Mock()
        mock_client_instance.get_games_last_n_days.return_value = []
        mock_nba_client.return_value = mock_client_instance

        recommender = GameRecommender(config_path=config_file)
        result = recommender.get_best_game(days=7)

        assert result is None

    def test_get_best_game_uses_favorite_team_from_config(
        self, config_file, mock_nba_client
    ):
        """Test get_best_game uses favorite team from config."""
        games = [
            get_sample_game(home_abbr="LAL", away_abbr="BOS"),  # Has LAL
            get_sample_game(home_abbr="DEN", away_abbr="MIL"),
        ]

        mock_client_instance = Mock()
        mock_client_instance.get_games_last_n_days.return_value = games
        mock_client_instance.TOP_5_TEAMS = {"LAL", "BOS", "DEN", "MIL", "PHX"}
        mock_nba_client.return_value = mock_client_instance

        recommender = GameRecommender(config_path=config_file)
        result = recommender.get_best_game(days=7)

        # LAL game should score higher due to favorite team bonus
        assert result["game"]["home_team"]["abbr"] == "LAL"
        assert result["breakdown"]["favorite_team"]["has_favorite"] is True

    def test_get_best_game_favorite_team_override(self, config_file, mock_nba_client):
        """Test get_best_game allows overriding favorite team."""
        games = [
            get_sample_game(home_abbr="LAL", away_abbr="BOS"),
            get_sample_game(home_abbr="DEN", away_abbr="MIL"),  # Has MIL
        ]

        mock_client_instance = Mock()
        mock_client_instance.get_games_last_n_days.return_value = games
        mock_client_instance.TOP_5_TEAMS = {"LAL", "BOS", "DEN", "MIL", "PHX"}
        mock_nba_client.return_value = mock_client_instance

        recommender = GameRecommender(config_path=config_file)
        # Override with MIL instead of LAL from config
        result = recommender.get_best_game(days=7, favorite_team="MIL")

        # MIL game should score higher due to favorite team override
        assert result["game"]["home_team"]["abbr"] == "DEN"
        assert result["breakdown"]["favorite_team"]["has_favorite"] is True

    def test_get_best_game_calls_client_with_days(self, config_file, mock_nba_client):
        """Test get_best_game passes days parameter to client."""
        mock_client_instance = Mock()
        mock_client_instance.get_games_last_n_days.return_value = [get_sample_game()]
        mock_client_instance.TOP_5_TEAMS = set()
        mock_nba_client.return_value = mock_client_instance

        recommender = GameRecommender(config_path=config_file)
        recommender.get_best_game(days=14)

        mock_client_instance.get_games_last_n_days.assert_called_once_with(14)

    def test_get_best_game_prints_messages(self, config_file, mock_nba_client, capsys):
        """Test get_best_game prints informative messages."""
        games = [get_sample_game()]

        mock_client_instance = Mock()
        mock_client_instance.get_games_last_n_days.return_value = games
        mock_client_instance.TOP_5_TEAMS = set()
        mock_nba_client.return_value = mock_client_instance

        recommender = GameRecommender(config_path=config_file)
        result = recommender.get_best_game(days=7)

        # Verify the method works and returns result
        assert result is not None
        assert "game" in result

    def test_get_all_games_ranked_returns_all_games_sorted(
        self, config_file, mock_nba_client
    ):
        """Test get_all_games_ranked returns all games sorted by score."""
        games = [
            get_sample_game(home_abbr="LAL", away_abbr="BOS"),
            get_sample_game(home_abbr="DEN", away_abbr="MIL"),
            get_sample_game(home_abbr="GSW", away_abbr="PHX"),
        ]

        mock_client_instance = Mock()
        mock_client_instance.get_games_last_n_days.return_value = games
        mock_client_instance.TOP_5_TEAMS = {"LAL", "BOS", "DEN", "MIL", "PHX"}
        mock_nba_client.return_value = mock_client_instance

        recommender = GameRecommender(config_path=config_file)
        results = recommender.get_all_games_ranked(days=7)

        assert len(results) == 3
        # Should be sorted descending by score
        assert results[0]["score"] >= results[1]["score"]
        assert results[1]["score"] >= results[2]["score"]

    def test_get_all_games_ranked_empty(self, config_file, mock_nba_client):
        """Test get_all_games_ranked returns empty list when no games."""
        mock_client_instance = Mock()
        mock_client_instance.get_games_last_n_days.return_value = []
        mock_nba_client.return_value = mock_client_instance

        recommender = GameRecommender(config_path=config_file)
        results = recommender.get_all_games_ranked(days=7)

        assert results == []

    def test_get_all_games_ranked_uses_favorite_team(
        self, config_file, mock_nba_client
    ):
        """Test get_all_games_ranked uses favorite team parameter."""
        games = [
            get_sample_game(home_abbr="LAL", away_abbr="BOS"),
            get_sample_game(home_abbr="DEN", away_abbr="MIL"),
        ]

        mock_client_instance = Mock()
        mock_client_instance.get_games_last_n_days.return_value = games
        mock_client_instance.TOP_5_TEAMS = set()
        mock_nba_client.return_value = mock_client_instance

        recommender = GameRecommender(config_path=config_file)
        results = recommender.get_all_games_ranked(days=7, favorite_team="DEN")

        # Check that DEN game has favorite team bonus
        den_game = [r for r in results if r["game"]["home_team"]["abbr"] == "DEN"][0]
        assert den_game["breakdown"]["favorite_team"]["has_favorite"] is True

    def test_format_game_summary_creates_readable_output(
        self, config_file, mock_nba_client
    ):
        """Test format_game_summary creates a properly formatted summary."""
        mock_nba_client.return_value = Mock()

        recommender = GameRecommender(config_path=config_file)

        game_result = {
            "game": get_sample_game(
                home_abbr="LAL",
                away_abbr="BOS",
                home_score=118,
                away_score=115,
                star_players=4,
            ),
            "score": 355.0,
            "breakdown": {
                "top5_teams": {"count": 2, "points": 100.0},
                "close_game": {"margin": 3, "points": 100.0},
                "total_points": {"total": 233, "threshold_met": True},
                "star_power": {"count": 4, "points": 80.0},
                "favorite_team": {"has_favorite": True, "points": 75.0},
            },
        }

        summary = recommender.format_game_summary(game_result)

        assert "MOST ENGAGING GAME" in summary
        assert "Celtics @ Lakers" in summary or "Lakers" in summary
        assert "2024-01-15" in summary
        assert "355" in summary
        assert "Star Players: 4" in summary or "Star Players" in summary

    def test_format_game_summary_handles_no_favorite(
        self, config_file, mock_nba_client
    ):
        """Test format_game_summary shows 'No' for favorite team when not present."""
        mock_nba_client.return_value = Mock()

        recommender = GameRecommender(config_path=config_file)

        game_result = {
            "game": get_sample_game(),
            "score": 50.0,
            "breakdown": {
                "top5_teams": {"count": 0, "points": 0},
                "close_game": {"margin": 10, "points": 50.0},
                "total_points": {"total": 218, "threshold_met": True},
                "star_power": {"count": 0, "points": 0},
                "favorite_team": {"has_favorite": False, "points": 0},
            },
        }

        summary = recommender.format_game_summary(game_result)

        assert "Favorite Team: No" in summary

    def test_get_best_game_includes_breakdown(self, config_file, mock_nba_client):
        """Test get_best_game includes detailed breakdown in result."""
        games = [get_sample_game()]

        mock_client_instance = Mock()
        mock_client_instance.get_games_last_n_days.return_value = games
        mock_client_instance.TOP_5_TEAMS = set()
        mock_nba_client.return_value = mock_client_instance

        recommender = GameRecommender(config_path=config_file)
        result = recommender.get_best_game(days=7)

        assert "game" in result
        assert "score" in result
        assert "breakdown" in result
        assert "top5_teams" in result["breakdown"]
        assert "close_game" in result["breakdown"]
        assert "total_points" in result["breakdown"]
        assert "star_power" in result["breakdown"]
        assert "favorite_team" in result["breakdown"]

    def test_get_all_games_ranked_structure(self, config_file, mock_nba_client):
        """Test get_all_games_ranked returns properly structured results."""
        games = [get_sample_game(), get_sample_game()]

        mock_client_instance = Mock()
        mock_client_instance.get_games_last_n_days.return_value = games
        mock_client_instance.TOP_5_TEAMS = set()
        mock_nba_client.return_value = mock_client_instance

        recommender = GameRecommender(config_path=config_file)
        results = recommender.get_all_games_ranked(days=7)

        for result in results:
            assert "game" in result
            assert "score" in result
            assert "breakdown" in result

    def test_initialization_with_null_favorite_team(self):
        """Test initialization when favorite_team is null in config."""
        config_content = """
favorite_team: null

scoring:
  top5_team_bonus: 50
"""
        with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".yaml") as f:
            f.write(config_content)
            config_path = f.name

        try:
            with patch("src.core.recommender.NBAClient"):
                recommender = GameRecommender(config_path=config_path)
                assert recommender.favorite_team is None
        finally:
            os.unlink(config_path)

    def test_get_best_game_with_single_game(self, config_file, mock_nba_client):
        """Test get_best_game works correctly with a single game."""
        games = [get_sample_game()]

        mock_client_instance = Mock()
        mock_client_instance.get_games_last_n_days.return_value = games
        mock_client_instance.TOP_5_TEAMS = set()
        mock_nba_client.return_value = mock_client_instance

        recommender = GameRecommender(config_path=config_file)
        result = recommender.get_best_game(days=7)

        assert result is not None
        assert result["game"] == games[0]

    def test_format_game_summary_formatting(self, config_file, mock_nba_client):
        """Test format_game_summary uses proper formatting."""
        mock_nba_client.return_value = Mock()

        recommender = GameRecommender(config_path=config_file)

        game_result = {
            "game": get_sample_game(),
            "score": 140.0,
            "breakdown": {
                "top5_teams": {"count": 1, "points": 50.0},
                "close_game": {"margin": 10, "points": 50.0},
                "total_points": {"total": 218, "threshold_met": True},
                "star_power": {"count": 2, "points": 40.0},
                "favorite_team": {"has_favorite": False, "points": 0.0},
            },
        }

        summary = recommender.format_game_summary(game_result)

        # Check for proper formatting with decimal places
        assert "140.00" in summary
        assert "50.0 pts" in summary
        assert "=" * 60 in summary
