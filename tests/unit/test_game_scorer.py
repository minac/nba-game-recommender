"""Unit tests for GameScorer class."""

from src.core.game_scorer import GameScorer
from tests.fixtures.sample_data import get_sample_game, get_sample_config


class TestGameScorer:
    """Test cases for GameScorer class."""

    def setup_method(self):
        """Set up test fixtures."""
        self.config = get_sample_config()
        self.scorer = GameScorer(self.config)

    def test_initialization_with_default_config(self):
        """Test GameScorer initializes with default values when config is empty."""
        scorer = GameScorer({})
        assert scorer.top5_team_bonus == 50
        assert scorer.close_game_bonus == 100
        assert scorer.min_total_points == 200
        assert scorer.high_score_bonus == 10
        assert scorer.star_power_weight == 20
        assert scorer.favorite_team_bonus == 20
        assert scorer.buzz_bonus == 40

    def test_initialization_with_custom_config(self):
        """Test GameScorer initializes with custom config values."""
        custom_config = {
            "top5_team_bonus": 60,
            "close_game_bonus": 120,
            "min_total_points": 180,
            "high_score_bonus": 15,
            "star_power_weight": 25,
            "favorite_team_bonus": 80,
            "buzz_bonus": 50,
        }
        scorer = GameScorer(custom_config)
        assert scorer.top5_team_bonus == 60
        assert scorer.close_game_bonus == 120
        assert scorer.min_total_points == 180
        assert scorer.high_score_bonus == 15
        assert scorer.star_power_weight == 25
        assert scorer.favorite_team_bonus == 80
        assert scorer.buzz_bonus == 50

    def test_top5_teams_both(self):
        """Test scoring when both teams are top 5."""
        game = get_sample_game(home_abbr="LAL", away_abbr="BOS")
        top5_teams = {"LAL", "BOS", "DEN", "MIL", "PHX"}
        result = self.scorer.score_game(game, top5_teams=top5_teams)

        assert result["breakdown"]["top5_teams"]["count"] == 2
        assert result["breakdown"]["top5_teams"]["points"] == 100  # 2 * 50

    def test_top5_teams_one(self):
        """Test scoring when only one team is top 5."""
        game = get_sample_game(home_abbr="LAL", away_abbr="SAC")
        top5_teams = {"LAL", "BOS", "DEN", "MIL", "PHX"}
        result = self.scorer.score_game(game, top5_teams=top5_teams)

        assert result["breakdown"]["top5_teams"]["count"] == 1
        assert result["breakdown"]["top5_teams"]["points"] == 50

    def test_top5_teams_none(self):
        """Test scoring when neither team is top 5."""
        game = get_sample_game(home_abbr="SAC", away_abbr="POR")
        top5_teams = {"LAL", "BOS", "DEN", "MIL", "PHX"}
        result = self.scorer.score_game(game, top5_teams=top5_teams)

        assert result["breakdown"]["top5_teams"]["count"] == 0
        assert result["breakdown"]["top5_teams"]["points"] == 0

    def test_top5_teams_none_when_set_is_none(self):
        """Test scoring when top5_teams set is None."""
        game = get_sample_game(home_abbr="LAL", away_abbr="BOS")
        result = self.scorer.score_game(game, top5_teams=None)

        assert result["breakdown"]["top5_teams"]["count"] == 0
        assert result["breakdown"]["top5_teams"]["points"] == 0

    def test_close_game_0_to_3_margin(self):
        """Test close game bonus for 0-3 point margin."""
        game = get_sample_game(home_score=100, away_score=98)  # 2 point margin
        result = self.scorer.score_game(game)

        assert result["breakdown"]["close_game"]["margin"] == 2
        assert result["breakdown"]["close_game"]["points"] == 100

    def test_close_game_4_to_5_margin(self):
        """Test close game bonus for 4-5 point margin."""
        game = get_sample_game(home_score=100, away_score=95)  # 5 point margin
        result = self.scorer.score_game(game)

        assert result["breakdown"]["close_game"]["margin"] == 5
        assert result["breakdown"]["close_game"]["points"] == 80

    def test_close_game_6_to_10_margin(self):
        """Test close game bonus for 6-10 point margin."""
        game = get_sample_game(home_score=100, away_score=92)  # 8 point margin
        result = self.scorer.score_game(game)

        assert result["breakdown"]["close_game"]["margin"] == 8
        assert result["breakdown"]["close_game"]["points"] == 50

    def test_close_game_11_to_15_margin(self):
        """Test close game bonus for 11-15 point margin."""
        game = get_sample_game(home_score=100, away_score=87)  # 13 point margin
        result = self.scorer.score_game(game)

        assert result["breakdown"]["close_game"]["margin"] == 13
        assert result["breakdown"]["close_game"]["points"] == 25

    def test_close_game_over_15_margin(self):
        """Test no close game bonus for over 15 point margin."""
        game = get_sample_game(home_score=120, away_score=95)  # 25 point margin
        result = self.scorer.score_game(game)

        assert result["breakdown"]["close_game"]["margin"] == 25
        assert result["breakdown"]["close_game"]["points"] == 0

    def test_total_points_above_threshold(self):
        """Test that games above point threshold get bonus points."""
        game = get_sample_game(home_score=110, away_score=108)  # 218 total
        result = self.scorer.score_game(game)

        assert result["breakdown"]["total_points"]["total"] == 218
        assert result["breakdown"]["total_points"]["threshold_met"] is True
        assert result["breakdown"]["total_points"]["points"] == 10

    def test_total_points_below_threshold(self):
        """Test that games below point threshold get no bonus points."""
        game = get_sample_game(
            home_score=85, away_score=90, star_players=2
        )  # 175 total, below 200
        result = self.scorer.score_game(game)

        assert result["breakdown"]["total_points"]["total"] == 175
        assert result["breakdown"]["total_points"]["threshold_met"] is False
        assert result["breakdown"]["total_points"]["points"] == 0
        # Score includes close game bonus (80) + star power (40) + no high score bonus (0)
        assert result["score"] == 120.0

    def test_total_points_exactly_at_threshold(self):
        """Test games exactly at threshold get bonus points."""
        game = get_sample_game(home_score=100, away_score=100)  # Exactly 200
        result = self.scorer.score_game(game)

        assert result["breakdown"]["total_points"]["total"] == 200
        assert result["breakdown"]["total_points"]["threshold_met"] is True
        assert result["breakdown"]["total_points"]["points"] == 10

    def test_star_power_scoring(self):
        """Test that star players are scored correctly."""
        game = get_sample_game(star_players=5)
        result = self.scorer.score_game(game)

        assert result["breakdown"]["star_power"]["count"] == 5
        assert result["breakdown"]["star_power"]["points"] == 100  # 5 * 20

    def test_star_power_zero(self):
        """Test scoring when no star players participated."""
        game = get_sample_game(star_players=0)
        result = self.scorer.score_game(game)

        assert result["breakdown"]["star_power"]["count"] == 0
        assert result["breakdown"]["star_power"]["points"] == 0

    def test_favorite_team_home(self):
        """Test favorite team bonus when favorite is home team."""
        game = get_sample_game(home_abbr="LAL", away_abbr="BOS")
        result = self.scorer.score_game(game, favorite_team="LAL")

        assert result["breakdown"]["favorite_team"]["has_favorite"] is True
        assert result["breakdown"]["favorite_team"]["points"] == 20

    def test_favorite_team_away(self):
        """Test favorite team bonus when favorite is away team."""
        game = get_sample_game(home_abbr="LAL", away_abbr="BOS")
        result = self.scorer.score_game(game, favorite_team="BOS")

        assert result["breakdown"]["favorite_team"]["has_favorite"] is True
        assert result["breakdown"]["favorite_team"]["points"] == 20

    def test_favorite_team_not_playing(self):
        """Test no favorite team bonus when favorite is not playing."""
        game = get_sample_game(home_abbr="LAL", away_abbr="BOS")
        result = self.scorer.score_game(game, favorite_team="GSW")

        assert result["breakdown"]["favorite_team"]["has_favorite"] is False
        assert result["breakdown"]["favorite_team"]["points"] == 0

    def test_favorite_team_none(self):
        """Test no favorite team bonus when favorite_team is None."""
        game = get_sample_game(home_abbr="LAL", away_abbr="BOS")
        result = self.scorer.score_game(game, favorite_team=None)

        assert result["breakdown"]["favorite_team"]["has_favorite"] is False
        assert result["breakdown"]["favorite_team"]["points"] == 0

    def test_comprehensive_high_score_game(self):
        """Test scoring for a highly engaging game with all positive factors."""
        game = get_sample_game(
            home_abbr="LAL",
            away_abbr="BOS",
            home_score=118,
            away_score=115,  # 3 point margin (close)
            star_players=6,
        )
        top5_teams = {"LAL", "BOS", "DEN", "MIL", "PHX"}
        result = self.scorer.score_game(
            game, favorite_team="LAL", top5_teams=top5_teams
        )

        # Verify individual components
        assert result["breakdown"]["top5_teams"]["points"] == 100  # 2 * 50
        assert result["breakdown"]["close_game"]["points"] == 100  # 3pt margin
        assert result["breakdown"]["total_points"]["points"] == 10  # 233 total >= 200
        assert result["breakdown"]["star_power"]["points"] == 120  # 6 * 20
        assert result["breakdown"]["favorite_team"]["points"] == 20

        # Total should be sum of all components
        expected_score = 100 + 100 + 10 + 120 + 20
        assert result["score"] == expected_score

    def test_comprehensive_low_score_game(self):
        """Test scoring for a less engaging game."""
        game = get_sample_game(
            home_abbr="SAC",
            away_abbr="POR",
            home_score=95,
            away_score=75,  # 20 point margin (blowout)
            star_players=0,
        )
        result = self.scorer.score_game(game)

        # Low score due to blowout, no stars, no top5 teams, below point threshold
        assert result["breakdown"]["top5_teams"]["points"] == 0
        assert result["breakdown"]["close_game"]["points"] == 0  # 20pt margin
        assert result["breakdown"]["total_points"]["points"] == 0  # 170 total < 200
        assert result["breakdown"]["star_power"]["points"] == 0
        assert result["breakdown"]["favorite_team"]["points"] == 0

        # Score is 0 (no bonuses applied)
        assert result["score"] == 0

    def test_score_rounded_to_two_decimals(self):
        """Test that final score is rounded to 2 decimal places."""
        game = get_sample_game(star_players=3)
        result = self.scorer.score_game(game)

        # Verify it's a number rounded to 2 decimal places
        assert isinstance(result["score"], (int, float))
        assert result["score"] == round(result["score"], 2)

    def test_score_structure(self):
        """Test that score_game returns correct structure."""
        game = get_sample_game()
        result = self.scorer.score_game(game)

        # Verify top-level structure
        assert "score" in result
        assert "breakdown" in result

        # Verify breakdown structure
        assert "top5_teams" in result["breakdown"]
        assert "close_game" in result["breakdown"]
        assert "total_points" in result["breakdown"]
        assert "star_power" in result["breakdown"]
        assert "favorite_team" in result["breakdown"]
        assert "buzz" in result["breakdown"]

    def test_high_score_bonus_calculation(self):
        """Test that the high score bonus is calculated correctly."""
        # Create a game with exactly 200 points (threshold)
        game = get_sample_game(
            home_score=100,
            away_score=100,  # Exactly 200 total points, 0 margin = 100 close bonus
            star_players=0,
        )
        result = self.scorer.score_game(game)

        # 100 (close) + 10 (high score bonus) = 110
        assert result["score"] == 110.0
        assert result["breakdown"]["total_points"]["points"] == 10

    def test_buzz_score_included_in_total(self):
        """Test that buzz score is added to total."""
        game = get_sample_game(buzz_score=30, buzz_reasoning="Buzzer beater finish")
        result = self.scorer.score_game(game)

        assert result["breakdown"]["buzz"]["points"] == 30
        assert result["breakdown"]["buzz"]["reasoning"] == "Buzzer beater finish"
        # Score should include buzz
        assert result["score"] >= 30

    def test_buzz_score_zero_when_absent(self):
        """Test that buzz score defaults to 0 when not present."""
        game = get_sample_game()
        # Remove buzz fields to simulate old data
        del game["buzz_score"]
        del game["buzz_reasoning"]
        result = self.scorer.score_game(game)

        assert result["breakdown"]["buzz"]["points"] == 0
        assert result["breakdown"]["buzz"]["reasoning"] == ""

    def test_margin_calculation_uses_absolute_value(self):
        """Test that margin is calculated correctly regardless of which team won."""
        game1 = get_sample_game(home_score=110, away_score=105)
        game2 = get_sample_game(home_score=105, away_score=110)

        result1 = self.scorer.score_game(game1)
        result2 = self.scorer.score_game(game2)

        # Both should have the same margin
        assert result1["breakdown"]["close_game"]["margin"] == 5
        assert result2["breakdown"]["close_game"]["margin"] == 5
        assert (
            result1["breakdown"]["close_game"]["points"]
            == result2["breakdown"]["close_game"]["points"]
        )
