"""Unit tests for BuzzScorer class."""

import json
from unittest.mock import patch, MagicMock

from src.core.buzz_scorer import BuzzScorer, _get_api_key, MAX_BUZZ_SCORE
from tests.fixtures.sample_data import get_sample_game


class TestGetApiKey:
    """Test API key retrieval."""

    @patch("src.core.buzz_scorer.subprocess.run")
    def test_reads_from_keychain(self, mock_run):
        """Test reading API key from macOS keychain."""
        mock_run.return_value = MagicMock(returncode=0, stdout="sk-ant-test-key\n")
        key = _get_api_key()
        assert key == "sk-ant-test-key"
        mock_run.assert_called_once()

    @patch("src.core.buzz_scorer.subprocess.run")
    @patch.dict("os.environ", {"ANTHROPIC_API_KEY": "sk-ant-env-key"})
    def test_falls_back_to_env_var(self, mock_run):
        """Test falling back to env var when keychain fails."""
        mock_run.return_value = MagicMock(returncode=44, stdout="")
        key = _get_api_key()
        assert key == "sk-ant-env-key"

    @patch("src.core.buzz_scorer.subprocess.run")
    @patch.dict("os.environ", {}, clear=True)
    def test_returns_none_when_no_key(self, mock_run):
        """Test returns None when no key available."""
        mock_run.return_value = MagicMock(returncode=44, stdout="")
        key = _get_api_key()
        assert key is None

    @patch("src.core.buzz_scorer.subprocess.run", side_effect=FileNotFoundError)
    @patch.dict("os.environ", {"ANTHROPIC_API_KEY": "sk-ant-env-key"})
    def test_handles_missing_security_command(self, mock_run):
        """Test handles missing security CLI (non-macOS)."""
        key = _get_api_key()
        assert key == "sk-ant-env-key"


class TestBuzzScorer:
    """Test BuzzScorer class."""

    def test_not_available_without_key(self):
        """Test scorer reports unavailable without API key."""
        scorer = BuzzScorer(api_key=None)
        assert scorer.available is False

    def test_available_with_key(self):
        """Test scorer reports available with API key."""
        scorer = BuzzScorer(api_key="sk-ant-test")
        assert scorer.available is True

    def test_returns_zeros_when_unavailable(self):
        """Test returns zero scores when no API key."""
        scorer = BuzzScorer(api_key=None)
        games = [get_sample_game(game_id="g1"), get_sample_game(game_id="g2")]
        result = scorer.score_games(games)

        assert result["g1"]["score"] == 0
        assert result["g2"]["score"] == 0

    def test_returns_empty_for_empty_games(self):
        """Test returns empty dict for empty game list."""
        scorer = BuzzScorer(api_key="sk-ant-test")
        result = scorer.score_games([])
        assert result == {}

    @patch.object(BuzzScorer, "_call_claude")
    def test_calls_claude_when_available(self, mock_call):
        """Test calls Claude API when key is available."""
        mock_call.return_value = {
            "g1": {"score": 25, "reasoning": "Great game"},
        }
        scorer = BuzzScorer(api_key="sk-ant-test")
        games = [get_sample_game(game_id="g1")]
        result = scorer.score_games(games)

        assert result["g1"]["score"] == 25
        assert result["g1"]["reasoning"] == "Great game"
        mock_call.assert_called_once()

    @patch.object(BuzzScorer, "_call_claude", side_effect=Exception("API error"))
    def test_returns_zeros_on_api_error(self, mock_call):
        """Test returns zero scores when API call fails."""
        scorer = BuzzScorer(api_key="sk-ant-test")
        games = [get_sample_game(game_id="g1")]
        result = scorer.score_games(games)

        assert result["g1"]["score"] == 0

    def test_format_game_list(self):
        """Test game list formatting for prompt."""
        scorer = BuzzScorer(api_key="sk-ant-test")
        games = [get_sample_game(game_id="g1")]
        formatted = scorer._format_game_list(games)
        assert "g1" in formatted
        assert "LAL" in formatted
        assert "BOS" in formatted


class TestParseResponse:
    """Test response parsing."""

    def setup_method(self):
        self.scorer = BuzzScorer(api_key="sk-ant-test")
        self.games = [
            get_sample_game(game_id="g1"),
            get_sample_game(game_id="g2"),
        ]

    def _make_response(self, text):
        """Create a mock response with text content."""
        block = MagicMock()
        block.text = text
        response = MagicMock()
        response.content = [block]
        return response

    def test_parses_valid_json(self):
        """Test parsing valid JSON response."""
        data = {
            "g1": {"score": 30, "reasoning": "Buzzer beater"},
            "g2": {"score": 10, "reasoning": "Regular game"},
        }
        response = self._make_response(json.dumps(data))
        result = self.scorer._parse_response(response, self.games)

        assert result["g1"]["score"] == 30
        assert result["g1"]["reasoning"] == "Buzzer beater"
        assert result["g2"]["score"] == 10

    def test_parses_json_in_code_fence(self):
        """Test parsing JSON wrapped in markdown code fence."""
        data = {
            "g1": {"score": 20, "reasoning": "Good game"},
            "g2": {"score": 5, "reasoning": ""},
        }
        text = f"```json\n{json.dumps(data)}\n```"
        response = self._make_response(text)
        result = self.scorer._parse_response(response, self.games)

        assert result["g1"]["score"] == 20

    def test_clamps_score_to_max(self):
        """Test scores above MAX_BUZZ_SCORE are clamped."""
        data = {
            "g1": {"score": 100, "reasoning": "Over max"},
            "g2": {"score": 20, "reasoning": ""},
        }
        response = self._make_response(json.dumps(data))
        result = self.scorer._parse_response(response, self.games)

        assert result["g1"]["score"] == MAX_BUZZ_SCORE

    def test_clamps_negative_to_zero(self):
        """Test negative scores are clamped to 0."""
        data = {
            "g1": {"score": -5, "reasoning": ""},
            "g2": {"score": 20, "reasoning": ""},
        }
        response = self._make_response(json.dumps(data))
        result = self.scorer._parse_response(response, self.games)

        assert result["g1"]["score"] == 0

    def test_handles_missing_game_ids(self):
        """Test handles games not in response."""
        data = {"g1": {"score": 20, "reasoning": "Decent"}}
        response = self._make_response(json.dumps(data))
        result = self.scorer._parse_response(response, self.games)

        assert result["g1"]["score"] == 20
        assert result["g2"]["score"] == 0  # Default for missing

    def test_handles_invalid_json(self):
        """Test returns zeros for invalid JSON."""
        response = self._make_response("not json at all")
        result = self.scorer._parse_response(response, self.games)

        assert result["g1"]["score"] == 0
        assert result["g2"]["score"] == 0

    def test_handles_empty_response(self):
        """Test returns zeros when response has no text."""
        response = MagicMock()
        response.content = []
        result = self.scorer._parse_response(response, self.games)

        assert result["g1"]["score"] == 0
