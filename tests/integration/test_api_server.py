"""Integration tests for API server."""

import pytest
from unittest.mock import Mock, patch
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.interfaces.api_server import app
from tests.fixtures.sample_data import get_sample_game


class TestAPIServer:
    """Integration tests for Flask API server."""

    @pytest.fixture
    def client(self):
        """Create a test client for the Flask app."""
        app.config["TESTING"] = True
        with app.test_client() as client:
            yield client

    @pytest.fixture
    def mock_recommender(self):
        """Mock the recommender instance."""
        with patch("src.interfaces.api_server.recommender") as mock:
            # Also patch the game_service's recommender to use the same mock
            with patch("src.interfaces.api_server.game_service.recommender", mock):
                yield mock

    def test_health_endpoint(self, client):
        """Test health check endpoint returns ok status."""
        response = client.get("/api/health")

        assert response.status_code == 200
        data = response.get_json()
        assert data["status"] == "ok"

    def test_get_best_game_success(self, client, mock_recommender):
        """Test best-game endpoint returns game data successfully."""
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

        mock_recommender.get_best_game.return_value = mock_game_result

        response = client.get("/api/best-game?days=7")

        assert response.status_code == 200
        data = response.get_json()
        assert data["success"] is True
        assert "data" in data
        assert data["data"]["score"] == 305.50

    def test_get_best_game_with_team_parameter(self, client, mock_recommender):
        """Test best-game endpoint accepts team parameter."""
        mock_game_result = {"game": get_sample_game(), "score": 300.0, "breakdown": {}}

        mock_recommender.get_best_game.return_value = mock_game_result

        response = client.get("/api/best-game?days=7&team=LAL")

        assert response.status_code == 200
        mock_recommender.get_best_game.assert_called_once_with(
            days=7, favorite_team="LAL"
        )

    def test_get_best_game_default_days(self, client, mock_recommender):
        """Test best-game endpoint uses default days value."""
        mock_game_result = {"game": get_sample_game(), "score": 300.0, "breakdown": {}}

        mock_recommender.get_best_game.return_value = mock_game_result

        response = client.get("/api/best-game")

        assert response.status_code == 200
        mock_recommender.get_best_game.assert_called_once_with(
            days=7, favorite_team=None
        )

    def test_get_best_game_no_games_found(self, client, mock_recommender):
        """Test best-game endpoint returns 404 when no games found."""
        mock_recommender.get_best_game.return_value = None

        response = client.get("/api/best-game?days=7")

        assert response.status_code == 404
        data = response.get_json()
        assert "error" in data
        assert data["error"] == "No games found"

    def test_get_best_game_invalid_days_too_low(self, client, mock_recommender):
        """Test best-game endpoint validates days parameter (too low)."""
        response = client.get("/api/best-game?days=0")

        assert response.status_code == 400
        data = response.get_json()
        assert "error" in data
        assert "between 1 and 30" in data["error"]

    def test_get_best_game_invalid_days_too_high(self, client, mock_recommender):
        """Test best-game endpoint validates days parameter (too high)."""
        response = client.get("/api/best-game?days=31")

        assert response.status_code == 400
        data = response.get_json()
        assert "error" in data
        assert "between 1 and 30" in data["error"]

    def test_get_best_game_handles_exception(self, client, mock_recommender):
        """Test best-game endpoint handles exceptions gracefully."""
        mock_recommender.get_best_game.side_effect = Exception("API Error")

        response = client.get("/api/best-game?days=7")

        assert response.status_code == 500
        data = response.get_json()
        assert "error" in data

    def test_get_all_games_success(self, client, mock_recommender):
        """Test games endpoint returns all games ranked."""
        mock_games = [
            {"game": get_sample_game(star_players=5), "score": 500.0, "breakdown": {}},
            {"game": get_sample_game(star_players=3), "score": 400.0, "breakdown": {}},
            {"game": get_sample_game(star_players=1), "score": 300.0, "breakdown": {}},
        ]

        mock_recommender.get_all_games_ranked.return_value = mock_games

        response = client.get("/api/games?days=7")

        assert response.status_code == 200
        data = response.get_json()
        assert data["success"] is True
        assert data["count"] == 3
        assert len(data["data"]) == 3
        assert data["data"][0]["score"] == 500.0

    def test_get_all_games_empty(self, client, mock_recommender):
        """Test games endpoint returns empty array when no games."""
        mock_recommender.get_all_games_ranked.return_value = []

        response = client.get("/api/games?days=7")

        assert response.status_code == 200
        data = response.get_json()
        assert data["success"] is True
        assert data["count"] == 0
        assert data["data"] == []

    def test_get_all_games_with_team_parameter(self, client, mock_recommender):
        """Test games endpoint accepts team parameter."""
        mock_recommender.get_all_games_ranked.return_value = []

        response = client.get("/api/games?days=5&team=BOS")

        assert response.status_code == 200
        mock_recommender.get_all_games_ranked.assert_called_once_with(
            days=5, favorite_team="BOS"
        )

    def test_get_all_games_default_days(self, client, mock_recommender):
        """Test games endpoint uses default days value."""
        mock_recommender.get_all_games_ranked.return_value = []

        response = client.get("/api/games")

        assert response.status_code == 200
        mock_recommender.get_all_games_ranked.assert_called_once_with(
            days=7, favorite_team=None
        )

    def test_get_all_games_invalid_days_too_low(self, client):
        """Test games endpoint validates days parameter (too low)."""
        response = client.get("/api/games?days=0")

        assert response.status_code == 400
        data = response.get_json()
        assert "error" in data
        assert "between 1 and 30" in data["error"]

    def test_get_all_games_invalid_days_too_high(self, client):
        """Test games endpoint validates days parameter (too high)."""
        response = client.get("/api/games?days=50")

        assert response.status_code == 400
        data = response.get_json()
        assert "error" in data
        assert "between 1 and 30" in data["error"]

    def test_get_all_games_handles_exception(self, client, mock_recommender):
        """Test games endpoint handles exceptions gracefully."""
        mock_recommender.get_all_games_ranked.side_effect = Exception("API Error")

        response = client.get("/api/games?days=7")

        assert response.status_code == 500
        data = response.get_json()
        assert "error" in data

    def test_get_config_success(self, client):
        """Test config endpoint returns configuration."""
        response = client.get("/api/config")

        assert response.status_code == 200
        data = response.get_json()
        assert data["success"] is True
        assert "data" in data
        # Config should have scoring settings
        assert "scoring" in data["data"] or "favorite_team" in data["data"]

    def test_api_endpoints_return_json(self, client, mock_recommender):
        """Test all endpoints return JSON content type."""
        mock_recommender.get_best_game.return_value = {
            "game": get_sample_game(),
            "score": 100.0,
            "breakdown": {},
        }
        mock_recommender.get_all_games_ranked.return_value = []

        endpoints = [
            "/api/health",
            "/api/best-game?days=7",
            "/api/games?days=7",
            "/api/config",
        ]

        for endpoint in endpoints:
            response = client.get(endpoint)
            assert response.content_type == "application/json"

    def test_best_game_query_param_parsing(self, client, mock_recommender):
        """Test best-game endpoint correctly parses query parameters."""
        mock_recommender.get_best_game.return_value = {
            "game": get_sample_game(),
            "score": 100.0,
            "breakdown": {},
        }

        response = client.get("/api/best-game?days=14&team=GSW")

        assert response.status_code == 200
        mock_recommender.get_best_game.assert_called_once_with(
            days=14, favorite_team="GSW"
        )

    def test_games_query_param_parsing(self, client, mock_recommender):
        """Test games endpoint correctly parses query parameters."""
        mock_recommender.get_all_games_ranked.return_value = []

        response = client.get("/api/games?days=3&team=MIL")

        assert response.status_code == 200
        mock_recommender.get_all_games_ranked.assert_called_once_with(
            days=3, favorite_team="MIL"
        )

    def test_invalid_endpoint_returns_404(self, client):
        """Test accessing invalid endpoint returns 404."""
        response = client.get("/api/invalid-endpoint")
        assert response.status_code == 404

    def test_post_method_not_allowed(self, client):
        """Test POST method is not allowed on GET-only endpoints."""
        response = client.post("/api/best-game")
        assert response.status_code == 405  # Method Not Allowed

    def test_days_parameter_as_string_number(self, client, mock_recommender):
        """Test days parameter works when passed as string."""
        mock_recommender.get_best_game.return_value = {
            "game": get_sample_game(),
            "score": 100.0,
            "breakdown": {},
        }

        response = client.get("/api/best-game?days=10")

        assert response.status_code == 200
        mock_recommender.get_best_game.assert_called_once_with(
            days=10, favorite_team=None
        )

    def test_days_parameter_invalid_format(self, client, mock_recommender):
        """Test days parameter with invalid format returns error."""
        response = client.get("/api/best-game?days=invalid")

        assert response.status_code == 400  # Validation error returns 400
        data = response.get_json()
        assert "error" in data
