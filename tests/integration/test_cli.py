"""Integration tests for CLI interface."""

import pytest
import sys
from unittest.mock import Mock, patch
from pathlib import Path
from io import StringIO

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.interfaces.cli import main
from tests.fixtures.sample_data import get_sample_game


class TestCLI:
    """Integration tests for CLI interface."""

    @pytest.fixture
    def mock_recommender(self):
        """Mock the GameRecommender class."""
        with patch("src.interfaces.cli.GameRecommender") as mock:
            yield mock

    def test_cli_default_arguments(self, mock_recommender, capsys):
        """Test CLI with default arguments."""
        mock_instance = Mock()
        mock_game_result = {
            "game": get_sample_game(),
            "score": 305.50,
            "breakdown": {
                "top5_teams": {"count": 2, "points": 100.0},
                "close_game": {"margin": 3, "points": 100.0},
                "total_points": {"total": 233, "threshold_met": True, "points": 10.0},
                "star_power": {"count": 4, "points": 80.0},
                "favorite_team": {"has_favorite": True, "points": 75.0},
            },
        }
        mock_instance.get_best_game.return_value = mock_game_result
        mock_instance.format_game_summary.return_value = "Test Summary"
        mock_recommender.return_value = mock_instance

        with patch("sys.argv", ["cli.py"]):
            main()

        # Should call with default days=7 and team=None
        mock_instance.get_best_game.assert_called_once_with(days=7, favorite_team=None)

    def test_cli_with_days_argument(self, mock_recommender):
        """Test CLI with custom days argument."""
        mock_instance = Mock()
        mock_instance.get_best_game.return_value = {
            "game": get_sample_game(),
            "score": 100.0,
            "breakdown": {},
        }
        mock_instance.format_game_summary.return_value = "Test Summary"
        mock_recommender.return_value = mock_instance

        with patch("sys.argv", ["cli.py", "--days", "14"]):
            main()

        mock_instance.get_best_game.assert_called_once_with(days=14, favorite_team=None)

    def test_cli_with_team_argument(self, mock_recommender):
        """Test CLI with favorite team argument."""
        mock_instance = Mock()
        mock_instance.get_best_game.return_value = {
            "game": get_sample_game(),
            "score": 100.0,
            "breakdown": {},
        }
        mock_instance.format_game_summary.return_value = "Test Summary"
        mock_recommender.return_value = mock_instance

        with patch("sys.argv", ["cli.py", "--team", "LAL"]):
            main()

        mock_instance.get_best_game.assert_called_once_with(days=7, favorite_team="LAL")

    def test_cli_with_short_arguments(self, mock_recommender):
        """Test CLI with short argument forms."""
        mock_instance = Mock()
        mock_instance.get_best_game.return_value = {
            "game": get_sample_game(),
            "score": 100.0,
            "breakdown": {},
        }
        mock_instance.format_game_summary.return_value = "Test Summary"
        mock_recommender.return_value = mock_instance

        with patch("sys.argv", ["cli.py", "-d", "3", "-t", "BOS"]):
            main()

        mock_instance.get_best_game.assert_called_once_with(days=3, favorite_team="BOS")

    def test_cli_all_games_mode(self, mock_recommender, capsys):
        """Test CLI with --all flag to show all games."""
        mock_instance = Mock()
        mock_games = [
            {
                "game": get_sample_game(
                    home_abbr="LAL", away_abbr="BOS", home_score=110, away_score=108
                ),
                "score": 500.0,
                "breakdown": {
                    "close_game": {"margin": 2, "points": 100.0},
                    "star_power": {"count": 3, "points": 60.0},
                },
            },
            {
                "game": get_sample_game(
                    home_abbr="DEN", away_abbr="MIL", home_score=115, away_score=112
                ),
                "score": 400.0,
                "breakdown": {
                    "close_game": {"margin": 3, "points": 100.0},
                    "star_power": {"count": 2, "points": 40.0},
                },
            },
        ]
        mock_instance.get_all_games_ranked.return_value = mock_games
        mock_recommender.return_value = mock_instance

        with patch("sys.argv", ["cli.py", "--all"]):
            main()

        mock_instance.get_all_games_ranked.assert_called_once()
        captured = capsys.readouterr()
        assert "ALL GAMES RANKED" in captured.out
        assert "BOS 108 @ 110 LAL" in captured.out
        assert "MIL 112 @ 115 DEN" in captured.out

    def test_cli_all_games_with_days(self, mock_recommender):
        """Test CLI --all flag with custom days."""
        mock_instance = Mock()
        mock_instance.get_all_games_ranked.return_value = []
        mock_recommender.return_value = mock_instance

        with patch("sys.argv", ["cli.py", "--all", "--days", "5"]):
            main()

        mock_instance.get_all_games_ranked.assert_called_once_with(
            days=5, favorite_team=None
        )

    def test_cli_all_games_with_team(self, mock_recommender):
        """Test CLI --all flag with favorite team."""
        mock_instance = Mock()
        mock_instance.get_all_games_ranked.return_value = []
        mock_recommender.return_value = mock_instance

        with patch("sys.argv", ["cli.py", "-a", "-t", "GSW"]):
            main()

        mock_instance.get_all_games_ranked.assert_called_once_with(
            days=7, favorite_team="GSW"
        )

    def test_cli_no_games_found(self, mock_recommender, capsys):
        """Test CLI output when no games are found."""
        mock_instance = Mock()
        mock_instance.get_best_game.return_value = None
        mock_recommender.return_value = mock_instance

        with patch("sys.argv", ["cli.py"]):
            main()

        captured = capsys.readouterr()
        assert "No completed games found" in captured.out

    def test_cli_all_games_no_games_found(self, mock_recommender, capsys):
        """Test CLI --all mode when no games are found."""
        mock_instance = Mock()
        mock_instance.get_all_games_ranked.return_value = []
        mock_recommender.return_value = mock_instance

        with patch("sys.argv", ["cli.py", "--all"]):
            main()

        captured = capsys.readouterr()
        assert "No completed games found" in captured.out

    def test_cli_custom_config_path(self, mock_recommender):
        """Test CLI with custom config file path."""
        mock_instance = Mock()
        mock_instance.get_best_game.return_value = {
            "game": get_sample_game(),
            "score": 100.0,
            "breakdown": {},
        }
        mock_instance.format_game_summary.return_value = "Test Summary"
        mock_recommender.return_value = mock_instance

        with patch("sys.argv", ["cli.py", "--config", "custom_config.yaml"]):
            main()

        mock_recommender.assert_called_once_with(config_path="custom_config.yaml")

    def test_cli_config_file_not_found(self, mock_recommender):
        """Test CLI exits gracefully when config file not found."""
        mock_recommender.side_effect = FileNotFoundError("Config not found")

        with patch("sys.argv", ["cli.py", "--config", "missing.yaml"]):
            with pytest.raises(SystemExit) as exc_info:
                main()

            assert exc_info.value.code == 1

    def test_cli_handles_general_exception(self, mock_recommender):
        """Test CLI handles general exceptions gracefully."""
        mock_recommender.side_effect = Exception("Unexpected error")

        with patch("sys.argv", ["cli.py"]):
            with pytest.raises(SystemExit) as exc_info:
                main()

            assert exc_info.value.code == 1

    def test_cli_prints_summary(self, mock_recommender, capsys):
        """Test CLI prints the formatted game summary."""
        mock_instance = Mock()
        mock_instance.get_best_game.return_value = {
            "game": get_sample_game(),
            "score": 425.50,
            "breakdown": {},
        }
        summary = """
============================================================
🏀 MOST ENGAGING GAME 🏀
============================================================

Celtics @ Lakers
Date: 2024-01-15

Final Score: BOS 108 - 110 LAL
"""
        mock_instance.format_game_summary.return_value = summary
        mock_recommender.return_value = mock_instance

        with patch("sys.argv", ["cli.py"]):
            main()

        captured = capsys.readouterr()
        assert "MOST ENGAGING GAME" in captured.out
        assert "Celtics @ Lakers" in captured.out

    def test_cli_all_games_displays_game_info(self, mock_recommender, capsys):
        """Test CLI --all mode displays game information correctly."""
        mock_instance = Mock()
        mock_games = [
            {
                "game": get_sample_game(
                    home_abbr="LAL",
                    away_abbr="BOS",
                    home_score=110,
                    away_score=108,
                    game_date="2024-01-15",
                ),
                "score": 500.0,
                "breakdown": {
                    "close_game": {"margin": 2, "points": 100.0},
                    "star_power": {"count": 4, "points": 80.0},
                },
            }
        ]
        mock_instance.get_all_games_ranked.return_value = mock_games
        mock_recommender.return_value = mock_instance

        with patch("sys.argv", ["cli.py", "--all"]):
            main()

        captured = capsys.readouterr()
        assert "1. BOS 108 @ 110 LAL" in captured.out
        assert "Date: 2024-01-15" in captured.out
        assert "Score: 500.00" in captured.out
        assert "Margin: 2 pts" in captured.out
        assert "Stars: 4" in captured.out

    def test_cli_argument_parsing_help(self):
        """Test CLI --help displays help message."""
        with patch("sys.argv", ["cli.py", "--help"]):
            with pytest.raises(SystemExit) as exc_info:
                main()

            # --help exits with code 0
            assert exc_info.value.code == 0

    def test_cli_days_argument_type_validation(self, mock_recommender):
        """Test CLI validates days argument is an integer."""
        with patch("sys.argv", ["cli.py", "--days", "invalid"]):
            with pytest.raises(SystemExit):
                main()

    def test_cli_all_games_multiple_games_numbered(self, mock_recommender, capsys):
        """Test CLI --all mode numbers games correctly."""
        mock_instance = Mock()
        mock_games = [
            {
                "game": get_sample_game(home_abbr="LAL", away_abbr="BOS"),
                "score": 500.0,
                "breakdown": {
                    "close_game": {"margin": 2, "points": 100.0},
                    "star_power": {"count": 3, "points": 60.0},
                },
            },
            {
                "game": get_sample_game(home_abbr="DEN", away_abbr="MIL"),
                "score": 400.0,
                "breakdown": {
                    "close_game": {"margin": 3, "points": 100.0},
                    "star_power": {"count": 2, "points": 40.0},
                },
            },
            {
                "game": get_sample_game(home_abbr="GSW", away_abbr="PHX"),
                "score": 300.0,
                "breakdown": {
                    "close_game": {"margin": 5, "points": 80.0},
                    "star_power": {"count": 1, "points": 20.0},
                },
            },
        ]
        mock_instance.get_all_games_ranked.return_value = mock_games
        mock_recommender.return_value = mock_instance

        with patch("sys.argv", ["cli.py", "--all"]):
            main()

        captured = capsys.readouterr()
        assert "1. BOS" in captured.out
        assert "2. MIL" in captured.out
        assert "3. PHX" in captured.out

    def test_cli_fetching_message(self, mock_recommender, capsys):
        """Test CLI displays fetching message in --all mode."""
        mock_instance = Mock()
        mock_instance.get_all_games_ranked.return_value = []
        mock_recommender.return_value = mock_instance

        with patch("sys.argv", ["cli.py", "--all", "--days", "5"]):
            main()

        captured = capsys.readouterr()
        assert "Fetching NBA games from the last 5 days" in captured.out
